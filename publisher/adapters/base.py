"""
publisher/adapters/base.py -- Abstract base adapter

All platform adapters inherit from BaseAdapter.
Defines the interface: publish(), auth_check(), rate_limit_check().

Ref: AC2 (auth_check), AC3/AC4 (publish), AC13 (token refresh), AC-OQ6 (rate_limit_check)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..models import Post, Brand, RateLimitState


logger = logging.getLogger(__name__)

# Refresh tokens if expiry is within this many seconds (AC13: 24-hour window)
TOKEN_REFRESH_WINDOW_SECONDS = 86400


class BaseAdapter(ABC):
    """
    Abstract base class for all platform adapters.

    Each adapter:
    - Implements publish(post, brand, copy_text, image_path) -> str (platform post ID)
    - Implements auth_check(brand) -> bool
    - Uses rate limit state from brands/<brand>/.state/rate_limits/<platform>.json
    - Raises PublishError, RateLimitError, or PermanentError (from retry.py)

    The retry wrapper (publisher/retry.py) handles the 10s/30s/90s backoff.
    Adapters should raise, not catch, retriable errors.
    """

    platform: str  # Override in subclass: "x", "facebook", etc.

    def __init__(self, brand: Brand, state_dir: Path):
        self.brand = brand
        self.state_dir = state_dir
        self._rate_limit_state: Optional[RateLimitState] = None

    @property
    def rate_limit_state(self) -> RateLimitState:
        if self._rate_limit_state is None:
            self._rate_limit_state = RateLimitState.load_or_create(
                self.state_dir / "rate_limits", self.platform
            )
        return self._rate_limit_state

    def save_rate_limit_state(self) -> None:
        if self._rate_limit_state:
            self._rate_limit_state.save(self.state_dir / "rate_limits")

    def check_rate_limit(self, post_id: str) -> bool:
        """
        AC-OQ6: Check rate limit before any API call.
        Returns True if allowed, False if deferred (limit exceeded).
        Logs deferral with next-window timestamp.
        """
        limited, next_window = self.rate_limit_state.is_limited()
        if limited:
            logger.info(
                f"[DEFERRED] {post_id} on {self.platform}: "
                f"rate limit {self.rate_limit_state.call_count}/{self.rate_limit_state.limit}, "
                f"next window: {next_window}"
            )
            return False
        return True

    def increment_rate_limit(self) -> None:
        """Increment counter after a successful API call."""
        self.rate_limit_state.increment()

    @abstractmethod
    def publish(
        self,
        post: Post,
        copy_text: str,
        image_path: Optional[Path] = None,
    ) -> str:
        """
        Publish the post to the platform.

        Args:
            post: Post model (for metadata: id, publish_at, etc.)
            copy_text: Platform-specific copy text (extracted from document)
            image_path: Optional path to image asset

        Returns:
            Platform post ID string (e.g. tweet ID, LinkedIn share URN)

        Raises:
            PublishError: Retryable failure (4xx except 400, 5xx, network)
            RateLimitError: HTTP 429
            PermanentError: Non-retryable failure (400 Bad Request, auth error)
        """
        ...

    @abstractmethod
    def auth_check(self) -> bool:
        """
        AC2: Lightweight authenticated API call to verify credentials.
        Returns True if auth is valid, False otherwise.
        Logs [AUTH OK] {platform} or [AUTH FAIL] {platform}.
        """
        ...

    def _get_credential(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a credential by Key Vault secret name or env var fallback.
        Phase 1: uses environment variables with the secret name as the key.
        Phase 2: reads from Azure Key Vault via OIDC.
        """
        # Try env var first (Phase 1 fallback, also used in GH Actions environment secrets)
        value = os.environ.get(secret_name.upper().replace("-", "_"))
        if value:
            return value

        # Try Key Vault via az CLI (Phase 2 — if AZURE_KEY_VAULT_NAME is set)
        vault_name = os.environ.get("AZURE_KEY_VAULT_NAME")
        if vault_name:
            try:
                result = subprocess.run(
                    ["az", "keyvault", "secret", "show",
                     "--vault-name", vault_name,
                     "--name", secret_name,
                     "--query", "value",
                     "--output", "tsv"],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                logger.warning(f"Key Vault secret '{secret_name}' not found: {result.stderr.strip()}")
            except Exception as e:
                logger.warning(f"Key Vault lookup failed for '{secret_name}': {e}")

        logger.warning(f"[CREDENTIAL] Could not retrieve secret: {secret_name}")
        return None

    def _write_credential(self, secret_name: str, value: str) -> bool:
        """
        Write a refreshed credential back to Key Vault (AC13).
        Falls back to env var update for Phase 1 (no-op — env vars are read-only at runtime).
        Returns True if written, False if Key Vault is unavailable.
        """
        vault_name = os.environ.get("AZURE_KEY_VAULT_NAME")
        if not vault_name:
            logger.warning(f"[AC13] AZURE_KEY_VAULT_NAME not set — cannot write back refreshed token for {secret_name}")
            return False

        try:
            result = subprocess.run(
                ["az", "keyvault", "secret", "set",
                 "--vault-name", vault_name,
                 "--name", secret_name,
                 "--value", value],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"[AC13] Refreshed token written to Key Vault: {secret_name}")
                return True
            logger.error(f"[AC13] Failed to write refreshed token to Key Vault: {result.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"[AC13] Exception writing refreshed token to Key Vault: {e}")
            return False

    def _check_and_refresh_token(self, cred_json: str, secret_name: str) -> str:
        """
        AC13: Check token expiry and refresh if within TOKEN_REFRESH_WINDOW_SECONDS (24h).

        Expects cred_json to be either:
          - A JSON object with keys: access_token, expires_at (ISO 8601), refresh_token,
            and optionally token_endpoint, client_id, client_secret.
          - A raw token string (no expiry tracking — returned as-is).

        On successful refresh, writes updated credential back to Key Vault.
        Returns the current (possibly refreshed) access token string.
        """
        try:
            creds = json.loads(cred_json)
        except (json.JSONDecodeError, TypeError):
            # Raw token string — no expiry metadata available, return as-is
            return cred_json

        access_token = creds.get("access_token", cred_json)
        expires_at_str = creds.get("expires_at")
        refresh_token = creds.get("refresh_token")

        if not expires_at_str:
            # No expiry tracked — return token without attempting refresh
            return access_token

        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(f"[AC13] Cannot parse expires_at '{expires_at_str}' for {secret_name}")
            return access_token

        now = datetime.now(timezone.utc)
        seconds_until_expiry = (expires_at - now).total_seconds()

        if seconds_until_expiry > TOKEN_REFRESH_WINDOW_SECONDS:
            # Token is fresh — no refresh needed
            logger.debug(f"[AC13] Token for {secret_name} valid for {int(seconds_until_expiry)}s — no refresh needed")
            return access_token

        if seconds_until_expiry <= 0:
            logger.warning(f"[AC13] Token for {secret_name} has EXPIRED — attempting refresh")
        else:
            logger.info(f"[AC13] Token for {secret_name} expires in {int(seconds_until_expiry)}s (<24h) — refreshing")

        if not refresh_token:
            logger.error(f"[AC13] Token for {secret_name} needs refresh but no refresh_token available")
            return access_token

        # Attempt platform-specific token refresh
        token_endpoint = creds.get("token_endpoint")
        client_id = creds.get("client_id") or os.environ.get("OAUTH_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.environ.get("OAUTH_CLIENT_SECRET")

        if not token_endpoint or not client_id:
            logger.error(
                f"[AC13] Cannot refresh token for {secret_name}: "
                f"token_endpoint or client_id missing from credential"
            )
            return access_token

        new_access_token, new_expires_at = self._exchange_refresh_token(
            token_endpoint, client_id, client_secret, refresh_token
        )

        if not new_access_token:
            logger.error(f"[AC13] Token refresh failed for {secret_name} — using existing token")
            return access_token

        # Update creds dict and write back to Key Vault
        creds["access_token"] = new_access_token
        if new_expires_at:
            creds["expires_at"] = new_expires_at.isoformat()

        self._write_credential(secret_name, json.dumps(creds))
        logger.info(f"[AC13] Token refreshed successfully for {secret_name}")
        return new_access_token

    def _exchange_refresh_token(
        self,
        token_endpoint: str,
        client_id: str,
        client_secret: Optional[str],
        refresh_token: str,
    ) -> tuple[Optional[str], Optional[datetime]]:
        """
        Perform OAuth 2.0 refresh token exchange (RFC 6749 section 6).
        Returns (new_access_token, new_expires_at) or (None, None) on failure.
        """
        import urllib.request
        import urllib.parse

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }
        if client_secret:
            payload["client_secret"] = client_secret

        try:
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(token_endpoint, data=data, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")

            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())

            new_token = body.get("access_token")
            if not new_token:
                logger.error(f"[AC13] Refresh response missing access_token: {body}")
                return None, None

            expires_in = body.get("expires_in")
            new_expires_at = None
            if expires_in:
                new_expires_at = datetime.now(timezone.utc).replace(microsecond=0)
                from datetime import timedelta
                new_expires_at = new_expires_at + timedelta(seconds=int(expires_in))

            return new_token, new_expires_at

        except Exception as e:
            logger.error(f"[AC13] Refresh token exchange failed: {e}")
            return None, None
