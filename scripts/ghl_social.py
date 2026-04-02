#!/usr/bin/env python3
"""
ghl_social.py -- GHL Social Planner CLI

Usage:
    ghl_social.py accounts [--json]
    ghl_social.py posts [--status STATUS] [--from DATE] [--to DATE] [--limit N] [--json]
    ghl_social.py create --account-id ID --content TEXT [--schedule-at ISO] [--image-url URL] [--dry-run]
    ghl_social.py delete --post-id ID [--dry-run]

Subcommands:
    accounts    List connected social accounts for this location
    posts       List scheduled/published/failed posts
    create      Create a post (--dry-run required for first run)
    delete      Delete a post by ID (--dry-run required, then confirm)

Global options (all subcommands):
    --location-id ID    GHL location ID (default: $GHL_LOCATION_ID)
    --api-key KEY       GHL API key (default: $GHL_API_KEY)
    --verbose, -v       Enable verbose logging

Environment Variables:
    GHL_API_KEY         GHL Bearer token (required)
    GHL_LOCATION_ID     Default location ID

Examples:
    # List connected social accounts
    python scripts/ghl_social.py accounts
    python scripts/ghl_social.py accounts --json | jq '.[].id'

    # List posts
    python scripts/ghl_social.py posts
    python scripts/ghl_social.py posts --status scheduled
    python scripts/ghl_social.py posts --from 2026-04-01 --to 2026-04-30 --limit 20

    # Create a post (always dry-run first)
    python scripts/ghl_social.py create \\
        --account-id acc_abc123 \\
        --content "Never miss another call. Second Ring answers 24/7." \\
        --schedule-at 2026-04-01T10:00:00-07:00 \\
        --dry-run

    # Delete a post (dry-run, then confirm)
    python scripts/ghl_social.py delete --post-id post_abc123 --dry-run
    python scripts/ghl_social.py delete --post-id post_abc123
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from publisher.adapters.ghl import GHLAdapter
from publisher.retry import PermanentError, PublishError, RateLimitError

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def check_credentials(api_key: str, location_id: str) -> bool:
    if not api_key:
        print("Error: GHL_API_KEY not set. Use --api-key or export GHL_API_KEY.", file=sys.stderr)
        return False
    if not location_id:
        print("Error: GHL_LOCATION_ID not set. Use --location-id or export GHL_LOCATION_ID.", file=sys.stderr)
        return False
    return True


def table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    """Render a list of dicts as an aligned text table.
    columns: list of (header, key) tuples in display order.
    """
    if not rows:
        return "(no results)"
    widths = {key: len(header) for header, key in columns}
    for row in rows:
        for _, key in columns:
            widths[key] = max(widths[key], len(str(row.get(key, ""))))

    def fmt_row(values: dict) -> str:
        return "  ".join(str(values.get(k, "")).ljust(widths[k]) for _, k in columns)

    sep = {k: "-" * widths[k] for _, k in columns}
    header_vals = {k: h for h, k in columns}
    lines = [fmt_row(header_vals), fmt_row(sep)]
    for row in rows:
        lines.append(fmt_row(row))
    return "\n".join(lines)


def truncate(text: str, max_len: int = 45) -> str:
    text = str(text).replace("\n", " ").strip()
    return text[:max_len - 3] + "..." if len(text) > max_len else text


# ---------------------------------------------------------------------------
# Subcommand: accounts
# ---------------------------------------------------------------------------

def cmd_accounts(args: argparse.Namespace) -> int:
    if not check_credentials(args.api_key, args.location_id):
        return 1
    try:
        adapter = make_adapter(args.api_key, args.location_id)
        accounts = adapter.get_accounts()
    except (PermanentError, Exception) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(accounts, indent=2))
        return 0

    rows = [
        {
            "id": str(a.get("id", "")),
            "platform": str(a.get("platform", a.get("type", ""))),
            "name": str(a.get("name", a.get("displayName", ""))),
            "status": str(a.get("status", "unknown")),
        }
        for a in accounts
    ]
    print(table(rows, [("ACCOUNT_ID", "id"), ("PLATFORM", "platform"), ("NAME", "name"), ("STATUS", "status")]))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: posts
# ---------------------------------------------------------------------------

def cmd_posts(args: argparse.Namespace) -> int:
    if not check_credentials(args.api_key, args.location_id):
        return 1
    filters: dict = {}
    if args.status:
        filters["status"] = args.status
    if args.from_date:
        filters["startDate"] = args.from_date
    if args.to_date:
        filters["endDate"] = args.to_date
    if args.limit:
        filters["limit"] = args.limit

    try:
        adapter = make_adapter(args.api_key, args.location_id)
        posts = adapter.list_posts(filters)[: args.limit]
    except (PermanentError, Exception) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(posts, indent=2))
        return 0

    rows = [
        {
            "id": str(p.get("id", "")),
            "status": str(p.get("status", "unknown")),
            "scheduled_at": str(p.get("scheduledAt", p.get("scheduled_at", ""))),
            "platforms": ",".join(str(a) for a in p.get("accountIds", [])[:2]) or str(p.get("platform", "")),
            "preview": truncate(p.get("content", p.get("text", ""))),
        }
        for p in posts
    ]
    print(table(rows, [
        ("POST_ID", "id"),
        ("STATUS", "status"),
        ("SCHEDULED_AT", "scheduled_at"),
        ("PLATFORMS", "platforms"),
        ("CONTENT_PREVIEW", "preview"),
    ]))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: create
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> int:
    if not check_credentials(args.api_key, args.location_id):
        return 1

    scheduled_at = args.schedule_at or datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "accountIds": [args.account_id],
        "content": args.content,
        "scheduledAt": scheduled_at,
        "type": "image" if args.image_url else "text",
    }
    if args.image_url:
        payload["mediaUrls"] = [args.image_url]

    if args.dry_run:
        print("[DRY RUN] Would POST to GHL Social Planner:")
        print(f"  Location: {args.location_id}")
        print(f"  Endpoint: POST /social-media-posting/{args.location_id}/posts")
        print(f"  Payload:\n{json.dumps(payload, indent=4)}")
        print("[DRY RUN] No API call made.")
        return 0

    print("WARNING: This will create a live post. Press Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0

    try:
        adapter = make_adapter(args.api_key, args.location_id)
        resp = adapter._request("POST", f"/social-media-posting/{args.location_id}/posts", payload)
        data = resp.json() if resp.content else {}
        print(f"Post created. GHL Post ID: {data.get('id', data.get('post_id', ''))}")
        print(json.dumps(data, indent=2))
        return 0
    except (PermanentError, PublishError, RateLimitError, Exception) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Subcommand: delete
# ---------------------------------------------------------------------------

def cmd_delete(args: argparse.Namespace) -> int:
    if not check_credentials(args.api_key, args.location_id):
        return 1

    if args.dry_run:
        print("[DRY RUN] Would DELETE from GHL Social Planner:")
        print(f"  Location: {args.location_id}")
        print(f"  Endpoint: DELETE /social-media-posting/{args.location_id}/posts/{args.post_id}")
        print("[DRY RUN] No API call made.")
        return 0

    print(f"WARNING: Permanently delete post {args.post_id}. This cannot be undone.")
    print(f"Type the post ID to confirm, or Ctrl+C to cancel: ", end="", flush=True)
    try:
        if input().strip() != args.post_id:
            print("Post ID mismatch — aborting.", file=sys.stderr)
            return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0

    try:
        adapter = make_adapter(args.api_key, args.location_id)
        if adapter.delete(args.post_id):
            print(f"Deleted post {args.post_id}.")
            return 0
        print(f"Error: deletion did not confirm success.", file=sys.stderr)
        return 1
    except PermanentError as e:
        status = getattr(e, "status_code", None)
        if status == 404:
            print(f"Error: Post {args.post_id} not found (404).", file=sys.stderr)
        elif status in (401, 403):
            print(f"Error: Auth failed ({status}).", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghl_social.py",
        description="GHL Social Planner CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Global args
    parser.add_argument("--location-id", default=os.environ.get("GHL_LOCATION_ID", ""),
                        help="GHL location ID (default: $GHL_LOCATION_ID)")
    parser.add_argument("--api-key", default=os.environ.get("GHL_API_KEY", ""),
                        help="GHL API key (default: $GHL_API_KEY)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # accounts
    p_accounts = sub.add_parser("accounts", help="List connected social accounts")
    p_accounts.add_argument("--json", action="store_true", dest="json", help="Output raw JSON")

    # posts
    p_posts = sub.add_parser("posts", help="List posts")
    p_posts.add_argument("--status", choices=["scheduled", "published", "failed", "draft"],
                         default=None, help="Filter by status")
    p_posts.add_argument("--from", dest="from_date", default=None, metavar="DATE",
                         help="Start date (YYYY-MM-DD)")
    p_posts.add_argument("--to", dest="to_date", default=None, metavar="DATE",
                         help="End date (YYYY-MM-DD)")
    p_posts.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")
    p_posts.add_argument("--json", action="store_true", dest="json", help="Output raw JSON")

    # create
    p_create = sub.add_parser("create", help="Create a post")
    p_create.add_argument("--account-id", required=True, help="GHL social account ID")
    p_create.add_argument("--content", required=True, help="Post text")
    p_create.add_argument("--schedule-at", default=None,
                          help="ISO 8601 datetime with tz (default: now)")
    p_create.add_argument("--image-url", default=None, help="Public image URL")
    p_create.add_argument("--dry-run", action="store_true", help="Preview without API call")

    # delete
    p_delete = sub.add_parser("delete", help="Delete a post")
    p_delete.add_argument("--post-id", required=True, help="GHL post ID to delete")
    p_delete.add_argument("--dry-run", action="store_true", help="Preview without API call")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    dispatch = {
        "accounts": cmd_accounts,
        "posts": cmd_posts,
        "create": cmd_create,
        "delete": cmd_delete,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
