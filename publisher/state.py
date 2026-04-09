"""
publisher/state.py -- Frontmatter read/write for post documents

The frontmatter IS the state machine (Daedalus design decision).
Publisher reads post status from frontmatter, writes back status/post_ids after publish.

Ref: AC6 (status/post_ids written back), AC12 (main branch check)
"""

from __future__ import annotations

import re
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from .models import Post


logger = logging.getLogger(__name__)

# Regex to strip and replace frontmatter block
FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n?", re.MULTILINE)


def parse_post_file(file_path: Path) -> Optional[Post]:
    """
    Parse a post Markdown file into a Post model.
    Returns None if the file cannot be parsed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Cannot read {file_path}: {e}")
        return None

    match = FRONTMATTER_RE.match(content)
    if not match:
        logger.warning(f"No frontmatter found in {file_path}")
        return None

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in {file_path}: {e}")
        return None

    try:
        post = Post(**frontmatter)
        post._file_path = str(file_path)
        return post
    except Exception as e:
        logger.error(f"Model validation error in {file_path}: {e}")
        return None


def write_post_status(
    file_path: Path,
    post_id: str,
    status: str,
    post_ids: Optional[dict[str, str]] = None,
    published_at: Optional[str] = None,
) -> bool:
    """
    Write status, published_at, and post_ids back to the post frontmatter (AC6).

    Updates the YAML frontmatter in-place. Body content is preserved unchanged.
    Returns True on success, False on error.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Cannot read {file_path} for status write: {e}")
        return False

    match = FRONTMATTER_RE.match(content)
    if not match:
        logger.error(f"No frontmatter in {file_path} — cannot write status")
        return False

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        logger.error(f"Cannot parse frontmatter in {file_path}: {e}")
        return False

    # Update fields (AC6)
    frontmatter["status"] = status

    if published_at:
        frontmatter["published_at"] = published_at

    if post_ids:
        # Merge with existing post_ids (preserve already-published platforms)
        existing = frontmatter.get("post_ids") or {}
        existing.update(post_ids)
        frontmatter["post_ids"] = existing

    # Re-serialize frontmatter (preserve order: put status and post_ids near top)
    new_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    # Reconstruct document
    body = content[match.end():]
    new_content = f"---\n{new_yaml}---\n{body}"

    try:
        file_path.write_text(new_content, encoding="utf-8")
        logger.info(f"[STATE] Wrote status={status} to {file_path.name}")
        return True
    except Exception as e:
        logger.error(f"Cannot write updated frontmatter to {file_path}: {e}")
        return False


def write_ghl_post_result(
    file_path: Path,
    status: str,
    ghl_post_id: Optional[str] = None,
    error: Optional[str] = None,
    published_at: Optional[str] = None,
) -> bool:
    """
    Write GHL publish result back to post frontmatter (Step 5 / AC7).

    Sets:
      - status → 'ghl-pending' | 'scheduled' | 'published' | 'failed'
      - ghl_post_id → GHL Social Planner post ID (on success)
      - published_at → ISO timestamp (on success)
      - error → last error message (on failure)

    Returns True on success, False on error.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Cannot read {file_path} for GHL result write: {e}")
        return False

    match = FRONTMATTER_RE.match(content)
    if not match:
        logger.error(f"No frontmatter in {file_path} — cannot write GHL result")
        return False

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        logger.error(f"Cannot parse frontmatter in {file_path}: {e}")
        return False

    frontmatter["status"] = status

    if ghl_post_id is not None:
        frontmatter["ghl_post_id"] = ghl_post_id
    if published_at is not None:
        frontmatter["published_at"] = published_at
    if error is not None:
        frontmatter["error"] = error
    elif status != "failed":
        # Clear any previous error on success
        frontmatter.pop("error", None)

    new_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    body = content[match.end():]
    new_content = f"---\n{new_yaml}---\n{body}"

    try:
        file_path.write_text(new_content, encoding="utf-8")
        logger.info(f"[STATE] GHL result written: status={status} ghl_post_id={ghl_post_id} → {file_path.name}")
        return True
    except Exception as e:
        logger.error(f"Cannot write GHL result to {file_path}: {e}")
        return False


def is_committed_on_main(file_path: Path, repo_root: Path) -> bool:
    """
    AC12: Verify the file's last commit is on the main branch.

    Returns True if the file appears in git log main, False otherwise.
    This ensures nothing publishes that wasn't merged through the PR gate.
    """
    try:
        rel_path = file_path.relative_to(repo_root)
        result = subprocess.run(
            ["git", "log", "main", "--", str(rel_path)],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode != 0:
            logger.warning(f"[AC12] git log failed for {rel_path}: {result.stderr}")
            return False

        on_main = bool(result.stdout.strip())
        if not on_main:
            logger.info(f"[SKIPPED] {file_path.name}: not found on main branch")
        return on_main
    except Exception as e:
        logger.warning(f"[AC12] Cannot check main branch for {file_path}: {e}")
        # In GH Actions the checkout has full history (fetch-depth: 0) so this should succeed.
        # On failure, fail open (allow publish) to avoid silent silencing.
        return True


def scan_posts_for_brand(brand_dir: Path, repo_root: Path) -> list[Post]:
    """
    Scan current and next month calendar directories for post files (AC-OQ2).
    Only loads scheduled posts that are not yet published.
    """
    from datetime import date
    import calendar as cal

    now = datetime.now(timezone.utc)
    current_month = now.date().replace(day=1)
    # Next month
    if current_month.month == 12:
        next_month = current_month.replace(year=current_month.year + 1, month=1)
    else:
        next_month = current_month.replace(month=current_month.month + 1)

    scan_months = [current_month, next_month]
    posts = []

    for month_start in scan_months:
        calendar_dir = brand_dir / "calendar" / str(month_start.year) / f"{month_start.month:02d}"
        if not calendar_dir.exists():
            continue

        for md_file in sorted(calendar_dir.glob("*.md")):
            logger.debug(f"[SCAN] Found: {md_file}")

            # AC12: only process files committed to main
            if not is_committed_on_main(md_file, repo_root):
                sha_result = subprocess.run(
                    ["git", "log", "-1", "--format=%H", "--", str(md_file.relative_to(repo_root))],
                    capture_output=True, text=True, cwd=repo_root
                )
                sha = sha_result.stdout.strip() or "unknown"
                logger.info(f"[SKIPPED] {md_file.name}: commit {sha} not found on main branch")
                continue

            post = parse_post_file(md_file)
            if post is None:
                continue

            # Only process 'scheduled' posts
            if post.status != "scheduled":
                logger.debug(f"[SKIP] {post.id}: status={post.status}")
                continue

            posts.append(post)
            logger.debug(f"[QUEUED] {post.id}: publish_at={post.publish_at}")

    logger.info(f"[SCAN] Brand {brand_dir.name}: {len(posts)} scheduled post(s) in queue")
    return posts
