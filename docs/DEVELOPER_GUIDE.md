# Developer Guide — GHL Social Planner Integration

**Issue:** [VelocityPoint/social-calendar#2](https://github.com/VelocityPoint/social-calendar/issues/2)
**Audience:** Engineers joining Second Ring who need to understand, extend, or debug the social calendar pipeline

---

## 1. How the System Works

The `social-calendar` repo is a **PR-driven social media publishing pipeline**. Here's the one-sentence version:

> Riley (an AI content agent) writes Markdown post files and opens a PR. Dave reviews and merges. The merge triggers GitHub Actions, which calls the GHL Social Planner API to schedule the posts.

### The Key Insight: Merge = Publish Approval

There is no separate approval workflow, webhook, or dashboard. The GitHub PR is the approval UI. When Dave merges to `main`, that merge event triggers the publisher. Post files with `status: ready` get scheduled in GHL.

### Why GHL Instead of Direct Platform APIs?

The repo originally had direct adapters for Facebook Graph API, LinkedIn Posts API, etc. These were replaced with a single `GHLAdapter` that routes through GHL Social Planner. Benefits:
- **GHL manages platform OAuth.** No token rotation, refresh logic, or per-platform auth code.
- **Social interactions create GHL Contacts.** Leads from social posts flow directly into the SR Sales pipeline.
- **Unified analytics** in GHL (Phase 2).

The old adapters (`publisher/adapters/facebook.py`, `linkedin.py`, etc.) are still in the tree but are deprecated and not used in GHL mode.

---

## 2. Repository Layout

```
social-calendar/
├── brands/
│   └── secondring/
│       ├── brand.yaml                    # Brand config: GHL location, account IDs, cadence, voice
│       ├── assets/                       # Image assets referenced by posts
│       └── calendar/
│           └── 2026/
│               └── 04/
│                   ├── 2026-04-09-facebook-missed-calls.md
│                   └── 2026-04-14-linkedin-receptionist.md
├── publisher/
│   ├── publisher.py                      # Main orchestrator — use --mode ghl for GHL Social Planner
│   ├── models.py                         # Pydantic models: Post, Brand, GHLConfig, RateLimitState
│   ├── state.py                          # Read/write post frontmatter (YAML)
│   ├── retry.py                          # Retry logic + error classes
│   └── adapters/
│       ├── base.py                       # Abstract adapter interface
│       ├── ghl.py                        # GHL Social Planner adapter (the live one)
│       ├── facebook.py                   # Deprecated
│       ├── instagram.py                  # Deprecated
│       ├── linkedin.py                   # Deprecated
│       ├── x_twitter.py                  # Deprecated
│       └── gbp.py                        # Deprecated
├── scripts/
│   ├── publish_posts.py                  # Standalone merge-trigger script (PR #7, superseded by publisher.py --mode ghl)
│   ├── ghl_social_list_accounts.py       # List connected GHL social accounts
│   ├── ghl_social_create_post.py         # Create a post (with --dry-run)
│   ├── ghl_social_list_posts.py          # List scheduled/published posts
│   ├── ghl_social_delete_post.py         # Delete a post (with --dry-run)
│   ├── validate-post.py                  # Schema validation (used by CI)
│   └── validate-brand.py                 # Brand config validation
├── schemas/
│   └── post.schema.yaml                  # Schema definition v1.1
├── tests/
│   ├── test_ghl_adapter.py               # 47 tests for GHLAdapter (arrives with PR #3)
│   ├── test_publisher_ghl_mode.py        # 18 tests for publisher --mode ghl
│   ├── test_publish_posts.py             # 6 tests for publish_posts.py
│   └── test_publisher_ghl_mode.py       # 18 tests for publisher.py --mode ghl (arrives with PR #8)
└── .github/workflows/
    ├── publish.yml                       # Merge trigger + workflow_dispatch publisher (no cron)
    ├── validate-pr.yml                   # PR schema check
    └── auth-check.yml                    # Weekly credential health check
```

---

## 3. Step-by-Step Post Creation Workflow

### Step 1: Riley (or you) creates a post file

Post files live at:
```
brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-{platform}-{slug}.md
```

**Example:**
```
brands/secondring/calendar/2026/04/2026-04-09-facebook-missed-calls.md
```

**File contents:**
```markdown
---
id: 2026-04-09-facebook-missed-calls
publish_at: 2026-04-09T08:00:00-07:00
platforms:
  - facebook
status: draft
brand: secondring
author: dave
tags:
  - missed-calls
  - small-business
---

How many calls did you miss last month?

For most service businesses, the answer is "more than I know." Calls go unanswered
while you're on a job. Voicemails pile up.

Second Ring's AI answering service picks up every call, handles the conversation,
and books the appointment. You keep working. The calendar fills up.

$297/month. Try it risk-free at second-ring.com
```

**Key rules:**
- `platforms` is a list (`- facebook`). One platform per file is recommended.
- `status` must start as `draft`. Never set `ready` in a new PR — Dave does that.
- `author` must be `dave` or `velocitypoint`. This maps to a GHL social account.
- `publish_at` must include a timezone offset (`-07:00` for PDT, `-08:00` for PST).
- `id` should match the filename slug.

### Step 2: Open a PR

```bash
git checkout -b riley/2026-04-batch-social
git add brands/secondring/calendar/2026/04/
git commit -m "feat: April week 2 social posts [Ref #2]"
git push origin riley/2026-04-batch-social
gh pr create --title "[Riley] April Week 2 — LinkedIn + Facebook posts" --body "Ref #2"
```

The `validate-pr.yml` workflow runs automatically:
- Validates schema (required fields, types, character limits)
- Runs `validate-post.py --dry-run` on every changed `.md` file
- PR check goes red if any file fails

### Step 3: Dave reviews and approves

Dave reads the post copy directly in the PR diff. He may edit the content inline. When satisfied, he sets `status: ready` on each approved post and merges.

### Step 4: Merge triggers publishing

Merging to `main` triggers `publish.yml`. The publisher:
1. Detects changed `.md` files via `git diff HEAD~1 HEAD`
2. Skips files without `status: ready`
3. For each `ready` file: resolves `author` + `platform` → GHL account ID → calls GHL API
4. Writes back `status: scheduled`, `ghl_post_id`, `published_at`
5. Commits the updates with `[skip ci]` to prevent a publish loop

### Step 5: GHL publishes at scheduled time

GHL holds the post and publishes it natively at `publish_at`. No further action needed.

---

## 4. Local Development Setup

### Prerequisites

```bash
# Python 3.12+
python3 --version

# Install publisher dependencies
pip install -r publisher/requirements.txt
# Core: pydantic, pyyaml, requests

# Set environment variables
export GHL_API_KEY="your-ghl-api-key"
export GHL_LOCATION_ID="cUgvqrKmBM4sAZvMH1JS"
```

### Run validation locally

```bash
# Validate a single post file
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-09-facebook-missed-calls.md

# Dry-run (no API calls) — same as CI
python scripts/validate-post.py --dry-run brands/secondring/calendar/2026/04/2026-04-09-facebook-missed-calls.md
```

### Run the publisher in dry-run mode

```bash
# Dry-run: shows what would be published without making API calls
python -m publisher.publisher --mode ghl --brand secondring --dry-run

# Dry-run on a specific file
python -m publisher.publisher --mode ghl --brand secondring \
  --files brands/secondring/calendar/2026/04/2026-04-09-facebook-missed-calls.md \
  --dry-run
```

### Run tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_ghl_adapter.py -v
python -m pytest tests/test_publisher_ghl_mode.py -v

# With coverage
pip install pytest-cov
python -m pytest tests/ --cov=publisher --cov-report=term-missing
```

---

## 5. CLI Tools Reference

### List connected social accounts

```bash
python scripts/ghl_social_list_accounts.py
```

**Output:**
```
ACCOUNT_ID        PLATFORM   NAME                     STATUS
acc_abc123        facebook   Second Ring Facebook      connected
acc_def456        linkedin   Dave Lawler               connected
acc_ghi789        instagram  @second_ring              connected
```

Use this to find account IDs for `brand.yaml`.

### Create a post (dry-run safe)

```bash
# Always dry-run first
python scripts/ghl_social_create_post.py \
  --account-id acc_abc123 \
  --content "Your post copy here" \
  --schedule-at 2026-04-15T09:00:00-07:00 \
  --dry-run

# Live post (requires interactive confirmation)
python scripts/ghl_social_create_post.py \
  --account-id acc_abc123 \
  --content "Your post copy here" \
  --schedule-at 2026-04-15T09:00:00-07:00
```

### List scheduled posts

```bash
# All posts
python scripts/ghl_social_list_posts.py

# Filtered
python scripts/ghl_social_list_posts.py --status scheduled
python scripts/ghl_social_list_posts.py --from 2026-04-01 --to 2026-04-30
python scripts/ghl_social_list_posts.py --json  # Machine-readable
```

### Delete a post

```bash
# Dry-run first
python scripts/ghl_social_delete_post.py --post-id post_xyz789 --dry-run

# Live delete (requires typing the post ID to confirm)
python scripts/ghl_social_delete_post.py --post-id post_xyz789
```

---

## 6. Understanding the Code

### `publisher/adapters/ghl.py` — The Core Adapter

The `GHLAdapter` is the single integration point with GHL API. Key methods:

```python
class GHLAdapter(BaseAdapter):
    def publish(self, post: Post, copy_text: str, image_path=None) -> str:
        """Creates a post via GHL. Returns GHL post ID."""
        account_ids = self._resolve_accounts(post)  # brand.yaml lookup
        payload = self._build_payload(post, copy_text, account_ids)
        response = self._request("POST", f"/social-media-posting/{self.location_id}/posts", json=payload)
        return response["id"]

    def _resolve_accounts(self, post: Post) -> list[str]:
        """Looks up author+platform → account_id from brand config."""
        account_map = self.account_map  # from brand.yaml ghl.accounts
        for platform in post.platforms:
            acc = account_map.get(post.author, {}).get(platform)
            if not acc:
                raise PermanentError(f"No GHL account for {post.author}/{platform}")
        ...

    def _request(self, method, path, **kwargs) -> dict:
        """Makes HTTP request with Bearer auth. Raises typed errors on failure."""
        # 429 → RateLimitError (retryable)
        # 4xx → PermanentError (not retryable)
        # 5xx → GHLError (retryable)
        # network → PublishError (retryable)
```

### `publisher/retry.py` — Error Hierarchy

```
Exception
├── PublishError       — network/timeout errors, retryable
│   └── RateLimitError — 429, retryable with backoff
└── PermanentError     — 400/401/403/404, not retryable
    └── GHLError       — GHL-specific 5xx, retryable
```

### `publisher/state.py` — Frontmatter Write-back

After publishing, `write_ghl_post_result()` updates the post file in-place:

```python
# On success:
post.status = "scheduled"  # or "published" if scheduled_at is in the past
post.ghl_post_id = "post_xyz789"
post.published_at = "2026-04-09T15:00:00Z"
post.error = None  # cleared

# On failure:
post.status = "failed"
post.error = "GHL Error 500: Internal Server Error (attempt 3)"
```

### `publisher/models.py` — Pydantic Models

```python
class Post(BaseModel):
    id: str
    publish_at: str           # ISO 8601 with timezone
    platforms: list[str]      # validated against VALID_PLATFORMS
    status: str               # validated against VALID_STATUSES
    brand: str
    author: str               # dave | velocitypoint
    ghl_mode: bool = True
    ghl_post_id: Optional[str] = None
    error: Optional[str] = None
    ...

class RateLimitState(BaseModel):
    ...
    DEFAULTS: ClassVar[dict[str, dict]]  # MUST be ClassVar — Pydantic quirk
```

**Important:** `RateLimitState.DEFAULTS` is a `ClassVar`. This was a bug in early versions — if declared as a plain field, Pydantic tries to validate it as an instance field, breaking `cls.DEFAULTS.get(platform)`. Always annotate class-level constants as `ClassVar` in Pydantic models.

---

## 7. Debugging Common Issues

### Issue: `No GHL account for dave/linkedin`

**Symptom:** Publisher fails with `PermanentError: No GHL account for dave/linkedin`. Post file gets `status: failed`.

**Cause:** `brand.yaml` has `linkedin: "<account_id>"` (placeholder not filled in) or the platform is missing from `ghl.accounts.dave`.

**Fix:**
```bash
# Discover real account IDs
python scripts/ghl_social_list_accounts.py

# Copy the linkedin account ID into brand.yaml
# brands/secondring/brand.yaml → ghl.accounts.dave.linkedin: "acc_actual_id"

# Reset the failed post
# Change status: failed → status: draft in the post .md file
# Open new PR, Dave sets ready, merge to re-publish
```

---

### Issue: `429 Too Many Requests`

**Symptom:** Publisher retries 3 times with backoff and ultimately sets `status: failed` + error message.

**Cause:** GHL or the underlying platform rate limit was hit. LinkedIn is most restrictive (~100 posts/day per org).

**Fix:**
- Check GHL dashboard to see if the rate limit window has passed
- If rate limit is temporary: reset post to `status: draft` and retry after the window (usually 1-24 hours)
- If this is a systematic issue: reduce posting cadence in `brand.yaml`

---

### Issue: `401 Unauthorized`

**Symptom:** All GHL API calls fail with 401.

**Cause:** `GHL_API_KEY` is expired, rotated, or wrong scope.

**Fix:**
```bash
# Test the key directly
curl -X GET \
  "https://services.leadconnectorhq.com/social-media-posting/cUgvqrKmBM4sAZvMH1JS/accounts" \
  -H "Authorization: Bearer <your-key>" \
  -H "Version: 2021-07-28"

# If 401: generate a new key in GHL UI
# GHL > [SR] Sales sub-account > Settings > API Keys
# Update GitHub secret: GHL_API_KEY
```

---

### Issue: PR schema check fails

**Symptom:** `validate-pr.yml` fails with an error on your post file.

**Common causes:**

| Error | Fix |
|-------|-----|
| `platform is required` | Add `platforms:` field to frontmatter |
| `Unknown platform: tiktok` | Only `facebook\|instagram\|linkedin\|gbp\|x` are valid |
| `scheduled_at must include timezone` | Change `2026-04-01T09:00:00` → `2026-04-01T09:00:00-07:00` |
| `Invalid author: 'davelawler'` | Must be `dave` or `velocitypoint` exactly |
| `Facebook body is 65000 chars, max 63000` | Trim the post copy |
| `id does not match filename pattern` | `id` should be `YYYY-MM-DD-{slug}`, matching the filename |

Run validation locally first to catch these before pushing:
```bash
python scripts/validate-post.py --dry-run brands/secondring/calendar/2026/04/your-post.md
```

---

### Issue: Publisher ran but post doesn't appear in GHL

**Symptom:** GitHub Actions succeeded, frontmatter shows `status: scheduled` and `ghl_post_id`, but the post isn't visible in GHL Social Planner UI.

**Debug steps:**
```bash
# Verify the post exists via API
python scripts/ghl_social_list_posts.py --status scheduled --json | grep <ghl_post_id>

# If not found: check if scheduled_at is far in the future
# GHL UI may not show posts scheduled > 30 days out in the default view

# Check the specific post
python scripts/ghl_social_create_post.py --dry-run  # to validate the payload format
```

---

### Issue: `status: draft` post was published (idempotency bug)

**Should never happen.** The publisher checks `post.status == "ready"` before publishing. If you're seeing this:
1. Check if the status was manually set to `ready` in the file before the publisher ran
2. Check if `ghl_post_id` is populated (it should be, preventing a re-publish)
3. Delete the duplicate post: `python scripts/ghl_social_delete_post.py --post-id <id>`

---

## 8. Testing Procedures

### Unit Tests (no GHL account needed)

All tests use `unittest.mock` to mock HTTP calls. No live GHL API calls.

```bash
# Run all tests
python -m pytest tests/ -v

# Just adapter tests (47 tests)
python -m pytest tests/test_ghl_adapter.py -v

# Just publisher GHL mode tests (18 tests)
python -m pytest tests/test_publisher_ghl_mode.py -v
```

**Test structure:** Each test:
1. Sets up a mock `requests.Session` or patches `GHLAdapter.publish`
2. Calls the function under test
3. Asserts: correct HTTP method/URL, correct payload fields, correct frontmatter write-back, correct error handling

### Dry-Run Testing (no GHL account, no API calls)

All CLI scripts and the publisher have `--dry-run` flags:

```bash
# Validate a post without publishing
python scripts/validate-post.py --dry-run brands/secondring/calendar/2026/04/your-post.md

# Publisher dry-run: shows what would be published
python -m publisher.publisher --mode ghl --brand secondring --dry-run

# CLI dry-run: shows what API call would be made
python scripts/ghl_social_create_post.py \
  --account-id acc_test \
  --content "Test post" \
  --dry-run
```

### Live E2E Testing (requires connected GHL account)

**Pre-condition:** At least one social account connected in GHL SR Sales.

```bash
# 1. List connected accounts
python scripts/ghl_social_list_accounts.py
# Note an account_id

# 2. Create a test post scheduled 1 hour from now
python scripts/ghl_social_create_post.py \
  --account-id acc_abc123 \
  --content "Second Ring test post — please ignore" \
  --schedule-at "$(date -v+1H -u +%Y-%m-%dT%H:%M:%SZ)"

# Note the returned post_id

# 3. Verify it appears in the list
python scripts/ghl_social_list_posts.py --status scheduled --json

# 4. Delete it (don't leave test posts live)
python scripts/ghl_social_delete_post.py --post-id <post_id>
```

---

## 9. Adding a New Platform

Currently supported: `facebook`, `instagram`, `linkedin`, `gbp`, `x`

To add a new platform (e.g., `tiktok` when GHL support is confirmed):

1. **Update `schemas/post.schema.yaml`** — add to `platforms.items.enum`
2. **Update `publisher/models.py`** — add to `VALID_PLATFORMS`
3. **Update `publisher/adapters/ghl.py`** — add character limit to `PLATFORM_CHAR_LIMITS`
4. **Update `brands/secondring/brand.yaml`** — add `tiktok: "<account_id>"` under `ghl.accounts.dave`
5. **Update tests** — add platform to `test_ghl_adapter.py` test cases
6. **Run validation** — `python scripts/validate-post.py --dry-run` on a test post with the new platform

---

## 10. Adding a New Brand

The system supports multiple brands (Second Ring, VelocityPoint, etc.).

1. Create `brands/<new-brand>/brand.yaml` with a `ghl:` block
2. Create `brands/<new-brand>/assets/` for image assets
3. Create `brands/<new-brand>/calendar/` for post files
4. Update `publish.yml` to run the publisher for the new brand:
   ```yaml
   python -m publisher.publisher --mode ghl --brand <new-brand>
   ```
5. Connect social accounts in GHL for the new brand's sub-account
6. Run `ghl_social_list_accounts.py` with the new location ID to get account IDs

---

*[Bob - claude-sonnet-4-6] — Forge #2 Docs Phase*
