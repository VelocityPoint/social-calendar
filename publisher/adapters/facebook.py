"""
publisher/adapters/facebook.py -- Facebook adapter (Meta Graph API)

Phase 1 skeleton. Interface is complete; full API integration pending credential setup.

Ref: AC3 (text publish), AC4 (image publish), AC13 (token refresh), AC14 (shared Meta creds)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import requests

from .base import BaseAdapter
from ..models import Post, Brand
from ..retry import PublishError, RateLimitError, PermanentError


logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class FacebookAdapter(BaseAdapter):
    platform = "facebook"

    def _get_page_access_token(self) -> str:
        """Load Facebook page access token from Key Vault or env, refreshing if near expiry (AC13)."""
        kv_name = self.brand.credentials.get_kv_secret_name("facebook")
        if not kv_name:
            raise PermanentError("No facebook credential configured in brand.yaml", status_code=401)
        cred_raw = self._get_credential(kv_name)
        if not cred_raw:
            raise PermanentError(f"Could not retrieve facebook token from secret: {kv_name}", status_code=401)
        # AC13: check expiry and refresh if within 24h window
        return self._check_and_refresh_token(cred_raw, kv_name)

    def auth_check(self) -> bool:
        """AC2: GET /{page-id} to verify token."""
        try:
            token = self._get_page_access_token()
            page_id = self._get_page_id()
            resp = requests.get(
                f"{GRAPH_API_BASE}/{page_id}",
                params={"fields": "id,name"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("[AUTH OK] facebook")
                return True
            else:
                logger.error(f"[AUTH FAIL] facebook: HTTP {resp.status_code} {resp.text[:100]}")
                return False
        except Exception as e:
            logger.error(f"[AUTH FAIL] facebook: {e}")
            return False

    def _get_page_id(self) -> str:
        """Get Facebook page ID from brand config or env."""
        import os
        return os.environ.get("FACEBOOK_PAGE_ID", "")

    def publish(
        self,
        post: Post,
        copy_text: str,
        image_path: Optional[Path] = None,
    ) -> str:
        """
        Publish to Facebook via Graph API.
        Text only: POST /{page-id}/feed
        With image: POST /{page-id}/photos
        """
        token = self._get_page_access_token()
        page_id = self._get_page_id()

        if not page_id:
            raise PermanentError("FACEBOOK_PAGE_ID not set", status_code=400)

        try:
            if image_path and image_path.exists():
                post_id = self._publish_with_photo(token, page_id, copy_text, image_path)
            else:
                post_id = self._publish_text(token, page_id, copy_text)

            logger.info(f"[PUBLISHED] {post.id} on facebook: post_id={post_id}")
            return post_id

        except (PublishError, RateLimitError, PermanentError):
            raise
        except Exception as e:
            raise PublishError(f"Facebook publish failed: {e}")

    def _publish_text(self, token: str, page_id: str, message: str) -> str:
        resp = requests.post(
            f"{GRAPH_API_BASE}/{page_id}/feed",
            json={"message": message},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        self._raise_for_status(resp)
        data = resp.json()
        return data.get("id", "")

    def _publish_with_photo(self, token: str, page_id: str, message: str, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_API_BASE}/{page_id}/photos",
                data={"message": message},
                headers={"Authorization": f"Bearer {token}"},
                files={"source": f},
                timeout=60,
            )
        self._raise_for_status(resp)
        data = resp.json()
        return data.get("post_id", data.get("id", ""))

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code == 200 or resp.status_code == 201:
            return
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 0)) or None
            raise RateLimitError(f"Facebook rate limit: {resp.text[:100]}", retry_after=retry_after)
        if resp.status_code in (400, 403):
            raise PermanentError(f"Facebook permanent error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
        raise PublishError(f"Facebook error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
