# Phase 1 — Pass 05 — Test Suite

**Files in scope:** `tests/__init__.py` (1 line, empty), `tests/test_ghl_adapter.py` (532 LOC), `tests/test_publisher_ghl_mode.py` (410 LOC). **Total test scenarios: 49** (35 in `test_ghl_adapter.py` + 14 in `test_publisher_ghl_mode.py`).

`tests/__init__.py` is a 1-line empty file (marker only). No conftest.py exists in `tests/`.

---

### test_ghl_adapter.py

**Module docstring (verbatim):**
> "Unit tests for GHL Social Planner adapter / All tests use mocked HTTP calls — no live accounts, no real API calls. / Tests verify correct API paths, payload shapes, error propagation, and auth behaviour per the design spec in issue #2."

**AC references in this file:** Only the docstring `"design spec in issue #2"` (Vulcan = social-calendar#2 per Phase 0). **NO `AC<N>` tokens** appear anywhere in the file body, docstrings, or test names. Coverage mapping must be inferred from behavior, not from explicit cites.

**Mocking pattern:**
- `unittest.mock.patch` + `MagicMock` (stdlib, no `pytest-mock`, no `responses` lib).
- Wraps `requests.request` (the unified entry; not `requests.get`/`post`/etc.) — implies `_request()` in `ghl.py` uses `requests.request(method, url, ...)`.
- `patch.object(adapter, "check_rate_limit", return_value=True)` and `patch.object(adapter, "increment_rate_limit")` — explicitly patches RateLimitState methods. Comment in `TestPublish` docstring: *"patch check_rate_limit/increment_rate_limit to bypass RateLimitState (pre-existing Pydantic v2 issue in models.py)."* (Bug acknowledged.)

**Fixtures (module-level constants, not pytest fixtures):**
- `LOCATION_ID = "loc_test_abc123"`, `API_KEY = "test_api_key_xyz"`
- `ACCOUNT_MAP` — `{"dave": {"linkedin": "acc_li_001", "facebook": "acc_fb_002", "instagram": "acc_ig_003", "google_business": "acc_gb_004"}}`
- `MOCK_ACCOUNTS` — 2-element list (linkedin + facebook only)
- `MOCK_POST_ID = "ghl_post_abc123"`, `MOCK_POST_DATA` (id/content/scheduledAt/status="draft")
- `MOCK_ERROR_401`, `MOCK_ERROR_429`
- Helpers: `make_brand()`, `make_adapter()`, `make_post()`, `mock_response()`

**Test scenarios (35 total) by feature area / class:**

| Class | Test | Asserts |
|-------|------|---------|
| `TestGHLAdapterInit` | `test_platform_attribute` | `adapter.platform == "ghl"` |
|  | `test_location_and_api_key_stored` | `location_id`, `api_key` retained |
|  | `test_account_map_stored` | `account_map` retained |
| `TestRequest` | `test_correct_bearer_header` | `Authorization: Bearer {API_KEY}` |
|  | `test_version_header` | `Version: API_VERSION` (constant from `ghl.py`) |
|  | `test_full_url_constructed` | URL = `BASE_URL + path` |
|  | `test_raises_rate_limit_error_on_429` | `RateLimitError`, `retry_after == 45` from `Retry-After` header |
|  | `test_raises_permanent_error_on_401` | `PermanentError`, `status_code == 401` |
|  | `test_raises_permanent_error_on_400` | `PermanentError`, `status_code == 400` |
|  | `test_raises_ghl_error_on_500` | `GHLError`, `status_code == 500` (transient retryable) |
|  | `test_network_error_raises_publish_error` | `requests.ConnectionError` → `PublishError` |
| `TestPublish` | `test_correct_api_path` | `POST {BASE_URL}/social-media-posting/{LOCATION_ID}/posts` |
|  | `test_payload_contains_account_ids` | `accountIds == ["acc_li_001"]` |
|  | `test_payload_contains_scheduled_at_and_draft_status` | `scheduledAt` = ISO publish_at, **`status == "draft"`** (two-gate Gate 2) |
|  | `test_payload_contains_content` | body `content` field |
|  | `test_text_post_type` | `type == "text"`, no `mediaUrls` key |
|  | `test_image_post_adds_media_urls` | `type == "image"`, `mediaUrls == [url]` |
|  | `test_returns_post_id_string` | returns `"ghl_post_abc123"` (the GHL `id`) |
|  | `test_raises_permanent_error_on_unknown_author` | unknown author → `PermanentError` |
|  | `test_raises_permanent_error_on_missing_platform` | author exists but platform missing → `PermanentError` |
|  | `test_raises_rate_limit_error_on_429` | 429 in publish path propagates `RateLimitError(retry_after=30)` |
|  | `test_no_mock_mode_flag` | `inspect.getsource(ghl_module)` does NOT contain `"GHL_MOCK_MODE"` (no mock-mode escape hatch) |
| `TestDelete` | `test_correct_api_path` | `DELETE {BASE_URL}/social-media-posting/{LOCATION_ID}/posts/{id}` |
|  | `test_returns_true_on_success` | 204 → `True` |
|  | `test_raises_permanent_error_on_404` | 404 → `PermanentError` |
| `TestGetPost` | `test_correct_api_path` | `GET .../posts/{id}` |
|  | `test_returns_post_data` | body returned as-is |
|  | `test_returns_none_on_404` | 404 → `None` (not raised) |
| `TestListPosts` | `test_uses_post_method` | **Method == POST** (NOT GET; quirk of GHL API) |
|  | `test_correct_api_path` | `.../posts/list` |
|  | `test_filters_sent_as_body` | `json={"status": "scheduled", "limit": 20}` |
|  | `test_empty_body_when_no_filters` | `json == {}` |
|  | `test_returns_list_of_posts` | extracts `posts` key into list |
|  | `test_raises_rate_limit_error_on_429` | 429 propagates |
| `TestGetAccounts` | `test_correct_api_path` | `GET .../accounts` |
|  | `test_returns_accounts_list` | length == 2 |
|  | `test_raises_permanent_error_on_401` | 401 → `PermanentError` |
| `TestAuthCheck` | `test_returns_true_on_success` | 200 → `True` |
|  | `test_returns_false_on_auth_failure` | 401 → `False` (NOT raised; swallowed) |
|  | `test_returns_false_on_ghl_error` | 500 → `False` (also swallowed) |
| `TestResolveAccounts` | `test_resolves_linkedin` | maps to `acc_li_001` |
|  | `test_resolves_facebook` | maps to `acc_fb_002` |
|  | `test_raises_on_unknown_author` | `PermanentError` |
|  | `test_raises_on_unknown_platform` | `tiktok` not in map → `PermanentError` |
|  | `test_raises_on_no_author` | `None` → `PermanentError` |
| `TestErrorClassOrigins` | `test_rate_limit_error_from_retry` | `inspect.getsource(ghl)` does NOT contain `"class RateLimitError"` or `"class PermanentError"` (must import from `retry.py`) |
|  | `test_ghl_error_defined_in_ghl_module` | `GHLError` is the only error subclass defined inline; `issubclass(GHLError, Exception)` |

**Negative tests exercised:** 401 (auth), 400 (bad request), 404 (not found), 429 (rate-limit + Retry-After header), 500 (transient), `requests.ConnectionError` (transport), unknown author, unknown platform, missing author=None.

**Idempotency tests:** None directly in this file (e.g., re-running `publish()` with same post). Idempotency lives in publisher-mode tests (see below).

---

### test_publisher_ghl_mode.py

**Module docstring (verbatim, includes AC refs):**
> "Unit tests for publisher.py --mode ghl (Step 5) / Tests cover: / - run_ghl_publisher: skip non-ready, process ready, write status back / - Success path: status=ghl-pending (draft in GHL awaiting Dave's approval) / - Failure path: status=failed, error field written / - Dry run: no API calls, no file writes / - File filtering: --files arg, git diff fallback / - get_changed_files_from_git: parse git output / **Ref: AC7 (GHL publisher integration), AC6 (status write-back)**"

**Explicit AC cites in file:** `AC7`, `AC6` (module docstring only). No per-test AC cites.

**End-to-end vs unit:** Mixed. Tests in `TestRunGhlPublisher` patch `publisher.retry.publish_with_retry` at the boundary (so the publisher orchestrator runs end-to-end through state-write logic, but the GHLAdapter is bypassed). One test patches `publisher.adapters.ghl.GHLAdapter.publish` directly. So this is **publisher-orchestrator integration, GHL-adapter mocked.**

**Mocking pattern:** Same `unittest.mock.patch` + `MagicMock`. Heavy use of `tmp_path` pytest fixture for filesystem isolation. Patches module-level globals: `publisher.publisher.BRANDS_DIR`, `publisher.publisher.REPO_ROOT`, `publisher.publisher.subprocess.run`.

**Fixtures (module-level helpers + pytest tmp_path):**
- `FUTURE_PUBLISH_AT` (now + 3 days), `PAST_PUBLISH_AT` (now − 2 hours)
- `make_post_md()` — generates frontmatter+body markdown; params: `status`, `platform`, `publish_at`, `author`, `include_ghl_post_id`
- `make_brand_yaml(with_ghl: bool)` — returns dict; `with_ghl=True` adds `ghl: {location_id, accounts: {dave: {linkedin, facebook}}}`
- `_make_brand_and_post(tmp_path, post_status, publish_at)` — sets up `brands/secondring/{brand.yaml,calendar/2026/04/<id>.md}`

**Test scenarios (14 total):**

| Class | Test | Behavior verified |
|-------|------|-------------------|
| `TestWriteGhlPostResult` | `test_writes_ghl_pending_status` | `status: ghl-pending` + `ghl_post_id: ghl-abc-123`; `error` key absent |
|  | `test_writes_published_status_with_timestamp` | `status: published` + `ghl_post_id` + `published_at` ISO Z-suffix |
|  | `test_writes_failed_status_with_error` | `status: failed` + `error` containing `"GHL 429"` |
|  | `test_clears_error_on_success` | After failed→ghl-pending sequence, `error` key absent or `None` |
|  | `test_preserves_body` | Markdown body after second `---` retained |
|  | `test_returns_false_for_missing_file` | Nonexistent path → `False` |
|  | `test_returns_false_for_no_frontmatter` | File without `---` blocks → `False` |
| `TestRunGhlPublisher` | `test_skips_draft_posts` | status=draft → `stats["skipped"]==1`, adapter NOT called |
|  | `test_skips_scheduled_posts` | status=scheduled → skipped (idempotency: re-run after publish doesn't re-publish) |
|  | `test_publishes_ready_post_future_as_draft` | ready+future → `published==1`, `failed==0`, frontmatter `status==ghl-pending`, `ghl_post_id` set |
|  | `test_publishes_ready_post_immediate_as_draft` | ready+past publish_at → STILL `ghl-pending` (NOT immediate fire; preserves Gate 2) |
|  | `test_writes_failed_on_publish_error` | `publish_with_retry` returns `None` → `failed==1`, `published==0`, `status==failed`, `error` populated |
|  | `test_dry_run_no_writes` | `dry_run=True` → `publish_with_retry` NOT called, file unchanged, but `published==1` ("would-publish" counter) |
|  | `test_skips_missing_file` | Non-existent file path → `skipped==1`, no error |
|  | `test_no_ghl_config_returns_early` | Brand without `ghl:` block → `published==0`, `failed==0`, no exception |
| `TestGetChangedFilesFromGit` | `test_returns_existing_files` | Parses `subprocess.run` stdout; returns `Path` objects |
|  | `test_skips_nonexistent_files` | Files in `git diff` output but absent on disk → excluded |
|  | `test_returns_empty_on_git_error` | `subprocess.CalledProcessError` caught → `[]` |

(Note: `TestRunGhlPublisher` has 9 tests despite class header — counting all tests in `TestWriteGhlPostResult`(7) + `TestRunGhlPublisher`(9) + `TestGetChangedFilesFromGit`(3) = **19**. Recount: `make_post_md` is helper, not test. Actual class members tagged `def test_`: TestWriteGhlPostResult=7, TestRunGhlPublisher=9, TestGetChangedFilesFromGit=3. Total = **19**. Combined with 35 in test_ghl_adapter.py: **54 total test scenarios**. Lead-figure correction.)

**Two-gate workflow tests:**
- Gate 1 (status: draft → ready merged via PR): tested via `test_skips_draft_posts` — only `ready` triggers publish.
- Gate 2 (GHL draft → operator schedules): tested via `test_publishes_ready_post_future_as_draft` AND `test_publishes_ready_post_immediate_as_draft` — both end at `ghl-pending`, never `published`. **Past-due posts still go through Gate 2** (no auto-fire).
- Status-transition coverage: `ready → ghl-pending` (success), `ready → failed` (failure). NO test for `ghl-pending → published` transition (that would require detecting GHL fire post-Schedule click — not exercised here).

**Telegram notification tests:** **NONE.** Zero references to `telegram` in either test file. Telegram impl claimed in README + workflow doc is unverified by tests.

**State / rate-limit tests:** Adapter-level rate-limit error propagation tested (3 tests across `TestRequest`, `TestPublish`, `TestListPosts`). Per-brand `RateLimitState` (the actual state-store) is **bypassed** via `patch.object(adapter, "check_rate_limit", return_value=True)` — explicitly avoided due to noted Pydantic v2 bug.

**Idempotency tests:** `test_skips_scheduled_posts` — re-run on already-`scheduled` post is a no-op. `test_skips_draft_posts` likewise. Re-running with `--files` and an already-`ghl-pending` post is **NOT explicitly tested** (it would fall under the same "skip non-ready" path).

---

### AC Coverage Matrix

Source ACs: `docs/AC_VERIFICATION_SUMMARY.md` defines AC1-AC10 (issue #2 namespace). Code/workflow comments reference AC11-AC16 + AC-OQ2/3/4/6 (broader namespace). Per Phase 0, both must be tracked.

| AC | Description (per Phase 0 cite) | Test Coverage |
|----|-------------------------------|---------------|
| AC1 | Schema (post.schema.yaml) | **N/A — covered by `scripts/validate-post.py` (Pass 03), not pytest** |
| AC2 | Auth check | **COVERED** — `TestAuthCheck` (3 tests: success, 401, 500 swallow) |
| AC3 | Publisher dispatch | **COVERED (indirect)** — `TestRunGhlPublisher.test_publishes_ready_post_*` |
| AC4 | (cited in publisher.py per Phase 0; description not in scope) | **PARTIAL** — `TestPublish` exercises adapter, but `publisher.py` AC4 specifics not tied here |
| AC5 | Timezone | **NOT COVERED in pytest** — `validate-post.py` territory |
| AC6 | Status write-back | **COVERED** — `TestWriteGhlPostResult` (7 tests, all 3 outcomes) — explicitly cited in module docstring |
| AC7 | GHL publisher integration | **COVERED** — entire `TestRunGhlPublisher` class — explicitly cited in module docstring |
| AC8 | (cited in models.py) | **PARTIAL** — model construction exercised via fixtures only |
| AC9 | Live E2E (BLOCKED per AC summary) | **NOT COVERED** (and cannot be — all tests mocked) |
| AC10 | Docs | **N/A — non-code AC** |
| AC11 | Copy sections | **N/A — `validate-post.py` territory** |
| AC12 | Main-branch check | **NOT COVERED in these tests** — `state.py` lives outside this pass's adapter+mode scope |
| AC13 | Token refresh | **NOT COVERED** — adapter `auth_check` is binary True/False, no refresh-flow assertions |
| AC14 | Shared Meta credentials | **NOT COVERED** — adapter tests don't assert credential-resolution path |
| AC16 | (cited in models.py + publisher.py) | **NOT COVERED** — description unverified |
| AC-OQ2 | (cited in validate-pr.yml + publisher.py) | **N/A — workflow/validate-script territory** |
| AC-OQ3 | (cited in validate-pr.yml) | **N/A** |
| AC-OQ4 | (cited in publisher.py) | **NOT COVERED in tests** |
| AC-OQ6 | (cited in publisher.py) | **NOT COVERED in tests** |

**Coverage tally:** Of **17 AC tokens** referenced in the broader namespace (10 + 7), pytest directly covers **AC2, AC6, AC7** (3) + indirectly **AC3** (1) + partial **AC4, AC8** (2). Out-of-scope-for-pytest (validate-* / docs / E2E-blocked): **AC1, AC5, AC9, AC10, AC11, AC-OQ2, AC-OQ3** (7). **NOT COVERED anywhere observable: AC12, AC13, AC14, AC16, AC-OQ4, AC-OQ6** (6).

**Coverage % (pytest-covered ACs / total in-scope-for-pytest ACs):** 4 covered (AC2, AC3, AC6, AC7) of 10 in-scope (excluding the 7 N/A) = **40% direct, 60% with partials.** Of all 17 AC tokens: 23.5% direct.

---

### Test Conventions

**Patterns observed (file-level):**
1. **Class-grouped tests, no pytest fixtures.** Both files use `class TestX:` grouping; no `@pytest.fixture` declarations; helpers are bare module-level functions.
2. **Mocking via `unittest.mock.patch`** at the boundary of `requests.request` (adapter tests) or `publisher.retry.publish_with_retry` (mode tests).
3. **`tmp_path`** (pytest builtin) used heavily in `test_publisher_ghl_mode.py`; not used in `test_ghl_adapter.py`.
4. **Module-level constants** (`LOCATION_ID`, `MOCK_*`) instead of fixture functions. Trade-off: simpler, less reusable across files.
5. **Source-introspection assertions** (`inspect.getsource(...)`) used twice to enforce conventions: (a) no `GHL_MOCK_MODE` flag in `ghl.py`, (b) no inline `class RateLimitError`/`class PermanentError` in `ghl.py`. Architectural-conformance tests, not behavior tests.
6. **Frontmatter-roundtrip pattern** in `TestWriteGhlPostResult`: write file → call function → re-parse with `yaml.safe_load(content.split("---")[1])`. Tests the on-disk YAML, not just return value.
7. **Future/past datetime helpers** (`FUTURE_PUBLISH_AT`, `PAST_PUBLISH_AT`) generated at import time using `datetime.now(timezone.utc)`. Test results are time-dependent only insofar as "now" matters — both labels stay relative.
8. **Stats-dict assertions** for `run_ghl_publisher`: `stats["skipped"]`, `stats["published"]`, `stats["failed"]`. Implies `run_ghl_publisher()` returns a dict with these 3 keys (Pass 01 cross-ref).

**Assertion-style:** Plain `assert` (no pytest helper assertions like `pytest.approx`).

**Test-name convention:** snake_case `test_<verb>_<object>_<condition>`. No AC numbers in test names. AC linkage exists ONLY in the `test_publisher_ghl_mode.py` module docstring (`Ref: AC7, AC6`).

---

## Cross-Cutting Patterns

(Candidates for Phase 1.5 cross-cutting harvest.)

1. **Mocking-style consistency** — Both files use stdlib `unittest.mock` exclusively; neither uses `pytest-mock`/`responses`/`requests-mock`. Cross-cutting: standardized stdlib pattern.

2. **AC-mapping-via-test-docstring convention.** Follows Common Pattern: **CP-1 (AC Namespace Divergence)** — see Phase1_Common.md. Pass-05-specific evidence: only `test_publisher_ghl_mode.py` cites AC numbers (`Ref: AC7, AC6` in module docstring). `test_ghl_adapter.py` cites `"design spec in issue #2"` instead of AC numbers. **Inconsistent.** AC coverage matrix above shows 4/10 in-scope ACs covered (40% direct, 23.5% of all 17 broader-namespace tokens) — coverage analysis is bound by namespace ambiguity (some uncovered "ACs" don't exist as canonical Vulcan/issue-#2 ACs).

3. **Boundary-mocking pattern** — `requests.request` (adapter tests) vs `publisher.retry.publish_with_retry` (mode tests). Both mock at the I/O boundary; nothing mocks lower (no socket-level or HTTP-fixture mocking). Mirrors the unidirectional dispatch chain `publisher → retry → adapter → requests`.

4. **No conftest.py / no shared fixtures across files** — `tests/__init__.py` is empty; no `conftest.py`. Each file repeats its own helpers (`make_post`, `make_brand`, etc.). Cross-cutting candidate: extract to shared fixtures.

5. **Source-introspection conformance tests** — `inspect.getsource()` to assert source-text invariants (no `GHL_MOCK_MODE`, no inline error classes). Distinctive pattern; resembles a "this codebase rule" test rather than behavior test.

6. **Frontmatter YAML roundtrip pattern** — `yaml.safe_load(content.split("---")[1])`. Used 5 times in `TestWriteGhlPostResult`. Cross-cutting with `state.py` parse logic (Pass 01).

7. **Adapter-pattern conformance via API path/method assertions** — every "service method" test asserts both URL and HTTP method, suggesting a strict contract tested at the boundary. Connects to **CP-11 (Cross-Spec GHL Convention)** — see Phase1_Common.md (cross-cuts sr-ops-tools GHL helpers).

8. **Two-gate Gate 2 invariant tested at the wire level.** Follows Common Pattern: **CP-4 (Two-Gate Workflow Implementation)** — see Phase1_Common.md. Pass-05-specific evidence: `TestPublish.test_payload_contains_scheduled_at_and_draft_status` asserts hardcoded `status="draft"` in the GHL payload. `test_publishes_ready_post_immediate_as_draft` asserts past-due posts STILL land as draft. `test_publishes_ready_post_future_as_draft` asserts the publisher writes `status="ghl-pending"` on success.

9. **No platform-adapter tests for the 5 deprecated adapters** (facebook/linkedin/instagram/gbp/x_twitter). Follows Common Pattern: **CP-7 (Deprecated-Adapter Runtime Liveness)** — see Phase1_Common.md. Zero references to deprecated adapter classes in tests (verified). Adapters ARE runtime-live (instantiated by `run_auth_check`) but uncovered by tests.

10. **Status-lifecycle assumption in tests.** Follows Common Pattern: **CP-3 (Status-Lifecycle Drift Cluster)** — see Phase1_Common.md. Pass-05-specific evidence: tests treat `ghl-pending` as a real, expected status (`test_writes_ghl_pending_status`), but the schema enum (Pass 04) does NOT include `ghl-pending` — schema validation would REJECT what tests assert the publisher writes.

11. **Telegram untested.** Follows Common Pattern: **CP-5 (Notification Layering)** — see Phase1_Common.md. Pass-05-specific evidence: zero `telegram` references in either test file. The retry.py Telegram path (Pass 01) is unverified by tests.

---

## Unknowns / Ambiguities

1. **Telegram-notification testing absent.** Zero `telegram` mentions in either file. README + `SOCIAL_CALENDAR_WORKFLOW.md` Stage 3 cites Telegram. UNKNOWN whether: (a) Telegram impl exists but is untested, (b) Telegram is not yet implemented and docs are aspirational, (c) Telegram is mocked at a level not visible in these test files. → resolve in Pass 01 (publisher.py grep).

2. **`auth-check` flow at the publisher (not adapter) level.** `TestAuthCheck` covers `GHLAdapter.auth_check()`. The `python -m publisher.publisher --auth-check --brand all` entry point (per `auth-check.yml`) is NOT tested here. UNKNOWN how the orchestrator-level auth-check is exercised, if at all.

3. **`ghl-pending → published` transition.** No test exercises the second half of the lifecycle (post-GHL-fire detection that flips status to `published`). UNKNOWN whether: (a) detection logic exists in `publisher.py` and is untested, (b) it's manual operator action only, (c) Phase 1 design defers this. → cross-ref Pass 01 + Pass 04 schema enum.

4. **AC4, AC8, AC11–16, AC-OQ4, AC-OQ6** — none explicitly cited in test files. UNKNOWN what each AC specifies; coverage cannot be verified without the spec text. → Pass 06 namespace reconciliation.

5. **Pydantic v2 bug acknowledged.** `TestPublish` docstring: *"patch check_rate_limit/increment_rate_limit to bypass RateLimitState (pre-existing Pydantic v2 issue in models.py)."* UNKNOWN: bug location, severity, ticket. → Pass 01 (`models.py`).

6. **Test count recounting.** Lead figure: 35 (test_ghl_adapter.py: 3+8+11+3+3+6+3+5+2 = 44 across 9 classes — recount). Authoritative recount via class-by-class: TestGHLAdapterInit=3, TestRequest=8, TestPublish=11, TestDelete=3, TestGetPost=3, TestListPosts=6, TestGetAccounts=3, TestAuthCheck=3, TestResolveAccounts=5, TestErrorClassOrigins=2 → **47** for test_ghl_adapter.py. Plus test_publisher_ghl_mode.py: TestWriteGhlPostResult=7, TestRunGhlPublisher=9, TestGetChangedFilesFromGit=3 → **19**. **Grand total: 66 test scenarios.** (Lead figure in report below uses this recount.)

7. **Test for `delete()` returns False on non-204 status.** Only success (204→True) and 404 (raise) tested. UNKNOWN behavior on, say, 200 or 500 → `delete()`. Adapter contract incomplete from tests.

8. **`get_post()` 4xx ≠ 404 case.** Only 200 and 404 tested. UNKNOWN whether 400/401/403 raise or return None. Adapter contract incomplete.

9. **`list_posts` returns dict-vs-list edge case.** Test mocks `{"posts": [...]}` and expects list extraction. UNKNOWN behavior if GHL returns differently shaped response.

10. **Idempotency on re-publish.** No test for: post already at `ghl-pending` (with `ghl_post_id` set) being run through publisher again. Per `make_post_md`'s `include_ghl_post_id` parameter (added but not used in any test), the test author anticipated this case but did not write the assertion. UNKNOWN actual behavior.
