#!/usr/bin/env python3
"""
scripts/ghl_social_delete_post.py -- Delete a post from GHL Social Planner.

Usage:
    python scripts/ghl_social_delete_post.py --post-id <id> [--dry-run] [--yes]
      [--location-id X] [--api-key X]

Ref: AC5 (delete post)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml

from publisher.models import Brand, BrandCredentials
from publisher.adapters.ghl import GHLAdapter


def resolve_config(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve location_id and api_key from args > env > brand.yaml."""
    location_id = args.location_id or os.environ.get("GHL_LOCATION_ID", "")
    api_key = args.api_key or os.environ.get("GHL_API_KEY", "")

    if not location_id:
        brand_path = REPO_ROOT / "brands" / "secondring" / "brand.yaml"
        if brand_path.exists():
            data = yaml.safe_load(brand_path.read_text())
            location_id = (data.get("ghl") or {}).get("location_id", "")

    return location_id, api_key


def make_adapter(location_id: str, api_key: str) -> GHLAdapter:
    """Create a GHLAdapter with minimal config for CLI use."""
    brand = Brand(
        brand_name="cli",
        credentials=BrandCredentials(),
        cadence={},
        pillars=[],
        slug="cli",
    )
    adapter = GHLAdapter(brand=brand, state_dir=Path("/tmp/ghl-cli-state"))
    adapter.location_id = location_id
    adapter.api_key = api_key
    return adapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete a GHL social post")
    parser.add_argument("--post-id", required=True, help="GHL post ID to delete")
    parser.add_argument("--dry-run", action="store_true", help="Show post details without deleting")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--location-id", help="GHL location ID")
    parser.add_argument("--api-key", help="GHL API key")
    args = parser.parse_args()

    location_id, api_key = resolve_config(args)

    if not location_id:
        print("Error: No location ID provided", file=sys.stderr)
        return 1
    if not api_key:
        print("Error: No API key provided", file=sys.stderr)
        return 1

    adapter = make_adapter(location_id, api_key)

    # Fetch post details first
    try:
        post_data = adapter.get_post(args.post_id)
    except Exception as e:
        print(f"Error fetching post: {e}", file=sys.stderr)
        return 1

    if post_data is None:
        print(f"Post not found: {args.post_id}", file=sys.stderr)
        return 1

    # Display post info
    print(f"Post ID:      {post_data.get('id', args.post_id)}")
    print(f"Platform:     {post_data.get('platform', '—')}")
    print(f"Status:       {post_data.get('status', '—')}")
    print(f"Scheduled at: {post_data.get('scheduledAt', post_data.get('scheduled_at', '—'))}")
    content = post_data.get("content", "")
    print(f"Content:      {content[:120]}{'...' if len(content) > 120 else ''}")

    if args.dry_run:
        print("\n[DRY RUN] Would delete this post. Use without --dry-run to proceed.")
        return 0

    # Confirmation
    if not args.yes:
        confirm = input("\nDelete this post? [y/N] ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return 0

    try:
        success = adapter.delete(args.post_id)
        if success:
            print(f"\nDeleted: {args.post_id}")
            return 0
        else:
            print("Delete returned unexpected status", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
