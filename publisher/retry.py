"""
publisher/retry.py -- Retry logic with exponential backoff (AC-OQ4)

Strategy per Dave's decision:
  - 3 attempts total
  - Backoff delays: 10s after attempt 1, 30s after attempt 2
  - On 429: respect Retry-After header (max 300s)
  - On exhaustion: create GitHub issue + Telegram notification

Ref: AC7 (GitHub issue on failure), AC-OQ4 (retry timing and dedup)
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Per Dave's OQ4 decision
BACKOFF_DELAYS = [10, 30, 90]  # seconds between attempts; len = number of delays = retries - 1
MAX_RETRIES = len(BACKOFF_DELAYS) + 1  # = 3 total attempts
MAX_RETRY_AFTER = 300  # cap on Retry-After header value (seconds)


class PublishError(Exception):
    """A retryable publish failure."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(PublishError):
    """HTTP 429 rate limit hit."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class PermanentError(Exception):
    """A non-retryable failure (e.g. 400 Bad Request, auth error)."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def publish_with_retry(
    publish_fn: Callable[[], str],
    post_id: str,
    platform: str,
    github_token: Optional[str] = None,
    github_repo: Optional[str] = None,
    post_file_path: Optional[str] = None,
    publish_at: Optional[str] = None,
) -> Optional[str]:
    """
    Call publish_fn() with retry logic per AC-OQ4.

    publish_fn: callable that returns a platform post ID string on success,
                raises PublishError/RateLimitError on failure,
                raises PermanentError on non-retryable failure.

    Returns platform post ID on success, None on exhaustion.
    On exhaustion: creates GitHub issue + sends Telegram notification per AC7/OQ4.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = publish_fn()
            logger.info(f"[PUBLISHED] {post_id} on {platform} (attempt {attempt}/{MAX_RETRIES})")
            return result

        except PermanentError as e:
            logger.error(
                f"[PERMANENT FAILURE] {post_id} on {platform}: "
                f"HTTP {e.status_code} {e} — not retrying"
            )
            _handle_final_failure(
                post_id, platform, str(e), e.status_code, attempt,
                github_token, github_repo, post_file_path, publish_at
            )
            return None

        except RateLimitError as e:
            wait = min(e.retry_after or BACKOFF_DELAYS[min(attempt - 1, len(BACKOFF_DELAYS) - 1)], MAX_RETRY_AFTER)
            logger.warning(
                f"[RETRY {attempt}/{MAX_RETRIES}] {post_id} on {platform}: "
                f"429 rate limited, waiting {wait}s (Retry-After={e.retry_after})"
            )
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(wait)

        except PublishError as e:
            delay = BACKOFF_DELAYS[attempt - 1] if attempt <= len(BACKOFF_DELAYS) else 0
            logger.warning(
                f"[RETRY {attempt}/{MAX_RETRIES}] {post_id} on {platform}: "
                f"{e} (HTTP {e.status_code}), waiting {delay}s"
            )
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(delay)

        except Exception as e:
            # Unexpected error — treat as retryable but log at error level
            delay = BACKOFF_DELAYS[attempt - 1] if attempt <= len(BACKOFF_DELAYS) else 0
            logger.error(
                f"[RETRY {attempt}/{MAX_RETRIES}] {post_id} on {platform}: "
                f"unexpected error: {e}, waiting {delay}s"
            )
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(delay)

    # All retries exhausted
    logger.error(f"[FAILED] {post_id} on {platform}: all {MAX_RETRIES} attempts exhausted")
    _handle_final_failure(
        post_id, platform,
        str(last_error) if last_error else "Unknown error",
        getattr(last_error, "status_code", None),
        MAX_RETRIES,
        github_token, github_repo, post_file_path, publish_at
    )
    return None


def _handle_final_failure(
    post_id: str,
    platform: str,
    error_message: str,
    status_code: Optional[int],
    attempt_count: int,
    github_token: Optional[str],
    github_repo: Optional[str],
    post_file_path: Optional[str],
    publish_at: Optional[str],
) -> None:
    """Create GitHub issue and send Telegram notification per AC7 and Dave's OQ4 decision."""
    _create_github_issue(
        post_id, platform, error_message, status_code, attempt_count,
        github_token, github_repo, post_file_path, publish_at
    )
    _send_telegram_notification(post_id, platform, error_message, status_code)


def _create_github_issue(
    post_id: str,
    platform: str,
    error_message: str,
    status_code: Optional[int],
    attempt_count: int,
    github_token: Optional[str],
    github_repo: Optional[str],
    post_file_path: Optional[str],
    publish_at: Optional[str],
) -> None:
    """
    Create or update a GitHub issue for the failed publish (AC7, AC-OQ4).

    Deduplication: if an open issue for post_id + platform already exists,
    add a comment instead of creating a new issue.
    """
    if not github_token or not github_repo:
        logger.warning("[GITHUB ISSUE] No GITHUB_TOKEN or GITHUB_REPOSITORY set — cannot create issue")
        return

    title = f"[Publish Failed] {post_id} on {platform}"
    search_query = f'"{title}" repo:{github_repo} is:open'

    # Check for existing open issue (AC-OQ4 dedup)
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--repo", github_repo, "--search", title, "--state", "open", "--json", "number,title"],
            capture_output=True, text=True,
            env={**os.environ, "GITHUB_TOKEN": github_token},
        )
        import json
        existing = json.loads(result.stdout or "[]")
        matching = [i for i in existing if i["title"] == title]

        if matching:
            issue_number = matching[0]["number"]
            comment_body = (
                f"Publish retry failed again.\n\n"
                f"Error: {error_message}\n"
                f"HTTP Status: {status_code or 'N/A'}\n"
                f"Attempts: {attempt_count}\n"
            )
            subprocess.run(
                ["gh", "issue", "comment", str(issue_number), "--repo", github_repo, "--body", comment_body],
                env={**os.environ, "GITHUB_TOKEN": github_token},
            )
            logger.info(f"[GITHUB ISSUE] Added comment to existing issue #{issue_number} for {post_id} on {platform}")
            return
    except Exception as e:
        logger.warning(f"[GITHUB ISSUE] Dedup check failed: {e}")

    # Create new issue (AC7)
    body_lines = [
        f"Post ID: {post_id}",
        f"Platform: {platform}",
        f"Error: {error_message}",
        f"HTTP Status: {status_code or 'N/A'}",
        f"Attempts: {attempt_count}",
    ]
    if post_file_path:
        body_lines.append(f"Post file: {post_file_path}")
    if publish_at:
        body_lines.append(f"Scheduled for: {publish_at}")

    body = "\n".join(body_lines)

    try:
        subprocess.run(
            [
                "gh", "issue", "create",
                "--repo", github_repo,
                "--title", title,
                "--body", body,
                "--label", "publish-failure",
                "--label", "agent:bob",
            ],
            capture_output=True, text=True,
            env={**os.environ, "GITHUB_TOKEN": github_token},
        )
        logger.info(f"[GITHUB ISSUE] Created issue for {post_id} on {platform}")
    except Exception as e:
        logger.error(f"[GITHUB ISSUE] Failed to create issue: {e}")


def _send_telegram_notification(
    post_id: str,
    platform: str,
    error_message: str,
    status_code: Optional[int],
) -> None:
    """
    Send Telegram notification per Dave's OQ4 decision (notify on final failure).
    Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("[TELEGRAM] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping notification")
        return

    message = (
        f"Publish failed: {post_id} on {platform}\n"
        f"Error: {error_message}\n"
        f"HTTP {status_code or 'N/A'} after {MAX_RETRIES} attempts\n"
        f"GitHub issue created. Check the repo for details."
    )

    try:
        import urllib.request
        import urllib.parse
        import json

        data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=data,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info(f"[TELEGRAM] Notification sent for {post_id} on {platform}")
            else:
                logger.warning(f"[TELEGRAM] Notification returned HTTP {resp.status}")
    except Exception as e:
        logger.warning(f"[TELEGRAM] Failed to send notification: {e}")
