#!/usr/bin/env python3
"""
publisher/publisher.py -- Main publisher orchestrator

Coordinates the full publish lifecycle:
  1. Scan brand calendar for scheduled posts (AC-OQ2)
  2. Check each post: status, publish_at gate (AC5), main branch check (AC12)
  3. Per platform: rate limit check (AC-OQ6), then publish with retry (AC-OQ4)
  4. Write status/post_ids back to frontmatter (AC6)
  5. Commit state updates [skip ci] per Daedalus's design

Usage:
    python publisher/publisher.py --brand secondring
    python publisher/publisher.py --brand all
    python publisher/publisher.py --brand secondring --dry-run
    python publisher/publisher.py --brand secondring --auth-check

Ref: AC3, AC4, AC5, AC6, AC7, AC11, AC12, AC16, AC-OQ2, AC-OQ4, AC-OQ6
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
    parser = argparse.ArgumentParser(description="Social Calendar Publisher")
    parser.add_argument("--brand", default="all", help="Brand slug or 'all'")
    parser.add_argument("--dry-run", action="store_true", help="Dry run — no API calls")
    parser.add_argument("--auth-check", action="store_true", help="Run auth check only (AC2)")
    args = parser.parse_args()

    if args.brand == "all":
        brand_slugs = [d.name for d in BRANDS_DIR.iterdir() if d.is_dir()]
    else:
        brand_slugs = [args.brand]

    if args.auth_check:
        all_ok = True
        for slug in brand_slugs:
            ok = run_auth_check(slug)
            if not ok:
                all_ok = False
        sys.exit(0 if all_ok else 1)

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
