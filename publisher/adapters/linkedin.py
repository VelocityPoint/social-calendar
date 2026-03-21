"""
publisher/adapters/linkedin.py -- LinkedIn adapter (LinkedIn Posts API v2)

Phase 1 skeleton. Interface complete; full integration pending credential setup.

Ref: AC3 (text publish <= 3000 chars), AC4 (image publish), AC13 (OAuth token refresh)
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

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_CHAR_LIMIT = 3000


class LinkedInAdapter(BaseAdapter):
    platform = "linkedin"

    def _get_token(self) -> str:
        kv_name = self.brand.credentials.get_kv_secret_name("linkedin")
        if not kv_name:
            raise PermanentError("No linkedin credential configured in brand.yaml")
        token = self._get_credential(kv_name)
        if not token:
            raise PermanentError(f"Could not retrieve linkedin token: {kv_name}")
        return token

    def _get_author_urn(self) -> str:
        """LinkedIn author URN: urn:li:organization:{id} or urn:li:person:{id}."""
        return os.environ.get("LINKEDIN_AUTHOR_URN", "")

    def auth_check(self) -> bool:
        """AC2: GET /rest/organizationAcls to verify auth."""
        try:
            token = self._get_token()
            resp = requests.get(
                f"{LINKEDIN_API_BASE}/rest/organizationAcls",
                headers={
                    "Authorization": f"Bearer {token}",
                    "LinkedIn-Version": "202401",
                },
                params={"q": "roleAssignee"},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("[AUTH OK] linkedin")
                return True
            else:
                logger.error(f"[AUTH FAIL] linkedin: HTTP {resp.status_code} {resp.text[:100]}")
                return False
        except Exception as e:
            logger.error(f"[AUTH FAIL] linkedin: {e}")
            return False

    def publish(
        self,
        post: Post,
        copy_text: str,
        image_path: Optional[Path] = None,
    ) -> str:
        """
        Publish to LinkedIn via Posts API.
        Uses ugcPosts endpoint for text and image posts.
        """
        if len(copy_text) > LINKEDIN_CHAR_LIMIT:
            raise PermanentError(
                f"LinkedIn copy exceeds {LINKEDIN_CHAR_LIMIT} chars ({len(copy_text)})"
            )

        token = self._get_token()
        author_urn = self._get_author_urn()
        if not author_urn:
            raise PermanentError("LINKEDIN_AUTHOR_URN not set")

        try:
            if image_path and image_path.exists():
                post_id = self._publish_with_image(token, author_urn, copy_text, image_path)
            else:
                post_id = self._publish_text(token, author_urn, copy_text)

            logger.info(f"[PUBLISHED] {post.id} on linkedin: urn={post_id}")
            return post_id

        except (PublishError, RateLimitError, PermanentError):
            raise
        except Exception as e:
            raise PublishError(f"LinkedIn publish failed: {e}")

    def _publish_text(self, token: str, author: str, text: str) -> str:
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        resp = requests.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"},
            timeout=30,
        )
        self._raise_for_status(resp)
        return resp.headers.get("X-RestLi-Id", resp.json().get("id", ""))

    def _publish_with_image(self, token: str, author: str, text: str, image_path: Path) -> str:
        # Step 1: Register upload
        reg_resp = requests.post(
            f"{LINKEDIN_API_BASE}/assets?action=registerUpload",
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": author,
                    "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}],
                }
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        self._raise_for_status(reg_resp)
        upload_data = reg_resp.json()
        upload_url = upload_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = upload_data["value"]["asset"]

        # Step 2: Upload image
        with open(image_path, "rb") as f:
            up_resp = requests.put(
                upload_url,
                data=f,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"},
                timeout=60,
            )
        if up_resp.status_code not in (200, 201):
            raise PublishError(f"LinkedIn image upload failed: HTTP {up_resp.status_code}")

        # Step 3: Create post with image
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "IMAGE",
                    "media": [{"status": "READY", "media": asset_urn}],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        resp = requests.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"},
            timeout=30,
        )
        self._raise_for_status(resp)
        return resp.headers.get("X-RestLi-Id", resp.json().get("id", ""))

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code in (200, 201):
            return
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 0)) or None
            raise RateLimitError(f"LinkedIn rate limit: {resp.text[:100]}", retry_after=retry_after)
        if resp.status_code in (400, 403):
            raise PermanentError(f"LinkedIn error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
        raise PublishError(f"LinkedIn error {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)
