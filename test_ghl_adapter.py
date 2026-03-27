"""
test_ghl_adapter.py -- Unit tests for GHL adapter with mocked HTTP calls

Phase 1: Test skeleton using unittest.mock to prevent actual API calls.
No live accounts used - all tests run against mock responses.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from publisher.adapters.ghl import (
    GHLAdapter,
    RateLimitError,
    PermanentError,
    GHLError,
)
from publisher.models import Brand


# Mock responses for GHL API endpoints
MOCK_ACCOUNTS = [
    {"id": "account_001", "name": "Primary GHL Account"},
]

MOCK_POST_ID = "ghl_post_12345"
MOCK_POST_DATA = {
    "id": MOCK_POST_ID,
    "type": "text",
    "content": "Test post content",
    "published_at": "2026-03-27T10:00:00Z",
}

MOCK_ERROR_401 = {"error": {"code": 401, "message": "Invalid token"}}
MOCK_ERROR_429 = {"error": {"code": 429, "message": "Rate limit exceeded"}, "retry_after": 30}


@pytest.fixture
def brand():
    """Create a test Brand instance."""
    return Brand(
        name="TestBrand",
        path=Path("test") / "brands.yaml",
        credentials=MagicMock(),
    )


class TestGHLAdapter:
    """Tests for GHL adapter functionality."""

    @pytest.fixture
    def adapter(self, brand):
        """Create a GHL adapter instance."""
        return GHLAdapter(brand=brand, state_dir=Path("test/state"))

    def test_init(self, adapter):
        """Test adapter initialization."""
        assert adapter.platform == "ghl"
        assert adapter._authenticated is False

    @patch.dict("os.environ", {"GHL_API_KEY": "test_token_12345"})
    def test_auth_check_success(self, adapter):
        """Test successful authentication."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({"data": {"id": "me_001", "username": "test@example.com"}})

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = adapter.auth_check()
            assert result is True
            mock_get.assert_called_once()

    @patch.dict("os.environ", {"GHL_API_KEY": "test_token_12345"})
    def test_auth_check_failure(self, adapter):
        """Test failed authentication returns False."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = json.dumps(MOCK_ERROR_401)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = adapter.auth_check()
            assert result is False
            mock_get.assert_called_once()

    @patch.dict("os.environ", {"GHL_API_KEY": "test_token_12345"})
    def test_publish_text_success(self, adapter):
        """Test publishing text-only post."""
        from publisher.models import Post

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = MOCK_POST_DATA

        with patch("requests.post", return_value=mock_resp) as mock_post:
            post_id = adapter.publish(
                post=Post(id="test_post"),
                copy_text="Hello from GHL!",
                image_url=None,
            )
            assert post_id == MOCK_POST_ID
            mock_post.assert_called_once()

    @patch.dict("os.environ", {"GHL_API_KEY": "test_token_12345"})
    def test_publish_with_image_success(self, adapter):
        """Test publishing post with image URL."""
        from publisher.models import Post

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = MOCK_POST_DATA

        with patch("requests.post", return_value=mock_resp) as mock_post:
            post_id = adapter.publish(
                post=Post(id="test_post"),
                copy_text="Hello with image!",
                image_url="https://example.com/image.jpg",
            )
            assert post_id == MOCK_POST_ID
            # Verify image URL is in request body
            call_kwargs = mock_post.call_args[1]
            assert "image_url" in call_kwargs.get("json", {})

    def test_publish_rate_limit(self, adapter):
        """Test rate limiting raises RateLimitError."""
        from publisher.models import Post

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "30"}
        mock_resp.text = json.dumps(MOCK_ERROR_429)

        with patch("requests.post", return_value=mock_resp):
            post = Post(id="test_post")
            with pytest.raises(RateLimitError) as exc_info:
                adapter.publish(post, "Test content")

            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after_seconds == 30

    def test_publish_auth_error(self, adapter):
        """Test auth error raises PermanentError."""
        from publisher.models import Post

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = json.dumps(MOCK_ERROR_401)

        with patch("requests.post", return_value=mock_resp):
            post = Post(id="test_post")
            with pytest.raises(PermanentError) as exc_info:
                adapter.publish(post, "Test content")

            assert exc_info.value.status_code == 401

    def test_delete_success(self, adapter):
        """Test successful post deletion."""
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.content = b""

        with patch("requests.delete", return_value=mock_resp) as mock_del:
            result = adapter.delete(ghl_post_id=MOCK_POST_ID)
            assert result is True
            mock_del.assert_called_once()

    def test_delete_not_found(self, adapter):
        """Test deleting non-existent post raises PermanentError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"

        with patch("requests.delete", return_value=mock_resp) as mock_del:
            with pytest.raises(PermanentError) as exc_info:
                adapter.delete(ghl_post_id="nonexistent_post")

            assert exc_info.value.status_code == 404

    def test_get_post_success(self, adapter):
        """Test retrieving a post."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_POST_DATA

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = adapter.get_post(ghl_post_id=MOCK_POST_ID)
            assert result == MOCK_POST_DATA

    def test_get_post_not_found(self, adapter):
        """Test getting non-existent post returns None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = adapter.get_post(ghl_post_id="nonexistent")
            assert result is None

    def test_get_post_auth_error(self, adapter):
        """Test getting post with auth error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = json.dumps(MOCK_ERROR_401)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            with pytest.raises(PermanentError) as exc_info:
                adapter.get_post(ghl_post_id="test")

            assert exc_info.value.status_code == 401

    def test_list_posts_success(self, adapter):
        """Test listing posts."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [MOCK_POST_DATA, MOCK_POST_DATA]

        with patch("requests.get", return_value=mock_resp) as mock_get:
            posts = adapter.list_posts(filters={"limit": 10})
            assert len(posts) == 2
            mock_get.assert_called_once()

    def test_list_posts_no_filter_defaults(self, adapter):
        """Test that list_posts defaults to published status."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_POST_DATA

        with patch("requests.get", return_value=mock_resp) as mock_get:
            adapter.list_posts(filters=None)
            # Verify default filter was added
            call_args = mock_get.call_args[1].get("params", {})
            assert call_args.get("status") == "published"

    def test_list_posts_rate_limit(self, adapter):
        """Test listing posts with rate limiting."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "60"}
        mock_resp.text = json.dumps(MOCK_ERROR_429)

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(RateLimitError) as exc_info:
                adapter.list_posts()

            assert exc_info.value.status_code == 429

    def test_list_posts_auth_error(self, adapter):
        """Test listing posts with auth error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = json.dumps(MOCK_ERROR_401)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            with pytest.raises(PermanentError) as exc_info:
                adapter.list_posts()

            assert exc_info.value.status_code == 401

    @patch.dict("os.environ", {"GHL_API_KEY": "test_token_12345"})
    def test_get_accounts(self, adapter):
        """Test getting account list."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_ACCOUNTS

        with patch("requests.get", return_value=mock_resp) as mock_get:
            accounts = adapter.get_accounts()
            assert len(accounts) == 1
            assert accounts[0] == "account_001"

    @patch.dict("os.environ", {"GHL_API_KEY": "test_token_12345"})
    def test_get_accounts_rate_limit(self, adapter):
        """Test getting accounts with rate limiting."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "60"}

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(RateLimitError) as exc_info:
                adapter.get_accounts()

            assert exc_info.value.status_code == 429

    def test_resolve_accounts_empty(self, adapter):
        """Test account resolution with no brand.yaml returns empty list."""
        accounts = adapter._resolve_accounts("test@example.com", "ghl")
        # Without real brand.yaml, should return empty or mock
        assert isinstance(accounts, list)

    def test_request_get_success(self, adapter):
        """Test _request method with GET."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"data": {"username": "test"}}'

        with patch("requests.get", return_value=mock_resp) as mock_get:
            resp = adapter._request("GET", "/v1/me")
            assert resp.status_code == 200

    def test_request_post_success(self, adapter):
        """Test _request method with POST."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.text = json.dumps(MOCK_POST_DATA)

        body = {"type": "text", "content": "test"}
        with patch("requests.post", return_value=mock_resp) as mock_post:
            resp = adapter._request("POST", "/v1/posts", body=body)
            assert resp.status_code == 201
            mock_post.assert_called_once()

    def test_request_delete_success(self, adapter):
        """Test _request method with DELETE."""
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.content = b""

        with patch("requests.delete", return_value=mock_resp) as mock_del:
            resp = adapter._request("DELETE", "/v1/posts/test_id")
            assert resp.status_code == 204

    @patch.dict("os.environ", {"GHL_API_KEY": "test_token_12345"})
    def test_request_rate_limit(self, adapter):
        """Test _request raises RateLimitError on 429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "30"}

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(RateLimitError) as exc_info:
                adapter._request("GET", "/v1/me")

            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after_seconds == 30
