#!/usr/bin/env python3
"""
scripts/ghl_social_list_posts.py -- List posts from GHL Social Planner.

Usage:
    python scripts/ghl_social_list_posts.py [--status scheduled|published|failed|all] [--limit 20]
      [--location-id X] [--api-key X]

Ref: AC4 (list posts)
"""

from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description="List posts from GHL Social Planner")
    parser.add_argument("--status", choices=["scheduled", "published", "failed", "all"], default="all",
                        help="Filter by post status (default: all)")
    parser.add_argument("--limit", type=int, default=20, help="Max posts to return (default: 20)")
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

    filters: dict = {"limit": args.limit}
    if args.status != "all":
        filters["status"] = args.status

    try:
        posts = adapter.list_posts(filters=filters)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not posts:
        print("No posts found.")
        return 0

    # Print table
    header = f"{'POST ID':<25} {'PLATFORM':<12} {'STATUS':<12} {'SCHEDULED AT':<28} {'CONTENT'}"
    print(header)
    print("-" * 120)
    for p in posts:
        post_id = str(p.get("id", "—"))[:24]
        platform = p.get("platform", "—")
        status = p.get("status", "—")
        scheduled = p.get("scheduledAt", p.get("scheduled_at", "—"))
        content = p.get("content", "")[:60]
        print(f"{post_id:<25} {platform:<12} {status:<12} {scheduled:<28} {content}")

    print(f"\nShowing {len(posts)} post(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
