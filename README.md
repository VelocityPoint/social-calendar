# social-calendar

GitHub-native social media content calendar and publisher for VelocityPoint.

**Issue:** VelocityPoint/Core_Business#222
**Phase:** 1 MVP

---

## How It Works

1. Author a post document in `brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-<slug>.md`
2. Open a PR — the `validate-pr.yml` workflow checks schema and copy sections
3. Merge to main — the PR merge is the approval gate (no post publishes without it)
4. The `publish.yml` workflow runs every 10 minutes and publishes posts whose `publish_at` has arrived
5. Publisher commits status and platform post IDs back to the document as `[skip ci]`

---

## Repo Structure

```
brands/
  <brand>/
    brand.yaml          -- Brand config: credential refs, cadence, pillars
    assets/             -- Image assets referenced by posts
    .state/
      rate_limits/      -- Per-platform rate limit counters (JSON, committed by publisher)
    calendar/
      YYYY/
        MM/
          YYYY-MM-DD-<slug>.md  -- Post documents

publisher/
  publisher.py          -- Main orchestrator
  models.py             -- Post, Brand, RateLimitState models
  state.py              -- Frontmatter read/write
  retry.py              -- Retry with 10s/30s/90s backoff
  adapters/
    base.py             -- Abstract adapter interface
    x_twitter.py        -- X/Twitter via xurl CLI
    facebook.py         -- Facebook via Meta Graph API
    instagram.py        -- Instagram via Meta Graph API (shared Facebook creds)
    linkedin.py         -- LinkedIn Posts API
    gbp.py              -- Google Business Profile API

scripts/
  validate-post.py      -- Post document schema validator
  validate-brand.py     -- Brand config validator

schemas/
  post.schema.yaml      -- Post document schema definition

.github/workflows/
  publish.yml           -- Scheduled publisher (10-min cron + push trigger)
  validate-pr.yml       -- Schema validation on PRs
  auth-check.yml        -- Weekly credential health check
```

---

## Post Document Format

```markdown
---
id: 2026-04-01-example-post
publish_at: 2026-04-01T09:00:00-07:00
platforms:
  - linkedin
  - facebook
  - x
  - gbp
  - instagram
status: scheduled
brand: secondring
tags:
  - example
---

# LinkedIn Version

Your LinkedIn copy here (max 3,000 characters).

# Facebook Version

Your Facebook copy here (max 2,200 characters).

# X Version

Your X/Twitter copy here (max 280 characters).

# Google Business Profile Version

Your GBP copy here (max 1,500 characters).

# Instagram Version

Your Instagram copy here (max 2,200 characters).
```

### Post Status Lifecycle

| Status | Meaning |
|--------|---------|
| `draft` | Work in progress — blocked from main by validate-pr.yml |
| `scheduled` | Merged to main, awaiting publish_at |
| `published` | All platforms confirmed, post_ids populated |
| `failed` | All retries exhausted, GitHub issue created |
| `deferred` | Rate-limited, will retry next run (no issue) |
| `video-pending` | HeyGen render in progress (Phase 2) |

---

## Validate a Post Locally

```bash
pip install pyyaml pydantic
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-example.md
```

---

## Run Publisher Locally

```bash
pip install -r publisher/requirements.txt

# Dry run (no API calls)
python -m publisher.publisher --brand secondring --dry-run

# Auth check only
python -m publisher.publisher --brand secondring --auth-check

# Full run
python -m publisher.publisher --brand secondring
```

Required environment variables (Phase 1 — before Key Vault):

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | Create failure issues |
| `GITHUB_REPOSITORY` | Repo for failure issues (e.g. VelocityPoint/social-calendar) |
| `XURL_CONFIG_JSON` | xurl auth config (written to `~/.config/xurl/config.json`) |
| `FACEBOOK_PAGE_ID` | Facebook page ID |
| `LINKEDIN_AUTHOR_URN` | LinkedIn organization or person URN |
| `GBP_LOCATION_NAME` | GBP location resource name |
| `INSTAGRAM_USER_ID` | Instagram Business Account user ID |
| `ASSETS_BASE_URL` | Azure Blob base URL for public image access |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for failure notifications |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications |

---

## Platform Notes

### X/Twitter
Uses [xurl](https://github.com/xurl/xurl) CLI. No direct API calls. Auth config written by workflow setup step.

### Instagram
Shares Meta app credentials with Facebook (AC14). Requires a public image URL — text-only posts are not supported by the Instagram API.

### Google Business Profile
Requires GBP_LOCATION_NAME in format `accounts/{account_id}/locations/{location_id}`.

---

## Adding a New Brand

1. Create `brands/<brand>/brand.yaml` (use `brands/secondring/brand.yaml` as template)
2. Add credential secrets to GitHub environment or Azure Key Vault
3. Create `brands/<brand>/calendar/YYYY/MM/` directories
4. No code changes required (AC16)

---

## Acceptance Criteria Reference

| AC | Status | Notes |
|----|--------|-------|
| AC1 | Phase 1 | validate-post.py, schemas/post.schema.yaml |
| AC2 | Phase 1 | auth_check() in each adapter, auth-check.yml workflow |
| AC3 | Phase 1 | Text publish in all adapters |
| AC4 | Phase 1 | Image publish in all adapters |
| AC5 | Phase 1 | publish_at gate in publisher.py + validate-post.py timezone check |
| AC6 | Phase 1 | write_post_status() in state.py, committed by publish.yml |
| AC7 | Phase 1 | _create_github_issue() in retry.py |
| AC8 | Phase 1 | validate-brand.py, brand.yaml templates |
| AC9 | Phase 2 | Content generation from brief (Spark pipeline) |
| AC10 | Phase 2 | HeyGen video integration |
| AC11 | Phase 1 | extract_copy_section() in publisher.py, validate-post.py |
| AC12 | Phase 1 | is_committed_on_main() in state.py |
| AC13 | Phase 1 | _get_credential() with Key Vault fallback in base.py |
| AC14 | Phase 1 | instagram.py reads only facebook credential (kv_secondring_facebook_token) |
| AC15 | Phase 1 | x_twitter.py uses subprocess.run(["xurl", ...]) only |
| AC16 | Phase 1 | ADAPTER_REGISTRY + brand.yaml pattern; zero code change for new brand |
| AC-OQ1 | Phase 1 | publish.yml cron + push trigger; summary log for Application Insights |
| AC-OQ2 | Phase 1 | scan_posts_for_brand() current+next month; validate-post.py path check |
| AC-OQ3 | Phase 1 | extract_copy_section(); validate-post.py copy section check |
| AC-OQ4 | Phase 1 | retry.py 3 attempts, 10s/30s/90s backoff, GitHub issue + Telegram |
| AC-OQ5 | Phase 2 | Azure Blob video storage (HeyGen) |
| AC-OQ6 | Phase 1 | RateLimitState in models.py; check_rate_limit() in base.py |

---

## Related

- Issue: [VelocityPoint/Core_Business#222](https://github.com/VelocityPoint/Core_Business/issues/222)
- Architecture: Daedalus design in issue #222 comments
- Requirements: Sibyl ACs in issue #222 comments
