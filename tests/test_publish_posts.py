"""
tests/test_publish_posts.py -- Unit tests for scripts/publish_posts.py

Tests verify:
- Draft posts are skipped
- Ready posts with existing ghl_post_id are skipped
- Ready posts without ghl_post_id trigger create_post (publish)
- Dry-run mode does not call the API
- Frontmatter is updated after successful publish

All tests mock GHLAdapter.publish() — no live API calls.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import sys

# Add repo root for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.publish_posts import (
    parse_frontmatter,
    write_frontmatter,
    process_post,
    load_brand_config,
    make_adapter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BRAND_YAML = """\
brand_name: "TestBrand"
credentials:
  facebook: test-fb-token
  linkedin: test-li-token
cadence: {}
pillars:
  - "testing"
ghl:
  location_id: "loc_test_123"
  accounts:
    dave:
      linkedin: "acc_li_001"
      facebook: "acc_fb_002"
"""

READY_POST = """\
---
platform: linkedin
scheduled_at: 2099-04-07T09:00:00-07:00
author: dave
status: ready
---

Test post content for LinkedIn.
"""

DRAFT_POST = """\
---
platform: linkedin
scheduled_at: 2099-04-07T09:00:00-07:00
author: dave
status: draft
---

Draft post content.
"""

ALREADY_PUBLISHED_POST = """\
---
platform: linkedin
scheduled_at: 2099-04-07T09:00:00-07:00
author: dave
status: ready
ghl_post_id: ghl_existing_123
---

Already published post.
"""


def make_brand_file(tmp_dir: Path) -> Path:
    brand_dir = tmp_dir / "brands" / "test"
    brand_dir.mkdir(parents=True)
    brand_path = brand_dir / "brand.yaml"
    brand_path.write_text(BRAND_YAML)
    return brand_path


def make_post_file(tmp_dir: Path, content: str, name: str = "test-post.md") -> Path:
    post_path = tmp_dir / name
    post_path.write_text(content)
    return post_path


# ---------------------------------------------------------------------------
# parse_frontmatter / write_frontmatter
# ---------------------------------------------------------------------------

class TestFrontmatter:
    def test_parse_frontmatter(self, tmp_path):
        f = make_post_file(tmp_path, READY_POST)
        fm, body = parse_frontmatter(f)
        assert fm["platform"] == "linkedin"
        assert fm["status"] == "ready"
        assert "Test post content" in body

    def test_write_frontmatter_roundtrip(self, tmp_path):
        f = make_post_file(tmp_path, READY_POST)
        fm, body = parse_frontmatter(f)
        fm["status"] = "scheduled"
        fm["ghl_post_id"] = "test_123"
        write_frontmatter(f, fm, body)

        fm2, body2 = parse_frontmatter(f)
        assert fm2["status"] == "scheduled"
        assert fm2["ghl_post_id"] == "test_123"
        assert "Test post content" in body2


# ---------------------------------------------------------------------------
# process_post — skip logic
# ---------------------------------------------------------------------------

class TestSkipDraft:
    def test_draft_post_is_skipped(self, tmp_path):
        brand_path = make_brand_file(tmp_path)
        brand_cfg = load_brand_config(brand_path)
        adapter = MagicMock()
        post_file = make_post_file(tmp_path, DRAFT_POST)

        result = process_post(post_file, adapter, brand_cfg, dry_run=False)

        assert result == "skipped"
        adapter.publish.assert_not_called()


class TestSkipAlreadyPublished:
    def test_ready_post_with_ghl_post_id_is_skipped(self, tmp_path):
        brand_path = make_brand_file(tmp_path)
        brand_cfg = load_brand_config(brand_path)
        adapter = MagicMock()
        post_file = make_post_file(tmp_path, ALREADY_PUBLISHED_POST)

        result = process_post(post_file, adapter, brand_cfg, dry_run=False)

        assert result == "skipped"
        adapter.publish.assert_not_called()


# ---------------------------------------------------------------------------
# process_post — publish logic
# ---------------------------------------------------------------------------

class TestPublishReady:
    def test_ready_post_calls_publish(self, tmp_path):
        brand_path = make_brand_file(tmp_path)
        brand_cfg = load_brand_config(brand_path)
        adapter = MagicMock()
        adapter.publish.return_value = "ghl_new_post_456"
        post_file = make_post_file(tmp_path, READY_POST)

        result = process_post(post_file, adapter, brand_cfg, dry_run=False)

        assert result == "scheduled"
        adapter.publish.assert_called_once()


class TestDryRun:
    def test_dry_run_does_not_call_publish(self, tmp_path):
        brand_path = make_brand_file(tmp_path)
        brand_cfg = load_brand_config(brand_path)
        adapter = MagicMock()
        post_file = make_post_file(tmp_path, READY_POST)

        result = process_post(post_file, adapter, brand_cfg, dry_run=True)

        assert result == "scheduled"
        adapter.publish.assert_not_called()


# ---------------------------------------------------------------------------
# Frontmatter update after publish
# ---------------------------------------------------------------------------

class TestFrontmatterUpdate:
    def test_frontmatter_updated_after_publish(self, tmp_path):
        brand_path = make_brand_file(tmp_path)
        brand_cfg = load_brand_config(brand_path)
        adapter = MagicMock()
        adapter.publish.return_value = "ghl_new_post_789"
        post_file = make_post_file(tmp_path, READY_POST)

        process_post(post_file, adapter, brand_cfg, dry_run=False)

        fm, body = parse_frontmatter(post_file)
        assert fm["status"] == "scheduled"
        assert fm["ghl_post_id"] == "ghl_new_post_789"
        assert "published_at" in fm
        assert "Test post content" in body
