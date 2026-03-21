#!/usr/bin/env python3
"""
validate-brand.py -- Brand config validator (AC8)

Usage:
    python scripts/validate-brand.py brands/secondring/brand.yaml

Exit codes:
    0 -- valid brand config
    1 -- validation errors (printed to stderr)

Security: detects raw OAuth tokens in credentials (JWT eyJ prefix, Google ya29. prefix).
"""

import sys
import re
import yaml
from pathlib import Path


REQUIRED_FIELDS = ["brand_name", "credentials", "cadence", "pillars"]
VALID_PLATFORMS = {"facebook", "linkedin", "gbp", "x", "instagram"}

# Patterns that indicate raw tokens (not KV secret name references)
RAW_TOKEN_PATTERNS = [
    (re.compile(r"^eyJ"), "JWT token (should be a Key Vault secret name)"),
    (re.compile(r"^ya29\."), "Google OAuth token (should be a Key Vault secret name)"),
    (re.compile(r"^EAA"), "Facebook/Meta access token (should be a Key Vault secret name)"),
    (re.compile(r"^AAAAAA"), "Twitter/X bearer token (should be a Key Vault secret name)"),
    (re.compile(r"[A-Za-z0-9+/]{100,}={0,2}$"), "long base64 string (likely a raw token — use a Key Vault secret name)"),
]

TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def check_raw_token(value: str) -> str | None:
    """Returns error message if value looks like a raw token, None otherwise."""
    if not isinstance(value, str):
        return None
    for pattern, description in RAW_TOKEN_PATTERNS:
        if pattern.search(value):
            return f"looks like a {description}"
    return None


def validate_credentials(credentials: dict) -> list[str]:
    errors = []
    if not isinstance(credentials, dict):
        errors.append("Error: 'credentials' must be a mapping of platform to secret name")
        return errors

    for platform, value in credentials.items():
        if platform not in VALID_PLATFORMS:
            errors.append(f"Error: unknown platform '{platform}' in credentials")
        raw_error = check_raw_token(str(value))
        if raw_error:
            errors.append(
                f"Error: credentials['{platform}'] {raw_error}. "
                f"Store the Key Vault secret name, not the token itself."
            )

    return errors


def validate_cadence(cadence: dict) -> list[str]:
    errors = []
    if not isinstance(cadence, dict):
        errors.append("Error: 'cadence' must be a mapping of platform to schedule config")
        return errors

    if len(cadence) == 0:
        errors.append("Error: 'cadence' must have at least one platform entry")
        return errors

    for platform, config in cadence.items():
        if not isinstance(config, dict):
            errors.append(f"Error: cadence['{platform}'] must be a mapping")
            continue

        if "posts_per_week" not in config:
            errors.append(f"Error: cadence['{platform}'] missing required field 'posts_per_week'")
        elif not isinstance(config["posts_per_week"], int) or config["posts_per_week"] < 1:
            errors.append(f"Error: cadence['{platform}'].posts_per_week must be a positive integer")

        if "preferred_times" not in config:
            errors.append(f"Error: cadence['{platform}'] missing required field 'preferred_times'")
        elif not isinstance(config["preferred_times"], list) or len(config["preferred_times"]) == 0:
            errors.append(f"Error: cadence['{platform}'].preferred_times must be a non-empty list")
        else:
            for t in config["preferred_times"]:
                if not TIME_PATTERN.match(str(t)):
                    errors.append(
                        f"Error: cadence['{platform}'].preferred_times entry '{t}' "
                        f"must be HH:MM format"
                    )

    return errors


def validate_file(file_path: str) -> list[str]:
    """Validate a brand.yaml file. Returns list of error strings."""
    errors = []
    path = Path(file_path)

    if not path.exists():
        return [f"Error: file not found: {file_path}"]

    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as e:
        return [f"Error: YAML parse error: {e}"]
    except Exception as e:
        return [f"Error: cannot read file: {e}"]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"Error: missing required field '{field}'")

    # Validate brand_name
    if "brand_name" in data and not isinstance(data["brand_name"], str):
        errors.append("Error: 'brand_name' must be a string")

    # Validate credentials (AC8 — security: detect raw tokens)
    if "credentials" in data:
        errors.extend(validate_credentials(data["credentials"]))

    # Validate cadence
    if "cadence" in data:
        errors.extend(validate_cadence(data["cadence"]))

    # Validate pillars
    if "pillars" in data:
        if not isinstance(data["pillars"], list) or len(data["pillars"]) == 0:
            errors.append("Error: 'pillars' must be a non-empty list of strings")

    # avatar_id may be null (Phase 1 OK)
    if "avatar_id" in data and data["avatar_id"] is not None:
        if not isinstance(data["avatar_id"], str):
            errors.append("Error: 'avatar_id' must be a string or null")

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-brand.py <brand.yaml> [brand2.yaml ...]", file=sys.stderr)
        sys.exit(1)

    files = sys.argv[1:]
    all_errors = []

    for f in files:
        errors = validate_file(f)
        if errors:
            for err in errors:
                print(f"{f}: {err}", file=sys.stderr)
            all_errors.extend(errors)
        else:
            print(f"OK: {f}")

    if all_errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
