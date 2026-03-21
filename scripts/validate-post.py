#!/usr/bin/env python3
"""
validate-post.py -- Post document schema validator (AC1, AC5, AC11, AC-OQ2, AC-OQ3)

Usage:
    python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-example.md
    python scripts/validate-post.py brands/secondring/calendar/2026/04/*.md

Exit codes:
    0 -- all files valid
    1 -- one or more validation errors (errors printed to stderr)
"""

import sys
import re
import os
import yaml
from pathlib import Path
from datetime import datetime, timezone


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "post.schema.yaml"

REQUIRED_FIELDS = ["id", "publish_at", "platforms", "status", "brand"]
VALID_PLATFORMS = {"facebook", "linkedin", "gbp", "x", "instagram"}
VALID_STATUSES = {"draft", "scheduled", "published", "failed", "deferred", "video-pending"}
PLATFORM_LIMITS = {
    "linkedin": 3000,
    "x": 280,
    "gbp": 1500,
    "facebook": 2200,
    "instagram": 2200,
}
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


def validate_file(file_path: str) -> list[str]:
    """Validate a single post document. Returns list of error strings."""
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

    # Check required fields (AC1)
    for field in REQUIRED_FIELDS:
        if field not in frontmatter or frontmatter[field] is None:
            errors.append(f"Error: missing required field '{field}'")

    # Validate id format
    if "id" in frontmatter and frontmatter["id"]:
        if not POST_ID_PATTERN.match(str(frontmatter["id"])):
            errors.append(
                f"Error: 'id' must match pattern YYYY-MM-DD-<slug> (got: {frontmatter['id']})"
            )

    # Validate publish_at (AC1, AC5)
    if "publish_at" in frontmatter and frontmatter["publish_at"]:
        val = frontmatter["publish_at"]
        publish_at_str = val.isoformat() if hasattr(val, "isoformat") else str(val)
        if not PUBLISH_AT_PATTERN.match(publish_at_str):
            errors.append(
                f"Error: publish_at must include timezone offset (got: {publish_at_str}). "
                f"Use ISO 8601 format with offset, e.g. 2026-04-01T09:00:00-07:00 or 2026-04-01T16:00:00Z"
            )

    # Validate platforms (AC1)
    if "platforms" in frontmatter:
        platforms = frontmatter.get("platforms")
        if not isinstance(platforms, list) or len(platforms) == 0:
            errors.append("Error: 'platforms' must be a non-empty list")
        else:
            for p in platforms:
                if p not in VALID_PLATFORMS:
                    errors.append(
                        f"Error: unknown platform '{p}' in 'platforms' list. "
                        f"Valid values: {sorted(VALID_PLATFORMS)}"
                    )

    # Validate status (AC1)
    if "status" in frontmatter and frontmatter["status"]:
        if frontmatter["status"] not in VALID_STATUSES:
            errors.append(
                f"Error: invalid status '{frontmatter['status']}'. "
                f"Valid values: {sorted(VALID_STATUSES)}"
            )

    # Validate copy sections exist for each target platform (AC11, AC-OQ3)
    if "platforms" in frontmatter and isinstance(frontmatter.get("platforms"), list):
        platforms = [p for p in frontmatter["platforms"] if p in VALID_PLATFORMS]
        copy_sections = extract_copy_sections(body)

        for platform in platforms:
            if platform not in copy_sections:
                errors.append(
                    f"Error: Missing copy section for platform: {platform} "
                    f"(expected '# {PLATFORM_SECTION_HEADERS.get(platform, platform)} Version' section)"
                )
            else:
                # Validate character limits
                limit = PLATFORM_LIMITS.get(platform, 0)
                text_len = len(copy_sections[platform])
                if limit and text_len > limit:
                    errors.append(
                        f"Error: {platform} copy section exceeds character limit "
                        f"({text_len} > {limit})"
                    )

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-post.py <file.md> [file2.md ...]", file=sys.stderr)
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
