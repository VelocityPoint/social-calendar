"""
publisher/adapters/gbp.py -- Google Business Profile adapter (My Business v4 API)

Phase 1 skeleton. Interface complete; full integration pending credential setup.

Ref: AC3 (text publish <= 1500 chars), AC4 (image/photo posts),
     AC13 (OAuth token refresh via Google), AC-OQ6 (rate limit)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import requests

from .base import BaseAdapter
from ..models import Post, Brand
from ..retry import PublishError, RateLimitError, PermanentError


logger = logging.getLogger(__name__)

GBP_API_BASE = "https://mybusiness.googleapis.com/v4"
GBP_CHAR_LIMIT = 1500


class GBPAdapter(BaseAdapter):
    platform = "gbp"

    def _get_credentials(self) -> dict:
        """Load GBP credentials JSON (service account or OAuth) from KV or env."""
        kv_name = self.brand.credentials.get_kv_secret_name("gbp")
        if not kv_name:
            raise PermanentError("No gbp credential configured in brand.yaml")
        cred_str = self._get_credential(kv_name)
        if not cred_str:
            raise PermanentError(f"Could not retrieve GBP credential: {kv_name}")
        try:
            return json.loads(cred_str)
        except json.JSONDecodeError:
            # Treat as access token string
            return {"access_token": cred_str}

    def _get_access_token(self) -> str:
        """Load GBP access token, refreshing if within 24h of expiry (AC13)."""
        kv_name = self.brand.credentials.get_kv_secret_name("gbp")
        cred_raw = self._get_credential(kv_name) if kv_name else None
        if cred_raw:
            # AC13: check expiry and refresh if within 24h window
            return self._check_and_refresh_token(cred_raw, kv_name)
        creds = self._get_credentials()
        return creds.get("access_token", "")

    def _get_location_name(self) -> str:
        """GBP location resource name: accounts/{account_id}/locations/{location_id}"""
        return os.environ.get("GBP_LOCATION_NAME", "")

    def auth_check(self) -> bool:
        """AC2: GET tokeninfo to verify GBP OAuth token."""
        try:
            token = self._get_access_token()
            resp = requests.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": token},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("[AUTH OK] gbp")
                return True
            else:
                logger.error(f"[AUTH FAIL] gbp: HTTP {resp.status_code} {resp.text[:100]}")
                return False
        except Exception as e:
            logger.error(f"[AUTH FAIL] gbp: {e}")
            return False

    def publish(
        self,
        post: Post,
        copy_text: str,
        image_path: Optional[Path] = None,
    ) -> str:
        """
        Publish to Google Business Profile via My Business API.
        Creates a LOCAL_POST at the configured location.
        """
        if len(copy_text) > GBP_CHAR_LIMIT:
            raise PermanentError(
                f"GBP copy exceeds {GBP_CHAR_LIMIT} chars ({len(copy_text)})"
            )

        token = self._get_access_token()
        location_name = self._get_location_name()
        if not location_name:
            raise PermanentError("GBP_LOCATION_NAME not set (e.g. accounts/123/locations/456)")

        post_body = {
            "languageCode": "en-US",
            "summary": copy_text,
            "topicType": "STANDARD",
        }

        if image_path and image_path.exists():
            # GBP uses public URL for media (AC4 — platforms requiring public URL)
            image_url = self._get_public_image_url(image_path, post)
            post_body["media"] = [{
                "mediaFormat": "PHOTO",
                "sourceUrl": image_url,
            }]

        try:
            resp = requests.post(
                f"{GBP_API_BASE}/{location_name}/localPosts",
                json=post_body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            self._raise_for_status(resp)
            data = resp.json()
            local_post_name = data.get("name", "")
            logger.info(f"[PUBLISHED] {post.id} on gbp: name={local_post_name}")
            return local_post_name

        except (PublishError, RateLimitError, PermanentError):
            raise
        except Exception as e:
            raise PublishError(f"GBP publish failed: {e}")

    def _get_public_image_url(self, image_path: Path, post: Post) -> str:
        base_url = os.environ.get("ASSETS_BASE_URL", "")
        if base_url:
            return f"{base_url.rstrip('/')}/{post.brand}/{image_path.name}"
        raise PermanentError(
            f"ASSETS_BASE_URL not set — GBP requires a public image URL."
        )

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code in (200, 201):
            return
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 0)) or None
            raise RateLimitError(f"GBP rate limit: {resp.text[:100]}", retry_after=retry_after)
        if resp.status_code in (400, 403):
            raise PermanentError(f"GBP error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
        raise PublishError(f"GBP error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
