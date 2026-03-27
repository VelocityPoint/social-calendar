"""
tests/test_publisher_ghl_mode.py -- Unit tests for publisher.py --mode ghl (Step 5)

Tests cover:
  - run_ghl_publisher: skip non-ready, process ready, write status back
  - Success path: status=scheduled (future), status=published (past)
  - Failure path: status=failed, error field written
  - Dry run: no API calls, no file writes
  - File filtering: --files arg, git diff fallback
  - get_changed_files_from_git: parse git output

Ref: AC7 (GHL publisher integration), AC6 (status write-back)
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, call

import pytest
import yaml

# We'll import after patching where needed
# from publisher.publisher import run_ghl_publisher, get_changed_files_from_git
# from publisher.state import write_ghl_post_result, parse_post_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FUTURE_PUBLISH_AT = (datetime.now(timezone.utc) + timedelta(days=3)).strftime(
    "%Y-%m-%dT%H:%M:%S+00:00"
)
PAST_PUBLISH_AT = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
    "%Y-%m-%dT%H:%M:%S+00:00"
)


def make_post_md(
    status: str = "ready",
    platform: str = "linkedin",
    publish_at: str = FUTURE_PUBLISH_AT,
    author: str = "dave",
    include_ghl_post_id: bool = False,
) -> str:
    """Generate minimal valid post markdown."""
    ghl_post_id_line = f'ghl_post_id: "existing-id"\n' if include_ghl_post_id else ""
    return textwrap.dedent(f"""\
        ---
        id: 2026-04-01-linkedin-test
        publish_at: "{publish_at}"
        platforms:
          - {platform}
        status: {status}
        brand: secondring
        author: {author}
        {ghl_post_id_line}---

        Test post body content for {platform}.
        """)


def make_brand_yaml(with_ghl: bool = True) -> dict:
    """Return brand dict with optional GHL config."""
    base = {
        "brand_name": "Second Ring",
        "credentials": {
            "facebook": "kv-fb",
            "linkedin": "kv-li",
            "instagram": "kv-fb",
            "gbp": "kv-gbp",
            "x": "kv-x",
        },
        "cadence": {
            "linkedin": {"posts_per_week": 3, "preferred_times": ["09:00"]},
        },
        "pillars": ["AI answering"],
    }
    if with_ghl:
        base["ghl"] = {
            "location_id": "test-loc-id",
            "accounts": {
                "dave": {
                    "linkedin": "acc-linkedin-123",
                    "facebook": "acc-facebook-456",
                }
            },
        }
    return base


# ---------------------------------------------------------------------------
# state.write_ghl_post_result tests
# ---------------------------------------------------------------------------

class TestWriteGhlPostResult:
    """Unit tests for state.write_ghl_post_result()."""

    def test_writes_scheduled_status(self, tmp_path):
        from publisher.state import write_ghl_post_result, parse_post_file

        post_file = tmp_path / "test.md"
        post_file.write_text(make_post_md(status="ready"))

        result = write_ghl_post_result(
            post_file,
            status="scheduled",
            ghl_post_id="ghl-abc-123",
        )

        assert result is True
        content = post_file.read_text()
        fm_yaml = content.split("---")[1]
        fm = yaml.safe_load(fm_yaml)
        assert fm["status"] == "scheduled"
        assert fm["ghl_post_id"] == "ghl-abc-123"
        assert "error" not in fm

    def test_writes_published_status_with_timestamp(self, tmp_path):
        from publisher.state import write_ghl_post_result

        post_file = tmp_path / "test.md"
        post_file.write_text(make_post_md(status="ready"))

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = write_ghl_post_result(
            post_file,
            status="published",
            ghl_post_id="ghl-xyz-789",
            published_at=now_str,
        )

        assert result is True
        fm = yaml.safe_load(post_file.read_text().split("---")[1])
        assert fm["status"] == "published"
        assert fm["ghl_post_id"] == "ghl-xyz-789"
        assert fm["published_at"] == now_str

    def test_writes_failed_status_with_error(self, tmp_path):
        from publisher.state import write_ghl_post_result

        post_file = tmp_path / "test.md"
        post_file.write_text(make_post_md(status="ready"))

        result = write_ghl_post_result(
            post_file,
            status="failed",
            error="GHL 429: Rate limit exceeded",
        )

        assert result is True
        fm = yaml.safe_load(post_file.read_text().split("---")[1])
        assert fm["status"] == "failed"
        assert "GHL 429" in fm["error"]

    def test_clears_error_on_success(self, tmp_path):
        from publisher.state import write_ghl_post_result

        # Post previously failed
        post_content = make_post_md(status="ready").replace(
            "---\n\nTest", '---\n\nTest'
        )
        post_file = tmp_path / "test.md"
        post_file.write_text(post_content)
        # First write a failure
        write_ghl_post_result(post_file, status="failed", error="previous error")
        # Now succeed
        write_ghl_post_result(post_file, status="scheduled", ghl_post_id="new-id")

        fm = yaml.safe_load(post_file.read_text().split("---")[1])
        assert fm["status"] == "scheduled"
        assert "error" not in fm or fm.get("error") is None

    def test_preserves_body(self, tmp_path):
        from publisher.state import write_ghl_post_result

        original = make_post_md(status="ready")
        post_file = tmp_path / "test.md"
        post_file.write_text(original)

        write_ghl_post_result(post_file, status="scheduled", ghl_post_id="id-1")

        content = post_file.read_text()
        # Body after second "---" delimiter should be preserved
        parts = content.split("---\n", 2)
        assert "Test post body content" in parts[-1]

    def test_returns_false_for_missing_file(self, tmp_path):
        from publisher.state import write_ghl_post_result

        result = write_ghl_post_result(
            tmp_path / "nonexistent.md",
            status="scheduled",
            ghl_post_id="id-1",
        )
        assert result is False

    def test_returns_false_for_no_frontmatter(self, tmp_path):
        from publisher.state import write_ghl_post_result

        post_file = tmp_path / "test.md"
        post_file.write_text("No frontmatter here\n\nJust body.")

        result = write_ghl_post_result(post_file, status="scheduled", ghl_post_id="id-1")
        assert result is False


# ---------------------------------------------------------------------------
# run_ghl_publisher tests
# ---------------------------------------------------------------------------

class TestRunGhlPublisher:
    """Integration-style tests for run_ghl_publisher() with mocked adapter."""

    def _make_brand_and_post(self, tmp_path, post_status="ready", publish_at=None):
        """Set up a minimal brands/<slug>/brand.yaml + post file."""
        publish_at = publish_at or FUTURE_PUBLISH_AT
        brand_dir = tmp_path / "brands" / "secondring"
        brand_dir.mkdir(parents=True)
        (brand_dir / "brand.yaml").write_text(
            yaml.dump(make_brand_yaml(with_ghl=True))
        )
        post_dir = brand_dir / "calendar" / "2026" / "04"
        post_dir.mkdir(parents=True)
        post_file = post_dir / "2026-04-01-linkedin-test.md"
        post_file.write_text(make_post_md(status=post_status, publish_at=publish_at))
        return brand_dir, post_file

    def test_skips_draft_posts(self, tmp_path):
        """Posts with status != ready are skipped."""
        brand_dir, post_file = self._make_brand_and_post(tmp_path, post_status="draft")

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path), \
             patch("publisher.adapters.ghl.GHLAdapter.publish") as mock_publish:

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[post_file])

        mock_publish.assert_not_called()
        assert stats["skipped"] == 1
        assert stats["published"] == 0

    def test_skips_scheduled_posts(self, tmp_path):
        """Posts already in 'scheduled' status are skipped (idempotency)."""
        brand_dir, post_file = self._make_brand_and_post(tmp_path, post_status="scheduled")

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path), \
             patch("publisher.adapters.ghl.GHLAdapter.publish") as mock_publish:

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[post_file])

        mock_publish.assert_not_called()
        assert stats["skipped"] == 1

    def test_publishes_ready_post_future_scheduled(self, tmp_path):
        """Ready post with future publish_at → status=scheduled after publish."""
        brand_dir, post_file = self._make_brand_and_post(
            tmp_path, post_status="ready", publish_at=FUTURE_PUBLISH_AT
        )

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path), \
             patch("publisher.retry.publish_with_retry", return_value="ghl-post-future"):

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[post_file])

        assert stats["published"] == 1
        assert stats["failed"] == 0
        fm = yaml.safe_load(post_file.read_text().split("---")[1])
        assert fm["status"] == "scheduled"
        assert fm["ghl_post_id"] == "ghl-post-future"

    def test_publishes_ready_post_immediate(self, tmp_path):
        """Ready post with past publish_at → status=published after publish."""
        brand_dir, post_file = self._make_brand_and_post(
            tmp_path, post_status="ready", publish_at=PAST_PUBLISH_AT
        )

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path), \
             patch("publisher.retry.publish_with_retry", return_value="ghl-post-now"):

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[post_file])

        assert stats["published"] == 1
        fm = yaml.safe_load(post_file.read_text().split("---")[1])
        assert fm["status"] == "published"
        assert fm["ghl_post_id"] == "ghl-post-now"
        assert "published_at" in fm

    def test_writes_failed_on_publish_error(self, tmp_path):
        """When publish_with_retry returns None, writes status=failed."""
        brand_dir, post_file = self._make_brand_and_post(tmp_path, post_status="ready")

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path), \
             patch("publisher.retry.publish_with_retry", return_value=None):

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[post_file])

        assert stats["failed"] == 1
        assert stats["published"] == 0
        fm = yaml.safe_load(post_file.read_text().split("---")[1])
        assert fm["status"] == "failed"
        assert fm.get("error")  # error field populated

    def test_dry_run_no_writes(self, tmp_path):
        """Dry run: no GHL API call, no file writes."""
        brand_dir, post_file = self._make_brand_and_post(tmp_path, post_status="ready")
        original_content = post_file.read_text()

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path), \
             patch("publisher.retry.publish_with_retry") as mock_retry:

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[post_file], dry_run=True)

        mock_retry.assert_not_called()
        assert stats["published"] == 1  # Counted as "would publish"
        assert post_file.read_text() == original_content  # No mutation

    def test_skips_missing_file(self, tmp_path):
        """Files that don't exist are skipped gracefully."""
        brand_dir, _ = self._make_brand_and_post(tmp_path)
        ghost_file = tmp_path / "brands" / "secondring" / "calendar" / "2026" / "04" / "ghost.md"

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path):

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[ghost_file])

        assert stats["skipped"] == 1

    def test_no_ghl_config_returns_early(self, tmp_path):
        """If brand.yaml has no ghl: block, publisher exits early without error."""
        brand_dir = tmp_path / "brands" / "secondring"
        brand_dir.mkdir(parents=True)
        (brand_dir / "brand.yaml").write_text(yaml.dump(make_brand_yaml(with_ghl=False)))

        with patch("publisher.publisher.BRANDS_DIR", tmp_path / "brands"), \
             patch("publisher.publisher.REPO_ROOT", tmp_path):

            from publisher.publisher import run_ghl_publisher
            stats = run_ghl_publisher("secondring", files=[])

        assert stats["published"] == 0
        assert stats["failed"] == 0


# ---------------------------------------------------------------------------
# get_changed_files_from_git tests
# ---------------------------------------------------------------------------

class TestGetChangedFilesFromGit:
    """Unit tests for get_changed_files_from_git()."""

    def test_returns_existing_files(self, tmp_path):
        """Returns Path objects for files that exist."""
        post_file = tmp_path / "brands" / "secondring" / "calendar" / "2026" / "04" / "post.md"
        post_file.parent.mkdir(parents=True)
        post_file.write_text("---\n---\n")

        mock_result = MagicMock()
        mock_result.stdout = "brands/secondring/calendar/2026/04/post.md\n"

        with patch("publisher.publisher.subprocess.run", return_value=mock_result), \
             patch("publisher.publisher.REPO_ROOT", tmp_path):

            from publisher.publisher import get_changed_files_from_git
            files = get_changed_files_from_git(tmp_path)

        assert len(files) == 1
        assert files[0] == post_file

    def test_skips_nonexistent_files(self, tmp_path):
        """Files listed by git diff but not on disk are excluded."""
        mock_result = MagicMock()
        mock_result.stdout = "brands/secondring/calendar/2026/04/missing.md\n"

        with patch("publisher.publisher.subprocess.run", return_value=mock_result), \
             patch("publisher.publisher.REPO_ROOT", tmp_path):

            from publisher.publisher import get_changed_files_from_git
            files = get_changed_files_from_git(tmp_path)

        assert files == []

    def test_returns_empty_on_git_error(self, tmp_path):
        """CalledProcessError is caught, returns empty list."""
        import subprocess

        with patch("publisher.publisher.subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "git", stderr="fatal")), \
             patch("publisher.publisher.REPO_ROOT", tmp_path):

            from publisher.publisher import get_changed_files_from_git
            files = get_changed_files_from_git(tmp_path)

        assert files == []
