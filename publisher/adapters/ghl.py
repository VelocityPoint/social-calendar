"""
publisher/adapters/ghl.py -- GoHighLevel (GHL) adapter for Loki

Phase 1 skeleton with mocked API calls for testing.
Full API integration uses GHL REST API endpoints.

Ref: AC3 (text publish), AC4 (image publish), AC6 (list accounts)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, List

import requests

from .base import BaseAdapter
from ..models import Post, Brand
from ..retry import PublishError, RateLimitError, PermanentError


logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when GHL API returns 429 Too Many Requests."""
    def __init__(self, status_code: int, retry_after_seconds: Optional[int] = None):
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limited: {retry_after_seconds}s before retry")


class PermanentError(Exception):
    """Raised for non-retryable GHL errors (400, 401, 403, etc.)."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class GHLError(Exception):
    """General GHL API error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GHL Error {status_code}: {message}")


BASE_URL = "https://services.leadconnectorhq.com"
API_VERSION = "2021-07-28"


class GHLAdapter(BaseAdapter):
    """
    GoHighLevel Social Calendar Adapter.

    Implements the social calendar interface for publishing to GHL.
    Uses GHL API v1 (Lead Connector Hub) with Bearer token authentication.
    
    Auth: GHL_API_KEY env var → OAuth2 Bearer token
    Base URL: https://services.leadconnectorhq.com
    """

    platform = "ghl"

    def __init__(self, brand: Brand, state_dir: Path):
        super().__init__(brand, state_dir)
        self._bearer_token: Optional[str] = None
        self._authenticated = False

    def _get_bearer_token(self) -> str:
        """
        Load GHL Bearer token from Key Vault or env var.
        
        The GHL API uses OAuth2 with Bearer token authentication.
        Token is stored in Azure Key Vault under secret name 'ghl-api-key'.
        Phase 1 falls back to GHL_API_KEY environment variable.
        """
        import os
        
        # Try env var first (Phase 1 fallback for GitHub Actions, local dev)
        token = os.environ.get("GHL_API_KEY")
        if token:
            return token

        # Try Key Vault (Phase 2)
        kv_name = self.brand.credentials.get_kv_secret_name("ghl")
        if not kv_name:
            raise PermanentError(
                "No GHL credential configured in brand.yaml",
                status_code=401,
            )
        
        secret_value = self._get_credential(kv_name)
        if not secret_value:
            raise PermanentError(
                f"Could not retrieve GHL token from secret: {kv_name}",
                status_code=401,
            )
        return secret_value

    def auth_check(self) -> bool:
        """
        AC2: Verify GHL API authentication.
        
        Makes a lightweight authenticated API call to verify credentials.
        Returns True if auth is valid, False otherwise.
        """
        try:
            token = self._get_bearer_token()
            # Test endpoint: GET /v1/me (standard OAuth2 introspection)
            resp = requests.get(
                f"{BASE_URL}/v1/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            
            if resp.status_code == 200:
                logger.info("[AUTH OK] ghl")
                self._authenticated = True
                return True
            else:
                logger.error(
                    f"[AUTH FAIL] ghl: HTTP {resp.status_code} {resp.text[:200]}"
                )
                self._authenticated = False
                return False
        except RateLimitError:
            logger.error("[AUTH FAIL] ghl: rate limited during auth check")
            return False
        except Exception as e:
            logger.error(f"[AUTH FAIL] ghl: {e}")
            return False

    def _request(
        self, method: str, path: str, body: Optional[dict] = None,
    ) -> requests.Response:
        """
        Make authenticated API request to GHL.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API endpoint path (e.g., /v1/accounts, /v1/posts/{id})
            body: Optional request body for POST/PUT
        
        Returns:
            requests.Response object
        
        Raises:
            RateLimitError: HTTP 429 with retry-after from headers
            PermanentError: Non-retryable errors (401, 403, 400)
            GHLError: General GHL API errors
        """
        if not self._authenticated and method == "GET":
            # Auth check on first GET request if not yet authenticated
            if not self.auth_check():
                raise PermanentError("Authentication failed", status_code=401)

        url = f"{BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {self._get_bearer_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                resp = requests.post(url, json=body, headers=headers, timeout=60)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=30)
            else:
                raise PermanentError(f"Unsupported method: {method}", status_code=400)

            # Handle rate limiting
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60")) or 60
                raise RateLimitError(status_code=429, retry_after_seconds=retry_after)

            # Handle permanent errors (401, 403, 400)
            if resp.status_code in (401, 403):
                raise PermanentError(
                    f"GHL auth error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                )
            
            if resp.status_code == 400:
                raise PermanentError(
                    f"GHL bad request {resp.status_code}: {resp.text[:500]}",
                    status_code=resp.status_code,
                )

            logger.debug(f"GHL {method} {path}: {resp.status_code}")
            return resp

        except RateLimitError:
            raise
        except PermanentError:
            raise
        except requests.exceptions.RequestException as e:
            raise PublishError(f"GHL network error: {e}")

    def _resolve_accounts(self, author: Optional[str], platform: str) -> List[str]:
        """
        Resolve GHL account IDs from brand.yaml mapping.
        
        Args:
            author: Platform username or email to match against accounts
            platform: Platform identifier (ignored for GHL - single account type)
        
        Returns:
            List of account IDs that match the provided author/platform
        
        For GHL, we typically have one master account. This method extracts
        the account ID from brand.yaml configuration.
        """
        # In Phase 1 with mocks, return a placeholder or extract from config
        import yaml
        
        try:
            brands_path = Path(self.brand.path).parent.parent / "brands.yaml"
            if not brands_path.exists():
                brands_path = Path(brands_path)
            
            if brands_path.exists():
                with open(brands_path) as f:
                    brands_config = yaml.safe_load(f)
                
                # Extract GHL accounts from config
                ghl_accounts = brands_config.get("accounts", {}).get("ghl", [])
                
                # Filter by author/platform if provided
                if author and platform:
                    return [
                        acc_id for acc_id in ghl_accounts
                        if acc_id.lower().strip() in str(author).lower()
                    ]
                elif not author:
                    # Return all GHL accounts
                    return [str(acc) for acc in ghl_accounts]
        
            except (yaml.YAMLError, IOError):
                logger.warning(f"Could not parse brand.yaml for account resolution")
        
        except Exception as e:
            logger.warning(f"Account resolution failed: {e}")

    def get_accounts(self) -> List[str]:
        """
        AC6: List all available GHL accounts.
        
        Returns:
            List of account IDs configured for GHL publishing
        
        Note: GHL typically has a single master account, but this method
              supports multi-account setups if the API allows listing them.
        """
        try:
            resp = self._request("GET", "/v1/accounts")
            if resp.status_code == 200:
                data = resp.json()
                # Response format may be list or dict with 'data' key
                accounts = data if isinstance(data, list) else data.get("data", [])
                return [str(acc) for acc in accounts]
            elif resp.status_code == 401:
                raise PermanentError("Authentication failed - no accounts accessible", status_code=401)
            
        except RateLimitError as e:
            raise
        except PermanentError as e:
            raise
        except Exception as e:
            # Fallback for mock mode: return placeholder account
            logger.info("Using mock GHL account ID")
            return ["mock_ghl_account_id"]

    def publish(
        self,
        post: Post,
        copy_text: str,
        image_url: Optional[str] = None,
    ) -> str:
        """
        Publish a post to GoHighLevel.
        
        Args:
            post: Post model with id, publish_at, author, etc.
            copy_text: Text content for the post
            image_url: Optional URL to image asset (GHL supports image URLs)
        
        Returns:
            GHL post ID string
        
        Raises:
            PublishError: Retryable failure (5xx, network)
            RateLimitError: HTTP 429
            PermanentError: Non-retryable (401, 403, 400)
        """
        # Check rate limit before publishing
        if not self.check_rate_limit(post.id):
            raise PublishError("Publish deferred - rate limit exceeded", status_code=429)

        try:
            # Prepare post payload
            body = {
                "type": "text",
                "content": copy_text,
            }

            # Add image if provided
            if image_url:
                body["image_url"] = image_url
                body["type"] = "post_with_image"

            # For mock mode, return a mock post ID
            import os
            if os.environ.get("GHL_MOCK_MODE", "").lower() == "true":
                logger.info(f"[MOCK] Publishing post {post.id}: copy_text='{copy_text[:50]}...' to GHL")
                return f"mock_post_{post.id}"

            # Actual API call: POST /v1/posts (GHL Lead Connector Hub)
            resp = self._request("POST", "/v1/posts", body=body)

            if resp.status_code == 201:
                data = resp.json()
                post_id = data.get("id") or data.get("post_id")
                logger.info(f"[PUBLISHED] {post.id} on ghl: post_id={post_id}")
                self.increment_rate_limit(post_id)
                return str(post_id)
            
            # Handle error responses
            resp.raise_for_status()

        except RateLimitError:
            raise
        except PermanentError:
            raise
        except PublishError:
            raise
        except Exception as e:
            raise PublishError(f"GHL publish failed: {e}")

    def delete(self, ghl_post_id: str) -> bool:
        """
        Delete a post from GoHighLevel.
        
        Args:
            ghl_post_id: The GHL post ID to delete
        
        Returns:
            True if deletion was successful
        
        Raises:
            RateLimitError: HTTP 429
            PermanentError: Non-retryable (401, 403, 404)
        """
        try:
            resp = self._request("DELETE", f"/v1/posts/{ghl_post_id}")

            if resp.status_code == 204 or resp.status_code == 200:
                logger.info(f"[DELETED] ghl post: {ghl_post_id}")
                return True
            elif resp.status_code == 404:
                raise PermanentError(f"Post not found: {ghl_post_id}", status_code=404)
            elif resp.status_code == 401 or resp.status_code == 403:
                raise PermanentError(f"Auth error deleting post: {resp.text[:200]}", status_code=resp.status_code)
            
            resp.raise_for_status()
            return False

        except RateLimitError:
            raise
        except PermanentError:
            raise
        except Exception as e:
            raise PublishError(f"GHL delete failed: {e}")

    def get_post(self, ghl_post_id: str) -> Optional[dict]:
        """
        Retrieve a single post from GoHighLevel.
        
        Args:
            ghl_post_id: The GHL post ID to retrieve
        
        Returns:
            Post data dict or None if not found
        
        Raises:
            RateLimitError: HTTP 429
            PermanentError: Non-retryable (401, 403)
        """
        try:
            resp = self._request("GET", f"/v1/posts/{ghl_post_id}")

            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"[RETRIEVED] ghl post: {ghl_post_id}")
                return data
            elif resp.status_code == 404:
                logger.warning(f"[NOT FOUND] ghl post: {ghl_post_id}")
                return None
            
            if resp.status_code in (401, 403):
                raise PermanentError(
                    f"Auth error getting post: {resp.text[:200]}",
                    status_code=resp.status_code,
                )
            
            resp.raise_for_status()

        except RateLimitError:
            raise
        except PermanentError:
            raise
        except Exception as e:
            raise PublishError(f"GHL get post failed: {e}")

    def list_posts(self, filters: Optional[dict] = None) -> List[dict]:
        """
        List recent posts from GoHighLevel.
        
        Args:
            filters: Optional dict of query params (e.g., {"status": "published", "date_from": "2024-01-01"})
        
        Returns:
            List of post data dicts
        
        Raises:
            RateLimitError: HTTP 429
            PermanentError: Non-retryable (401, 403)
        """
        try:
            params = filters or {}
            # Add default status filter if not specified
            if "status" not in params:
                params["status"] = "published"

            resp = self._request("GET", "/v1/posts", params=params)

            if resp.status_code == 200:
                data = resp.json()
                # Normalize response format (handle list vs {"data": [...]})
                posts = data if isinstance(data, list) else data.get("data", [])
                logger.info(f"[LISTED] ghl posts: {len(posts)} found")
                return posts
            
            resp.raise_for_status()

        except RateLimitError:
            raise
        except PermanentError:
            raise
        except Exception as e:
            raise PublishError(f"GHL list posts failed: {e}")
