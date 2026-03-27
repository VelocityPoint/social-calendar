"""
tests/test_ghl_adapter.py -- Unit tests for GHL Social Planner adapter

All tests use mocked HTTP calls — no live accounts, no real API calls.
Tests verify correct API paths, payload shapes, error propagation, and
auth behaviour per the design spec in issue #2.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

from publisher.adapters.ghl import GHLAdapter, GHLError, BASE_URL, API_VERSION
from publisher.models import Brand, BrandCredentials, BrandCadence, Post
from publisher.retry import RateLimitError, PermanentError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LOCATION_ID = "loc_test_abc123"
API_KEY = "test_api_key_xyz"

ACCOUNT_MAP = {
    "dave": {
        "linkedin": "acc_li_001",
        "facebook": "acc_fb_002",
        "instagram": "acc_ig_003",
        "google_business": "acc_gb_004",
    }
}

MOCK_ACCOUNTS = [
    {"id": "acc_li_001", "platform": "linkedin", "name": "Dave - LinkedIn"},
    {"id": "acc_fb_002", "platform": "facebook", "name": "Dave - Facebook"},
]

MOCK_POST_ID = "ghl_post_abc123"
MOCK_POST_DATA = {
    "id": MOCK_POST_ID,
    "content": "Test post content",
    "scheduledAt": "2026-04-01T14:00:00-07:00",
    "status": "scheduled",
}

MOCK_ERROR_401 = {"error": {"code": 401, "message": "Invalid token"}}
MOCK_ERROR_429 = {"error": {"code": 429, "message": "Rate limit exceeded"}}


def make_brand() -> Brand:
    return Brand(
        brand_name="TestBrand",
        credentials=BrandCredentials(),
        cadence={},
        pillars=[],
        slug="testbrand",
    )


def make_adapter(location_id=LOCATION_ID, api_key=API_KEY) -> GHLAdapter:
    brand = make_brand()
    adapter = GHLAdapter(brand=brand, state_dir=Path("test/state"))
    adapter.location_id = location_id
    adapter.api_key = api_key
    adapter.account_map = ACCOUNT_MAP
    return adapter


def make_post(
    author="dave",
    platform="linkedin",
    publish_at="2026-04-01T14:00:00-07:00",
) -> Post:
    return Post(
        id="2026-04-01-linkedin-test",
        publish_at=publish_at,
        platforms=[platform],
        status="scheduled",
        brand="testbrand",
        author=author,
    )


def mock_response(status_code: int, body=None, headers=None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = json.dumps(body).encode() if body is not None else b""
    resp.text = json.dumps(body) if body is not None else ""
    resp.headers = headers or {}
    resp.json = MagicMock(return_value=body)
    return resp


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestGHLAdapterInit:
    def test_platform_attribute(self):
        adapter = make_adapter()
        assert adapter.platform == "ghl"

    def test_location_and_api_key_stored(self):
        adapter = make_adapter()
        assert adapter.location_id == LOCATION_ID
        assert adapter.api_key == API_KEY

    def test_account_map_stored(self):
        adapter = make_adapter()
        assert adapter.account_map == ACCOUNT_MAP


# ---------------------------------------------------------------------------
# _request — correct headers and URL construction
# ---------------------------------------------------------------------------

class TestRequest:
    def test_correct_bearer_header(self):
        adapter = make_adapter()
        resp = mock_response(200, {})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter._request("GET", f"/social-media-posting/{LOCATION_ID}/accounts")
            _, kwargs = mock_req.call_args
            headers = kwargs.get("headers") or mock_req.call_args[0][2] if len(mock_req.call_args[0]) > 2 else {}
            # headers passed as keyword
            actual_headers = mock_req.call_args.kwargs.get("headers", {})
            assert actual_headers.get("Authorization") == f"Bearer {API_KEY}"

    def test_version_header(self):
        adapter = make_adapter()
        resp = mock_response(200, {})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter._request("GET", f"/social-media-posting/{LOCATION_ID}/accounts")
            actual_headers = mock_req.call_args.kwargs.get("headers", {})
            assert actual_headers.get("Version") == API_VERSION

    def test_full_url_constructed(self):
        adapter = make_adapter()
        path = f"/social-media-posting/{LOCATION_ID}/accounts"
        resp = mock_response(200, {})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter._request("GET", path)
            args = mock_req.call_args[0]
            assert args[1] == f"{BASE_URL}{path}"

    def test_raises_rate_limit_error_on_429(self):
        adapter = make_adapter()
        resp = mock_response(429, MOCK_ERROR_429, headers={"Retry-After": "45"})
        with patch("requests.request", return_value=resp):
            with pytest.raises(RateLimitError) as exc:
                adapter._request("GET", "/social-media-posting/loc/accounts")
            assert exc.value.retry_after == 45

    def test_raises_permanent_error_on_401(self):
        adapter = make_adapter()
        resp = mock_response(401, MOCK_ERROR_401)
        with patch("requests.request", return_value=resp):
            with pytest.raises(PermanentError) as exc:
                adapter._request("GET", "/social-media-posting/loc/accounts")
            assert exc.value.status_code == 401

    def test_raises_permanent_error_on_400(self):
        adapter = make_adapter()
        resp = mock_response(400, {"error": "bad request"})
        with patch("requests.request", return_value=resp):
            with pytest.raises(PermanentError) as exc:
                adapter._request("POST", "/social-media-posting/loc/posts", {})
            assert exc.value.status_code == 400

    def test_raises_ghl_error_on_500(self):
        adapter = make_adapter()
        resp = mock_response(500, {"error": "internal server error"})
        with patch("requests.request", return_value=resp):
            with pytest.raises(GHLError) as exc:
                adapter._request("POST", "/social-media-posting/loc/posts", {})
            assert exc.value.status_code == 500

    def test_network_error_raises_publish_error(self):
        from publisher.retry import PublishError
        import requests as req_lib
        adapter = make_adapter()
        with patch("requests.request", side_effect=req_lib.exceptions.ConnectionError("refused")):
            with pytest.raises(PublishError):
                adapter._request("GET", "/social-media-posting/loc/accounts")


# ---------------------------------------------------------------------------
# publish — correct path, payload, and return value
# ---------------------------------------------------------------------------

class TestPublish:
    """patch check_rate_limit/increment_rate_limit to bypass RateLimitState (pre-existing Pydantic v2 issue in models.py)."""

    def test_correct_api_path(self):
        adapter = make_adapter()
        post = make_post()
        resp = mock_response(200, {"id": MOCK_POST_ID})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch.object(adapter, "increment_rate_limit"), \
             patch("requests.request", return_value=resp) as mock_req:
            adapter.publish(post, "Hello LinkedIn!")
            args = mock_req.call_args[0]
            assert args[1] == f"{BASE_URL}/social-media-posting/{LOCATION_ID}/posts"

    def test_payload_contains_account_ids(self):
        adapter = make_adapter()
        post = make_post(author="dave", platform="linkedin")
        resp = mock_response(200, {"id": MOCK_POST_ID})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch.object(adapter, "increment_rate_limit"), \
             patch("requests.request", return_value=resp) as mock_req:
            adapter.publish(post, "Hello LinkedIn!")
            body = mock_req.call_args.kwargs.get("json", {})
            assert "accountIds" in body
            assert body["accountIds"] == ["acc_li_001"]

    def test_payload_contains_scheduled_at(self):
        adapter = make_adapter()
        post = make_post(publish_at="2026-04-01T14:00:00-07:00")
        resp = mock_response(200, {"id": MOCK_POST_ID})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch.object(adapter, "increment_rate_limit"), \
             patch("requests.request", return_value=resp) as mock_req:
            adapter.publish(post, "Test content")
            body = mock_req.call_args.kwargs.get("json", {})
            assert "scheduledAt" in body
            assert body["scheduledAt"] == "2026-04-01T14:00:00-07:00"

    def test_payload_contains_content(self):
        adapter = make_adapter()
        post = make_post()
        resp = mock_response(200, {"id": MOCK_POST_ID})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch.object(adapter, "increment_rate_limit"), \
             patch("requests.request", return_value=resp) as mock_req:
            adapter.publish(post, "My post content")
            body = mock_req.call_args.kwargs.get("json", {})
            assert body["content"] == "My post content"

    def test_text_post_type(self):
        adapter = make_adapter()
        post = make_post()
        resp = mock_response(200, {"id": MOCK_POST_ID})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch.object(adapter, "increment_rate_limit"), \
             patch("requests.request", return_value=resp) as mock_req:
            adapter.publish(post, "Text only post")
            body = mock_req.call_args.kwargs.get("json", {})
            assert body["type"] == "text"
            assert "mediaUrls" not in body

    def test_image_post_adds_media_urls(self):
        from publisher.models import CreativeAsset
        adapter = make_adapter()
        post = make_post()
        post.creative = [CreativeAsset(type="image", url="https://cdn.example.com/hero.jpg")]
        resp = mock_response(200, {"id": MOCK_POST_ID})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch.object(adapter, "increment_rate_limit"), \
             patch("requests.request", return_value=resp) as mock_req:
            adapter.publish(post, "Post with image")
            body = mock_req.call_args.kwargs.get("json", {})
            assert body["type"] == "image"
            assert body["mediaUrls"] == ["https://cdn.example.com/hero.jpg"]

    def test_returns_post_id_string(self):
        adapter = make_adapter()
        post = make_post()
        resp = mock_response(200, {"id": MOCK_POST_ID})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch.object(adapter, "increment_rate_limit"), \
             patch("requests.request", return_value=resp):
            result = adapter.publish(post, "Test content")
            assert result == MOCK_POST_ID

    def test_raises_permanent_error_on_unknown_author(self):
        adapter = make_adapter()
        post = make_post(author="unknown_author")
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             pytest.raises(PermanentError) as exc:
            adapter.publish(post, "Test")
        assert "unknown_author" in str(exc.value).lower() or "Unknown author" in str(exc.value)

    def test_raises_permanent_error_on_missing_platform(self):
        """author exists but platform not in their account_map."""
        adapter = make_adapter()
        # Remove instagram from dave's map to force the error
        adapter.account_map = {"dave": {"linkedin": "acc_li_001"}}
        post = make_post(author="dave", platform="instagram")
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             pytest.raises(PermanentError):
            adapter.publish(post, "Test")

    def test_raises_rate_limit_error_on_429(self):
        adapter = make_adapter()
        post = make_post()
        resp = mock_response(429, MOCK_ERROR_429, headers={"Retry-After": "30"})
        with patch.object(adapter, "check_rate_limit", return_value=True), \
             patch("requests.request", return_value=resp):
            with pytest.raises(RateLimitError) as exc:
                adapter.publish(post, "Test")
            assert exc.value.retry_after == 30

    def test_no_mock_mode_flag(self):
        """GHL_MOCK_MODE must not appear in publish logic."""
        import inspect
        from publisher.adapters import ghl as ghl_module
        source = inspect.getsource(ghl_module)
        assert "GHL_MOCK_MODE" not in source


# ---------------------------------------------------------------------------
# delete — correct path
# ---------------------------------------------------------------------------

class TestDelete:
    def test_correct_api_path(self):
        adapter = make_adapter()
        resp = mock_response(204)
        with patch("requests.request", return_value=resp) as mock_req:
            adapter.delete(MOCK_POST_ID)
            args = mock_req.call_args[0]
            assert args[1] == f"{BASE_URL}/social-media-posting/{LOCATION_ID}/posts/{MOCK_POST_ID}"
            assert args[0] == "DELETE"

    def test_returns_true_on_success(self):
        adapter = make_adapter()
        resp = mock_response(204)
        with patch("requests.request", return_value=resp):
            assert adapter.delete(MOCK_POST_ID) is True

    def test_raises_permanent_error_on_404(self):
        adapter = make_adapter()
        resp = mock_response(404, {"error": "not found"})
        with patch("requests.request", return_value=resp):
            with pytest.raises(PermanentError):
                adapter.delete("nonexistent_id")


# ---------------------------------------------------------------------------
# get_post — correct path
# ---------------------------------------------------------------------------

class TestGetPost:
    def test_correct_api_path(self):
        adapter = make_adapter()
        resp = mock_response(200, MOCK_POST_DATA)
        with patch("requests.request", return_value=resp) as mock_req:
            adapter.get_post(MOCK_POST_ID)
            args = mock_req.call_args[0]
            assert args[1] == f"{BASE_URL}/social-media-posting/{LOCATION_ID}/posts/{MOCK_POST_ID}"

    def test_returns_post_data(self):
        adapter = make_adapter()
        resp = mock_response(200, MOCK_POST_DATA)
        with patch("requests.request", return_value=resp):
            result = adapter.get_post(MOCK_POST_ID)
            assert result == MOCK_POST_DATA

    def test_returns_none_on_404(self):
        adapter = make_adapter()
        resp = mock_response(404, {"error": "not found"})
        with patch("requests.request", return_value=resp):
            result = adapter.get_post("nonexistent_id")
            assert result is None


# ---------------------------------------------------------------------------
# list_posts — must use POST with body filters
# ---------------------------------------------------------------------------

class TestListPosts:
    def test_uses_post_method(self):
        adapter = make_adapter()
        resp = mock_response(200, {"posts": [MOCK_POST_DATA]})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter.list_posts()
            args = mock_req.call_args[0]
            assert args[0] == "POST"

    def test_correct_api_path(self):
        adapter = make_adapter()
        resp = mock_response(200, {"posts": [MOCK_POST_DATA]})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter.list_posts()
            args = mock_req.call_args[0]
            assert args[1] == f"{BASE_URL}/social-media-posting/{LOCATION_ID}/posts/list"

    def test_filters_sent_as_body(self):
        adapter = make_adapter()
        filters = {"status": "scheduled", "limit": 20}
        resp = mock_response(200, {"posts": []})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter.list_posts(filters=filters)
            body = mock_req.call_args.kwargs.get("json", {})
            assert body == filters

    def test_empty_body_when_no_filters(self):
        adapter = make_adapter()
        resp = mock_response(200, {"posts": []})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter.list_posts()
            body = mock_req.call_args.kwargs.get("json", {})
            assert body == {}

    def test_returns_list_of_posts(self):
        adapter = make_adapter()
        resp = mock_response(200, {"posts": [MOCK_POST_DATA, MOCK_POST_DATA]})
        with patch("requests.request", return_value=resp):
            result = adapter.list_posts()
            assert isinstance(result, list)
            assert len(result) == 2

    def test_raises_rate_limit_error_on_429(self):
        adapter = make_adapter()
        resp = mock_response(429, MOCK_ERROR_429, headers={"Retry-After": "60"})
        with patch("requests.request", return_value=resp):
            with pytest.raises(RateLimitError):
                adapter.list_posts()


# ---------------------------------------------------------------------------
# get_accounts — correct path
# ---------------------------------------------------------------------------

class TestGetAccounts:
    def test_correct_api_path(self):
        adapter = make_adapter()
        resp = mock_response(200, {"accounts": MOCK_ACCOUNTS})
        with patch("requests.request", return_value=resp) as mock_req:
            adapter.get_accounts()
            args = mock_req.call_args[0]
            assert args[1] == f"{BASE_URL}/social-media-posting/{LOCATION_ID}/accounts"
            assert args[0] == "GET"

    def test_returns_accounts_list(self):
        adapter = make_adapter()
        resp = mock_response(200, {"accounts": MOCK_ACCOUNTS})
        with patch("requests.request", return_value=resp):
            accounts = adapter.get_accounts()
            assert len(accounts) == 2

    def test_raises_permanent_error_on_401(self):
        adapter = make_adapter()
        resp = mock_response(401, MOCK_ERROR_401)
        with patch("requests.request", return_value=resp):
            with pytest.raises(PermanentError):
                adapter.get_accounts()


# ---------------------------------------------------------------------------
# auth_check — delegates to get_accounts
# ---------------------------------------------------------------------------

class TestAuthCheck:
    def test_returns_true_on_success(self):
        adapter = make_adapter()
        resp = mock_response(200, {"accounts": MOCK_ACCOUNTS})
        with patch("requests.request", return_value=resp):
            assert adapter.auth_check() is True

    def test_returns_false_on_auth_failure(self):
        adapter = make_adapter()
        resp = mock_response(401, MOCK_ERROR_401)
        with patch("requests.request", return_value=resp):
            assert adapter.auth_check() is False

    def test_returns_false_on_ghl_error(self):
        adapter = make_adapter()
        resp = mock_response(500, {"error": "server error"})
        with patch("requests.request", return_value=resp):
            assert adapter.auth_check() is False


# ---------------------------------------------------------------------------
# _resolve_accounts — mapping logic
# ---------------------------------------------------------------------------

class TestResolveAccounts:
    def test_resolves_linkedin(self):
        adapter = make_adapter()
        ids = adapter._resolve_accounts("dave", "linkedin")
        assert ids == ["acc_li_001"]

    def test_resolves_facebook(self):
        adapter = make_adapter()
        ids = adapter._resolve_accounts("dave", "facebook")
        assert ids == ["acc_fb_002"]

    def test_raises_on_unknown_author(self):
        adapter = make_adapter()
        with pytest.raises(PermanentError):
            adapter._resolve_accounts("nobody", "linkedin")

    def test_raises_on_unknown_platform(self):
        adapter = make_adapter()
        with pytest.raises(PermanentError):
            adapter._resolve_accounts("dave", "tiktok")

    def test_raises_on_no_author(self):
        adapter = make_adapter()
        with pytest.raises(PermanentError):
            adapter._resolve_accounts(None, "linkedin")


# ---------------------------------------------------------------------------
# Error class imports — must come from retry.py, not defined inline
# ---------------------------------------------------------------------------

class TestErrorClassOrigins:
    def test_rate_limit_error_from_retry(self):
        from publisher.retry import RateLimitError as RetryRLE
        from publisher.adapters.ghl import GHLAdapter
        import inspect
        # RateLimitError used in ghl.py must be the one from retry.py
        ghl_source = inspect.getsource(
            __import__("publisher.adapters.ghl", fromlist=["ghl"])
        )
        # Inline class definition must not exist for RateLimitError or PermanentError
        assert "class RateLimitError" not in ghl_source
        assert "class PermanentError" not in ghl_source

    def test_ghl_error_defined_in_ghl_module(self):
        """GHLError is the only error class defined inline in ghl.py."""
        from publisher.adapters.ghl import GHLError
        assert issubclass(GHLError, Exception)
