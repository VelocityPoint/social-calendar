#!/usr/bin/env python3
"""
ghl_social_delete_post.py -- Delete a GHL Social Planner post

Deletes a post by ID from GHL Social Planner. All deletions require --dry-run
unless explicitly confirmed (no --dry-run flag + interactive confirmation).

Usage:
    python scripts/ghl_social_delete_post.py --post-id POST_ID --dry-run

Arguments:
    --post-id       GHL post ID to delete (required)
    --dry-run       REQUIRED for safety — previews what would be deleted without calling API
    --location-id   GHL location ID (default: $GHL_LOCATION_ID)
    --api-key       GHL API key (default: $GHL_API_KEY)

Environment Variables:
    GHL_API_KEY       -- GHL Bearer token (required)
    GHL_LOCATION_ID   -- Default location ID

Examples:
    # Dry run (safe — shows what would be deleted)
    python scripts/ghl_social_delete_post.py --post-id post_abc123 --dry-run

    # Live delete (requires explicit confirmation)
    python scripts/ghl_social_delete_post.py --post-id post_abc123

    # With explicit credentials
    python scripts/ghl_social_delete_post.py \\
        --post-id post_abc123 \\
        --location-id pVJjc3aFLNffIlJCvY6B \\
        --api-key eyJhbGciOiJSUzI1NiJ9... \\
        --dry-run

Exit codes:
    0 -- success (or dry-run completed)
    1 -- error (missing args, API error, not found)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from publisher.adapters.ghl import GHLAdapter

import types
from publisher.retry import PermanentError, PublishError, RateLimitError


logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete a GHL Social Planner post",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--post-id",
        required=True,
        help="GHL post ID to delete",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletion without making any API call (recommended)",
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

    if args.dry_run:
        print("[DRY RUN] Would DELETE from GHL Social Planner:")
        print(f"  Location:  {args.location_id}")
        print(f"  Endpoint:  DELETE /social-media-posting/{args.location_id}/posts/{args.post_id}")
        print(f"  Post ID:   {args.post_id}")
        print("[DRY RUN] No API call made.")
        return 0

    # Live delete — require interactive confirmation
    print(f"WARNING: This will permanently delete post {args.post_id}.")
    print("This action CANNOT be undone. Use --dry-run to preview first.")
    print(f"Type the post ID to confirm, or Ctrl+C to cancel: ", end="")
    try:
        confirmation = input().strip()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0

    if confirmation != args.post_id:
        print("Confirmation failed — post ID does not match. Aborting.", file=sys.stderr)
        return 1

    try:
        adapter = make_adapter(args.api_key, args.location_id)
        success = adapter.delete(args.post_id)
        if success:
            print(f"Post {args.post_id} deleted successfully.")
            return 0
        else:
            print(f"Error: Deletion did not confirm success for post {args.post_id}.", file=sys.stderr)
            return 1
    except PermanentError as e:
        status = getattr(e, "status_code", None)
        if status == 404:
            print(f"Error: Post {args.post_id} not found (404).", file=sys.stderr)
        elif status in (401, 403):
            print(f"Error: Authentication/authorization failed ({status}).", file=sys.stderr)
        else:
            print(f"Error: GHL API error: {e}", file=sys.stderr)
        return 1
    except (PublishError, RateLimitError) as e:
        print(f"Error: GHL API error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
