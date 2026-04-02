# social-calendar

GitHub-native social media content calendar and publisher for VelocityPoint.

**Status:** Active
**Issue:** VelocityPoint/Core_Business#222
**Phase:** 1 (GHL Social Planner integration)

---

## How It Works — Two Gates

Every post requires two explicit approvals before going live:

**Gate 1 — GitHub PR (copy approval)**
1. Riley generates post `.md` files and opens a PR
2. `validate-pr.yml` checks schema and character limits automatically
3. Dave reads the copy in the GitHub diff, sets `status: ready` on approved posts, and merges

**Gate 2 — GHL Social Planner (visual approval + activation)**
4. Merge triggers `publish.yml` — publisher creates posts in GHL as **drafts** (not auto-fired)
5. Dave receives a Telegram notification: "X posts pending approval in GHL"
6. Dave opens GHL Social Planner, reviews visual previews, and clicks Schedule
7. GHL fires each post at its `publish_at` time

> See [`docs/SOCIAL_CALENDAR_WORKFLOW.md`](docs/SOCIAL_CALENDAR_WORKFLOW.md) for the full formalized workflow.

---

## Repo Structure

```
brands/
  <brand>/
    brand.yaml          -- Brand config: GHL location ID, account IDs, cadence, voice
    assets/             -- Image assets referenced by posts
    calendar/
      YYYY/
        MM/
          YYYY-MM-DD-{platform}-{slug}.md  -- Post documents (one file per platform)

publisher/
  publisher.py          -- Main orchestrator (--mode ghl)
  models.py             -- Post, Brand, GHLConfig, RateLimitState models
  state.py              -- Frontmatter read/write
  retry.py              -- Retry with 10s/30s/90s backoff
  adapters/
    ghl.py              -- GHL Social Planner adapter (active)
    base.py             -- Abstract adapter interface
    facebook.py         -- Deprecated (GHL handles Meta OAuth)
    instagram.py        -- Deprecated
    linkedin.py         -- Deprecated
    x_twitter.py        -- Deprecated
    gbp.py              -- Deprecated

scripts/
  validate-post.py           -- Post document schema validator
  validate-brand.py          -- Brand config validator
  ghl_social.py              -- GHL Social Planner CLI (accounts / posts / create / delete)

schemas/
  post.schema.yaml      -- Post document schema definition v1.1

docs/
  SOCIAL_CALENDAR_WORKFLOW.md      -- Canonical workflow (start here)
  GHL_SOCIAL_PLANNER_ARCHITECTURE.md  -- Architecture + data flow diagrams
  DEVELOPER_GUIDE.md               -- Step-by-step for engineers
  RILEY_HANDOFF_SPEC.md            -- Instructions for Riley (content agent)
  OPERATIONAL_RUNBOOK.md           -- Day-to-day ops and incident response

.github/workflows/
  publish.yml           -- Merge-triggered publisher (push to main)
  validate-pr.yml       -- Schema validation on PRs
  auth-check.yml        -- Weekly credential health check
```

---

## Post Document Format

One file per platform. Filename: `YYYY-MM-DD-{platform}-{slug}.md`

```markdown
---
id: 2026-04-14-linkedin-spring-rush
publish_at: 2026-04-14T09:00:00-07:00
platforms:
  - linkedin
status: draft
brand: secondring
author: dave
tags:
  - spring-2026
  - service-business
---

Your LinkedIn copy here (max 3,000 characters).
```

### Post Status Lifecycle

```
draft → ready → ghl-pending → scheduled → published
```

| Status | Set by | Meaning |
|--------|--------|---------|
| `draft` | Riley | Work in progress — CI blocks merge |
| `ready` | Dave (in PR) | Copy approved — publisher picks up on merge |
| `ghl-pending` | Publisher | Post created in GHL draft queue — awaiting Dave's Gate 2 approval |
| `scheduled` | GHL / Publisher | Dave approved in GHL — will fire at `publish_at` |
| `published` | GHL / Publisher | Post is live on platform |
| `failed` | Publisher | All retries exhausted — `error` field populated, GitHub issue created |

---

## Validate a Post Locally

```bash
pip install pyyaml pydantic
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-14-linkedin-spring-rush.md
```

---

## Run Publisher Locally

```bash
pip install -r publisher/requirements.txt

# Dry run (no API calls)
python -m publisher.publisher --mode ghl --brand secondring --dry-run

# Full run
python -m publisher.publisher --mode ghl --brand secondring
```

Required secrets (GitHub Actions environment):

| Secret | Purpose |
|--------|---------|
| `GHL_API_KEY` | GHL Social Planner API — Bearer token |
| `GHL_LOCATION_ID` | GHL sub-account location ID |
| `GITHUB_TOKEN` | Auto-provided — status commit-back + failure issues |
| `TELEGRAM_BOT_TOKEN` | Telegram notification on pending approval |
| `TELEGRAM_CHAT_ID` | Telegram chat for notifications |

---

## Platform Notes

### GHL Social Planner (primary)
All publishing routes through GHL. GHL manages platform OAuth — no token rotation needed on our side. Platforms: Facebook, Instagram, LinkedIn, Google Business Profile, X/Twitter.

### Instagram
Shares Meta app credentials with Facebook via GHL. Requires a public image URL — text-only posts are not supported.

### Google Business Profile
Requires `GBP_LOCATION_NAME` in format `accounts/{account_id}/locations/{location_id}`.

---

## Adding a New Brand

1. Create `brands/<brand>/brand.yaml` (use `brands/secondring/brand.yaml` as template)
2. Connect social accounts in GHL sub-account; get account IDs via `python scripts/ghl_social.py accounts`
3. Add credential secrets to GitHub environment
4. Create `brands/<brand>/calendar/YYYY/MM/` directories
5. No code changes required

---

## Related

- Workflow: [`docs/SOCIAL_CALENDAR_WORKFLOW.md`](docs/SOCIAL_CALENDAR_WORKFLOW.md)
- Architecture: [`docs/GHL_SOCIAL_PLANNER_ARCHITECTURE.md`](docs/GHL_SOCIAL_PLANNER_ARCHITECTURE.md)
- Core issue: [VelocityPoint/Core_Business#222](https://github.com/VelocityPoint/Core_Business/issues/222)
- GHL draft gate: [#13](https://github.com/VelocityPoint/social-calendar/issues/13)
- Telegram notification: [#14](https://github.com/VelocityPoint/social-calendar/issues/14)
- Published status sync: [#15](https://github.com/VelocityPoint/social-calendar/issues/15)
