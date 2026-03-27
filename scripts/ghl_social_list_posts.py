#!/usr/bin/env python3
"""
ghl_social_list_posts.py -- List GHL Social Planner posts

Lists scheduled and/or published posts for a GHL location with optional
filtering by status, date range, and result limit.

Usage:
    python scripts/ghl_social_list_posts.py [options]

Arguments:
    --status STATUS     Filter by post status (scheduled, published, failed, draft)
    --from DATE         Filter posts on or after this date (YYYY-MM-DD)
    --to DATE           Filter posts on or before this date (YYYY-MM-DD)
    --limit N           Maximum number of posts to display (default: 50)
    --json              Output raw JSON instead of tabular format
    --location-id ID    GHL location ID (default: $GHL_LOCATION_ID)
    --api-key KEY       GHL API key (default: $GHL_API_KEY)

Environment Variables:
    GHL_API_KEY       -- GHL Bearer token (required)
    GHL_LOCATION_ID   -- Default location ID

Output (default tabular):
    POST_ID           STATUS     SCHEDULED_AT              PLATFORMS  CONTENT_PREVIEW
    post_abc123       scheduled  2026-04-01T10:00:00-07:00 facebook   Never miss a call...
    post_def456       published  2026-03-25T09:00:00-07:00 linkedin   Second Ring AI...

Output (--json):
    JSON array of raw post objects from GHL API

Examples:
    # List all posts
    python scripts/ghl_social_list_posts.py

    # List only scheduled posts
    python scripts/ghl_social_list_posts.py --status scheduled

    # List posts in April 2026
    python scripts/ghl_social_list_posts.py --from 2026-04-01 --to 2026-04-30

    # Get last 10 posts as JSON
    python scripts/ghl_social_list_posts.py --limit 10 --json

Exit codes:
    0 -- success (even if 0 posts found)
    1 -- error (missing credentials, API error)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from publisher.adapters.ghl import GHLAdapter

import types
from publisher.retry import PermanentError


logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

VALID_STATUSES = {"scheduled", "published", "failed", "draft", "all"}
DEFAULT_LIMIT = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List GHL Social Planner posts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--status",
        default=None,
        choices=["scheduled", "published", "failed", "draft"],
        help="Filter by post status",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        default=None,
        help="Filter posts on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        default=None,
        help="Filter posts on or before this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum number of posts to display (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output raw JSON instead of tabular format",
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


def build_filters(
    status: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    limit: int,
) -> dict:
    """Build the filter body for GHL list_posts POST endpoint."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if from_date:
        filters["startDate"] = from_date
    if to_date:
        filters["endDate"] = to_date
    if limit:
        filters["limit"] = limit
    return filters


def truncate(text: str, max_len: int = 40) -> str:
    """Truncate text for preview display."""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text


def format_tabular(posts: list[dict]) -> str:
    """Format posts as aligned columns."""
    if not posts:
        return "(no posts found)"

    def get_platform(post: dict) -> str:
        accounts = post.get("accountIds", post.get("accounts", []))
        if isinstance(accounts, list) and accounts:
            return ",".join(str(a) for a in accounts[:2])
        platform = post.get("platform", post.get("type", ""))
        return str(platform) if platform else "unknown"

    rows = []
    for p in posts:
        rows.append({
            "id": str(p.get("id", "")),
            "status": str(p.get("status", "unknown")),
            "scheduled_at": str(p.get("scheduledAt", p.get("scheduled_at", ""))),
            "platforms": get_platform(p),
            "preview": truncate(str(p.get("content", p.get("text", "")))),
        })

    col_widths = {
        "id": max(len("POST_ID"), max(len(r["id"]) for r in rows)),
        "status": max(len("STATUS"), max(len(r["status"]) for r in rows)),
        "scheduled_at": max(len("SCHEDULED_AT"), max(len(r["scheduled_at"]) for r in rows)),
        "platforms": max(len("PLATFORMS"), max(len(r["platforms"]) for r in rows)),
        "preview": max(len("CONTENT_PREVIEW"), max(len(r["preview"]) for r in rows)),
    }

    def row(post_id: str, status: str, scheduled_at: str, platforms: str, preview: str) -> str:
        return (
            f"{post_id:<{col_widths['id']}}  "
            f"{status:<{col_widths['status']}}  "
            f"{scheduled_at:<{col_widths['scheduled_at']}}  "
            f"{platforms:<{col_widths['platforms']}}  "
            f"{preview}"
        )

    lines = [
        row("POST_ID", "STATUS", "SCHEDULED_AT", "PLATFORMS", "CONTENT_PREVIEW"),
        row(
            "-" * col_widths["id"],
            "-" * col_widths["status"],
            "-" * col_widths["scheduled_at"],
            "-" * col_widths["platforms"],
            "-" * col_widths["preview"],
        ),
    ]
    for r in rows:
        lines.append(row(r["id"], r["status"], r["scheduled_at"], r["platforms"], r["preview"]))

    return "\n".join(lines)


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

    filters = build_filters(
        status=args.status,
        from_date=args.from_date,
        to_date=args.to_date,
        limit=args.limit,
    )

    try:
        adapter = make_adapter(args.api_key, args.location_id)
        posts = adapter.list_posts(filters)
    except PermanentError as e:
        print(f"Error: GHL API error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Apply client-side limit (in case API ignores it)
    posts = posts[: args.limit]

    if args.output_json:
        print(json.dumps(posts, indent=2))
    else:
        print(format_tabular(posts))

    return 0


if __name__ == "__main__":
    sys.exit(main())
