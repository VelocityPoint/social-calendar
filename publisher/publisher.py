#!/usr/bin/env python3
"""
publisher/publisher.py -- Main publisher orchestrator

Coordinates the full publish lifecycle:
  1. Scan brand calendar for scheduled posts (AC-OQ2)
  2. Check each post: status, publish_at gate (AC5), main branch check (AC12)
  3. Per platform: rate limit check (AC-OQ6), then publish with retry (AC-OQ4)
  4. Write status/post_ids back to frontmatter (AC6)
  5. Commit state updates [skip ci] per Daedalus's design

Usage (original cron mode):
    python -m publisher.publisher --brand secondring
    python -m publisher.publisher --brand all
    python -m publisher.publisher --brand secondring --dry-run
    python -m publisher.publisher --brand secondring --auth-check

Usage (GHL merge-trigger mode — Step 5):
    python -m publisher.publisher --mode ghl --brand secondring
    python -m publisher.publisher --mode ghl --brand secondring --files "brands/secondring/calendar/2026/04/2026-04-01-linkedin-never-miss.md"
    python -m publisher.publisher --mode ghl --brand secondring --dry-run

GHL mode differences from cron mode:
  - Processes only files listed in --files (changed in the merge commit)
  - If --files is not given, detects changed files via `git diff HEAD~1 HEAD`
  - Only publishes posts with status: ready (not scheduled)
  - One file = one platform (single GHLAdapter call per file)
  - On success: writes status=scheduled (or published if scheduled_at is in past),
    ghl_post_id, published_at back to frontmatter
  - On failure: writes status=failed, error field
  - Uses GHLAdapter exclusively (no per-platform adapter registry lookup)

Ref: AC3, AC4, AC5, AC6, AC7, AC11, AC12, AC16, AC-OQ2, AC-OQ4, AC-OQ6, AC7 (GHL)
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
BRANDS_DIR = REPO_ROOT / "brands"

PLATFORM_SECTION_HEADERS = {
    "linkedin": "LinkedIn Version",
    "facebook": "Facebook Version",
    "x": "X Version",
    "gbp": "Google Business Profile Version",
    "instagram": "Instagram Version",
}


def extract_copy_section(body: str, platform: str) -> Optional[str]:
    """Extract platform copy from multi-section document (AC11, AC-OQ3)."""
    header = PLATFORM_SECTION_HEADERS.get(platform)
    if not header:
        return None

    pattern = re.compile(
        r"^# " + re.escape(header) + r"\n([\s\S]*?)(?=^# |\Z)",
        re.MULTILINE
    )
    match = pattern.search(body)
    if match:
        return match.group(1).strip()
    return None


def get_document_body(file_path: Path) -> str:
    """Extract body (non-frontmatter) from post document."""
    content = file_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:].strip()
    return content


def get_changed_files_from_git(repo_root: Path) -> list[Path]:
    """
    Detect post files changed in the most recent commit via git diff.
    Used by GHL mode when --files is not provided.
    Returns list of Path objects (only .md files matching brands/**/calendar/**/*.md).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", "brands/**/calendar/**/*.md"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=True,
        )
        paths = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line:
                p = repo_root / line
                if p.exists():
                    paths.append(p)
        logger.info(f"[GHL] Detected {len(paths)} changed post file(s) via git diff")
        return paths
    except subprocess.CalledProcessError as e:
        logger.warning(f"[GHL] git diff failed: {e.stderr} — falling back to empty file list")
        return []


def run_ghl_publisher(
    brand_slug: str,
    files: Optional[list[Path]] = None,
    dry_run: bool = False,
) -> dict:
    """
    GHL merge-trigger publisher mode (Step 5 / AC7).

    Processes only files changed in the merge commit with status: ready.
    Each file = one platform. Calls GHLAdapter.publish(), writes back:
      - status: scheduled (scheduled_at in future) or published (in past)
      - ghl_post_id
      - published_at (if immediate)
      - error + status: failed (on exhausted retries)

    Args:
        brand_slug: Brand directory name (e.g. "secondring")
        files: List of changed post file paths. If None, detect via git diff.
        dry_run: If True, print what would be published without calling GHL API.

    Returns:
        stats dict: {evaluated, published, skipped, failed}
    """
    from .models import Brand
    from .state import parse_post_file, write_ghl_post_result
    from .retry import publish_with_retry, PermanentError
    from .adapters.ghl import GHLAdapter

    stats = {"evaluated": 0, "published": 0, "skipped": 0, "failed": 0}

    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        logger.error(f"[GHL] Brand directory not found: {brand_dir}")
        return stats

    brand_yaml_path = brand_dir / "brand.yaml"
    if not brand_yaml_path.exists():
        logger.error(f"[GHL] brand.yaml not found: {brand_yaml_path}")
        return stats

    brand = Brand.from_yaml(brand_yaml_path, slug=brand_slug)

    # Validate GHL config is present
    if not brand.ghl:
        logger.error(
            f"[GHL] No 'ghl:' block in {brand_yaml_path}. "
            "Add location_id and accounts mapping (see Step 4 brand config)."
        )
        return stats

    if not brand.ghl.location_id and not os.environ.get("GHL_LOCATION_ID"):
        logger.error("[GHL] GHL_LOCATION_ID not set in env or brand.yaml ghl.location_id")
        return stats

    state_dir = brand_dir / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

    adapter = GHLAdapter(brand=brand, state_dir=state_dir)

    # Resolve which files to process
    if files is None:
        files = get_changed_files_from_git(REPO_ROOT)
        if not files:
            logger.info("[GHL] No changed post files detected — nothing to publish")
            return stats

    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY")

    for file_path in files:
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"[GHL] File not found, skipping: {file_path}")
            stats["skipped"] += 1
            continue

        post = parse_post_file(file_path)
        if post is None:
            logger.warning(f"[GHL] Could not parse: {file_path.name}")
            stats["skipped"] += 1
            continue

        stats["evaluated"] += 1
        logger.info(f"--- GHL Processing: {post.id} (status={post.status}) ---")

        # Only publish posts with status: ready
        if post.status != "ready":
            logger.info(f"[SKIP] {post.id}: status={post.status} (only 'ready' posts are published)")
            stats["skipped"] += 1
            continue

        # Extract post body (copy_text)
        body = get_document_body(file_path)

        # GHL mode: one file = one platform
        # Use single platform from frontmatter (post.platforms[0])
        if not post.platforms:
            logger.error(f"[GHL] {post.id}: no platforms defined in frontmatter")
            write_ghl_post_result(file_path, "failed", error="No platforms defined in frontmatter")
            stats["failed"] += 1
            continue

        platform = post.platforms[0]

        # Extract copy: try platform-specific section first, fall back to full body
        copy_text = extract_copy_section(body, platform) or body
        if not copy_text:
            logger.error(f"[GHL] {post.id}: empty copy text for platform={platform}")
            write_ghl_post_result(file_path, "failed", error=f"Empty copy text for platform={platform}")
            stats["failed"] += 1
            continue

        # Determine if post is immediate or future-scheduled
        now_utc = datetime.now(timezone.utc)
        try:
            publish_at_dt = post.get_publish_at_utc()
        except Exception as e:
            logger.error(f"[GHL] {post.id}: cannot parse publish_at: {e}")
            write_ghl_post_result(file_path, "failed", error=f"Cannot parse publish_at: {e}")
            stats["failed"] += 1
            continue

        is_immediate = publish_at_dt <= now_utc

        if dry_run:
            logger.info(
                f"[DRY RUN] Would GHL-publish: {post.id}\n"
                f"  platform={platform}, author={post.author}\n"
                f"  scheduled_at={post.publish_at} ({'immediate' if is_immediate else 'future'})\n"
                f"  copy_preview={copy_text[:120].replace(chr(10), ' ')}..."
            )
            stats["published"] += 1
            continue

        # Publish with retry (3x, 10s/30s/90s backoff)
        def publish_fn():
            return adapter.publish(post, copy_text)

        ghl_post_id = publish_with_retry(
            publish_fn=publish_fn,
            post_id=post.id,
            platform=platform,
            github_token=github_token,
            github_repo=github_repo,
            post_file_path=str(file_path),
            publish_at=post.publish_at,
        )

        if ghl_post_id:
            # Success: write back scheduled or published status
            new_status = "published" if is_immediate else "scheduled"
            published_at_str = None
            if is_immediate:
                published_at_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            write_ghl_post_result(
                file_path,
                status=new_status,
                ghl_post_id=ghl_post_id,
                published_at=published_at_str,
            )
            logger.info(f"[GHL] {post.id}: status={new_status}, ghl_post_id={ghl_post_id}")
            stats["published"] += 1
            adapter.increment_rate_limit()
            adapter.save_rate_limit_state()
        else:
            # Failure: publish_with_retry returns None only after exhausting all retries
            # The last error is logged by retry.py; we write failed status here
            write_ghl_post_result(
                file_path,
                status="failed",
                error=f"All retries exhausted — see GitHub issue for details",
            )
            logger.error(f"[GHL] {post.id}: publish failed after all retries")
            stats["failed"] += 1

    return stats


def run_publisher(brand_slug: str, dry_run: bool = False) -> dict:
    """
    Run publisher for a single brand.
    Returns stats dict: {evaluated, published, deferred, skipped, failed}.
    """
    from .models import Brand, Post
    from .state import scan_posts_for_brand, write_post_status
    from .retry import publish_with_retry
    from .adapters import ADAPTER_REGISTRY

    stats = {"evaluated": 0, "published": 0, "deferred": 0, "skipped": 0, "failed": 0}

    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        logger.error(f"Brand directory not found: {brand_dir}")
        return stats

    brand_yaml_path = brand_dir / "brand.yaml"
    if not brand_yaml_path.exists():
        logger.error(f"brand.yaml not found: {brand_yaml_path}")
        return stats

    logger.info(f"[BRAND] Using brand: {brand_slug}")
    brand = Brand.from_yaml(brand_yaml_path, slug=brand_slug)

    state_dir = brand_dir / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

    posts = scan_posts_for_brand(brand_dir, REPO_ROOT)
    stats["evaluated"] = len(posts)

    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY")

    for post in posts:
        file_path = Path(post._file_path)
        logger.info(f"--- Processing: {post.id} (publish_at={post.publish_at}) ---")

        # AC5: Scheduling gate — skip if publish_at > now
        if not post.is_ready_to_publish():
            logger.info(f"[SKIP] {post.id}: publish_at not yet reached")
            stats["skipped"] += 1
            continue

        body = get_document_body(file_path)
        post_results: dict[str, str] = {}
        any_deferred = False
        any_failed = False

        for platform in post.platforms:
            # Skip if already published to this platform (idempotency)
            if post.is_published_to(platform):
                logger.info(f"[SKIP] {post.id} on {platform}: already published (post_ids entry exists)")
                continue

            # Extract platform copy (AC11, AC-OQ3)
            copy_text = extract_copy_section(body, platform)
            if copy_text is None:
                logger.error(f"[SKIP] {post.id} on {platform}: missing copy section '# {PLATFORM_SECTION_HEADERS.get(platform)}' — skipping platform")
                any_failed = True
                continue

            # Get adapter
            adapter_cls = ADAPTER_REGISTRY.get(platform)
            if not adapter_cls:
                logger.error(f"[SKIP] {post.id}: no adapter for platform '{platform}'")
                any_failed = True
                continue

            adapter = adapter_cls(brand=brand, state_dir=state_dir)

            # AC-OQ6: Rate limit check before any API call
            if not adapter.check_rate_limit(post.id):
                any_deferred = True
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Would publish {post.id} on {platform}: {copy_text[:80]}...")
                continue

            # Find image path if creative asset exists
            image_path = _find_image_for_platform(post, platform, brand_dir)

            # Publish with retry (AC-OQ4)
            def publish_fn():
                return adapter.publish(post, copy_text, image_path)

            platform_post_id = publish_with_retry(
                publish_fn=publish_fn,
                post_id=post.id,
                platform=platform,
                github_token=github_token,
                github_repo=github_repo,
                post_file_path=str(file_path),
                publish_at=post.publish_at,
            )

            if platform_post_id:
                post_results[platform] = platform_post_id
                adapter.increment_rate_limit()
                adapter.save_rate_limit_state()
            else:
                any_failed = True

        # Update frontmatter status (AC6)
        if post_results and not dry_run:
            # Determine new status
            if any_failed:
                new_status = "failed"
            elif any_deferred:
                new_status = "deferred"
            else:
                # Check if all platforms are now published
                all_published = all(
                    post.is_published_to(p) or p in post_results
                    for p in post.platforms
                )
                new_status = "published" if all_published else "deferred"

            published_at = None
            if new_status == "published":
                published_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            write_post_status(
                file_path,
                post.id,
                status=new_status,
                post_ids=post_results,
                published_at=published_at,
            )

        # Update stats
        if dry_run:
            stats["published"] += 1
        elif post_results:
            if any_failed:
                stats["failed"] += 1
            elif any_deferred:
                stats["deferred"] += 1
            else:
                stats["published"] += 1
        elif any_deferred:
            stats["deferred"] += 1
        elif any_failed:
            stats["failed"] += 1

    return stats


def _find_image_for_platform(post, platform: str, brand_dir: Path) -> Optional[Path]:
    """Find image asset for this platform from post creative list."""
    if not post.creative:
        return None

    for asset in post.creative:
        if asset.type != "image":
            continue
        # Check platform override (AC4)
        if asset.platforms and platform not in asset.platforms:
            continue
        if asset.path:
            image_path = brand_dir / "assets" / asset.path
            if image_path.exists():
                return image_path

    return None


def run_auth_check(brand_slug: str) -> bool:
    """AC2: Run auth check for all platforms in a brand."""
    from .models import Brand
    from .adapters import ADAPTER_REGISTRY
    from pathlib import Path

    brand_dir = BRANDS_DIR / brand_slug
    brand_yaml_path = brand_dir / "brand.yaml"
    if not brand_yaml_path.exists():
        logger.error(f"brand.yaml not found: {brand_yaml_path}")
        return False

    brand = Brand.from_yaml(brand_yaml_path, slug=brand_slug)
    state_dir = brand_dir / ".state"
    all_ok = True

    for platform, kv_name in brand.credentials.__dict__.items():
        if not kv_name:
            continue
        adapter_cls = ADAPTER_REGISTRY.get(platform)
        if not adapter_cls:
            continue
        adapter = adapter_cls(brand=brand, state_dir=state_dir)
        ok = adapter.auth_check()
        if not ok:
            all_ok = False

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Social Calendar Publisher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Cron mode (existing): scan all brands for scheduled posts
  python -m publisher.publisher --brand secondring

  # GHL mode (Step 5): merge-triggered, process changed files with status=ready
  python -m publisher.publisher --mode ghl --brand secondring
  python -m publisher.publisher --mode ghl --brand secondring --files "brands/secondring/calendar/2026/04/foo.md"
  python -m publisher.publisher --mode ghl --brand secondring --dry-run
"""
    )
    parser.add_argument("--brand", default="all", help="Brand slug or 'all'")
    parser.add_argument(
        "--mode",
        choices=["cron", "ghl"],
        default="cron",
        help="Publisher mode: 'cron' (default, cron-scheduled posts) or 'ghl' (merge-triggered, ready posts via GHL Social Planner)",
    )
    parser.add_argument(
        "--files",
        default=None,
        help="(GHL mode) Whitespace/newline-separated list of changed post file paths. If omitted, uses git diff HEAD~1 HEAD.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run — no API calls")
    parser.add_argument("--auth-check", action="store_true", help="Run auth check only (AC2)")
    args = parser.parse_args()

    if args.brand == "all":
        brand_slugs = [d.name for d in BRANDS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
    else:
        brand_slugs = [args.brand]

    if args.auth_check:
        all_ok = True
        for slug in brand_slugs:
            ok = run_auth_check(slug)
            if not ok:
                all_ok = False
        sys.exit(0 if all_ok else 1)

    # --- GHL merge-trigger mode ---
    if args.mode == "ghl":
        # Parse --files arg: whitespace/newline-delimited list of paths
        files: Optional[list[Path]] = None
        if args.files:
            raw = args.files.strip()
            files = [Path(f.strip()) for f in raw.splitlines() + raw.split() if f.strip()]
            # Deduplicate while preserving order
            seen = set()
            deduped = []
            for f in files:
                if str(f) not in seen:
                    seen.add(str(f))
                    deduped.append(f)
            files = deduped
            logger.info(f"[GHL] --files provided: {len(files)} file(s)")

        total_stats = {"evaluated": 0, "published": 0, "skipped": 0, "failed": 0}

        for slug in brand_slugs:
            logger.info(f"=== GHL Brand: {slug} ===")
            stats = run_ghl_publisher(slug, files=files, dry_run=args.dry_run)
            for k, v in stats.items():
                total_stats[k] += v

        logger.info(
            f"[GHL SUMMARY] "
            f"evaluated={total_stats['evaluated']} "
            f"published={total_stats['published']} "
            f"skipped={total_stats['skipped']} "
            f"failed={total_stats['failed']}"
        )

        if total_stats["failed"] > 0:
            sys.exit(1)
        sys.exit(0)

    # --- Cron mode (existing) ---
    total_stats = {"evaluated": 0, "published": 0, "deferred": 0, "skipped": 0, "failed": 0}

    for slug in brand_slugs:
        logger.info(f"=== Brand: {slug} ===")
        stats = run_publisher(slug, dry_run=args.dry_run)
        for k, v in stats.items():
            total_stats[k] += v

    # Log summary (AC-OQ1: Application Insights log format)
    logger.info(
        f"[PUBLISHER SUMMARY] "
        f"evaluated={total_stats['evaluated']} "
        f"published={total_stats['published']} "
        f"deferred={total_stats['deferred']} "
        f"skipped={total_stats['skipped']} "
        f"failed={total_stats['failed']}"
    )

    if total_stats["failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
