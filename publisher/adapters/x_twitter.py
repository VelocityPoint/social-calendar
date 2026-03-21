"""
publisher/adapters/x_twitter.py -- X/Twitter adapter via xurl CLI (AC15)

Uses xurl as a subprocess. No direct HTTP calls to api.twitter.com or api.x.com.
No Twitter/X SDK imports.

Ref: AC15 (xurl subprocess, no direct HTTP), AC3 (text publish), AC4 (image publish),
     AC-OQ4 (retry via publisher/retry.py), AC-OQ6 (rate limit)
"""

from __future__ import annotations

import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from .base import BaseAdapter
from ..models import Post, Brand
from ..retry import PublishError, RateLimitError, PermanentError


logger = logging.getLogger(__name__)

X_CHAR_LIMIT = 280


class XTwitterAdapter(BaseAdapter):
    platform = "x"

    def auth_check(self) -> bool:
        """
        AC2: Verify X/Twitter auth by calling xurl whoami.
        Returns True on success (exit code 0), False otherwise.
        """
        if not shutil.which("xurl"):
            logger.error("[AUTH FAIL] x: xurl CLI not found in PATH")
            return False

        try:
            result = subprocess.run(
                ["xurl", "whoami"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("[AUTH OK] x")
                return True
            else:
                logger.error(f"[AUTH FAIL] x: xurl whoami returned exit {result.returncode}: {result.stderr.strip()}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("[AUTH FAIL] x: xurl whoami timed out after 10s")
            return False
        except Exception as e:
            logger.error(f"[AUTH FAIL] x: {e}")
            return False

    def publish(
        self,
        post: Post,
        copy_text: str,
        image_path: Optional[Path] = None,
    ) -> str:
        """
        Publish to X/Twitter via xurl CLI subprocess (AC15).

        Text posts: xurl post -t "<text>"
        Image posts: xurl post -t "<text>" -m <media_id>
                     (media uploaded via xurl media upload first)

        Returns tweet ID string on success.
        Raises PublishError, RateLimitError, or PermanentError on failure.
        """
        if not shutil.which("xurl"):
            raise PermanentError("xurl CLI not found in PATH — cannot publish to X")

        # Validate copy length (AC3)
        if len(copy_text) > X_CHAR_LIMIT:
            raise PermanentError(
                f"X copy text exceeds {X_CHAR_LIMIT} character limit ({len(copy_text)} chars)"
            )

        media_id: Optional[str] = None

        # Upload image if provided (AC4)
        if image_path and image_path.exists():
            media_id = self._upload_media(image_path)

        # Build xurl command (AC15: no direct HTTP calls)
        cmd = ["xurl", "post", "-t", copy_text]
        if media_id:
            cmd += ["-m", media_id]

        logger.info(f"[EXEC] {' '.join(cmd[:4])} ... (post_id={post.id})")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30
            )
        except subprocess.TimeoutExpired:
            raise PublishError("xurl post timed out after 30s")
        except Exception as e:
            raise PublishError(f"xurl execution failed: {e}")

        logger.debug(f"[EXEC] xurl exit={result.returncode} stdout={result.stdout[:200]}")

        if result.returncode != 0:
            stderr = result.stderr.strip()
            self._raise_for_xurl_error(result.returncode, stderr, result.stdout)

        # Parse tweet ID from xurl output
        tweet_id = self._parse_tweet_id(result.stdout)
        if not tweet_id:
            raise PublishError(f"Could not parse tweet ID from xurl output: {result.stdout[:200]}")

        logger.info(f"[PUBLISHED] {post.id} on x: tweet_id={tweet_id}")
        return tweet_id

    def _upload_media(self, image_path: Path) -> str:
        """
        Upload media via xurl and return media_id.
        """
        logger.info(f"[EXEC] xurl media upload {image_path.name}")
        try:
            result = subprocess.run(
                ["xurl", "media", "upload", str(image_path)],
                capture_output=True, text=True, timeout=60
            )
        except subprocess.TimeoutExpired:
            raise PublishError("xurl media upload timed out after 60s")
        except Exception as e:
            raise PublishError(f"xurl media upload failed: {e}")

        if result.returncode != 0:
            raise PublishError(f"xurl media upload failed (exit {result.returncode}): {result.stderr.strip()}")

        media_id = self._parse_media_id(result.stdout)
        if not media_id:
            raise PublishError(f"Could not parse media_id from xurl output: {result.stdout[:200]}")

        logger.info(f"[MEDIA] Uploaded {image_path.name} -> media_id={media_id}")
        return media_id

    def _raise_for_xurl_error(self, exit_code: int, stderr: str, stdout: str) -> None:
        """Map xurl exit codes and error strings to appropriate exception types."""
        error_text = f"{stderr} {stdout}".lower()

        if "429" in error_text or "rate limit" in error_text:
            raise RateLimitError(f"X rate limit hit: {stderr}", retry_after=None)

        if "401" in error_text or "unauthorized" in error_text or "forbidden" in error_text:
            raise PermanentError(f"X auth failure: {stderr}", status_code=401)

        if "400" in error_text or "bad request" in error_text:
            raise PermanentError(f"X bad request: {stderr}", status_code=400)

        raise PublishError(f"xurl failed (exit {exit_code}): {stderr}")

    def _parse_tweet_id(self, output: str) -> Optional[str]:
        """
        Parse tweet ID from xurl output.
        xurl may output JSON with 'id' field, or just the ID as a plain string.
        """
        output = output.strip()

        # Try JSON
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                for key in ("id", "id_str", "tweet_id"):
                    if key in data:
                        return str(data[key])
        except json.JSONDecodeError:
            pass

        # Try plain numeric ID
        import re
        match = re.search(r"\b(\d{10,})\b", output)
        if match:
            return match.group(1)

        return None

    def _parse_media_id(self, output: str) -> Optional[str]:
        """Parse media_id from xurl media upload output."""
        output = output.strip()
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                for key in ("media_id", "media_id_string", "id"):
                    if key in data:
                        return str(data[key])
        except json.JSONDecodeError:
            pass

        import re
        match = re.search(r"\b(\d{10,})\b", output)
        if match:
            return match.group(1)

        return None
