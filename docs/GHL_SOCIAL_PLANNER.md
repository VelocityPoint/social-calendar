# GHL Social Planner — As-Built Reference

**Issue:** [VelocityPoint/social-calendar#2](https://github.com/VelocityPoint/social-calendar/issues/2)
**Status:** Built, pending live E2E (social accounts not yet connected in GHL)
**Sub-account:** [SR] Sales (`cUgvqrKmBM4sAZvMH1JS`)

---

## Architecture Overview

The GHL Social Planner integration replaces the direct platform adapters (Facebook Graph API, LinkedIn Posts API, etc.) with a single adapter that routes all posts through the GoHighLevel Social Planner API. GHL manages platform OAuth tokens internally and handles native scheduling.

```
Riley (content agent)
  │
  ▼
Opens PR to VelocityPoint/social-calendar
  │  Post .md files in brands/<brand>/calendar/YYYY/MM/
  │
  ▼
Dave reviews post copy in GitHub PR diff
  │  Sets status: ready on approved posts
  │
  ▼
Merge to main
  │
  ▼
GitHub Actions (publish.yml) triggers
  │  Runs: python scripts/publish_posts.py --brand brands/secondring/brand.yaml --all
  │
  ▼
publish_posts.py
  │  1. Finds changed .md files with status: ready
  │  2. Parses frontmatter (platform, author, scheduled_at)
  │  3. Resolves author → GHL account ID via brand.yaml
  │  4. Calls GHLAdapter.publish() with post body + scheduledAt
  │
  ▼
GHLAdapter (publisher/adapters/ghl.py)
  │  POST /social-media-posting/{locationId}/posts
  │  Bearer token auth, API version 2021-07-28
  │
  ▼
GHL Social Planner API
  │  Holds the post until scheduled_at, then publishes
  │
  ▼
LinkedIn / Facebook / Instagram / Google Business Profile
```

**Key design decisions:**
- **GHL-only publishing** (Approach A). Direct platform adapters are deprecated but remain in the tree.
- **PR = approval gate.** Merge to main is the only way posts get published. No separate `auto_publish` flag.
- **GHL handles scheduling.** We pass `scheduledAt` to `createPost`. No cron polling needed on our side.
- **One file per platform.** Cross-platform campaigns are batches of files in one PR.

---

## Repo Structure

```
social-calendar/
├── brands/
│   └── secondring/
│       ├── brand.yaml                              # Brand config with ghl: block
│       ├── assets/                                 # Image assets
│       └── calendar/
│           └── 2026/
│               └── 04/
│                   ├── 2026-04-01-never-miss-a-call.md
│                   ├── 2026-04-09-facebook.md
│                   └── 2026-04-14-linkedin.md
├── publisher/
│   ├── publisher.py                                # Main orchestrator (legacy cron + GHL mode)
│   ├── models.py                                   # Post, Brand, RateLimitState models
│   ├── state.py                                    # Frontmatter read/write
│   ├── retry.py                                    # Retry with 10s/30s/90s backoff
│   └── adapters/
│       ├── base.py                                 # Abstract adapter interface
│       ├── ghl.py                                  # GHL Social Planner adapter (NEW)
│       ├── facebook.py                             # Deprecated — direct Meta Graph API
│       ├── instagram.py                            # Deprecated — direct Meta Graph API
│       ├── linkedin.py                             # Deprecated — direct LinkedIn API
│       ├── x_twitter.py                            # Deprecated — xurl CLI
│       └── gbp.py                                  # Deprecated — direct Google API
├── scripts/
│   ├── publish_posts.py                            # Merge-triggered GHL publisher (NEW)
│   ├── ghl_social_list_accounts.py                 # CLI: list connected accounts (NEW)
│   ├── ghl_social_create_post.py                   # CLI: create a post (NEW)
│   ├── ghl_social_list_posts.py                    # CLI: list posts (NEW)
│   ├── ghl_social_delete_post.py                   # CLI: delete a post (NEW)
│   ├── validate-post.py                            # Post schema validator (updated)
│   └── validate-brand.py                           # Brand config validator
├── schemas/
│   └── post.schema.yaml                            # Post document schema v1.1 (updated)
└── .github/workflows/
    ├── publish.yml                                 # Merge-trigger + cron publisher (updated)
    ├── validate-pr.yml                             # PR validation
    └── auth-check.yml                              # Weekly credential health check
```

**File naming convention:** `YYYY-MM-DD-{platform}-{slug}.md`

One file per platform per post. A cross-platform campaign (same content on LinkedIn + Facebook + Instagram) is 3 files in one PR.

---

## Post Frontmatter Spec

### Required Fields

| Field | Type | Set by | Description |
|-------|------|--------|-------------|
| `platform` | string | User | Target platform. One of: `linkedin`, `facebook`, `instagram`, `google_business` |
| `scheduled_at` | string (ISO 8601) | User | When to publish. Must include timezone offset (e.g., `2026-04-01T14:00:00-07:00`) |
| `author` | string | User | Maps to GHL social account via `brand.yaml → ghl.accounts`. Values: `dave`, `velocitypoint` |
| `status` | string | User / Publisher | Lifecycle status. User sets `draft` or `ready`; publisher sets `scheduled`, `published`, `failed` |

### Optional Fields

| Field | Type | Set by | Description |
|-------|------|--------|-------------|
| `tags` | list of strings | User | Content tags for filtering and reporting |
| `campaign` | string | User | Groups related posts (e.g., `q2-2026-launch`) |
| `image` | string | User | Relative path to image under `brands/<brand>/assets/` |
| `ghl_mode` | boolean | User | Default `true`. Set `false` only for legacy direct-adapter posts |
| `account_id` | string | User (rare) | GHL account ID override. Normally resolved from brand config |

### Publisher-Managed Fields (do not set manually)

| Field | Type | Set by | Description |
|-------|------|--------|-------------|
| `ghl_post_id` | string | Publisher | GHL post ID after successful `createPost` call |
| `published_at` | string (ISO 8601 UTC) | Publisher | Actual publish/schedule timestamp |
| `error` | string | Publisher | Last error message if `status: failed` |

---

## Status Lifecycle

```
draft ──[Dave sets ready in PR]──> ready ──[merge + publish]──> scheduled ──[GHL publishes at scheduled_at]──> published
                                              │
                                              └──[API error, retries exhausted]──> failed
```

| Status | Meaning | Who sets it |
|--------|---------|-------------|
| `draft` | Work in progress. Riley creates files with this status. | Riley |
| `ready` | Approved for publishing. Dave sets this during PR review. | Dave |
| `scheduled` | `createPost` succeeded. GHL holds the post until `scheduled_at`. | Publisher |
| `published` | Post is live on the platform. | Publisher |
| `failed` | All retries exhausted. `error` field populated. | Publisher |

---

## Brand Config — `ghl:` Block

Located in `brands/secondring/brand.yaml`:

```yaml
ghl:
  location_id: cUgvqrKmBM4sAZvMH1JS    # [SR] Sales production sub-account
  accounts:
    dave:                                # Maps to author: dave in post frontmatter
      linkedin: "<account_id>"           # Replace with ID from ghl_social_list_accounts.py
      facebook: "<account_id>"
      instagram: "<account_id>"
      google_business: "<account_id>"
    velocitypoint:                       # Company brand accounts (future use)
      linkedin: "<account_id>"
      facebook: "<account_id>"
```

**How account resolution works:**
1. Publisher reads post frontmatter: `author: dave`, `platform: linkedin`
2. Loads `brand.yaml` → `ghl.accounts.dave.linkedin` → GHL account ID
3. Passes account ID to GHL API as `accountIds: ["<id>"]`

**Bootstrap (one-time):**
1. Connect social accounts in GHL UI (Marketing > Social Planner > Connect Accounts)
2. Run `ghl_social_list_accounts.py` to discover account IDs
3. Copy IDs into `brand.yaml`

---

## GitHub Actions — `publish.yml`

### Trigger

- **Push to `main`** when files match `brands/**/calendar/**/*.md` (merge event)
- **Cron** every 10 minutes (legacy; GHL mode does not rely on cron)
- **Manual** via `workflow_dispatch` with optional `brand` and `dry_run` inputs

### What it does

1. Checks out the repo (full history for branch verification)
2. Installs Python 3.12 and publisher dependencies
3. Configures git for status commit-back (`github-actions[bot]`)
4. Validates GHL CLI scripts (dry-run smoke tests on all 4 tools)
5. Runs `publish_posts.py --brand brands/secondring/brand.yaml --all`
   - Finds all `.md` files under `brands/secondring/calendar/`
   - Filters to `status: ready` only
   - For each: resolves author → account ID, calls `GHLAdapter.publish()`
   - Updates frontmatter: `status: scheduled`, `ghl_post_id`, `published_at`
6. Commits status updates with `[skip ci]` and pushes

### Idempotency

- Only processes files with `status: ready`
- Posts with `status: draft`, `scheduled`, `published`, or `failed` are skipped
- Posts with an existing `ghl_post_id` are skipped (defense-in-depth)
- `[skip ci]` in the status commit prevents publish-loop

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `GHL_API_KEY` | Bearer token for GHL Lead Connector Hub API |
| `GHL_LOCATION_ID` | GHL sub-account ID (e.g., `cUgvqrKmBM4sAZvMH1JS`) |
| `ASSETS_BASE_URL` | Public URL prefix for image assets (optional) |
| `GITHUB_TOKEN` | Auto-provided; used for status commit-back |

---

## CLI Tools Reference

All tools live in `scripts/`. All accept `--location-id` (default: `$GHL_LOCATION_ID`) and `--api-key` (default: `$GHL_API_KEY`).

### `ghl_social_list_accounts.py`

Lists connected social accounts for a GHL location.

```bash
python scripts/ghl_social_list_accounts.py
python scripts/ghl_social_list_accounts.py --json
python scripts/ghl_social_list_accounts.py --location-id pVJjc3aFLNffIlJCvY6B
```

**Output (tabular):**
```
ACCOUNT_ID        PLATFORM   NAME              STATUS
acc_abc123        facebook   My Page           connected
acc_def456        instagram  @myhandle         connected
```

**Flags:** `--json` (raw JSON output), `--verbose` / `-v`

---

### `ghl_social_create_post.py`

Creates a post to a connected social account.

```bash
# Dry run (safe)
python scripts/ghl_social_create_post.py \
  --account-id acc_abc123 \
  --content "Never miss another call." \
  --schedule-at 2026-04-01T10:00:00-07:00 \
  --dry-run

# With image
python scripts/ghl_social_create_post.py \
  --account-id acc_abc123 \
  --content "Our AI answers every call." \
  --image-url https://cdn.example.com/banner.jpg \
  --dry-run

# Live post (prompts for confirmation)
python scripts/ghl_social_create_post.py \
  --account-id acc_abc123 \
  --content "Hello from Second Ring!" \
  --schedule-at 2026-04-01T09:00:00-07:00
```

**Required:** `--account-id`, `--content`
**Optional:** `--schedule-at` (ISO 8601; defaults to now), `--image-url`, `--dry-run`

---

### `ghl_social_list_posts.py`

Lists scheduled/published posts with optional filtering.

```bash
python scripts/ghl_social_list_posts.py
python scripts/ghl_social_list_posts.py --status scheduled
python scripts/ghl_social_list_posts.py --from 2026-04-01 --to 2026-04-30
python scripts/ghl_social_list_posts.py --limit 10 --json
```

**Output (tabular):**
```
POST_ID           STATUS     SCHEDULED_AT              PLATFORMS  CONTENT_PREVIEW
post_abc123       scheduled  2026-04-01T10:00:00-07:00 facebook   Never miss a call...
```

**Flags:** `--status` (scheduled/published/failed/draft), `--from` / `--to` (YYYY-MM-DD), `--limit` (default 50), `--json`

---

### `ghl_social_delete_post.py`

Deletes a post by ID. Live deletions require typing the post ID to confirm.

```bash
# Dry run (safe)
python scripts/ghl_social_delete_post.py --post-id post_abc123 --dry-run

# Live delete (requires confirmation)
python scripts/ghl_social_delete_post.py --post-id post_abc123
```

**Required:** `--post-id`
**Optional:** `--dry-run`

---

### `publish_posts.py`

Merge-triggered publisher. Called by GitHub Actions; can also be run manually.

```bash
# Publish all ready posts for secondring
python scripts/publish_posts.py --brand brands/secondring/brand.yaml --all

# Specific files
python scripts/publish_posts.py --brand brands/secondring/brand.yaml \
  --files brands/secondring/calendar/2026/04/2026-04-09-facebook.md

# Dry run
python scripts/publish_posts.py --brand brands/secondring/brand.yaml --all --dry-run
```

**Required:** `--brand` (path to brand.yaml), plus `--files` or `--all`
**Optional:** `--dry-run`

---

## Going Live Checklist

1. **Connect social accounts** in GHL UI
   - Log into GHL > [SR] Sales sub-account
   - Marketing > Social Planner > Connect Accounts
   - Connect LinkedIn, Facebook, Instagram, and/or Google Business Profile

2. **Discover account IDs**
   ```bash
   export GHL_API_KEY=<your-api-key>
   export GHL_LOCATION_ID=cUgvqrKmBM4sAZvMH1JS
   python scripts/ghl_social_list_accounts.py
   ```

3. **Update brand config** — replace `<account_id>` placeholders in `brands/secondring/brand.yaml` with real IDs

4. **Add GitHub secrets** to `VelocityPoint/social-calendar`:
   - `GHL_API_KEY` — GHL Bearer token with `social-media-posting` scope
   - `GHL_LOCATION_ID` — `cUgvqrKmBM4sAZvMH1JS`

5. **Test with dry-run**
   ```bash
   python scripts/publish_posts.py --brand brands/secondring/brand.yaml --all --dry-run
   ```

6. **Create a test post** — open a PR with a single post file, merge, verify it appears in GHL Social Planner UI

7. **Verify end-to-end** — use `ghl_social_list_posts.py` to confirm the post was scheduled, then delete it with `ghl_social_delete_post.py`

---

## Known Limitations and Polish Items

### From Holmes QA (non-blocking)

| ID | Issue | Impact | Status |
|----|-------|--------|--------|
| W1 | Double `increment_rate_limit()` call in `ghl.py` + `publisher.py` | Rate limits counted 2x per publish; conservative limits absorb this | Track for cleanup |
| W2 | `--files` arg space-separated parsing edge case on manual dispatch | Only affects `workflow_dispatch` with filenames containing spaces | Low risk (naming convention prevents this) |
| W3 | `$FILES_ARG` quoting in manual dispatch workflow step | Same as W2 | Low risk |

### Design Limitations

- **Recurring post rules** — GHL's native recurring feature is UI-only. Workaround: Riley generates a batch of N future posts in one PR.
- **Already-published recall** — GHL can delete scheduled posts. Posts that have already gone live must be deleted on-platform manually. This is the one irreversible action.
- **Instagram image requirement** — Instagram API requires a public image URL. Text-only Instagram posts are not supported.

---

## Not Implemented (Phase 2)

| Feature | Notes |
|---------|-------|
| **TikTok** | GHL supports TikTok OAuth and posting, but out of scope for Phase 1 |
| **Analytics** | GHL has a `statistics` endpoint; collection deferred to Phase 2 |
| **Reels / Stories** | GHL docs don't confirm API support; UI-only for now |
| **Auto-publish mode** | All posts require PR approval; no direct-publish path |
| **HeyGen video** | Video rendering integration deferred to Phase 2 |
| **CSV bulk import** | GHL supports CSV upload endpoint; not yet integrated |

---

## GHL API Reference

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create post | POST | `/social-media-posting/{locationId}/posts` |
| Get post | GET | `/social-media-posting/{locationId}/posts/{id}` |
| List posts | POST | `/social-media-posting/{locationId}/posts/list` |
| Delete post | DELETE | `/social-media-posting/{locationId}/posts/{id}` |
| List accounts | GET | `/social-media-posting/{locationId}/accounts` |

**Base URL:** `https://services.leadconnectorhq.com`
**Auth:** Bearer token via `Authorization: Bearer <GHL_API_KEY>`
**Version header:** `Version: 2021-07-28`

**Error handling:**
- `429` → `RateLimitError` — retry with backoff (10s/30s/90s, 3 attempts)
- `400/401/403/404` → `PermanentError` — no retry
- `5xx` → `GHLError` — retry with backoff
- Network errors → `PublishError` — retry with backoff

---

[Scribe - Technical Writer - claude-opus-4-6]
