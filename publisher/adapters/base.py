"""
publisher/adapters/base.py -- Abstract base adapter

All platform adapters inherit from BaseAdapter.
Defines the interface: publish(), auth_check(), rate_limit_check().

Ref: AC2 (auth_check), AC3/AC4 (publish), AC-OQ6 (rate_limit_check)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..models import Post, Brand, RateLimitState


logger = logging.getLogger(__name__)


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
        import os
        # Try env var first (Phase 1 fallback, also used in GH Actions environment secrets)
        value = os.environ.get(secret_name.upper().replace("-", "_"))
        if value:
            return value

        # Try Key Vault via az CLI (Phase 2 — if AZURE_KEY_VAULT_NAME is set)
        vault_name = os.environ.get("AZURE_KEY_VAULT_NAME")
        if vault_name:
            import subprocess
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
