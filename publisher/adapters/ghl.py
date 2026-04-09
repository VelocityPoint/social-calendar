"""
publisher/adapters/ghl.py -- GoHighLevel Social Planner adapter

Publishes posts to GHL Social Planner via the Lead Connector Hub API.
Replaces direct platform adapters (LinkedIn, Facebook, Instagram, GBP).

Auth: Bearer token (GHL_API_KEY env var) via GHL_API_KEY env var.
Base URL: https://services.leadconnectorhq.com
API version: 2021-07-28

Ref: AC3 (text publish), AC4 (image publish), AC6 (list accounts)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, List

import requests

from .base import BaseAdapter
from ..models import Post, Brand
from ..retry import PublishError, RateLimitError, PermanentError


logger = logging.getLogger(__name__)


class GHLError(Exception):
    """General GHL API error (non-retryable for 4xx, retryable for 5xx)."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GHL Error {status_code}: {message}")


BASE_URL = "https://services.leadconnectorhq.com"
API_VERSION = "2021-07-28"


class GHLAdapter(BaseAdapter):
    """
    Single adapter for all platforms via GHL Social Planner API.

    Auth: Bearer token (GHL API key) via GHL_API_KEY env var.
    Base URL: https://services.leadconnectorhq.com
    API version: 2021-07-28

    account_map format (from brand.yaml ghl.accounts):
        {author: {platform: account_id}}
    e.g.:
        {"dave": {"linkedin": "acc_123", "facebook": "acc_456"}}
    """

    platform = "ghl"

    def __init__(self, brand: Brand, state_dir: Path):
        super().__init__(brand, state_dir)
        # Extract GHL config from brand.yaml ghl block
        ghl_cfg = getattr(brand, "ghl", None) or {}
        self.location_id: str = (
            os.environ.get("GHL_LOCATION_ID")
            or (ghl_cfg.get("location_id") if isinstance(ghl_cfg, dict) else None)
            or ""
        )
        self.api_key: str = os.environ.get("GHL_API_KEY", "")
        # account_map: {author: {platform: account_id}}
        self.account_map: dict = (
            (ghl_cfg.get("accounts") if isinstance(ghl_cfg, dict) else None) or {}
        )

    # ------------------------------------------------------------------
    # BaseAdapter contract implementation
    # ------------------------------------------------------------------

    def publish(
        self,
        post: Post,
        copy_text: str,
        image_path: Optional[Path] = None,
    ) -> str:
        """
        Create a post via GHL Social Planner API.

        Args:
            post: Post model with id, publish_at, author, platforms, etc.
            copy_text: Text content for the post
            image_path: Unused (GHL uses image URLs; pass via post.creative)

        Returns:
            GHL post ID string

        Raises:
            PublishError: Retryable failure (5xx, network)
            RateLimitError: HTTP 429
            PermanentError: Non-retryable (400, 401, 403)
        """
        if not self.check_rate_limit(post.id):
            raise PublishError(f"Publish deferred — rate limit exceeded for {post.id}")

        # Resolve account IDs from brand.yaml mapping
        platform = post.platforms[0] if post.platforms else "unknown"
        account_ids = self._resolve_accounts(post.author, platform)

        # Build image URL from creative assets if available
        image_url: Optional[str] = None
        if post.creative:
            for asset in post.creative:
                if asset.url:
                    image_url = asset.url
                    break

        payload: dict = {
            "accountIds": account_ids,
            "content": copy_text,
            "scheduledAt": post.publish_at,  # ISO 8601 with timezone (preserved for GHL reference)
            "status": "draft",  # Gate 2: land as draft for Dave's manual approval in GHL UI
            "type": "image" if image_url else "text",
        }
        if image_url:
            payload["mediaUrls"] = [image_url]

        resp = self._request(
            "POST",
            f"/social-media-posting/{self.location_id}/posts",
            payload,
        )

        data = resp.json() if resp.content else {}
        post_id = data.get("id") or data.get("post_id")
        if not post_id:
            raise PublishError(f"GHL returned no post ID: {data}")

        logger.info(f"[PUBLISHED] {post.id} on ghl: ghl_post_id={post_id}")
        self.increment_rate_limit()
        return str(post_id)

    def auth_check(self) -> bool:
        """
        AC2: Verify GHL API authentication by listing connected accounts.

        Returns True if auth is valid, False otherwise.
        Logs [AUTH OK] ghl or [AUTH FAIL] ghl.
        """
        try:
            self.get_accounts()
            logger.info("[AUTH OK] ghl")
            return True
        except GHLError:
            logger.error("[AUTH FAIL] ghl: API error during auth check")
            return False
        except PermanentError as e:
            logger.error(f"[AUTH FAIL] ghl: {e}")
            return False
        except Exception as e:
            logger.error(f"[AUTH FAIL] ghl: unexpected error: {e}")
            return False

    # ------------------------------------------------------------------
    # GHL-specific methods
    # ------------------------------------------------------------------

    def delete(self, ghl_post_id: str) -> bool:
        """
        Delete a post from GHL Social Planner.

        Args:
            ghl_post_id: The GHL post ID to delete

        Returns:
            True if deletion was successful

        Raises:
            RateLimitError: HTTP 429
            PermanentError: 401, 403, 404
        """
        resp = self._request(
            "DELETE",
            f"/social-media-posting/{self.location_id}/posts/{ghl_post_id}",
        )
        if resp.status_code in (200, 204):
            logger.info(f"[DELETED] ghl post: {ghl_post_id}")
            return True
        return False

    def get_post(self, ghl_post_id: str) -> Optional[dict]:
        """
        Retrieve a single post from GHL Social Planner.

        Returns:
            Post data dict or None if 404.
        """
        try:
            resp = self._request(
                "GET",
                f"/social-media-posting/{self.location_id}/posts/{ghl_post_id}",
            )
            data = resp.json() if resp.content else None
            logger.info(f"[RETRIEVED] ghl post: {ghl_post_id}")
            return data
        except PermanentError as e:
            if getattr(e, "status_code", None) == 404:
                logger.warning(f"[NOT FOUND] ghl post: {ghl_post_id}")
                return None
            raise
        except GHLError as e:
            if e.status_code == 404:
                logger.warning(f"[NOT FOUND] ghl post: {ghl_post_id}")
                return None
            raise

    def list_posts(self, filters: Optional[dict] = None) -> List[dict]:
        """
        List posts from GHL Social Planner.

        Uses POST /social-media-posting/{locationId}/posts/list with body filters.

        Args:
            filters: Optional dict of body filters (e.g., {"status": "scheduled"})

        Returns:
            List of post data dicts
        """
        body = filters or {}
        resp = self._request(
            "POST",
            f"/social-media-posting/{self.location_id}/posts/list",
            body,
        )
        data = resp.json() if resp.content else {}
        posts = data if isinstance(data, list) else data.get("posts", data.get("data", []))
        logger.info(f"[LISTED] ghl posts: {len(posts)} found")
        return posts

    def get_accounts(self) -> List[dict]:
        """
        List connected social accounts for this GHL location.

        Returns:
            List of account dicts from GHL API
        """
        resp = self._request(
            "GET",
            f"/social-media-posting/{self.location_id}/accounts",
        )
        data = resp.json() if resp.content else {}
        accounts = data if isinstance(data, list) else data.get("accounts", data.get("data", []))
        return accounts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_accounts(self, author: Optional[str], platform: str) -> List[str]:
        """
        Resolve GHL account IDs from brand.yaml account_map.

        Args:
            author: Post author (maps to ghl.accounts key in brand.yaml)
            platform: Social platform (e.g. "linkedin", "facebook")

        Returns:
            List of GHL account IDs (single element for normal posts)

        Raises:
            PermanentError: author or platform not found in account_map
        """
        if not author:
            raise PermanentError(f"No author specified for platform {platform}")
        if author not in self.account_map:
            raise PermanentError(f"Unknown author: {author}")
        platform_map = self.account_map[author]
        if platform not in platform_map:
            raise PermanentError(
                f"No GHL account configured for author={author} platform={platform}"
            )
        return [platform_map[platform]]

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
    ) -> requests.Response:
        """
        Make authenticated request to GHL Lead Connector Hub API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API endpoint path (must start with /)
            body: Optional JSON body for POST requests

        Returns:
            requests.Response

        Raises:
            RateLimitError: HTTP 429 (respects Retry-After header)
            PermanentError: HTTP 400, 401, 403, 404
            GHLError: Other 4xx/5xx errors
            PublishError: Network/timeout errors
        """
        url = f"{BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Version": API_VERSION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            resp = requests.request(
                method,
                url,
                headers=headers,
                json=body,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise PublishError(f"GHL network error: {e}")

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            raise RateLimitError(
                f"GHL rate limit, retry after {retry_after}s",
                retry_after=retry_after,
            )

        if resp.status_code in (400, 401, 403, 404):
            raise PermanentError(
                f"GHL {resp.status_code}: {resp.text[:500]}",
                status_code=resp.status_code,
            )

        if resp.status_code >= 500:
            raise GHLError(resp.status_code, resp.text[:500])

        logger.debug(f"GHL {method} {path}: {resp.status_code}")
        return resp
