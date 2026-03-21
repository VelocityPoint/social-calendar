# social-calendar

GitHub-native social media content calendar and automated publisher for VelocityPoint brands.

Posts are authored as Markdown files, reviewed through a standard GitHub pull request, and published automatically by a GitHub Actions workflow. The merged PR is the sole approval gate. Nothing publishes without it.

**Tracking issue:** VelocityPoint/Core_Business#222
**Phase:** 1 MVP — manual authoring, automated publish
**Phase 2 (planned):** AI content generation from briefs, HeyGen video integration

---

## Contents

- [How It Works](#how-it-works)
- [Repository Structure](#repository-structure)
- [Creating a Post](#creating-a-post)
- [Post Document Format](#post-document-format)
- [Post Status Lifecycle](#post-status-lifecycle)
- [Publishing Workflow](#publishing-workflow)
- [Brand Configuration](#brand-configuration)
- [Credential Setup](#credential-setup)
- [Adding a New Brand](#adding-a-new-brand)
- [Adding a New Platform Adapter](#adding-a-new-platform-adapter)
- [Running Locally](#running-locally)
- [Validating Posts Locally](#validating-posts-locally)
- [Platform Notes](#platform-notes)

---

## How It Works

1. Author a post document at `brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-<slug>.md`
2. Open a pull request — the `validate-pr.yml` workflow validates schema and copy sections before merge is allowed
3. Merge to `main` — the merged PR is the approval gate; nothing publishes without a commit on `main`
4. The `publish.yml` workflow runs every 10 minutes on a cron schedule and also triggers immediately on any push to `main` that touches calendar files
5. Publisher checks `publish_at` against the current time, publishes each target platform in turn, and commits the platform post IDs and final status back to the document as `[skip ci]`

No post ever reaches a platform API without first being:
- Schema-valid (caught at PR time by `validate-pr.yml`)
- Merged to `main` (enforced at runtime by `is_committed_on_main()` in `state.py`)
- Past its `publish_at` timestamp

---

## Repository Structure

```
brands/
  <brand>/
    brand.yaml                   Brand config: credential refs, cadence, pillars, voice
    assets/                      Image assets referenced by post creative blocks
    .state/
      rate_limits/               Per-platform rate limit counters (JSON, committed by publisher)
    calendar/
      YYYY/
        MM/
          YYYY-MM-DD-<slug>.md   Post documents

campaigns/
  <campaign>/
    campaign.yaml                Campaign metadata
    brief.md                     Content brief (Phase 2: feeds AI generation)

templates/
  *.md                           Example post templates for authors

publisher/
  publisher.py                   Main orchestrator
  models.py                      Post, Brand, RateLimitState Pydantic models
  state.py                       Frontmatter read/write, main branch verification
  retry.py                       Retry with 10s/30s/90s backoff, failure handling
  adapters/
    base.py                      Abstract adapter interface
    x_twitter.py                 X/Twitter via xurl CLI
    facebook.py                  Facebook via Meta Graph API
    instagram.py                 Instagram via Meta Graph API (shared Facebook credentials)
    linkedin.py                  LinkedIn Posts API
    gbp.py                       Google Business Profile API

scripts/
  validate-post.py               Post document schema validator (AC1)
  validate-brand.py              Brand config validator (AC8)

schemas/
  post.schema.yaml               Post document schema definition

.github/workflows/
  publish.yml                    Scheduled publisher (10-min cron + push trigger)
  validate-pr.yml                Schema validation gate on pull requests
  auth-check.yml                 Weekly credential health check
```

---

## Creating a Post

### Step 1: Create the file

Place the post document at the correct path:

```
brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-<slug>.md
```

Example:

```
brands/secondring/calendar/2026/04/2026-04-01-never-miss-a-call.md
```

The `YYYY-MM-DD` prefix and slug must be lowercase with hyphens. The filename doubles as a human-readable identifier.

### Step 2: Write the frontmatter

Every post document opens with a YAML frontmatter block:

```yaml
---
id: 2026-04-01-never-miss-a-call
publish_at: '2026-04-01T09:00:00-07:00'
platforms:
  - linkedin
  - facebook
  - x
  - gbp
  - instagram
status: scheduled
brand: secondring
author: davelawler-vp
tags:
  - ai-answering
  - q2-2026
---
```

Quote the `publish_at` value (or use `Z` UTC suffix) to prevent YAML from parsing it as a datetime object. Both forms are accepted by the validator, but quoting is cleaner.

### Step 3: Write platform copy sections

After the frontmatter, add one section per target platform:

```markdown
# LinkedIn Version

(up to 3,000 characters)

# Facebook Version

(up to 2,200 characters)

# X Version

(up to 280 characters)

# Google Business Profile Version

(up to 1,500 characters)

# Instagram Version

(up to 2,200 characters)
```

The section header must match exactly: `# {Platform Name} Version`. The publisher extracts only the section matching the target platform. Extra sections (platforms not in the `platforms` list) are ignored without error.

### Step 4: Add image assets (optional)

Place image files in `brands/<brand>/assets/` and reference them in the frontmatter `creative` block:

```yaml
creative:
  - type: image
    path: never-miss-a-call.jpg
```

To send a different image per platform:

```yaml
creative:
  - type: image
    path: never-miss-a-call-square.jpg
    platforms:
      - instagram
  - type: image
    path: never-miss-a-call-landscape.jpg
    platforms:
      - linkedin
      - facebook
```

Image requirements across all platforms: JPEG format, width 320–1440px, file size under 8MB.

### Step 5: Validate locally

```bash
pip install pyyaml
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-never-miss-a-call.md
```

### Step 6: Open a pull request

Open a PR against `main`. The `validate-pr.yml` workflow runs automatically and blocks merge if any validation error is found. Merge when the check passes and review is complete.

The publisher runs within 10 minutes of the merge (sooner if the push trigger fires immediately).

---

## Post Document Format

### Required frontmatter fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique post identifier. Format: `YYYY-MM-DD-<slug>`. Must match the filename without `.md`. |
| `publish_at` | string | ISO 8601 datetime with timezone offset. Example: `'2026-04-01T09:00:00-07:00'` or `'2026-04-01T16:00:00Z'`. Bare datetimes without an offset fail validation. |
| `platforms` | list | One or more of: `facebook`, `linkedin`, `gbp`, `x`, `instagram`. Non-empty. |
| `status` | string | Initial value must be `scheduled`. See status lifecycle below. |
| `brand` | string | Brand slug matching a directory under `brands/`. Example: `secondring`. |

### Optional frontmatter fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | GitHub username or agent name. Informational only. |
| `campaign` | string | Campaign slug linking to a directory under `campaigns/`. |
| `tags` | list | Content tags for filtering and reporting. |
| `creative` | list | Image or video assets. See creative block format below. |

### Publisher-written fields (do not set manually)

| Field | Type | Description |
|-------|------|-------------|
| `published_at` | string | ISO 8601 UTC timestamp. Set by publisher after all platforms succeed. |
| `post_ids` | object | Map of platform to platform-specific post ID. Set incrementally as each platform succeeds. |

### Creative block format

```yaml
creative:
  - type: image         # image | video | heygen (heygen is Phase 2)
    path: image.jpg     # Relative to brands/<brand>/assets/
    platforms:          # Optional: restrict this asset to specific platforms
      - linkedin
      - facebook
```

### Full example

```markdown
---
id: 2026-04-01-never-miss-a-call
publish_at: '2026-04-01T09:00:00-07:00'
platforms:
  - linkedin
  - facebook
  - x
  - gbp
  - instagram
status: scheduled
brand: secondring
author: davelawler-vp
tags:
  - ai-answering
  - q2-2026
---

# LinkedIn Version

Every missed call is a missed customer.

Service businesses run on the phone. A roofer finishing a job, an HVAC tech on a ladder,
a plumber under a sink -- none of them can answer when it rings. The call goes to voicemail.
The customer calls the next number on their list.

Second Ring's AI receptionist answers every call, qualifies the lead, and books the appointment.

30-day risk-free trial. No long-term contracts. Setup in 48 hours.

second-ring.com

# Facebook Version

How many calls did you miss last month?

(Facebook copy here -- up to 2,200 characters)

# X Version

Every missed call is a missed customer. Second Ring's AI receptionist answers 24/7.

$297/mo. 30-day guarantee. second-ring.com

# Google Business Profile Version

(GBP copy here -- up to 1,500 characters)

# Instagram Version

(Instagram copy here -- up to 2,200 characters. Instagram requires an image.)
```

---

## Post Status Lifecycle

The frontmatter `status` field is the canonical state machine. The publisher reads it before acting and writes it back after each run.

| Status | Set by | Meaning |
|--------|--------|---------|
| `draft` | Author | Work in progress. Not ready for merge. The publisher skips draft posts. |
| `scheduled` | Author | Merged to `main`, awaiting `publish_at`. The publisher processes this status. |
| `published` | Publisher | All targeted platforms confirmed. `post_ids` map is fully populated. |
| `failed` | Publisher | All retry attempts exhausted on at least one platform. A GitHub issue is created tagged `agent:bob`. |
| `deferred` | Publisher | One or more platforms hit a rate limit. No issue is created. The publisher retries on the next run. |
| `video-pending` | Publisher | HeyGen video render not yet complete (Phase 2). |

If a run publishes some platforms but not all before a crash, per-platform `post_ids` entries are written incrementally. The next run skips already-published platforms and retries only the outstanding ones.

---

## Publishing Workflow

### Triggers

The `publish.yml` workflow fires on two triggers:

1. **Cron schedule** (`*/10 * * * *`): every 10 minutes, checks all brands for posts whose `publish_at` has arrived.
2. **Push to `main`** on paths matching `brands/**/calendar/**/*.md`: fires immediately when a content PR is merged. This ensures a post merged close to its `publish_at` is not delayed by up to 10 minutes.

Both triggers run the same publisher code. Posts with a future `publish_at` are skipped regardless of what triggered the run.

A `concurrency` group (`publisher`, `cancel-in-progress: false`) serializes workflow runs. Overlapping runs are queued, not cancelled. This prevents race conditions on rate limit state files and on the frontmatter commit-back step.

The `[skip ci]` string in publisher commit messages prevents the status commit from retriggering the workflow.

### Publisher execution flow

For each brand and each post in the queue:

1. Check `status`: skip if not `scheduled` or `deferred`.
2. Check `publish_at` against current UTC time: skip if not yet reached.
3. Verify the file is committed on `main` via `git log main -- <file>`: skip if not (fail-closed gate).
4. For each target platform:
   a. Skip if `post_ids[platform]` already exists (idempotency).
   b. Extract the platform copy section from the document body.
   c. Check the rate limit counter for that platform: skip to next run if limit reached.
   d. Publish via the platform adapter with retry.
   e. On success: immediately write `post_ids[platform]` to frontmatter (crash recovery).
5. Write final `status` to frontmatter: `published`, `failed`, or `deferred`.
6. Commit all changes to `brands/` with message `chore: record publish status [skip ci]`.

### Retry strategy

On a publish failure (4xx, 5xx, or network timeout) for a given post and platform:

- Attempt 1 fails: wait 10 seconds, retry
- Attempt 2 fails: wait 30 seconds, retry
- Attempt 3 fails: wait 90 seconds, retry
- Attempt 4 fails: all retries exhausted

On exhaustion: sets `status: failed`, creates a GitHub issue with label `publish-failure` and `agent:bob`, and sends a Telegram notification. If an open issue for the same post and platform already exists, a comment is added instead of creating a duplicate.

On HTTP 429 (rate limit from the platform API itself, distinct from the pre-flight rate limit check): the `Retry-After` response header is respected, up to a maximum of 300 seconds, before the retry count increments.

`PermanentError` exceptions (400 Bad Request, authentication errors) bypass the retry loop entirely and go straight to failure handling.

### Rate limiting

Before each platform API call, the publisher checks a per-platform counter stored in `brands/<brand>/.state/rate_limits/<platform>.json`. If the current window's call count has reached the configured limit, the post is deferred (not failed) to the next run.

Configured limits per platform (conservative, configurable in `models.py`):

| Platform | Limit | Window |
|----------|-------|--------|
| LinkedIn | 100 | 24 hours |
| Facebook | 200 | 1 hour |
| Instagram | 50 | 24 hours |
| X | 500 | 30 days |
| GBP | 1,000 | 24 hours |

Rate limit state files are committed to the repo once per publisher run alongside status updates.

### State management

The post Markdown frontmatter is the state store. There is no external database or cache. This means:

- The git history is the complete audit trail of every status transition.
- Publisher runs are idempotent: rerunning on an already-published post skips it.
- Partial failures (some platforms succeed, run crashes) are recoverable: per-platform `post_ids` are written immediately after each success, so the next run skips completed platforms.

---

## Brand Configuration

Each brand has its configuration in `brands/<brand>/brand.yaml`.

### Format reference

```yaml
# Brand display name
brand_name: "Second Ring"

# HeyGen avatar ID for AI video generation (Phase 2; set to null for Phase 1)
avatar_id: null

# Platform credentials: Key Vault secret NAME, not the raw token.
# The publisher resolves these names against Azure Key Vault or environment variables.
credentials:
  facebook: kv-secondring-facebook-token
  instagram: kv-secondring-facebook-token   # Shared Meta app credentials (same secret as facebook)
  linkedin: kv-secondring-linkedin-token
  gbp: kv-secondring-gbp-credentials
  x: kv-secondring-x-config               # xurl config JSON

# Posting cadence per platform (informational; used by Phase 2 content generation)
cadence:
  linkedin:
    posts_per_week: 3
    preferred_times:
      - "09:00"
      - "17:00"
    timezone: "America/Los_Angeles"
  facebook:
    posts_per_week: 5
    preferred_times:
      - "08:00"
      - "12:00"
      - "18:00"
    timezone: "America/Los_Angeles"

# Content pillars: topics this brand focuses on (used by Phase 2 content generation)
pillars:
  - "AI-powered answering service"
  - "Never miss a customer call"
  - "Small business growth"

# Brand voice (used by Phase 2 content generation)
voice:
  tone: "Professional, approachable, and confident"
  avoid:
    - "corporate jargon"
    - "exclamation points in every sentence"
  cta_style: "Direct -- tell them what to do next"
```

### Credential names

Values under `credentials` are Key Vault secret names (or environment variable names in Phase 1). They are never raw tokens. The `validate-brand.py` script detects raw tokens in the config and exits non-zero.

Instagram intentionally references the same secret as Facebook. Both platforms use the same Meta app. The publisher reads only the Facebook credential entry for both adapters.

### Validate a brand config

```bash
python scripts/validate-brand.py brands/secondring/brand.yaml
```

---

## Credential Setup

### Phase 1: GitHub environment secrets and variables

In Phase 1, credentials are passed to the publisher via GitHub Actions environment variables. The Key Vault secret names in `brand.yaml` are used as environment variable names (uppercased, hyphens to underscores).

For example, `kv-secondring-facebook-token` maps to the environment variable `KV_SECONDRING_FACEBOOK_TOKEN`.

Configure these in the GitHub repository under **Settings > Environments > production**:

| Secret / Variable | Type | Purpose |
|-------------------|------|---------|
| `GITHUB_TOKEN` | Automatic | Create failure issues; no setup required |
| `XURL_CONFIG_JSON` | Secret | xurl authentication config JSON (see X/Twitter notes) |
| `TELEGRAM_BOT_TOKEN` | Secret | Telegram bot token for failure notifications |
| `TELEGRAM_CHAT_ID` | Variable | Telegram chat ID for notifications |
| `FACEBOOK_PAGE_ID` | Variable | Facebook page ID |
| `LINKEDIN_AUTHOR_URN` | Variable | LinkedIn organization or person URN |
| `GBP_LOCATION_NAME` | Variable | GBP location resource name (`accounts/{id}/locations/{id}`) |
| `INSTAGRAM_USER_ID` | Variable | Instagram Business Account user ID |
| `ASSETS_BASE_URL` | Variable | Azure Blob base URL for public image access |
| `KV_SECONDRING_FACEBOOK_TOKEN` | Secret | Facebook page access token (or JSON blob with `access_token`, `expires_at`, `refresh_token`) |
| `KV_SECONDRING_LINKEDIN_TOKEN` | Secret | LinkedIn access token (or JSON blob) |
| `KV_SECONDRING_GBP_CREDENTIALS` | Secret | GBP credentials (JSON blob) |

Tokens can be either a raw string (no expiry tracking) or a JSON object with the following shape (enables automatic 24-hour preemptive refresh per AC13):

```json
{
  "access_token": "...",
  "expires_at": "2026-06-01T00:00:00Z",
  "refresh_token": "...",
  "token_endpoint": "https://oauth2.googleapis.com/token",
  "client_id": "...",
  "client_secret": "..."
}
```

### Phase 2: Azure Key Vault with OIDC

Set the GitHub Actions variable `AZURE_KEY_VAULT_NAME` to the Key Vault name. Configure a GitHub OIDC federated identity with Key Vault Secrets Officer role. The publisher resolves credential names via `az keyvault secret show` and writes refreshed tokens back via `az keyvault secret set`.

No long-lived secrets need to be stored in GitHub once Key Vault is configured.

### OAuth token refresh

The publisher checks token expiry before each publisher run (AC13). If a token expires within 24 hours, it is refreshed via the platform's OAuth 2.0 refresh token grant and written back to Key Vault. If the refresh fails (revoked token), the publisher skips that platform and creates a GitHub issue labeled `credential-failure` and `agent:bob`.

### X/Twitter credentials

X uses the `xurl` CLI for all API interactions. The `XURL_CONFIG_JSON` secret is the full xurl config JSON, written by the workflow to `~/.config/xurl/config.json` before the publisher runs. No OAuth flow is managed by the publisher for X.

---

## Adding a New Brand

1. Create the brand directory:
   ```
   brands/<brand>/
     brand.yaml
     assets/
     .state/rate_limits/
     calendar/
   ```

2. Copy `brands/secondring/brand.yaml` as a template and update all values.

3. Add credential secrets to GitHub environment secrets or Azure Key Vault.

4. Create the calendar directory structure as needed:
   ```bash
   mkdir -p brands/<brand>/calendar/2026/04
   ```

5. No code changes are required. The publisher discovers brands by scanning `brands/` directories at runtime.

---

## Adding a New Platform Adapter

All platform adapters implement the `BaseAdapter` interface defined in `publisher/adapters/base.py`.

### Adapter interface

```python
class BaseAdapter(ABC):
    platform: str  # Platform slug: "x", "facebook", "linkedin", "gbp", "instagram"

    def __init__(self, brand: Brand, state_dir: Path):
        """Receive brand config and path to .state/ directory."""

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
            post: Post model containing id, publish_at, and all frontmatter.
            copy_text: Platform-specific copy already extracted from the document.
            image_path: Optional path to an image asset from brands/<brand>/assets/.

        Returns:
            Platform-specific post ID string (tweet ID, LinkedIn share URN, etc.)

        Raises:
            PublishError: Retryable failure. The retry wrapper calls publish() again.
            RateLimitError: HTTP 429. Retry-After header is respected if set.
            PermanentError: Non-retryable failure (400 Bad Request, auth error).
        """

    @abstractmethod
    def auth_check(self) -> bool:
        """
        Make a lightweight authenticated API call to verify credentials.
        Logs [AUTH OK] {platform} on success, [AUTH FAIL] {platform} on failure.
        Returns True if credentials are valid.
        """
```

Error classes (`PublishError`, `RateLimitError`, `PermanentError`) are defined in `publisher/retry.py`.

Rate limit checking and incrementing use the inherited `check_rate_limit(post_id)` and `increment_rate_limit()` methods from `BaseAdapter`. Adapters do not manage the rate limit state directly.

Token retrieval uses `self._get_credential(secret_name)` which resolves against environment variables and Key Vault. Token expiry and refresh logic is in `_check_and_refresh_token(cred_json, secret_name)`.

### Step-by-step: adding a new adapter

1. Create `publisher/adapters/<platform>.py`:

```python
"""
publisher/adapters/<platform>.py -- <Platform Name> adapter

Ref: AC3 (text publish), AC4 (image publish), AC2 (auth_check), AC15 (pattern: use CLI or SDK)
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from .base import BaseAdapter
from ..models import Post, Brand
from ..retry import PublishError, PermanentError, RateLimitError

logger = logging.getLogger(__name__)


class <Platform>Adapter(BaseAdapter):
    platform = "<platform_slug>"

    def publish(self, post: Post, copy_text: str, image_path: Optional[Path] = None) -> str:
        token = self._get_platform_token()
        # ... make API call ...
        # On success: return post ID string
        # On 429: raise RateLimitError("message", retry_after=int)
        # On 400: raise PermanentError("message", status_code=400)
        # On 5xx: raise PublishError("message", status_code=500)

    def auth_check(self) -> bool:
        # Make a lightweight call to verify the token
        # Log [AUTH OK] or [AUTH FAIL]
        pass

    def _get_platform_token(self) -> str:
        secret_name = self.brand.credentials.get_kv_secret_name("<platform_slug>")
        raw = self._get_credential(secret_name)
        return self._check_and_refresh_token(raw, secret_name)
```

2. Register the adapter in `publisher/adapters/__init__.py`:

```python
from .my_platform import MyPlatformAdapter

ADAPTER_REGISTRY["<platform_slug>"] = MyPlatformAdapter
```

3. Add the platform to the valid platforms list in `scripts/validate-post.py`:

```python
VALID_PLATFORMS = {"facebook", "linkedin", "gbp", "x", "instagram", "<platform_slug>"}
```

4. Add the copy section header to `PLATFORM_SECTION_HEADERS` in both `scripts/validate-post.py` and `publisher/publisher.py`:

```python
PLATFORM_SECTION_HEADERS = {
    ...
    "<platform_slug>": "<Platform Name> Version",
}
```

5. Add the character limit to `PLATFORM_LIMITS` in `scripts/validate-post.py` and to `schemas/post.schema.yaml`.

6. Add rate limit defaults to `RateLimitState.DEFAULTS` in `publisher/models.py`.

7. Update `brands/<brand>/brand.yaml` with the new platform's credential key.

8. Add the new platform to the `copy_section_headers` and `platform_limits` sections in `schemas/post.schema.yaml`.

---

## Running Locally

Install dependencies:

```bash
pip install -r publisher/requirements.txt
```

Validate a post document:

```bash
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-example.md
```

Validate a brand config:

```bash
python scripts/validate-brand.py brands/secondring/brand.yaml
```

Dry run (no API calls, validates logic only):

```bash
python -m publisher.publisher --brand secondring --dry-run
```

Auth check (verifies credentials are live):

```bash
python -m publisher.publisher --brand secondring --auth-check
```

Full publisher run:

```bash
python -m publisher.publisher --brand secondring
```

Run for all brands:

```bash
python -m publisher.publisher --brand all
```

### Required environment variables for local runs

| Variable | Required | Purpose |
|----------|----------|---------|
| `GITHUB_TOKEN` | For failure issues | GitHub personal access token with `repo` scope |
| `GITHUB_REPOSITORY` | For failure issues | `VelocityPoint/social-calendar` |
| `XURL_CONFIG_JSON` | For X publishing | Write to `~/.config/xurl/config.json` before running |
| `FACEBOOK_PAGE_ID` | For Facebook | Facebook page ID |
| `LINKEDIN_AUTHOR_URN` | For LinkedIn | LinkedIn organization or person URN |
| `GBP_LOCATION_NAME` | For GBP | `accounts/{id}/locations/{id}` format |
| `INSTAGRAM_USER_ID` | For Instagram | Instagram Business Account user ID |
| `ASSETS_BASE_URL` | For image posts | Azure Blob base URL (required for Instagram images) |
| `TELEGRAM_BOT_TOKEN` | For notifications | Telegram bot token |
| `TELEGRAM_CHAT_ID` | For notifications | Telegram chat ID |

Credentials for each platform are resolved by uppercasing the Key Vault secret name and replacing hyphens with underscores. For example, `kv-secondring-facebook-token` resolves to environment variable `KV_SECONDRING_FACEBOOK_TOKEN`.

---

## Validating Posts Locally

The `validate-post.py` script checks:

- File path matches `brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-<slug>.md`
- Filename matches `YYYY-MM-DD-<slug>.md`
- All required frontmatter fields are present
- `id` matches the `YYYY-MM-DD-<slug>` pattern
- `publish_at` includes a timezone offset (bare datetimes without offset fail)
- `platforms` is a non-empty list of valid platform slugs
- `status` is a valid status value
- A `# {Platform Name} Version` section exists in the body for each platform in `platforms`
- Copy sections do not exceed platform character limits

Exit code 0 means the file is valid. Exit code 1 means one or more errors were found; error messages are printed to stderr.

The `validate-pr.yml` GitHub Actions workflow runs this validator against all changed calendar files in a pull request. The PR cannot be merged until the workflow passes.

---

## Platform Notes

### X/Twitter

X publishing uses the `xurl` CLI exclusively. The adapter invokes `xurl` as a subprocess and does not make direct HTTP calls to the X API. The xurl config is written from the `XURL_CONFIG_JSON` environment variable by the workflow setup step.

Known gap: the xurl install step in `publish.yml` is a placeholder. The correct install method for `xurl` must be confirmed and the step updated before X publishing can run in CI.

### Instagram

Instagram shares Meta app credentials with Facebook. The `instagram.py` adapter reads the Facebook credential secret name from `brand.yaml` (the `instagram` entry in `credentials` must point to the same Key Vault secret as `facebook`). No separate Instagram credential file exists.

Instagram does not support text-only posts via the Graph API. Every post targeting Instagram must include a `creative` image block. The adapter raises `PermanentError` for text-only Instagram posts.

Images for Instagram must be accessible via a public URL. The publisher derives this URL from `ASSETS_BASE_URL` plus the asset path.

### Google Business Profile

The `GBP_LOCATION_NAME` variable must be in the format `accounts/{account_id}/locations/{location_id}`. This value can be found via the Google My Business API or the GBP dashboard.

### OAuth token expiry

Facebook, Instagram, LinkedIn, and GBP tokens expire. The publisher checks expiry before each run and refreshes tokens within 24 hours of expiry. Tokens must be stored as JSON with `expires_at` and `refresh_token` fields to enable automatic refresh. Raw token strings are accepted but do not expire-check.

The weekly `auth-check.yml` workflow makes a live authenticated call to each platform and creates a GitHub issue labeled `credential-failure` if any token is invalid.

---

## Related

- Tracking issue: [VelocityPoint/Core_Business#222](https://github.com/VelocityPoint/Core_Business/issues/222)
- Architecture design: Daedalus comment in issue #222
- Acceptance criteria: Sibyl comment in issue #222
- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
