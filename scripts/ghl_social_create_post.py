#!/usr/bin/env python3
"""
ghl_social_create_post.py -- Create a GHL Social Planner post

Creates a post to one or more connected social accounts via the
GoHighLevel Social Planner API. All write operations require --dry-run
unless explicitly bypassed.

Usage:
    python scripts/ghl_social_create_post.py \\
        --account-id ACC_ID \\
        --content "Your post text here" \\
        [--schedule-at 2026-04-01T10:00:00-07:00] \\
        [--image-url https://example.com/image.jpg] \\
        --dry-run

Arguments:
    --account-id    GHL social account ID to post to (required)
    --content       Post text content (required)
    --schedule-at   ISO 8601 datetime with timezone offset (optional; defaults to now)
    --image-url     URL of image to include (optional)
    --dry-run       REQUIRED for write ops — previews what would be sent without posting
    --location-id   GHL location ID (default: $GHL_LOCATION_ID)
    --api-key       GHL API key (default: $GHL_API_KEY)

Environment Variables:
    GHL_API_KEY       -- GHL Bearer token (required)
    GHL_LOCATION_ID   -- Default location ID

Examples:
    # Dry run (safe — shows payload, no API call)
    python scripts/ghl_social_create_post.py \\
        --account-id acc_abc123 \\
        --content "Never miss another call. Second Ring answers 24/7." \\
        --schedule-at 2026-04-01T10:00:00-07:00 \\
        --dry-run

    # With image
    python scripts/ghl_social_create_post.py \\
        --account-id acc_abc123 \\
        --content "Our AI answers every call." \\
        --image-url https://cdn.example.com/secondring-banner.jpg \\
        --dry-run

    # Live post (requires --dry-run to be omitted AND confirmation)
    python scripts/ghl_social_create_post.py \\
        --account-id acc_abc123 \\
        --content "Hello from Second Ring!" \\
        --schedule-at 2026-04-01T09:00:00-07:00

Exit codes:
    0 -- success (or dry-run preview completed)
    1 -- error (missing args, API error)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from publisher.adapters.ghl import GHLAdapter

import types
from publisher.retry import PermanentError, PublishError, RateLimitError


logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a GHL Social Planner post",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--account-id",
        required=True,
        help="GHL social account ID to post to",
    )
    parser.add_argument(
        "--content",
        required=True,
        help="Post text content",
    )
    parser.add_argument(
        "--schedule-at",
        default=None,
        help="ISO 8601 datetime with timezone (e.g. 2026-04-01T10:00:00-07:00). Defaults to now.",
    )
    parser.add_argument(
        "--image-url",
        default=None,
        help="URL of image to include in post",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview payload without making any API call (REQUIRED for safety)",
    )
    parser.add_argument(
        "--location-id",
        default=os.environ.get("GHL_LOCATION_ID", ""),
        help="GHL location ID (default: $GHL_LOCATION_ID)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GHL_API_KEY", ""),
        help="GHL API key / Bearer token (default: $GHL_API_KEY)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def make_adapter(api_key: str, location_id: str) -> GHLAdapter:
    os.environ["GHL_API_KEY"] = api_key
    os.environ["GHL_LOCATION_ID"] = location_id

    brand = types.SimpleNamespace(ghl={"location_id": location_id, "accounts": {}})

    state_dir = Path(os.environ.get("TMPDIR", "/tmp")) / "ghl_cli_state"
    state_dir.mkdir(parents=True, exist_ok=True)

    adapter = GHLAdapter(brand, state_dir)
    adapter.api_key = api_key
    adapter.location_id = location_id
    return adapter


def build_payload(
    account_id: str,
    content: str,
    schedule_at: Optional[str],
    image_url: Optional[str],
) -> dict:
    """Build the GHL API request payload."""
    scheduled_at = schedule_at
    if not scheduled_at:
        scheduled_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload: dict = {
        "accountIds": [account_id],
        "content": content,
        "scheduledAt": scheduled_at,
        "type": "image" if image_url else "text",
    }
    if image_url:
        payload["mediaUrls"] = [image_url]

    return payload


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.api_key:
        print("Error: GHL_API_KEY not set. Use --api-key or set the environment variable.", file=sys.stderr)
        return 1

    if not args.location_id:
        print("Error: GHL_LOCATION_ID not set. Use --location-id or set the environment variable.", file=sys.stderr)
        return 1

    payload = build_payload(
        account_id=args.account_id,
        content=args.content,
        schedule_at=args.schedule_at,
        image_url=args.image_url,
    )

    if args.dry_run:
        print("[DRY RUN] Would POST to GHL Social Planner:")
        print(f"  Location: {args.location_id}")
        print(f"  Endpoint: /social-media-posting/{args.location_id}/posts")
        print(f"  Payload:")
        print(json.dumps(payload, indent=4))
        print("[DRY RUN] No API call made.")
        return 0

    # Live write — confirm intent (no --dry-run flag provided)
    print("WARNING: This will create a live post. Use --dry-run to preview first.")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0

    try:
        adapter = make_adapter(args.api_key, args.location_id)
        resp = adapter._request("POST", f"/social-media-posting/{args.location_id}/posts", payload)
        data = resp.json() if resp.content else {}
        post_id = data.get("id") or data.get("post_id", "")
        print(f"Post created successfully.")
        print(f"  GHL Post ID: {post_id}")
        print(json.dumps(data, indent=2))
        return 0
    except (PermanentError, PublishError, RateLimitError) as e:
        print(f"Error: GHL API error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
