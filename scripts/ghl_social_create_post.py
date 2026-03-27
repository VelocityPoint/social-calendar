#!/usr/bin/env python3
"""
scripts/ghl_social_create_post.py -- Create/schedule a single post via GHL Social Planner.

Usage:
    python scripts/ghl_social_create_post.py \\
      --platform linkedin \\
      --author dave \\
      --content "Post text here" \\
      --scheduled-at 2026-04-03T14:00:00-07:00 \\
      [--image-url https://...] \\
      [--dry-run] \\
      [--location-id X] [--api-key X]

Ref: AC3 (text publish), AC4 (image publish)
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

from publisher.models import Brand, BrandCredentials, Post, CreativeAsset
from publisher.adapters.ghl import GHLAdapter


def resolve_config(args: argparse.Namespace) -> tuple[str, str, dict]:
    """Resolve location_id, api_key, and account_map from args > env > brand.yaml."""
    location_id = args.location_id or os.environ.get("GHL_LOCATION_ID", "")
    api_key = args.api_key or os.environ.get("GHL_API_KEY", "")
    account_map = {}

    brand_path = REPO_ROOT / "brands" / "secondring" / "brand.yaml"
    if brand_path.exists():
        data = yaml.safe_load(brand_path.read_text())
        ghl_cfg = data.get("ghl") or {}
        if not location_id:
            location_id = ghl_cfg.get("location_id", "")
        account_map = ghl_cfg.get("accounts", {})

    return location_id, api_key, account_map


def make_adapter(location_id: str, api_key: str, account_map: dict) -> GHLAdapter:
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
    adapter.account_map = account_map
    return adapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/schedule a GHL social post")
    parser.add_argument("--platform", required=True, help="Target platform (linkedin, facebook, instagram, google_business)")
    parser.add_argument("--author", required=True, help="Author key from brand.yaml accounts")
    parser.add_argument("--content", required=True, help="Post text content")
    parser.add_argument("--scheduled-at", required=True, help="ISO 8601 datetime with timezone")
    parser.add_argument("--image-url", help="Optional image URL to attach")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without calling API")
    parser.add_argument("--location-id", help="GHL location ID")
    parser.add_argument("--api-key", help="GHL API key")
    args = parser.parse_args()

    location_id, api_key, account_map = resolve_config(args)

    if not location_id:
        print("Error: No location ID provided", file=sys.stderr)
        return 1
    if not api_key and not args.dry_run:
        print("Error: No API key provided", file=sys.stderr)
        return 1

    # Build Post object
    creative = None
    if args.image_url:
        creative = [CreativeAsset(type="image", url=args.image_url)]

    post = Post(
        id=f"cli-{args.platform}-{args.scheduled_at[:10]}",
        publish_at=args.scheduled_at,
        platforms=[args.platform],
        status="scheduled",
        brand="cli",
        author=args.author,
        creative=creative,
    )

    adapter = make_adapter(location_id, api_key, account_map)

    # Build payload preview for dry-run
    account_ids = []
    try:
        account_ids = adapter._resolve_accounts(args.author, args.platform)
    except Exception as e:
        if args.dry_run:
            account_ids = [f"UNRESOLVED ({e})"]
        else:
            print(f"Error resolving account: {e}", file=sys.stderr)
            return 1

    payload = {
        "accountIds": account_ids,
        "content": args.content,
        "scheduledAt": args.scheduled_at,
        "type": "image" if args.image_url else "text",
    }
    if args.image_url:
        payload["mediaUrls"] = [args.image_url]

    if args.dry_run:
        print("[DRY RUN] Would send to GHL API:")
        print(json.dumps(payload, indent=2))
        return 0

    try:
        ghl_post_id = adapter.publish(post, args.content)
        print(f"Post created: {ghl_post_id}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
