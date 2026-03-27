#!/usr/bin/env python3
"""
scripts/ghl_social_list_accounts.py -- List connected social accounts for a GHL location.

Usage:
    python scripts/ghl_social_list_accounts.py [--location-id X] [--api-key X]

Auth/location resolution order:
    1. CLI args (--location-id, --api-key)
    2. Environment variables (GHL_LOCATION_ID, GHL_API_KEY)
    3. brands/secondring/brand.yaml (location_id only)

Ref: AC2 (auth check), AC6 (list accounts)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add repo root to path for imports
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
    parser = argparse.ArgumentParser(description="List connected GHL social accounts")
    parser.add_argument("--location-id", help="GHL location ID")
    parser.add_argument("--api-key", help="GHL API key")
    args = parser.parse_args()

    location_id, api_key = resolve_config(args)

    if not location_id:
        print("Error: No location ID provided (--location-id, GHL_LOCATION_ID, or brand.yaml)", file=sys.stderr)
        return 1
    if not api_key:
        print("Error: No API key provided (--api-key or GHL_API_KEY)", file=sys.stderr)
        return 1

    adapter = make_adapter(location_id, api_key)

    try:
        accounts = adapter.get_accounts()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not accounts:
        print("No connected social accounts found.")
        return 0

    # Print table
    header = f"{'PLATFORM':<15} {'ACCOUNT NAME':<30} {'ACCOUNT ID':<25} {'STATUS':<10}"
    print(header)
    print("-" * len(header))
    for acct in accounts:
        platform = acct.get("platform", "unknown")
        name = acct.get("name", acct.get("account_name", "—"))
        acct_id = acct.get("id", acct.get("account_id", "—"))
        status = acct.get("status", acct.get("active", "—"))
        print(f"{platform:<15} {name:<30} {acct_id:<25} {status:<10}")

    print(f"\nTotal: {len(accounts)} account(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
