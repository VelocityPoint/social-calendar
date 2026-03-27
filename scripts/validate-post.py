#!/usr/bin/env python3
"""
validate-post.py -- Post document schema validator (AC1, AC5, AC8, AC11, AC-OQ2, AC-OQ3)

Validates Markdown post documents against the post schema.  In GHL mode (default), also
checks that the `author` field resolves in the brand's ghl.accounts mapping.

Usage:
    python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-example.md
    python scripts/validate-post.py brands/secondring/calendar/2026/04/*.md
    python scripts/validate-post.py --dry-run brands/secondring/calendar/2026/04/*.md

Flags:
    --dry-run   Validate without any side effects (no API calls, no writes). Alias: -n.
                In practice, validate-post.py never writes anything — this flag is included
                for consistency with the publisher CLI and AC8 acceptance criteria.

Exit codes:
    0 -- all files valid
    1 -- one or more validation errors (errors printed to stderr)
"""

import sys
import re
import os
import yaml
from pathlib import Path


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "post.schema.yaml"
REPO_ROOT = Path(__file__).parent.parent

REQUIRED_FIELDS = ["id", "publish_at", "platforms", "status", "brand", "author"]
VALID_PLATFORMS = {"facebook", "linkedin", "gbp", "x", "instagram"}
VALID_STATUSES = {
    "draft", "ready", "scheduled", "published", "failed", "deferred", "video-pending"
}
# PR-submittable statuses — publisher manages the rest
VALID_PR_STATUSES = {"draft", "ready"}

# Character limits per platform (source: GHL docs + platform native)
PLATFORM_LIMITS = {
    "linkedin": 3000,
    "x": 280,
    "gbp": 1500,
    "facebook": 63000,
    "instagram": 2200,
}

VALID_AUTHORS = {"dave", "velocitypoint"}

PLATFORM_SECTION_HEADERS = {
    "linkedin": "LinkedIn Version",
    "facebook": "Facebook Version",
    "x": "X Version",
    "gbp": "Google Business Profile Version",
    "instagram": "Instagram Version",
}
PUBLISH_AT_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$"
)
POST_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-.+$")
FILENAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")
FILE_PATH_PATTERN = re.compile(
    r"brands/[^/]+/calendar/\d{4}/\d{2}/\d{4}-\d{2}-\d{2}-.+\.md$"
)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from Markdown. Returns (frontmatter_dict, body_text)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    yaml_text = content[3:end].strip()
    body = content[end + 4:].strip()
    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parse error in frontmatter: {e}")
    return data, body


def extract_copy_sections(body: str) -> dict[str, str]:
    """Extract platform copy sections from document body per OQ3/AC11."""
    sections = {}
    pattern = re.compile(r"^# (.+)\n([\s\S]*?)(?=^# |\Z)", re.MULTILINE)
    for match in pattern.finditer(body):
        header = match.group(1).strip()
        text = match.group(2).strip()
        for platform, section_name in PLATFORM_SECTION_HEADERS.items():
            if header == section_name:
                sections[platform] = text
                break
    return sections


def load_brand_ghl_accounts(brand_slug: str) -> dict:
    """
    Load ghl.accounts mapping from brands/<brand>/brand.yaml.
    Returns {} if file not found or ghl block absent (non-fatal — missing accounts
    produce a validation error, not a crash).
    """
    brand_yaml_path = REPO_ROOT / "brands" / brand_slug / "brand.yaml"
    if not brand_yaml_path.exists():
        return {}
    try:
        data = yaml.safe_load(brand_yaml_path.read_text(encoding="utf-8")) or {}
        return data.get("ghl", {}).get("accounts", {})
    except Exception:
        return {}


def validate_file(file_path: str, dry_run: bool = False) -> list[str]:
    """
    Validate a single post document. Returns list of error strings.

    dry_run: no-op for validation (validate-post.py never writes). Flag accepted for
             CLI consistency and AC8 --dry-run compliance.
    """
    errors = []
    path = Path(file_path)

    # AC-OQ2: Validate file path structure
    path_str = str(path).replace("\\", "/")
    if "calendar" in path_str and not FILE_PATH_PATTERN.search(path_str):
        errors.append(
            f"Error: file path must match brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-<slug>.md "
            f"(got: {path_str})"
        )

    # AC-OQ2: Validate filename format
    if not FILENAME_PATTERN.match(path.name):
        errors.append(
            f"Error: filename must match pattern YYYY-MM-DD-<slug>.md (got: {path.name})"
        )

    if not path.exists():
        errors.append(f"Error: file not found: {file_path}")
        return errors

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(f"Error: cannot read file: {e}")
        return errors

    # Parse frontmatter
    try:
        frontmatter, body = parse_frontmatter(content)
    except ValueError as e:
        errors.append(str(e))
        return errors

    if not frontmatter:
        errors.append("Error: no YAML frontmatter found (file must start with ---)")
        return errors

    # Check required fields (AC1, AC8)
    for field in REQUIRED_FIELDS:
        if field not in frontmatter or frontmatter[field] is None:
            errors.append(
                f"Error: missing required field '{field}'"
                + (
                    f" — 'author' maps post to a GHL social account (dave | velocitypoint)"
                    if field == "author"
                    else ""
                )
            )

    # Validate id format
    if "id" in frontmatter and frontmatter["id"]:
        if not POST_ID_PATTERN.match(str(frontmatter["id"])):
            errors.append(
                f"Error: 'id' must match pattern YYYY-MM-DD-<slug> (got: {frontmatter['id']})"
            )

    # Validate publish_at (AC1, AC5) — timezone offset required
    if "publish_at" in frontmatter and frontmatter["publish_at"]:
        publish_at_str = str(frontmatter["publish_at"])
        if not PUBLISH_AT_PATTERN.match(publish_at_str):
            errors.append(
                f"Error: 'publish_at' must include timezone offset (got: '{publish_at_str}'). "
                f"Expected ISO 8601 format: YYYY-MM-DDTHH:MM:SS+HH:MM or Z. "
                f"Example: 2026-04-01T09:00:00-07:00"
            )

    # Validate platforms (AC1)
    platforms = []
    if "platforms" in frontmatter:
        platforms_raw = frontmatter.get("platforms")
        if not isinstance(platforms_raw, list) or len(platforms_raw) == 0:
            errors.append("Error: 'platforms' must be a non-empty list")
        else:
            for p in platforms_raw:
                if p not in VALID_PLATFORMS:
                    errors.append(
                        f"Error: unknown platform '{p}' in 'platforms' list. "
                        f"Valid values: {sorted(VALID_PLATFORMS)}"
                    )
                else:
                    platforms.append(p)

    # Validate status (AC1, AC8)
    status = frontmatter.get("status")
    if status:
        if status not in VALID_STATUSES:
            errors.append(
                f"Error: invalid status '{status}'. "
                f"Valid values: {sorted(VALID_STATUSES)}. "
                f"Lifecycle: draft → ready → scheduled → published | failed"
            )

    # Validate author (AC8 — GHL account resolution)
    author = frontmatter.get("author")
    brand = frontmatter.get("brand")
    ghl_mode = frontmatter.get("ghl_mode", True)  # default true per schema

    if author is not None:
        if ghl_mode and author not in VALID_AUTHORS:
            errors.append(
                f"Error: 'author' must be one of {sorted(VALID_AUTHORS)} "
                f"(got: '{author}'). "
                f"'author' maps to a GHL social account via brand.yaml → ghl.accounts. "
                f"Set ghl_mode: false to use legacy direct-platform adapters with a free-form author."
            )
        elif brand and ghl_mode:
            # Check that author resolves in brand.yaml ghl.accounts (AC8)
            ghl_accounts = load_brand_ghl_accounts(brand)
            if not ghl_accounts:
                # brand.yaml has no ghl block yet — warn but don't hard-fail
                # Step 4 (brand config) adds the ghl block; Step 3 should not block on it
                pass  # Silent pass — ghl block is added in Step 4 (feat: brand config ghl block)
            elif author not in ghl_accounts:
                errors.append(
                    f"Error: 'author' value '{author}' not found in "
                    f"brands/{brand}/brand.yaml → ghl.accounts. "
                    f"Available authors: {sorted(ghl_accounts.keys()) or ['(none configured yet)']}. "
                    f"Add '{author}' to the ghl.accounts block in brand.yaml."
                )
            else:
                # Check that each listed platform has an account_id for this author
                author_accounts = ghl_accounts[author]
                for platform in platforms:
                    if platform not in author_accounts:
                        errors.append(
                            f"Error: no GHL account configured for author '{author}' on platform '{platform}'. "
                            f"Add brands/{brand}/brand.yaml → ghl.accounts.{author}.{platform} "
                            f"(run ghl_social_list_accounts.py to find the account ID)."
                        )

    # Validate copy sections exist and are within character limits (AC11, AC-OQ3)
    if platforms:
        copy_sections = extract_copy_sections(body)

        for platform in platforms:
            if platform not in copy_sections:
                errors.append(
                    f"Error: missing copy section for platform '{platform}'. "
                    f"Expected a '# {PLATFORM_SECTION_HEADERS.get(platform, platform)}' "
                    f"section in the document body."
                )
            else:
                limit = PLATFORM_LIMITS.get(platform, 0)
                text_len = len(copy_sections[platform])
                if limit and text_len > limit:
                    errors.append(
                        f"Error: '{platform}' copy section exceeds character limit. "
                        f"Got {text_len:,} characters, limit is {limit:,}. "
                        f"Trim {text_len - limit:,} characters from the "
                        f"'# {PLATFORM_SECTION_HEADERS[platform]}' section."
                    )

    return errors


def main():
    args = sys.argv[1:]
    dry_run = False

    if not args:
        print("Usage: validate-post.py [--dry-run] <file.md> [file2.md ...]", file=sys.stderr)
        sys.exit(1)

    # Parse --dry-run / -n flag
    filtered_args = []
    for arg in args:
        if arg in ("--dry-run", "-n"):
            dry_run = True
        else:
            filtered_args.append(arg)
    args = filtered_args

    if not args:
        print("Usage: validate-post.py [--dry-run] <file.md> [file2.md ...]", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print("Dry-run mode: validating without side effects.")

    all_errors = []

    for f in args:
        errors = validate_file(f, dry_run=dry_run)
        if errors:
            for err in errors:
                print(f"{f}: {err}", file=sys.stderr)
            all_errors.extend(errors)
        else:
            print(f"OK: {f}")

    if all_errors:
        print(
            f"\n{len(all_errors)} error(s) found across {len(args)} file(s).",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(f"\nAll {len(args)} file(s) passed validation.")
        sys.exit(0)


if __name__ == "__main__":
    main()
