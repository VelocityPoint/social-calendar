"""
publisher/adapters/instagram.py -- Instagram adapter (Instagram Graph API)

Shares Meta app credentials with facebook.py (AC14).
Reads ONLY from the facebook credential — no separate instagram credential file.

Ref: AC14 (shared Meta creds — must only read facebook.json / facebook KV secret),
     AC3 (text publish), AC4 (image publish — Instagram requires media URL, not file upload)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import requests

from .base import BaseAdapter
from ..models import Post, Brand
from ..retry import PublishError, RateLimitError, PermanentError


logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class InstagramAdapter(BaseAdapter):
    platform = "instagram"

    def _get_credentials(self) -> tuple[str, str]:
        """
        AC14: Load Instagram credentials from facebook KV secret / env.
        Returns (instagram_user_id, instagram_access_token).
        Must NOT reference any separate instagram credential.
        """
        # AC14: Use SAME credential name as facebook
        kv_name = self.brand.credentials.get_kv_secret_name("facebook")
        if not kv_name:
            raise PermanentError("No facebook credential configured (required for Instagram per AC14)")

        # The facebook KV secret is expected to be a JSON blob containing
        # both page access token and Instagram user credentials from the same Meta app.
        import json
        cred_json = self._get_credential(kv_name)
        if not cred_json:
            raise PermanentError(f"Could not retrieve credential: {kv_name}")

        try:
            creds = json.loads(cred_json)
            ig_user_id = creds.get("instagram_user_id") or os.environ.get("INSTAGRAM_USER_ID", "")
            ig_token = creds.get("instagram_access_token") or creds.get("page_access_token", "")
        except (json.JSONDecodeError, AttributeError):
            # If not JSON, treat as raw token (legacy)
            ig_user_id = os.environ.get("INSTAGRAM_USER_ID", "")
            ig_token = cred_json

        if not ig_user_id or not ig_token:
            raise PermanentError("Instagram user_id or access_token not found in facebook credential")

        # AC13: check expiry and refresh if within 24h window.
        # Instagram tokens are long-lived; refresh uses the same facebook KV secret.
        ig_token = self._check_and_refresh_token(cred_json, kv_name)

        return ig_user_id, ig_token

    def auth_check(self) -> bool:
        """AC2: GET /{ig-user-id}?fields=id to verify Instagram auth."""
        try:
            ig_user_id, ig_token = self._get_credentials()
            resp = requests.get(
                f"{GRAPH_API_BASE}/{ig_user_id}",
                params={"fields": "id,username"},
                headers={"Authorization": f"Bearer {ig_token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("[AUTH OK] instagram")
                return True
            else:
                logger.error(f"[AUTH FAIL] instagram: HTTP {resp.status_code} {resp.text[:100]}")
                return False
        except Exception as e:
            logger.error(f"[AUTH FAIL] instagram: {e}")
            return False

    def publish(
        self,
        post: Post,
        copy_text: str,
        image_path: Optional[Path] = None,
    ) -> str:
        """
        Publish to Instagram via Instagram Graph API.

        Instagram requires a 2-step process:
        1. Create media container (POST /{ig-user-id}/media) with image_url or video_url
        2. Publish container (POST /{ig-user-id}/media_publish)

        For image posts, image must be a public URL (not file upload).
        """
        ig_user_id, ig_token = self._get_credentials()

        try:
            if image_path and image_path.exists():
                # Image posts require a public URL — derive from Azure Blob or CDN
                image_url = self._get_public_image_url(image_path, post)
                media_id = self._create_image_container(ig_user_id, ig_token, copy_text, image_url)
            else:
                # Text-only post requires reel or uses IMAGE with placeholder
                # Instagram does not support text-only posts via API — use caption-only image
                logger.warning(f"[WARN] {post.id}: Instagram text-only posts require an image; skipping media step")
                media_id = self._create_text_container(ig_user_id, ig_token, copy_text)

            ig_post_id = self._publish_container(ig_user_id, ig_token, media_id)
            logger.info(f"[PUBLISHED] {post.id} on instagram: ig_post_id={ig_post_id}")
            return ig_post_id

        except (PublishError, RateLimitError, PermanentError):
            raise
        except Exception as e:
            raise PublishError(f"Instagram publish failed: {e}")

    def _get_public_image_url(self, image_path: Path, post: Post) -> str:
        """
        Derive a public URL for an image asset.
        Checks for Azure Blob CDN URL in environment, falls back to constructing from path.
        """
        base_url = os.environ.get("ASSETS_BASE_URL", "")
        if base_url:
            return f"{base_url.rstrip('/')}/{post.brand}/{image_path.name}"
        raise PermanentError(
            f"ASSETS_BASE_URL not set — Instagram requires a public image URL. "
            f"Set ASSETS_BASE_URL to your Azure Blob Storage base URL."
        )

    def _create_image_container(self, user_id: str, token: str, caption: str, image_url: str) -> str:
        resp = requests.post(
            f"{GRAPH_API_BASE}/{user_id}/media",
            json={"image_url": image_url, "caption": caption},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        self._raise_for_status(resp)
        return resp.json().get("id", "")

    def _create_text_container(self, user_id: str, token: str, caption: str) -> str:
        """Instagram requires an image for posts — this creates a placeholder reel."""
        raise PermanentError(
            "Instagram does not support text-only posts via API. "
            "Provide a creative image in the post document."
        )

    def _publish_container(self, user_id: str, token: str, media_id: str) -> str:
        resp = requests.post(
            f"{GRAPH_API_BASE}/{user_id}/media_publish",
            json={"creation_id": media_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        self._raise_for_status(resp)
        return resp.json().get("id", "")

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code in (200, 201):
            return
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 0)) or None
            raise RateLimitError(f"Instagram rate limit: {resp.text[:100]}", retry_after=retry_after)
        if resp.status_code in (400, 403):
            raise PermanentError(f"Instagram permanent error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
        raise PublishError(f"Instagram error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
