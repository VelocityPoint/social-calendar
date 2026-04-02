# Acceptance Criteria Verification Summary

**Issue:** [VelocityPoint/social-calendar#2](https://github.com/VelocityPoint/social-calendar/issues/2)
**Prepared by:** Scribe (Forge Documentation Phase)
**Build complete:** PRs #3, #4, #5, #6, #8 merged (PR #9 open — docs)
**Date:** 2026-03-27

---

## AC Status Summary

| AC | Description | Status | Verified by |
|----|-------------|--------|------------|
| AC1 | Capability matrix (API endpoints, platform support, rate limits) | ✅ PASS | Sibyl (requirements), architecture doc |
| AC2 | `ghl_social_list_accounts.py` | ✅ PASS | Holmes QA on PR #4 |
| AC3 | `ghl_social_create_post.py` with dry-run | ✅ PASS | Holmes QA on PR #4 |
| AC4 | `ghl_social_list_posts.py` | ✅ PASS | Holmes QA on PR #4 |
| AC5 | `ghl_social_delete_post.py` with dry-run | ✅ PASS | Holmes QA on PR #4 |
| AC6 | `--location-id`/`--api-key` with env var fallback on all tools | ✅ PASS | Holmes QA on PR #4 |
| AC7 | GHL adapter routes through GHL API (not direct platform) | ✅ PASS | Holmes QA on PR #8 |
| AC8 | Riley post document → schema → publishable | ✅ PASS (unit tests) | Holmes QA on PRs #5, #8 |
| AC9 | End-to-end test (live) | ⚠️ BLOCKED | Social accounts not yet connected |
| AC10 | Tests in dev, production documentation | ⚠️ PARTIAL | Unit tests pass; live tests blocked; docs complete |

---

## AC-by-AC Detail

### AC1 — Capability Matrix

**Requirement:** A capability matrix documenting every GHL Social Planner API endpoint, per-platform support (text/image/video/schedule), known limitations, and rate limits.

**Status:** ✅ PASS

**Deliverables:**
- Sibyl's requirements analysis in issue #2 comments — full capability matrix with 15 GHL API endpoints, platform-by-platform support matrix, API vs. UI-only breakdown, rate limits per platform
- `docs/GHL_SOCIAL_PLANNER_ARCHITECTURE.md` § Platform Support Matrix — as-built reference

**Verification method:** Read Sibyl's requirements comment in issue #2. Cross-reference with `publisher/adapters/ghl.py` endpoint usage. All 5 target platforms (Facebook, Instagram, LinkedIn, GBP, X) are covered.

**Pass criteria met:** Matrix covers all 5 platforms with verified endpoint data and rate limits.

---

### AC2 — `ghl_social_list_accounts.py`

**Requirement:** Lists connected social accounts for a given location ID. Returns account names, platforms, and connection status.

**Status:** ✅ PASS

**Implementation:** `scripts/ghl_social_list_accounts.py`

**Key behaviors verified (Holmes QA, PR #4):**
- Tabular output with columns: `ACCOUNT_ID`, `PLATFORM`, `NAME`, `STATUS`
- `--json` flag for machine-readable output
- `--location-id` defaults to `$GHL_LOCATION_ID` env var
- `--api-key` defaults to `$GHL_API_KEY` env var
- Exits with clear error if neither location-id nor env var is provided

**Test coverage:** `tests/test_ghl_adapter.py` — `test_get_accounts_*` (mock HTTP)

**Verification method:**
```bash
export GHL_API_KEY=<key>
export GHL_LOCATION_ID=cUgvqrKmBM4sAZvMH1JS
python scripts/ghl_social_list_accounts.py
# Expected: tabular list of connected accounts
```

**Pass criteria met:** Returns account names, platforms, and connection status. Handles both tabular and JSON output.

---

### AC3 — `ghl_social_create_post.py`

**Requirement:** Creates a post (text, optional image URL) to one or more connected accounts with optional scheduling. Supports `--dry-run`.

**Status:** ✅ PASS

**Implementation:** `scripts/ghl_social_create_post.py`

**Key behaviors verified (Holmes QA, PR #4):**
- `--account-id` (required), `--content` (required)
- `--schedule-at` (ISO 8601 with tz offset; defaults to now if omitted)
- `--image-url` adds `mediaUrls` to payload → `type: image`
- `--dry-run` prints payload and exits without API call
- Live mode requires interactive confirmation (prevents accidents)
- Payload includes `accountIds`, `content`, `scheduledAt`, `type`

**Test coverage:** `tests/test_ghl_adapter.py` — `test_publish_*` (mock HTTP with payload assertions)

**Verification method:**
```bash
python scripts/ghl_social_create_post.py \
  --account-id acc_test \
  --content "Test post" \
  --schedule-at 2026-04-15T09:00:00-07:00 \
  --dry-run
# Expected: payload printed, no API call made
```

**Pass criteria met:** Text + image support, scheduling, dry-run mode all verified.

---

### AC4 — `ghl_social_list_posts.py`

**Requirement:** Lists scheduled/published posts with filtering by status and date range. Returns post ID, status, platform, scheduled time.

**Status:** ✅ PASS

**Implementation:** `scripts/ghl_social_list_posts.py`

**Key behaviors verified (Holmes QA, PR #4):**
- `--status` filter: `scheduled`, `published`, `failed`, `draft`
- `--from` / `--to` date filters (YYYY-MM-DD)
- `--limit` (default 50)
- Uses `POST /social-media-posting/{locationId}/posts/list` (correct — GET would not support body filters)
- Tabular output: `POST_ID`, `STATUS`, `SCHEDULED_AT`, `PLATFORMS`, `CONTENT_PREVIEW`
- `--json` flag for machine-readable output

**Test coverage:** `tests/test_ghl_adapter.py` — `test_list_posts_*` (mock HTTP)

**Pass criteria met:** Filtering by status and date range, all required output fields present.

---

### AC5 — `ghl_social_delete_post.py`

**Requirement:** Deletes a post by ID. Supports `--dry-run`.

**Status:** ✅ PASS

**Implementation:** `scripts/ghl_social_delete_post.py`

**Key behaviors verified (Holmes QA, PR #4):**
- `--post-id` (required)
- `--dry-run` prints endpoint and post ID without API call
- Live mode requires typing the post ID to confirm (intentional friction)
- Uses `DELETE /social-media-posting/{locationId}/posts/{id}` via `GHLAdapter.delete()`

**Test coverage:** `tests/test_ghl_adapter.py` — `test_delete_*` (mock HTTP)

**Pass criteria met:** Delete by ID, dry-run mode, live confirmation gate all verified.

---

### AC6 — Auth Handling on All Tools

**Requirement:** All tools accept `--location-id` (default from `$GHL_LOCATION_ID`) and `--api-key` (default from `$GHL_API_KEY`).

**Status:** ✅ PASS

**Verification (Holmes QA, PR #4):** All four CLI scripts use identical auth pattern:

```python
parser.add_argument("--location-id", default=os.environ.get("GHL_LOCATION_ID", ""))
parser.add_argument("--api-key", default=os.environ.get("GHL_API_KEY", ""))
```

All four tools verified:
- `ghl_social_list_accounts.py` lines 60-68
- `ghl_social_create_post.py` lines 96-104
- `ghl_social_list_posts.py` lines 82-90
- `ghl_social_delete_post.py` lines 72-80

All tools exit with a clear error message if neither flag nor env var provides the required credentials.

**Pass criteria met:** Explicit args and env vars both work on all four tools.

---

### AC7 — GHL Adapter Routes Through GHL API

**Requirement:** Publisher can publish a post document to GHL Social Planner, and the post appears in GHL UI. No direct platform API calls.

**Status:** ✅ PASS (unit-tested; live E2E blocked by AC9)

**Implementation:** `publisher/adapters/ghl.py` (`GHLAdapter`), `publisher/publisher.py` (`--mode ghl`), `scripts/publish_posts.py`

**Architecture verified (Loki re-review + Holmes QA, PR #8):**
- `GHLAdapter` extends `BaseAdapter`
- All API calls target `https://services.leadconnectorhq.com`
- No direct calls to Facebook Graph API, LinkedIn Posts API, etc.
- `publish.yml` uses `publisher.py --mode ghl` (not the deprecated direct adapters)
- 18 unit tests in `tests/test_publisher_ghl_mode.py` — all passing
- 47 tests in `tests/test_ghl_adapter.py` — all passing

**Known non-blocking issue (W1):** Double `increment_rate_limit()` call in `ghl.py` + `publisher.py` — rate limits counted 2x. Conservative limits absorb this. Tracked for cleanup.

**Pass criteria met:** Publisher routes through GHL adapter. No direct platform calls. Unit tests pass.

---

### AC8 — Riley Post Document → Schema → Publishable

**Requirement:** A Riley-generated post document passes schema validation and can be published via the GHL adapter.

**Status:** ✅ PASS (unit-tested; live publish blocked by AC9)

**Implementation:** `schemas/post.schema.yaml` v1.1, `scripts/validate-post.py`, `publisher/models.py`

**Verification (Holmes QA, PRs #5 + #8):**
- Schema v1.1 covers all required Riley fields: `platform`, `scheduled_at`/`publish_at`, `author`, `status`, `brand`, `id`
- Pydantic `Post` model validates all fields at parse time
- `validate-post.py --dry-run` runs on every PR (CI gate)
- `publisher.py --mode ghl` reads `.md` frontmatter → `Post` model → `GHLAdapter.publish()`
- 3 sample post files created in `brands/velocitypoint/calendar/` — all pass validation

**Sample posts in repo:**
- `brands/velocitypoint/calendar/2026/04/2026-04-07-linkedin-ai-for-service-business.md`
- `brands/velocitypoint/calendar/2026/04/2026-04-09-facebook-never-miss-a-call.md`
- `brands/velocitypoint/calendar/2026/04/2026-04-11-instagram-ai-receptionist.md`

**Pass criteria met:** Schema validation enforced in CI. Post model → GHLAdapter publish path verified by unit tests.

---

### AC9 — End-to-End Test (Live)

**Requirement:** Create a test post via `ghl_social_create_post.py` → verify in GHL UI → verify via `ghl_social_list_posts.py` → delete via `ghl_social_delete_post.py`. All four steps succeed against [SR] Sales sub-account.

**Status:** ⚠️ BLOCKED — social accounts not yet connected in GHL

**Blocking condition:** The [SR] Sales sub-account has 0 social accounts connected (per Dave's answer to Q2 in issue #2: "build first, test once accounts are connected"). All `ghl_social_*.py` CLI tools require at least one connected social account to create/list/delete real posts.

**What IS tested:** Dry-run mode on all three scripts — verified in PR #4 CI step (`validate-pr.yml` additions). Dry-run exits 0 without API calls for all four tools.

**Unblocking steps:**
1. Connect at least one social account in GHL (Marketing > Social Planner > Connect Accounts)
2. Run `python scripts/ghl_social_list_accounts.py` to verify connection
3. Update `brands/secondring/brand.yaml` with discovered account IDs
4. Run E2E test:
   ```bash
   # Step 1: Create test post
   python scripts/ghl_social_create_post.py \
     --account-id <discovered_id> \
     --content "Second Ring E2E test — delete me" \
     --schedule-at "$(date -v+1H -u +%Y-%m-%dT%H:%M:%SZ)"

   # Step 2: List to verify
   python scripts/ghl_social_list_posts.py --status scheduled --json

   # Step 3: Delete
   python scripts/ghl_social_delete_post.py --post-id <returned_id>
   ```
5. Document test evidence (screenshot of GHL UI + CLI output) in this file

**Estimated timeline:** Unblocked once Dave connects social accounts. Estimated 30-60 minutes of operator time after accounts are connected.

---

### AC10 — Tests Against Dev, Production Documentation

**Requirement:** Test evidence exists for dev; production instructions documented.

**Status:** ⚠️ PARTIAL

**What's done:**
- ✅ 65 unit tests total (47 adapter + 18 publisher GHL mode) — all mocked, no live GHL needed
- ✅ CI runs unit tests on every PR (`validate-pr.yml`)
- ✅ Production documentation complete (this PR: `docs/` directory)
  - `GHL_SOCIAL_PLANNER_ARCHITECTURE.md` — system design and going-live steps
  - `DEVELOPER_GUIDE.md` — setup, debugging, testing procedures
  - `OPERATIONAL_RUNBOOK.md` — monitoring, incident response, key rotation
  - `RILEY_HANDOFF_SPEC.md` — Riley content creation workflow
  - `AC_VERIFICATION_SUMMARY.md` — this document

**What's missing:**
- Live API test evidence against SR Sales Dev (blocked by AC9 — zero social accounts connected)
- Per Dave's Q2 answer, this was expected: build first, test once accounts are connected

**Pass criteria (current state):** Unit test evidence exists. Production docs complete. Live test evidence pending account connection.

---

## Known Limitations and Non-Blocking Items

### From Holmes QA Reviews

| ID | Issue | Impact | Resolution path |
|----|-------|--------|----------------|
| W1 | Double `increment_rate_limit()` in `ghl.py` + `publisher.py` | Rate limits counted 2x per publish | Cleanup in follow-up; conservative limits absorb it |
| W2 | `--files` arg space-separated parsing edge case (manual dispatch) | Rare; only on `workflow_dispatch` with unusual filenames | Naming convention prevents in practice |
| W3 | `$FILES_ARG` quoting in manual dispatch workflow step | Same as W2 | Same mitigation |

### Design Limitations (Phase 1 scope decisions)

| Limitation | Rationale | Phase 2 plan |
|------------|-----------|-------------|
| TikTok not supported | Out of scope per Dave (Q4 answer) | Add when Dave requests; GHL OAuth ready |
| Analytics not collected | Out of scope per Dave (Q5 answer) | Phase 2: pull from GHL `statistics` endpoint |
| Reels/Stories not confirmed | GHL API docs unclear | Phase 2 research |
| Recurring posts via generated batches | GHL recurring feature is UI-only | Current approach (batch PRs) works well |

---

## Remaining Work Timeline

| Task | Owner | Dependency | Estimate |
|------|-------|-----------|----------|
| Connect social accounts in GHL | Dave | None — operator task | 30 min |
| Discover + update account IDs in brand.yaml | Bob | Social accounts connected | 15 min |
| Run AC9 live E2E test | Bob | Account IDs in brand.yaml | 30 min |
| Document AC9 test evidence | Bob | E2E test passes | 15 min |
| Fix W1 (double rate limit increment) | Vulcan/Bob | Low priority | 1 hour dev |
| Fix W2/W3 (FILES_ARG quoting) | Vulcan/Bob | Low priority | 30 min dev |
| Close PR #7 (superseded by #8) | Dave | None | 5 min |

**Estimated time to full AC10 PASS:** 1.5-2 hours of operator + dev time after social accounts are connected.

---

## Build Deliverable Inventory

| PR | What was built | ACs addressed |
|----|---------------|--------------|
| [#3](https://github.com/VelocityPoint/social-calendar/pull/3) | `publisher/adapters/ghl.py` — GHLAdapter (47 tests) | AC7 (partial) |
| [#4](https://github.com/VelocityPoint/social-calendar/pull/4) | CLI tools: list_accounts, create_post, list_posts, delete_post | AC2, AC3, AC4, AC5, AC6 |
| [#5](https://github.com/VelocityPoint/social-calendar/pull/5) | Schema v1.1, `validate-post.py`, sample posts, Pydantic models | AC8 (partial) |
| [#6](https://github.com/VelocityPoint/social-calendar/pull/6) | `brands/secondring/brand.yaml` GHL config block | AC8 (partial) |
| [#8](https://github.com/VelocityPoint/social-calendar/pull/8) | `publisher.py --mode ghl`, `publish_posts.py`, `state.py`, 18 tests | AC7 (complete), AC8 (complete) |
| [#9](https://github.com/VelocityPoint/social-calendar/pull/9) — this PR | `docs/` directory: architecture, developer guide, runbook, Riley spec | AC10 (docs) |

---

*[Bob - claude-sonnet-4-6] — Forge #2 Docs Phase*
