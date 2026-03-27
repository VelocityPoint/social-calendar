# GHL Social Planner — System Architecture

**Issue:** [VelocityPoint/social-calendar#2](https://github.com/VelocityPoint/social-calendar/issues/2)
**Version:** 1.0 — as-built post Forge pipeline (PRs #3, #4, #5, #6, #8)
**Sub-account:** [SR] Sales (`cUgvqrKmBM4sAZvMH1JS`)

---

## 1. System Overview

The GHL Social Planner integration is a **PR-driven social media publishing pipeline** for Second Ring. It replaces direct platform API calls (Meta Graph, LinkedIn, etc.) with a single adapter that routes all posts through the GoHighLevel Social Planner API. GHL manages platform OAuth tokens internally and handles native scheduling.

**Core design decisions:**
- **GHL-only publishing (Approach A).** Direct platform adapters are deprecated but preserved in the codebase.
- **Merge = approval gate.** No post is published without merging to `main`. There is no `auto_publish` flag.
- **GHL handles scheduling.** The `scheduledAt` field is passed to `createPost`. No polling cron needed.
- **One file per platform.** Cross-platform campaigns are batches of files in one PR.

---

## 2. Pipeline Overview

```
Riley (content-generation agent)
  │
  │  Generates post .md files
  │  brands/secondring/calendar/YYYY/MM/YYYY-MM-DD-{platform}-{slug}.md
  │
  ▼
Opens PR → VelocityPoint/social-calendar
  │
  │  validate-pr.yml runs automatically:
  │  • Schema validation (required fields, types, character limits)
  │  • Platform enum check
  │  • Author enum check (dave | velocitypoint)
  │  • Timezone offset required on scheduled_at
  │
  ▼
Dave reviews PR in GitHub diff
  │
  │  Reads post copy directly in the diff (Markdown body)
  │  Optionally edits frontmatter or copy
  │  Sets status: ready on approved posts
  │  Merges to main
  │
  ▼
GitHub Actions — publish.yml (push trigger)
  │
  │  Triggered by: push to main, paths: brands/**/calendar/**/*.md
  │  Serialized via concurrency group "publisher"
  │  Skipped if commit message contains [skip ci]
  │
  ▼
publisher.py --mode ghl --brand secondring
  │
  │  1. Detects changed .md files via git diff HEAD~1 HEAD
  │  2. Filters to status: ready
  │  3. Parses YAML frontmatter → Post model (Pydantic)
  │  4. Resolves author → platform → GHL account ID via brand.yaml
  │  5. Calls GHLAdapter.publish(post, copy_text)
  │  6. On success: write-back ghl_post_id, status: scheduled/published, published_at
  │  7. On failure: write-back status: failed, error field
  │  8. Commits updates [skip ci] to prevent loop
  │
  ▼
GHLAdapter → GHL Social Planner API
  │
  │  POST /social-media-posting/{locationId}/posts
  │  Bearer token: GHL_API_KEY
  │  Version: 2021-07-28
  │  Payload: { accountIds, content, scheduledAt, type, mediaUrls? }
  │
  ▼
GHL Social Planner
  │
  │  Holds post until scheduledAt, then publishes natively
  │  GHL manages platform OAuth — no token management on our side
  │
  ▼
LinkedIn / Facebook / Instagram / Google Business Profile
```

---

## 3. Component Interactions and Dependencies

### 3.1 Component Map

| Component | Location | Purpose |
|-----------|----------|---------|
| Post documents | `brands/<brand>/calendar/YYYY/MM/*.md` | Source of truth for post content |
| `brand.yaml` | `brands/<brand>/brand.yaml` | Brand config, GHL location ID, account ID map |
| `publisher/models.py` | Pydantic models | `Post`, `Brand`, `GHLConfig`, `GHLAccountMap`, `RateLimitState` |
| `publisher/adapters/ghl.py` | `GHLAdapter` | HTTP calls to GHL API; retry-aware |
| `publisher/adapters/base.py` | `BaseAdapter` | Abstract base class for all adapters |
| `publisher/retry.py` | `publish_with_retry()` | 3-attempt exponential backoff (10s/30s/90s) |
| `publisher/state.py` | `write_ghl_post_result()` | Frontmatter write-back after publish |
| `publisher/publisher.py` | `run_ghl_publisher()` | Orchestrates GHL mode publish loop |
| `scripts/publish_posts.py` | Merge-trigger entry | Called by GitHub Actions |
| `scripts/ghl_social_*.py` | CLI tools | Manual account/post management |
| `.github/workflows/publish.yml` | GitHub Actions | Merge trigger, secrets injection |
| `.github/workflows/validate-pr.yml` | GitHub Actions | PR schema gate |

### 3.2 Dependency Chain

```
publish.yml
  └── publisher.py --mode ghl
        ├── Post (models.py)           ← brand.yaml, *.md frontmatter
        ├── GHLAdapter (adapters/ghl.py)
        │     ├── BaseAdapter (adapters/base.py)
        │     └── RateLimitError / PermanentError / PublishError (retry.py)
        ├── publish_with_retry (retry.py)
        └── write_ghl_post_result (state.py)
```

### 3.3 Auth Surfaces

| Credential | Where stored | Used by |
|-----------|-------------|---------|
| `GHL_API_KEY` | GitHub Actions secret | `GHLAdapter` — Bearer token for all API calls |
| `GHL_LOCATION_ID` | GitHub Actions secret | `GHLAdapter` — URL path `{locationId}` |
| `GITHUB_TOKEN` | Auto-provided by Actions | Status commit-back push |

---

## 4. Data Flow Diagrams

### 4.1 Happy Path — Post Creation

```
Riley creates file                 Dave reviews PR             GitHub Actions
─────────────────                  ──────────────              ──────────────
brands/secondring/                 PR diff shows Markdown      publish.yml triggers
  calendar/2026/04/                copy directly              on push to main
  2026-04-09-fb-cta.md
                                   Dave sets:                  python -m publisher.publisher
frontmatter:                       status: ready               --mode ghl --brand secondring
  platform: facebook               and merges
  scheduled_at: ...                                           git diff HEAD~1 HEAD
  author: dave                                                → changed files list
  status: draft
                                                              Parse .md → Post model
                                                              Pydantic validation
                                                              author: dave
                                                              platform: facebook
                                                              status: ready ✓

                                                              brand.yaml lookup:
                                                              ghl.accounts.dave.facebook
                                                              → account_id: acc_abc123

                                                              GHLAdapter.publish()
                                                              POST /social-media-posting/
                                                                cUgvqrKmBM4sAZvMH1JS/posts
                                                              {
                                                                accountIds: ["acc_abc123"],
                                                                content: "copy text...",
                                                                scheduledAt: "2026-04-09T...",
                                                                type: "text"
                                                              }

                                                              GHL responds:
                                                              { id: "post_xyz789" }

                                                              write_ghl_post_result():
                                                              status: scheduled
                                                              ghl_post_id: post_xyz789
                                                              published_at: 2026-04-09T...

                                                              git commit [skip ci] + push
```

### 4.2 Failure Path — API Error with Retry

```
GHLAdapter.publish()
  │
  ├── Attempt 1 → GHL returns 429
  │     RateLimitError raised
  │     Wait 10 seconds
  │
  ├── Attempt 2 → GHL returns 500
  │     PublishError raised
  │     Wait 30 seconds
  │
  ├── Attempt 3 → GHL returns 500
  │     PublishError raised
  │     Retries exhausted
  │
  └── write_ghl_post_result():
        status: failed
        error: "GHL Error 500: Internal Server Error (attempt 3)"
        git commit [skip ci] + push

        (Optional) Create GitHub issue for persistent failure (AC7)
```

### 4.3 Validation Gate — PR Reject

```
Riley opens PR with post .md file
  │
  ▼
validate-pr.yml triggers
  │
  ▼
validate-post.py --dry-run <file>
  │
  ├── Missing required field → FAIL (exit 1)
  │     "platform is required"
  │
  ├── Unknown platform → FAIL
  │     "Unknown platform: tiktok. Valid: facebook, instagram, ..."
  │
  ├── Unknown author → FAIL
  │     "Invalid author: 'dave.lawler'. Valid: dave, velocitypoint"
  │
  ├── scheduled_at missing timezone → FAIL
  │     "scheduled_at must include timezone offset"
  │
  ├── Character limit exceeded → FAIL
  │     "Facebook body is 65000 chars, max 63000"
  │
  └── All checks pass → PR check green
```

---

## 5. Post Document Schema (v1.1)

### 5.1 Frontmatter Fields

**Required (user-set):**

| Field | Type | Values | Notes |
|-------|------|--------|-------|
| `id` | string | `YYYY-MM-DD-{slug}` | Unique identifier. Must match file slug. |
| `publish_at` | string | ISO 8601 + tz offset | `2026-04-01T09:00:00-07:00` |
| `platforms` | list | `facebook\|instagram\|linkedin\|gbp\|x` | One or more platforms |
| `status` | string | `draft` (initial) | Riley always sets `draft`; Dave sets `ready` |
| `brand` | string | `secondring\|velocitypoint` | Must match a `brands/` directory |
| `author` | string | `dave\|velocitypoint` | Maps to GHL account via `brand.yaml` |

**Optional (user-set):**

| Field | Type | Notes |
|-------|------|-------|
| `ghl_mode` | bool | Default `true`. Set `false` for legacy direct-adapter posts. |
| `account_id` | string | Override: skip `brand.yaml` lookup and use this GHL account ID directly |
| `campaign` | string | Logical grouping for analytics/reporting |
| `tags` | list | Content tags for filtering |
| `creative` | list | Creative asset references (image URLs, video paths) |

**Publisher-managed (do not set manually):**

| Field | Type | Notes |
|-------|------|-------|
| `ghl_post_id` | string | GHL post ID after successful `createPost` |
| `published_at` | string | ISO 8601 UTC timestamp of publish/schedule call |
| `error` | string | Last error if `status: failed`; cleared on success |

### 5.2 Status Lifecycle

```
draft ─[Dave sets ready in PR review]─▶ ready ─[merge + publisher]─▶ scheduled ─[GHL fires]─▶ published
                                                     │
                                                     └─[retries exhausted]─▶ failed
```

| Status | Set by | Meaning |
|--------|--------|---------|
| `draft` | Riley | Work in progress. Not eligible for publishing. |
| `ready` | Dave | Approved. Eligible for publisher to pick up on next merge. |
| `scheduled` | Publisher | `createPost` succeeded. GHL holds post until `publish_at`. |
| `published` | Publisher | Post is live (or `publish_at` was in the past at create time). |
| `failed` | Publisher | All retries exhausted. `error` field populated. |

---

## 6. Brand Configuration

Located at `brands/secondring/brand.yaml`:

```yaml
ghl:
  location_id: cUgvqrKmBM4sAZvMH1JS    # [SR] Sales production sub-account
  accounts:
    dave:
      linkedin: "<account_id>"           # Dave's LinkedIn personal
      facebook: "<account_id>"           # Dave's Facebook page
      instagram: "<account_id>"          # Dave's Instagram
      gbp: "<account_id>"               # Google Business Profile
    velocitypoint:
      linkedin: "<account_id>"           # Company LinkedIn (future)
      facebook: "<account_id>"           # Company Facebook (future)
```

**Account resolution at publish time:**
1. Post frontmatter: `author: dave`, `platforms: [linkedin]`
2. `brand.yaml` → `ghl.accounts.dave.linkedin` → `"acc_abc123"`
3. GHL API payload: `{ accountIds: ["acc_abc123"] }`

---

## 7. GitHub Actions Workflows

### `publish.yml` — Merge-Trigger Publisher

| Attribute | Value |
|-----------|-------|
| **Triggers** | Push to `main` (paths: `brands/**/calendar/**/*.md`), cron `*/10 * * * *`, `workflow_dispatch` |
| **Concurrency** | `group: publisher`, `cancel-in-progress: false` (serialize) |
| **Loop guard** | Skips if commit message contains `[skip ci]` |
| **Permissions** | `contents: write`, `issues: write`, `id-token: write` (OIDC) |

**Steps:**
1. Checkout (full history, `fetch-depth: 0`)
2. Setup Python 3.12 + install `publisher/requirements.txt`
3. Configure git identity (`github-actions[bot]`)
4. Validate CLI scripts (dry-run smoke test on all 4 tools)
5. Run `publisher.py --mode ghl --brand secondring`
6. Commit status write-back with `[skip ci]`

### `validate-pr.yml` — PR Schema Gate

| Attribute | Value |
|-----------|-------|
| **Triggers** | PR open/update (paths: `brands/**/calendar/**/*.md`, `schemas/*.yaml`) |
| **Runs** | `validate-post.py --dry-run` on every changed post file |

### `auth-check.yml` — Credential Health Check

| Attribute | Value |
|-----------|-------|
| **Triggers** | Weekly cron, `workflow_dispatch` |
| **Runs** | `GHLAdapter.auth_check()` — verifies API key and location ID are valid |

---

## 8. GHL API Reference

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create post | `POST` | `/social-media-posting/{locationId}/posts` |
| Get post | `GET` | `/social-media-posting/{locationId}/posts/{id}` |
| List posts | `POST` | `/social-media-posting/{locationId}/posts/list` |
| Delete post | `DELETE` | `/social-media-posting/{locationId}/posts/{id}` |
| List accounts | `GET` | `/social-media-posting/{locationId}/accounts` |

**Base URL:** `https://services.leadconnectorhq.com`
**Auth:** `Authorization: Bearer <GHL_API_KEY>`
**Version header:** `Version: 2021-07-28`

### Platform Support Matrix

| Platform | Text post | Image post | Video | Scheduling | OAuth via GHL |
|----------|-----------|-----------|-------|------------|---------------|
| **Facebook** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Instagram** | ✅ (needs image) | ✅ (public URL) | ✅ | ✅ | ✅ |
| **LinkedIn** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Google Business Profile** | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Twitter/X** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **TikTok** | N/A (video only) | N/A | ✅ | ✅ | ✅ (Phase 2) |

### Rate Limits

| Layer | Limit |
|-------|-------|
| GHL API | Per-account; 429 returned when exceeded |
| LinkedIn (via GHL) | ~100 posts/day per org |
| Instagram (via GHL) | ~50 API-published posts/24h |
| Facebook (via GHL) | ~200 calls/hour |

**Our retry policy:** 3 attempts, backoff delays: 10s → 30s → 90s. 429 responses honor `Retry-After` header (capped at 300s).

---

## 9. Failure Modes and Recovery

### 9.1 Failure Scenarios

| Failure | Detection | Recovery |
|---------|-----------|---------|
| **Invalid API key** | `401 Unauthorized` on first call | `PermanentError`; status → `failed`; rotate `GHL_API_KEY` secret |
| **GHL rate limit (429)** | `429 Too Many Requests` | `RateLimitError`; retry up to 3x with backoff; status → `failed` if exhausted |
| **GHL server error (5xx)** | `500/502/503` | `GHLError`; retry up to 3x; status → `failed` if exhausted |
| **Account ID not mapped** | `brand.yaml` lookup miss | `PermanentError`; no retry; status → `failed`; fix brand config |
| **Author not in brand config** | `_resolve_accounts()` raises | `PermanentError`; no retry; status → `failed` |
| **Post file parse error** | YAML parse or Pydantic validation fail | File skipped; logged; no status update |
| **Git commit failure** | `git push` fails in Actions | Status updates lost; re-run workflow; idempotent on `status: ready` |
| **Network timeout** | `requests.Timeout` | `PublishError`; retry up to 3x |
| **Instagram text-only post** | Platform requires image | `PermanentError` from GHL; status → `failed` |

### 9.2 Recovery Procedures

**Failed status → re-publish:**
1. Identify the failed file (it has `status: failed` and an `error:` field in frontmatter)
2. Fix the underlying issue (wrong account ID, expired key, etc.)
3. Manually reset `status: draft` in the file
4. Open a new PR → Dave sets `status: ready` → merge → publisher re-runs

**Account mapping failure:**
1. Run `python scripts/ghl_social_list_accounts.py` to discover real account IDs
2. Update `brands/secondring/brand.yaml` with correct IDs
3. Open a PR with brand config update + reset the failed post to `status: draft`
4. Merge to re-trigger publishing

**API key expired:**
1. Generate a new GHL API key in GHL UI (sub-account Settings > API Keys)
2. Update `GHL_API_KEY` in GitHub repository secrets
3. Re-run the failed workflow via `workflow_dispatch`

---

## 10. Known Limitations (Phase 1)

| Limitation | Impact | Workaround / Plan |
|------------|--------|-------------------|
| **Recurring posts are not native** | GHL's repeat feature is UI-only | Riley generates batches of future-dated posts |
| **Instagram requires public image URL** | Text-only Instagram posts will fail | Always include `creative` with a hosted image for Instagram posts |
| **Already-published posts are irreversible** | Scheduled posts can be deleted via `ghl_social_delete_post.py`, but live posts must be managed on-platform | Document this in OPERATIONAL_RUNBOOK.md |
| **Double `increment_rate_limit()` call** | Rate limits counted 2x per publish (W1 from Holmes QA) | Conservative limits absorb this; track as follow-up cleanup |
| **`--files` arg space-parsing edge case** | Rare edge case on `workflow_dispatch` with unusual filenames | Naming convention (`YYYY-MM-DD-*.md`) prevents this in practice |
| **TikTok out of scope** | Cannot post to TikTok via this pipeline | Phase 2 |
| **Analytics out of scope** | GHL `statistics` endpoint not integrated | Phase 2 |
| **Reels/Stories not confirmed** | GHL API docs don't confirm Reels/Stories support | Phase 2 research |

---

## 11. Phase 2 Roadmap

| Feature | Notes |
|---------|-------|
| **TikTok** | GHL supports TikTok OAuth; add `tiktok` to platform enum |
| **Analytics collection** | Pull engagement data from GHL `statistics` endpoint; store in `.state/` |
| **Reels / Stories** | Research GHL API support; possibly UI-only |
| **HeyGen video integration** | AI-generated video assets for posts |
| **CSV bulk import** | GHL supports CSV endpoint for bulk scheduling |
| **VelocityPoint brand** | Add `velocitypoint` brand accounts to `brand.yaml` when company accounts are connected |

---

*[Bob - claude-sonnet-4-6] — Forge #2 Docs Phase*
