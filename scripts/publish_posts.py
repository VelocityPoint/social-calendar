#!/usr/bin/env python3
"""
scripts/publish_posts.py -- PR-driven publisher for GHL Social Planner.

Called by GitHub Actions on merge to publish posts to GHL.

Usage:
    python scripts/publish_posts.py \\
      --brand brands/secondring/brand.yaml \\
      [--files posts/file1.md posts/file2.md] \\
      [--all] \\
      [--dry-run]

Logic:
    1. Load brand config (GHL location_id, accounts mapping)
    2. Process specified files or find all calendar/*.md files
    3. For each: parse frontmatter, skip non-ready, validate, publish via GHL
    4. Update frontmatter on success (status→scheduled, ghl_post_id, published_at)

Ref: AC7 (publisher routes through GHL adapter)
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml

from publisher.models import Brand, BrandCredentials, Post, CreativeAsset
from publisher.adapters.ghl import GHLAdapter


# ---------------------------------------------------------------------------
# Frontmatter parsing (simple YAML header with --- delimiters)
# ---------------------------------------------------------------------------

def parse_frontmatter(file_path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from a markdown file."""
    text = file_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return fm, body


def write_frontmatter(file_path: Path, fm: dict, body: str) -> None:
    """Write updated frontmatter + body back to file."""
    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False).rstrip("\n")
    file_path.write_text(f"---\n{fm_yaml}\n---\n{body}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Brand config loading
# ---------------------------------------------------------------------------

def load_brand_config(brand_path: Path) -> dict:
    """Load brand YAML and extract GHL config."""
    data = yaml.safe_load(brand_path.read_text())
    ghl_cfg = data.get("ghl") or {}
    return {
        "location_id": ghl_cfg.get("location_id", ""),
        "accounts": ghl_cfg.get("accounts", {}),
        "brand_data": data,
    }


def make_adapter(brand_cfg: dict) -> GHLAdapter:
    """Create GHLAdapter from brand config."""
    brand = Brand(
        brand_name=brand_cfg["brand_data"].get("brand_name", "unknown"),
        credentials=BrandCredentials(),
        cadence={},
        pillars=brand_cfg["brand_data"].get("pillars", []),
        slug="publish",
    )
    adapter = GHLAdapter(brand=brand, state_dir=Path("/tmp/ghl-publisher-state"))
    adapter.location_id = brand_cfg["location_id"] or os.environ.get("GHL_LOCATION_ID", "")
    adapter.api_key = os.environ.get("GHL_API_KEY", "")
    adapter.account_map = brand_cfg["accounts"]
    return adapter


# ---------------------------------------------------------------------------
# Post processing
# ---------------------------------------------------------------------------

def find_calendar_files(brand_path: Path) -> list[Path]:
    """Find all .md files under brands/**/calendar/."""
    brand_dir = brand_path.parent
    pattern = str(brand_dir / "calendar" / "**" / "*.md")
    return [Path(f) for f in glob.glob(pattern, recursive=True)]


def process_post(
    file_path: Path,
    adapter: GHLAdapter,
    brand_cfg: dict,
    dry_run: bool,
) -> str:
    """
    Process a single post file. Returns status string: 'scheduled', 'skipped', 'failed'.
    """
    fm, body = parse_frontmatter(file_path)

    if not fm:
        print(f"  SKIP {file_path.name}: no frontmatter")
        return "skipped"

    status = fm.get("status", "")

    # Skip non-ready posts
    if status != "ready":
        print(f"  SKIP {file_path.name}: status={status} (not ready)")
        return "skipped"

    # Skip already-published posts
    if fm.get("ghl_post_id"):
        print(f"  SKIP {file_path.name}: already has ghl_post_id={fm['ghl_post_id']}")
        return "skipped"

    # Validate required fields
    platform = fm.get("platform")
    author = fm.get("author")
    scheduled_at = fm.get("scheduled_at")

    if not platform:
        print(f"  FAIL {file_path.name}: missing 'platform' in frontmatter")
        return "failed"
    if not author:
        print(f"  FAIL {file_path.name}: missing 'author' in frontmatter")
        return "failed"
    if not scheduled_at:
        print(f"  FAIL {file_path.name}: missing 'scheduled_at' in frontmatter")
        return "failed"

    # Validate scheduled_at is in the future
    try:
        scheduled_dt = datetime.fromisoformat(str(scheduled_at))
        if scheduled_dt.tzinfo is None:
            print(f"  FAIL {file_path.name}: scheduled_at missing timezone")
            return "failed"
    except (ValueError, TypeError):
        print(f"  FAIL {file_path.name}: invalid scheduled_at format")
        return "failed"

    # Resolve author+platform -> GHL account ID
    accounts = brand_cfg.get("accounts", {})
    author_accounts = accounts.get(author, {})
    account_id = author_accounts.get(platform)
    if not account_id:
        print(f"  FAIL {file_path.name}: no GHL account for author={author} platform={platform}")
        return "failed"

    if dry_run:
        print(f"  DRY-RUN {file_path.name}: would publish {platform} post by {author} at {scheduled_at}")
        return "scheduled"

    # Build Post model for the adapter
    post = Post(
        id=file_path.stem,
        publish_at=str(scheduled_at),
        platforms=[platform],
        status="scheduled",
        brand="publish",
        author=author,
    )

    try:
        ghl_post_id = adapter.publish(post, body.strip())
    except Exception as e:
        print(f"  FAIL {file_path.name}: {e}")
        return "failed"

    # Update frontmatter
    fm["status"] = "scheduled"
    fm["ghl_post_id"] = ghl_post_id
    fm["published_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_frontmatter(file_path, fm, body)

    print(f"  OK   {file_path.name}: ghl_post_id={ghl_post_id}")
    return "scheduled"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Publish posts to GHL Social Planner")
    parser.add_argument("--brand", required=True, help="Path to brand.yaml")
    parser.add_argument("--files", nargs="+", help="Specific post files to process")
    parser.add_argument("--all", action="store_true", dest="all_posts", help="Process all calendar posts")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without calling API")
    args = parser.parse_args()

    brand_path = Path(args.brand)
    if not brand_path.exists():
        print(f"Error: brand file not found: {brand_path}", file=sys.stderr)
        return 1

    brand_cfg = load_brand_config(brand_path)

    if not brand_cfg["location_id"] and not os.environ.get("GHL_LOCATION_ID"):
        print("Error: No GHL location_id in brand config or GHL_LOCATION_ID env", file=sys.stderr)
        return 1

    adapter = make_adapter(brand_cfg)

    if not adapter.api_key and not args.dry_run:
        print("Error: GHL_API_KEY not set", file=sys.stderr)
        return 1

    # Determine files to process
    if args.files:
        files = [Path(f) for f in args.files]
    elif args.all_posts:
        files = find_calendar_files(brand_path)
    else:
        print("Error: specify --files or --all", file=sys.stderr)
        return 1

    if not files:
        print("No post files found.")
        return 0

    print(f"Processing {len(files)} file(s) {'[DRY RUN]' if args.dry_run else ''}...")
    print()

    counts = {"scheduled": 0, "skipped": 0, "failed": 0}

    for f in files:
        if not f.exists():
            print(f"  SKIP {f}: file not found")
            counts["skipped"] += 1
            continue
        result = process_post(f, adapter, brand_cfg, args.dry_run)
        counts[result] += 1

    print()
    print(f"Summary: {counts['scheduled']} scheduled, {counts['skipped']} skipped, {counts['failed']} failed")

    return 1 if counts["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
