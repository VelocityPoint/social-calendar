"""
publisher/models.py -- Pydantic models for Post, Brand, Credentials

Ref: AC1 (schema), AC6 (status/post_ids), AC8 (brand config),
     AC13 (token refresh), AC14 (Instagram/Facebook shared creds),
     AC16 (multi-brand)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


VALID_PLATFORMS = {"facebook", "linkedin", "gbp", "x", "instagram"}
VALID_STATUSES = {
    "draft", "ready", "scheduled", "published", "failed", "deferred", "video-pending"
}
VALID_AUTHORS = {"dave", "velocitypoint"}


class CreativeAsset(BaseModel):
    type: str  # image, video, heygen
    path: Optional[str] = None      # relative to brands/<brand>/assets/
    url: Optional[str] = None       # public URL
    video_url: Optional[str] = None # Azure Blob URL for HeyGen output (Phase 2)
    platforms: Optional[list[str]] = None  # platform override; None = all platforms


class Post(BaseModel):
    """Represents a parsed post document."""

    # Core fields (required)
    id: str
    publish_at: str  # ISO 8601 with timezone — validated by validate-post.py
    platforms: list[str]
    status: str
    brand: str
    author: str  # GHL account mapping: dave | velocitypoint (required per AC8)

    # GHL-specific fields (AC8)
    ghl_mode: bool = True  # True = publish via GHL Social Planner (default)
    account_id: Optional[str] = None  # Override: GHL account ID (normally resolved from brand.yaml)

    # Optional metadata
    campaign: Optional[str] = None
    tags: Optional[list[str]] = None

    # Written by publisher after publish (AC6, AC8)
    published_at: Optional[str] = None
    ghl_post_id: Optional[str] = None  # GHL Social Planner post ID (set by publisher)
    post_ids: Optional[dict[str, str]] = None
    error: Optional[str] = None  # Last error if status=failed (set by publisher)

    # Creative assets
    creative: Optional[list[CreativeAsset]] = None

    # Internal: file path (not in frontmatter)
    _file_path: Optional[str] = None

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str]) -> list[str]:
        for p in v:
            if p not in VALID_PLATFORMS:
                raise ValueError(f"Unknown platform: {p}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status: '{v}'. "
                f"Valid: {sorted(VALID_STATUSES)}. "
                f"Lifecycle: draft → ready → scheduled → published | failed"
            )
        return v

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        if v not in VALID_AUTHORS:
            raise ValueError(
                f"Invalid author: '{v}'. Must be one of {sorted(VALID_AUTHORS)}. "
                f"'author' maps to a GHL social account via brand.yaml → ghl.accounts."
            )
        return v

    def is_published_to(self, platform: str) -> bool:
        """Check if post_ids already has an entry for this platform (idempotency check)."""
        return bool(self.post_ids and self.post_ids.get(platform))

    def get_publish_at_utc(self) -> datetime:
        """Parse publish_at to an aware datetime object."""
        from datetime import timezone
        dt = datetime.fromisoformat(self.publish_at.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)

    def is_ready_to_publish(self) -> bool:
        """Returns True if publish_at <= now UTC and status is 'scheduled'."""
        from datetime import timezone
        if self.status != "scheduled":
            return False
        return self.get_publish_at_utc() <= datetime.now(timezone.utc)


class BrandCadence(BaseModel):
    posts_per_week: int
    preferred_times: list[str]  # HH:MM strings
    timezone: Optional[str] = "America/Los_Angeles"


class BrandCredentials(BaseModel):
    """
    Maps platform name to Key Vault secret name (not raw tokens).
    Instagram shares facebook creds (AC14).
    """
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    gbp: Optional[str] = None
    x: Optional[str] = None
    instagram: Optional[str] = None  # Should reference same KV key as facebook per AC14

    def get_kv_secret_name(self, platform: str) -> Optional[str]:
        return getattr(self, platform, None)


class GHLAccountMap(BaseModel):
    """
    GHL Social Planner account mapping for a brand author.
    Maps platform names to GHL account IDs.
    Added as part of Step 3/4 (post schema + brand config ghl block).
    """
    linkedin: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    google_business: Optional[str] = None
    gbp: Optional[str] = None  # Alias for google_business

    def get_account_id(self, platform: str) -> Optional[str]:
        """Return GHL account ID for a platform. Returns None if not configured."""
        # Normalise gbp / google_business
        if platform == "gbp":
            return self.gbp or self.google_business
        if platform == "google_business":
            return self.google_business or self.gbp
        return getattr(self, platform, None)


class GHLConfig(BaseModel):
    """
    GHL block in brand.yaml (added in Step 4: feat: brand config ghl block).
    Optional — absent until Step 4 PR merges. Validated gracefully in publisher.
    """
    location_id: Optional[str] = None
    accounts: Optional[dict[str, dict[str, str]]] = None  # author -> {platform -> account_id}

    def resolve_account_id(self, author: str, platform: str) -> Optional[str]:
        """Resolve GHL account ID for a given author + platform."""
        if not self.accounts:
            return None
        author_map = self.accounts.get(author, {})
        return author_map.get(platform) or author_map.get(
            "google_business" if platform == "gbp" else platform
        )


class Brand(BaseModel):
    brand_name: str
    credentials: BrandCredentials
    cadence: dict[str, BrandCadence]  # platform -> cadence
    pillars: list[str]
    avatar_id: Optional[str] = None  # HeyGen avatar (Phase 2)
    slug: Optional[str] = None  # Set from directory name
    ghl: Optional[GHLConfig] = None  # GHL config block (Step 4)

    @classmethod
    def from_yaml(cls, yaml_path: Path, slug: str) -> "Brand":
        import yaml
        data = yaml.safe_load(yaml_path.read_text())
        data["slug"] = slug
        # Normalize cadence values
        cadence_raw = data.get("cadence", {})
        cadence = {k: BrandCadence(**v) for k, v in cadence_raw.items()}
        data["cadence"] = cadence
        creds_raw = data.get("credentials", {})
        data["credentials"] = BrandCredentials(**creds_raw)
        # GHL config block (optional — present after Step 4 merges)
        ghl_raw = data.get("ghl")
        if ghl_raw:
            data["ghl"] = GHLConfig(**ghl_raw)
        return cls(**data)


class RateLimitState(BaseModel):
    """Per-platform rate limit counter stored as JSON (AC-OQ6)."""
    platform: str
    window_start: str  # ISO 8601 UTC
    call_count: int = 0
    limit: int
    window_seconds: int

    # Platform defaults (conservative per AC-OQ6)
    DEFAULTS: dict[str, dict] = {
        "linkedin":  {"limit": 100,  "window_seconds": 86400},   # 100/day
        "facebook":  {"limit": 200,  "window_seconds": 3600},    # 200/hour
        "instagram": {"limit": 50,   "window_seconds": 86400},   # 50/24h
        "x":         {"limit": 500,  "window_seconds": 2592000}, # 500/month (~30d)
        "gbp":       {"limit": 1000, "window_seconds": 86400},   # 1000/day (conservative)
    }

    @classmethod
    def load_or_create(cls, state_dir: Path, platform: str) -> "RateLimitState":
        """Load state from JSON file or create fresh with platform defaults."""
        from datetime import timezone
        state_file = state_dir / f"{platform}.json"
        defaults = cls.DEFAULTS.get(platform, {"limit": 100, "window_seconds": 86400})

        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                return cls(**data)
            except Exception:
                pass  # Corrupt file — recreate

        return cls(
            platform=platform,
            window_start=datetime.now(timezone.utc).isoformat(),
            call_count=0,
            **defaults,
        )

    def is_window_expired(self) -> bool:
        """Check if current window has expired and should reset."""
        from datetime import timezone
        window_start = datetime.fromisoformat(self.window_start.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - window_start).total_seconds()
        return elapsed >= self.window_seconds

    def is_limited(self) -> tuple[bool, Optional[str]]:
        """
        Returns (is_limited, next_window_iso).
        Handles window expiry reset per AC-OQ6.
        """
        from datetime import timezone, timedelta
        if self.is_window_expired():
            # Reset window — call is allowed
            self.window_start = datetime.now(timezone.utc).isoformat()
            self.call_count = 0
            return False, None

        if self.call_count >= self.limit:
            window_start_dt = datetime.fromisoformat(self.window_start.replace("Z", "+00:00"))
            next_window = window_start_dt + timedelta(seconds=self.window_seconds)
            return True, next_window.isoformat()

        return False, None

    def increment(self) -> None:
        """Increment call_count after a successful API call (AC-OQ6)."""
        self.call_count += 1

    def save(self, state_dir: Path) -> None:
        """Write state to JSON file atomically using write-then-rename (AC-OQ6)."""
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / f"{self.platform}.json"
        tmp_file = state_dir / f"{self.platform}.json.tmp"
        tmp_file.write_text(self.model_dump_json(indent=2))
        tmp_file.rename(state_file)


class PublishResult(BaseModel):
    """Result of a publish attempt for one post+platform."""
    post_id: str
    platform: str
    success: bool
    platform_post_id: Optional[str] = None  # returned by platform API
    error: Optional[str] = None
    attempts: int = 1
    deferred: bool = False  # rate-limited, retry next run
