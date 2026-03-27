#!/usr/bin/env python3
"""
ghl_social_list_accounts.py -- List connected GHL Social Planner accounts

Lists all connected social media accounts for a GHL location via the
GoHighLevel Social Planner API.

Usage:
    python scripts/ghl_social_list_accounts.py [--location-id ID] [--json]

Environment Variables:
    GHL_API_KEY       -- GHL Bearer token (required)
    GHL_LOCATION_ID   -- Default location ID (overridden by --location-id)

Output (default tabular):
    ACCOUNT_ID        PLATFORM   NAME              STATUS
    acc_abc123        facebook   My Page           connected
    acc_def456        instagram  @myhandle         connected

Output (--json):
    JSON array of raw account objects from GHL API

Examples:
    # Use default location from env
    python scripts/ghl_social_list_accounts.py

    # Specify location explicitly
    python scripts/ghl_social_list_accounts.py --location-id pVJjc3aFLNffIlJCvY6B

    # Get raw JSON for piping
    python scripts/ghl_social_list_accounts.py --json | jq '.[].id'

Exit codes:
    0 -- success (even if 0 accounts found)
    1 -- error (missing credentials, API error)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add repo root to path so we can import publisher
sys.path.insert(0, str(Path(__file__).parent.parent))

from publisher.adapters.ghl import GHLAdapter

import types
from publisher.retry import PermanentError


logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List connected GHL Social Planner accounts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Exit codes:")[0].strip(),
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
        "--json",
        action="store_true",
        dest="output_json",
        help="Output raw JSON instead of tabular format",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def make_adapter(api_key: str, location_id: str) -> GHLAdapter:
    """Build a minimal GHLAdapter without a full Brand/state_dir."""
    # Patch env vars so the adapter constructor picks them up
    os.environ["GHL_API_KEY"] = api_key
    os.environ["GHL_LOCATION_ID"] = location_id

    # Minimal brand stub — only ghl block matters for the adapter
    brand = types.SimpleNamespace(ghl={"location_id": location_id, "accounts": {}})

    state_dir = Path(os.environ.get("TMPDIR", "/tmp")) / "ghl_cli_state"
    state_dir.mkdir(parents=True, exist_ok=True)

    adapter = GHLAdapter(brand, state_dir)
    adapter.api_key = api_key
    adapter.location_id = location_id
    return adapter


def format_tabular(accounts: list[dict]) -> str:
    """Format accounts as aligned columns."""
    if not accounts:
        return "(no accounts found)"

    col_widths = {
        "id": max(len("ACCOUNT_ID"), max(len(str(a.get("id", ""))) for a in accounts)),
        "platform": max(len("PLATFORM"), max(len(str(a.get("platform", a.get("type", "")))) for a in accounts)),
        "name": max(len("NAME"), max(len(str(a.get("name", a.get("displayName", "")))) for a in accounts)),
        "status": max(len("STATUS"), max(len(str(a.get("status", "unknown"))) for a in accounts)),
    }

    def row(account_id: str, platform: str, name: str, status: str) -> str:
        return (
            f"{account_id:<{col_widths['id']}}  "
            f"{platform:<{col_widths['platform']}}  "
            f"{name:<{col_widths['name']}}  "
            f"{status:<{col_widths['status']}}"
        )

    lines = [
        row("ACCOUNT_ID", "PLATFORM", "NAME", "STATUS"),
        row("-" * col_widths["id"], "-" * col_widths["platform"],
            "-" * col_widths["name"], "-" * col_widths["status"]),
    ]
    for a in accounts:
        lines.append(row(
            str(a.get("id", "")),
            str(a.get("platform", a.get("type", ""))),
            str(a.get("name", a.get("displayName", ""))),
            str(a.get("status", "unknown")),
        ))
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

    try:
        adapter = make_adapter(args.api_key, args.location_id)
        accounts = adapter.get_accounts()
    except PermanentError as e:
        print(f"Error: GHL API error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.output_json:
        print(json.dumps(accounts, indent=2))
    else:
        print(format_tabular(accounts))

    return 0


if __name__ == "__main__":
    sys.exit(main())
