# Phase 1 — Pass 01 — Publisher Core Engine

**Files extracted:** `publisher/__init__.py` (1 LOC), `publisher/publisher.py` (605 LOC), `publisher/models.py` (286 LOC), `publisher/retry.py` (276 LOC), `publisher/state.py` (270 LOC) — total **1,438 LOC**.
**Snapshot:** `67d061c`. Method: literal-evidence extraction; no Phase 2 inference.

`publisher/__init__.py` is a single-line package docstring: `"""Social Calendar Publisher package."""` — no exports, no init logic.

---

## Publisher Orchestrator

### CLI surface — `main()` in `publisher.py:499-601`

`argparse.ArgumentParser` flags (verbatim from `publisher.py:514-528`):

| Flag | Default | Help text (verbatim) |
|------|---------|----------------------|
| `--brand` | `"all"` | `"Brand slug or 'all'"` |
| `--mode` | `"cron"` | `"Publisher mode: 'cron' (default, cron-scheduled posts) or 'ghl' (merge-triggered, ready posts via GHL Social Planner)"`. `choices=["cron", "ghl"]` |
| `--files` | `None` | `"(GHL mode) Whitespace/newline-separated list of changed post file paths. If omitted, uses git diff HEAD~1 HEAD."` |
| `--dry-run` | False (`store_true`) | `"Dry run — no API calls"` |
| `--auth-check` | False (`store_true`) | `"Run auth check only (AC2)"` |

When `--brand all`, brand slugs are enumerated from subdirectories of `BRANDS_DIR = REPO_ROOT / "brands"` (line 531): `[d.name for d in BRANDS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]`.

### Three invocation paths (mutually selected, in dispatch order)

`main()` (lines 535-601) dispatches in this priority:

1. **`--auth-check`** (line 535): runs `run_auth_check(slug)` for every brand, exits 0 if all pass else 1. **Bypasses both publish modes entirely.** Does NOT touch calendar files; does NOT consult `--mode`; does NOT consult `--files`; does NOT consult `--dry-run`.
2. **`--mode ghl`** (line 544): GHL merge-trigger path. Calls `run_ghl_publisher(slug, files=files, dry_run=args.dry_run)` per brand.
3. **`--mode cron`** (default, line 581): cron path. Calls `run_publisher(slug, dry_run=args.dry_run)` per brand.

Both publish modes exit 1 if any brand reports `failed > 0` (lines 576-578, 599-601).

### `--auth-check` flow (`run_auth_check`, lines 469-496) — distinct from publish flow

- Loads `Brand.from_yaml(brand_yaml_path, slug=brand_slug)`.
- Iterates `brand.credentials.__dict__.items()` — every platform name → KV-secret-name pair declared in `BrandCredentials` (facebook, linkedin, gbp, x, instagram).
- For each non-null `kv_name`, looks up an adapter class in `ADAPTER_REGISTRY` (imported from `.adapters`) and calls `adapter.auth_check()`.
- Returns False if any adapter's `auth_check()` returned False; main exits 1.
- **No frontmatter is read or written. No GHL adapter is invoked specifically — auth_check iterates the deprecated platform adapters via the registry.** This corroborates Phase 0 review note 8 / Unknown #4: `auth-check.yml`'s env vars (`FACEBOOK_PAGE_ID`, `LINKEDIN_AUTHOR_URN`, etc.) are consumed by the deprecated adapters' `auth_check` methods.
- Comment: `# AC2: Run auth check for all platforms in a brand.` (line 470)

### Cron publish flow (`run_publisher`, lines 301-447)

Stats dict shape: `{evaluated, published, deferred, skipped, failed}` (line 311).

Sequence per brand:
1. Load `Brand.from_yaml`. Create `state_dir = brand_dir / ".state"` with `mkdir(parents=True, exist_ok=True)` (lines 326-327).
2. `posts = scan_posts_for_brand(brand_dir, REPO_ROOT)` — only returns posts with `status == "scheduled"` AND `is_committed_on_main` (state.py:262, 248).
3. For each post:
   - **AC5 scheduling gate** (line 339): `if not post.is_ready_to_publish(): skipped += 1; continue`. The `Post.is_ready_to_publish` predicate requires `status == "scheduled"` AND `publish_at <= now UTC` (models.py:105-110).
   - For each platform in `post.platforms`:
     - **Idempotency** (line 352): `if post.is_published_to(platform): continue` — skip silently. `is_published_to` returns `bool(self.post_ids and self.post_ids.get(platform))` (models.py:96-97).
     - **AC11 / AC-OQ3 copy extraction** (line 357): `extract_copy_section(body, platform)` — fails the platform with `any_failed = True` if section header missing.
     - **Adapter lookup** (line 364): `adapter_cls = ADAPTER_REGISTRY.get(platform)`. None → `any_failed = True`.
     - **Rate-limit gate (AC-OQ6)** (line 373): `if not adapter.check_rate_limit(post.id): any_deferred = True; continue`.
     - **Dry-run short-circuit** (line 377): logs preview, no API call, no state write.
     - **Image lookup** (line 382): `_find_image_for_platform(post, platform, brand_dir)` (helper at lines 450-466).
     - **Publish with retry** (line 388): `publish_with_retry(...)` returns platform_post_id string or None.
     - On non-None result: record `post_results[platform] = platform_post_id`, `adapter.increment_rate_limit()`, `adapter.save_rate_limit_state()` (lines 398-401). On None: `any_failed = True`.
4. **AC6 status writeback** (lines 405-430): if `post_results` and not dry_run, compute new_status:
   - `failed` if `any_failed` else
   - `deferred` if `any_deferred` else
   - `published` if every platform in `post.platforms` either has an existing `post_ids` entry or appears in this run's `post_results`, else `deferred`.
   - `published_at` is set to `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` only when new_status is `published` (lines 420-422).
   - Calls `write_post_status(file_path, post.id, status=new_status, post_ids=post_results, published_at=published_at)`.
5. **Stats accounting** (lines 432-446): on dry_run, every evaluated post counts `published += 1`; otherwise classification follows the new_status logic.

### GHL merge-trigger flow (`run_ghl_publisher`, lines 125-298)

Stats dict shape: `{evaluated, published, skipped, failed}` (line 152) — note **no `deferred`**, distinct from cron mode.

- **Brand + GHL config validation** (lines 154-176): brand_dir exists; brand.yaml exists; `brand.ghl` is non-None (with verbatim error: `"No 'ghl:' block in {brand_yaml_path}. Add location_id and accounts mapping (see Step 4 brand config)."`); `brand.ghl.location_id` or `os.environ.get("GHL_LOCATION_ID")` is set.
- **Adapter** (line 181): `GHLAdapter(brand=brand, state_dir=state_dir)` — exclusive. Comment block at lines 23-31 states verbatim: *"Uses GHLAdapter exclusively (no per-platform adapter registry lookup)"*.
- **File resolution** (lines 183-188): If `files is None`, calls `get_changed_files_from_git(REPO_ROOT)`. That helper runs `git diff --name-only HEAD~1 HEAD -- brands/**/calendar/**/*.md` (lines 104-110) and filters paths that exist on disk. Empty list → returns immediately.
- **Per-file processing** (lines 193-296):
  - `parse_post_file(file_path)` → None ⇒ `skipped`.
  - **`status == "ready"` gate** (line 210): only `ready` posts publish. Note: distinct from cron mode's `scheduled` gate. Comment verbatim: `# Only publish posts with status: ready` and the log message `"only 'ready' posts are published"`.
  - **Empty `post.platforms`** (line 220) → write `status="failed"`, `error="No platforms defined in frontmatter"`. **One file = one platform**: `platform = post.platforms[0]` (line 226). Comment verbatim: `# GHL mode: one file = one platform`.
  - **Copy extraction** (line 229): `extract_copy_section(body, platform) or body` — falls back to full body if no section header. Empty result → `failed`.
  - **`publish_at` parse** (line 239): exception → `failed` with `error=f"Cannot parse publish_at: {e}"`.
  - `is_immediate = publish_at_dt <= now_utc` (line 246) — computed for logging only; not gating publish in GHL mode (i.e., GHL accepts both immediate and future-scheduled posts).
  - **Dry-run** (line 248): logs preview, increments `published`. Does NOT write frontmatter.
  - **Real publish** (line 259): `publish_with_retry(publish_fn=lambda: adapter.publish(post, copy_text), ...)`. On non-None ghl_post_id: writes `status="ghl-pending"`, `ghl_post_id=ghl_post_id`, `published_at=None` via `write_ghl_post_result`, then calls `adapter.increment_rate_limit()` + `adapter.save_rate_limit_state()`. On None: writes `status="failed"`, `error="All retries exhausted — see GitHub issue for details"`.

### AC reference inventory in `publisher.py` (verbatim, with line cites)

- Module docstring (line 33): `"Ref: AC3, AC4, AC5, AC6, AC7, AC11, AC12, AC16, AC-OQ2, AC-OQ4, AC-OQ6, AC7 (GHL)"`.
- Lifecycle bullets in module docstring (lines 5-10): `AC-OQ2`, `AC5`, `AC12`, `AC-OQ6`, `AC-OQ4`, `AC6`.
- `extract_copy_section` docstring (line 72): `"(AC11, AC-OQ3)"`.
- `run_ghl_publisher` docstring (line 131): `"GHL merge-trigger publisher mode (Step 5 / AC7)"`.
- Cron loop comment (line 339): `# AC5: Scheduling gate — skip if publish_at > now`.
- Cron loop comment (line 356): `# Extract platform copy (AC11, AC-OQ3)`.
- Cron loop comment (line 372): `# AC-OQ6: Rate limit check before any API call`.
- Cron loop comment (line 384): `# Publish with retry (AC-OQ4)`.
- Cron writeback comment (line 405): `# Update frontmatter status (AC6)`.
- Image helper comment (line 458): `# Check platform override (AC4)`.
- `run_auth_check` docstring (line 470): `"AC2: Run auth check for all platforms in a brand."`.
- Summary log comment (line 589): `# Log summary (AC-OQ1: Application Insights log format)`.

### Two-gate workflow — how the publisher learns about new posts

Two distinct triggers, observed:

- **Cron mode**: `scan_posts_for_brand` (state.py:220) walks `brand_dir/calendar/<YYYY>/<MM>/*.md` for the **current** and **next** month only (state.py:228-236). Filters: `is_committed_on_main` AND `status == "scheduled"`. **Gate 1 is implicit**: only posts already merged to `main` (verified via `git log main -- <relpath>`, state.py:199-204) are eligible. **Gate 2 is implicit**: only `status: scheduled` posts publish — operator must transition `ready → scheduled` upstream (no code in this pass does that transition; UNKNOWN — see Unknowns).
- **GHL mode**: changed files come from `--files` (workflow-supplied) or `git diff HEAD~1 HEAD -- brands/**/calendar/**/*.md` (publisher.py:104-110). Filter: `status == "ready"`. **Gate 1**: PR merge into main triggers the workflow (the merge commit IS the gate). **Gate 2**: post lands as draft in GHL with `status: ghl-pending` — operator-scheduled in GHL Social Planner UI (per docstring lines 26-29: *"post lands in GHL as draft — Dave approves in GHL Social Planner UI"*).

### Adapter dispatch decision logic

- **Cron mode**: `adapter_cls = ADAPTER_REGISTRY.get(platform)` at publisher.py:364, where platform is iterated from `post.platforms`. Adapter chosen per platform per post.
- **GHL mode**: hardcoded `GHLAdapter(brand=brand, state_dir=state_dir)` at publisher.py:181. The registry is not consulted. Comment line 31: *"Uses GHLAdapter exclusively (no per-platform adapter registry lookup)"*. **Confirmed: in Phase-1/GHL mode, all posts route through `ghl.py` adapter.**
- **Auth-check**: `ADAPTER_REGISTRY.get(platform)` for each KV-mapped platform (publisher.py:488).

### Telegram notification — location and trigger

**Located in `publisher/retry.py`, not `publisher.py`.** Resolves Phase 0 Unknown #2.

- Definition: `_send_telegram_notification(post_id, platform, error_message, status_code)` at retry.py:235-276.
- **Trigger event**: called only from `_handle_final_failure` (retry.py:147) which is invoked by `publish_with_retry` on (a) `PermanentError` (retry.py:82-86), or (b) exhaustion of all `MAX_RETRIES = 3` attempts (retry.py:121-127). **Never sent on success, never sent on a single retryable failure that later succeeds.**
- **Credentials source** (retry.py:245-246): `os.environ.get("TELEGRAM_BOT_TOKEN")` and `os.environ.get("TELEGRAM_CHAT_ID")`. Both must be set; otherwise the function logs a warning and returns silently. **Resolves Unknown #7: env-var-based, not KV-resolved at call time** (KV → env injection, if any, happens in the workflow not in the publisher).
- **API call**: HTTPS POST to `https://api.telegram.org/bot{bot_token}/sendMessage` with `urllib.request`, 10-second timeout, body params `chat_id` + `text` (retry.py:260-270).
- **Always paired with GitHub-issue creation** in `_handle_final_failure` (retry.py:143-147). Both fire on the same trigger.

Verbatim docstring line 242-243: *"Send Telegram notification per Dave's OQ4 decision (notify on final failure). Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables."*

### Error handling + status reporting (commit status back per AC6)

- **Frontmatter writeback is the only "commit" mechanism** observed. No git-commit-or-push code in `publisher.py` itself; the `[skip ci]` mechanism mentioned in the module docstring (line 10: *"Commit state updates [skip ci] per Daedalus's design"*) is not implemented in this file. The publisher **mutates the .md file in-place**; the workflow (out of scope for this pass) presumably commits.
- **Failure mode A (cron)**: `write_post_status` is called only when `post_results` non-empty (line 406). If a post had ALL platforms fail before any platform succeeded, `post_results` stays empty and **no frontmatter writeback occurs**. Stats still register `failed += 1` (line 444). Dead-letter handling lives in retry.py via GitHub issue + Telegram.
- **Failure mode B (GHL)**: `write_ghl_post_result(file_path, status="failed", error=...)` is called in every error branch (publisher.py:222, 232, 242, 290).
- GitHub issues created per `_create_github_issue` (retry.py:150-232): labels `publish-failure` + `agent:bob` (lines 224-225). Dedup against existing open issues by exact title `"[Publish Failed] {post_id} on {platform}"` via `gh issue list` + title equality match (retry.py:171-198). On dup hit, a comment is posted instead of a new issue.

### Idempotency — re-running on already-published posts

- **Cron mode**: `Post.is_published_to(platform)` (models.py:95-97) checks `post_ids[platform]` exists and short-circuits the per-platform inner loop (publisher.py:352). Each platform is independently idempotent. The `all_published` calculation (publisher.py:414-417) treats already-published platforms as satisfied — useful when partial-success runs are re-run.
- **GHL mode**: gating is by `status == "ready"` (publisher.py:210). Once a post lands as `ghl-pending`, `published`, `failed`, or any other status, it is skipped on re-run. **No `ghl_post_id`-based idempotency** — relies entirely on the status gate. Re-running on a `ready` post would re-publish (creating a duplicate GHL draft).

---

## Models (`publisher/models.py`)

Module docstring (lines 1-7): `"Ref: AC1 (schema), AC6 (status/post_ids), AC8 (brand config), AC13 (token refresh), AC14 (Instagram/Facebook shared creds), AC16 (multi-brand)"`.

### Constants

- `VALID_PLATFORMS = {"facebook", "linkedin", "gbp", "x", "instagram"}` (line 20). 5 platforms — note `gbp`, not `google_business`; note `x`, not `twitter` or `x_twitter`.
- `VALID_STATUSES = {"draft", "ready", "ghl-pending", "scheduled", "published", "failed", "deferred", "video-pending"}` (lines 21-23). **Eight states** — including `video-pending` (Phase-2 HeyGen forward-pointer, no code path produces it in this pass).
- `VALID_AUTHORS = {"dave", "velocitypoint"}` (line 24). Closed set; mapped to GHL accounts via `brand.yaml → ghl.accounts` per validator error message (line 91).

### `CreativeAsset` (lines 27-32)

Fields: `type: str` (no enum on the model — values "image", "video", "heygen" called out in inline comment), `path: Optional[str]` (relative to `brands/<brand>/assets/`), `url: Optional[str]`, `video_url: Optional[str]` (Azure Blob URL for HeyGen Phase 2 — comment line 31), `platforms: Optional[list[str]]` (override; None ⇒ all platforms — comment line 32).

### `Post` (lines 35-110) — the central model

Required fields: `id: str`, `publish_at: str`, `platforms: list[str]`, `status: str`, `brand: str`, `author: str`. Author comment line 44: *"GHL account mapping: dave | velocitypoint (required per AC8)"*.

GHL-specific fields (AC8, comment line 46): `ghl_mode: bool = True` (default True — *"True = publish via GHL Social Planner (default)"*, line 48), `account_id: Optional[str]` (override).

Optional metadata: `campaign`, `tags`. Written by publisher: `published_at`, `ghl_post_id`, `post_ids: Optional[dict[str, str]]`, `error: Optional[str]`. Plus `creative: Optional[list[CreativeAsset]]` and a `_file_path: Optional[str]` private/internal (set after parsing — state.py:54).

**Validators** (all `@field_validator(...)` `@classmethod`):

- `validate_platforms` (lines 66-72): rejects any platform not in `VALID_PLATFORMS` with `ValueError(f"Unknown platform: {p}")`. Quote: `for p in v: if p not in VALID_PLATFORMS: raise ValueError(...)`.
- `validate_status` (lines 74-83): checks against `VALID_STATUSES` with verbatim message: `f"Invalid status: '{v}'. Valid: {sorted(VALID_STATUSES)}. Lifecycle: draft → ready → scheduled → published | failed"`. **Note:** the error message describes the lifecycle but is NOT exhaustive (missing `ghl-pending`, `video-pending`, `deferred`).
- `validate_author` (lines 85-93): closed set, message verbatim: `f"Invalid author: '{v}'. Must be one of {sorted(VALID_AUTHORS)}. 'author' maps to a GHL social account via brand.yaml → ghl.accounts."`.

**No timezone validator on `publish_at` in this model.** Comment line 41 says *"validated by validate-post.py"* — defers to Pass 03. Resolves part of "AC5 timezone": enforced in scripts, not in model.

**No `extra=forbid` and no `frozen=True`** observed on any model in this file. Models accept and silently drop unknown fields. (In contrast: scripts and the schema may be stricter — Pass 03/04.)

Methods on `Post`:
- `is_published_to(platform)` (line 95): idempotency check.
- `get_publish_at_utc()` (line 99): parses ISO 8601 (replacing `Z` → `+00:00`), normalizes to UTC.
- `is_ready_to_publish()` (line 105): True iff `status == "scheduled"` AND `get_publish_at_utc() <= now`. **Note:** despite the name, this does NOT return True for `status == "ready"` — naming is cron-mode-centric. GHL mode does its own check.

### `BrandCadence` (lines 113-116)

Fields: `posts_per_week: int`, `preferred_times: list[str]` (HH:MM), `timezone: Optional[str] = "America/Los_Angeles"`. **Default timezone is hardcoded to LA.**

### `BrandCredentials` (lines 119-131)

Fields: `facebook`, `linkedin`, `gbp`, `x`, `instagram` — all `Optional[str]`. Each holds a **Key Vault secret name**, not a raw token (docstring line 121-122).

Comment line 128 (AC14 evidence): `"Should reference same KV key as facebook per AC14"` on the `instagram` field. **Resolves AC14 surface**: Instagram and Facebook are expected to share the underlying KV secret.

Method `get_kv_secret_name(platform)` (line 130) is `getattr(self, platform, None)`.

### `GHLAccountMap` + `GHLConfig` (lines 134-171)

- `GHLAccountMap`: maps platform → GHL account ID for a single author. Fields: `linkedin`, `facebook`, `instagram`, `google_business`, `gbp`. `gbp`/`google_business` are aliases — `get_account_id("gbp")` returns `self.gbp or self.google_business` (line 150).
- `GHLConfig`: `location_id: Optional[str]`, `accounts: Optional[dict[str, dict[str, str]]]` (author → platform → account_id). Method `resolve_account_id(author, platform)` falls back from `platform` to `"google_business"` only when `platform == "gbp"` (line 169-171).
- Docstring line 159-160: *"Optional — absent until Step 4 PR merges. Validated gracefully in publisher."* — confirms cron-mode-first, GHL-bolted-on history.

### `Brand` (lines 174-198)

Fields: `brand_name`, `credentials: BrandCredentials`, `cadence: dict[str, BrandCadence]`, `pillars: list[str]`, `avatar_id: Optional[str] = None` (HeyGen Phase 2 — comment line 179), `slug: Optional[str]` (set from directory name), `ghl: Optional[GHLConfig]`.

`from_yaml` classmethod (lines 183-198): loads YAML, sets `slug`, normalizes `cadence` dict values into `BrandCadence` instances, normalizes `credentials` into `BrandCredentials`, and normalizes `ghl` if present. **No model-level rejection of unknown fields**: pydantic default. `extra` policy: not declared (= `"ignore"` default).

### `RateLimitState` (lines 201-275)

Fields: `platform: str`, `window_start: str` (ISO 8601 UTC), `call_count: int = 0`, `limit: int`, `window_seconds: int`.

`DEFAULTS` ClassVar (lines 210-216, AC-OQ6 platform defaults — verbatim):

| Platform  | limit | window_seconds | Comment |
|-----------|------:|---------------:|---------|
| linkedin  | 100   | 86400          | `100/day` |
| facebook  | 200   | 3600           | `200/hour` |
| instagram | 50    | 86400          | `50/24h` |
| x         | 500   | 2592000        | `500/month (~30d)` |
| gbp       | 1000  | 86400          | `1000/day (conservative)` |

Class methods:
- `load_or_create(state_dir, platform)` (line 218): reads `{state_dir}/{platform}.json`. On parse failure, **silently swallows** (`except Exception: pass` line 229) and creates a fresh state with defaults.
- `is_window_expired()` (line 239): `(now - window_start).total_seconds() >= window_seconds`.
- `is_limited()` (line 246): returns `(bool, Optional[str next_window_iso])`. Side effect: when `is_window_expired()` is True, **mutates** `self.window_start` and `self.call_count = 0` and returns `(False, None)`. The reset is in-place.
- `increment()` (line 265): `self.call_count += 1`. AC-OQ6 ref in docstring.
- `save(state_dir)` (line 269): **atomic write-then-rename**: writes `{platform}.json.tmp` then renames to `{platform}.json` (lines 273-275). AC-OQ6 ref. **Path layout: `state_dir/{platform}.json`** — `state_dir` is set by callers to `brand_dir / ".state"` (publisher.py:178, 326). State file is at the brand root `.state/`, NOT at `.state/rate_limits/` (despite the gitkeep at `brands/<brand>/.state/rate_limits/.gitkeep` from Phase 0 listing). **Pass 02 should confirm whether GHLAdapter writes to a different subdirectory.**

### `PublishResult` (lines 278-286)

Fields: `post_id`, `platform`, `success: bool`, `platform_post_id: Optional[str]`, `error: Optional[str]`, `attempts: int = 1`, `deferred: bool = False`. **Defined but never imported or constructed in `publisher.py` or `retry.py` or `state.py`** (Grep-pending — Pass 02/05 should confirm test usage). Vestigial in this pass.

---

## Retry Primitive (`publisher/retry.py`)

Module docstring (lines 1-11): *"3 attempts total. Backoff delays: 10s after attempt 1, 30s after attempt 2. On 429: respect Retry-After header (max 300s). On exhaustion: create GitHub issue + Telegram notification. Ref: AC7 (GitHub issue on failure), AC-OQ4 (retry timing and dedup)."*

### Public API

Exposed names: `publish_with_retry`, `PublishError`, `RateLimitError`, `PermanentError`. Imported by `publisher.py` as `from .retry import publish_with_retry, PermanentError` (publisher.py:149, 308).

### Backoff strategy

- `BACKOFF_DELAYS = [10, 30, 90]` (line 24) — three delays.
- `MAX_RETRIES = len(BACKOFF_DELAYS) + 1 = 4` (line 25). **Comment line 25 says `# = 3 total attempts` but the code computes 4.** Module docstring also says "3 attempts total". Behavior: the loop is `for attempt in range(1, MAX_RETRIES + 1)` (line 71), i.e. attempts 1..4 — so **4 attempts max, not 3**. **Inconsistency between comment/docstring and code.** Flagged in Unknowns.
- `MAX_RETRY_AFTER = 300` (line 26) — cap on Retry-After header.
- Strategy is fixed-delay-from-table (10/30/90s), NOT computed exponential. Not jittered.

### Retry-eligible vs terminal-error decision

Three exception hierarchies:
- `PermanentError` (line 43, NOT a subclass of PublishError): immediate exit. `_handle_final_failure` is called with the current attempt count, then returns None.
- `RateLimitError` (line 36, subclass of `PublishError`, status_code=429): waits `min(e.retry_after or BACKOFF_DELAYS[min(attempt-1, len(BACKOFF_DELAYS)-1)], MAX_RETRY_AFTER)`. Uses Retry-After header when present, falls back to fixed-delay table. Capped at 300s.
- `PublishError` (line 29): waits `BACKOFF_DELAYS[attempt - 1]` (lines 99-106). Note: when `attempt == 4` (after the loop's last iteration), `BACKOFF_DELAYS[3]` would IndexError — **guarded by the `if attempt <= len(BACKOFF_DELAYS)` check** (line 99 and 110), defaults to 0.
- Bare `Exception` (line 108): treated as retryable — same delay logic as `PublishError`, logs at error level.

After loop exhaustion, `_handle_final_failure` is called and `None` returned (line 128).

### Sleep mechanics

`time.sleep(wait)` (lines 96, 106, 117) — **synchronous, blocking**. Not asyncio. Sleep is skipped on the final attempt (`if attempt < MAX_RETRIES`).

### Final failure side effects

`_handle_final_failure` (line 131) calls `_create_github_issue` then `_send_telegram_notification`. Both are best-effort: failures are logged at warning level and swallowed.

`_create_github_issue` (line 150) shells out to `gh` CLI (`subprocess.run`). Issue title format: `f"[Publish Failed] {post_id} on {platform}"`. Body fields: post_id, platform, error, http status, attempts, post_file_path (if provided), publish_at (if provided). Labels: `publish-failure`, `agent:bob`. **Dedup**: pre-search via `gh issue list --search <title> --state open --json number,title`, exact-title match on first result; if found, posts comment via `gh issue comment <num>` instead of creating new issue. Requires `GITHUB_TOKEN` and `GITHUB_REPOSITORY` env vars; warns and returns if either is missing (line 167-169).

### AC references in retry.py

- Module docstring line 10: `"Ref: AC7 (GitHub issue on failure), AC-OQ4 (retry timing and dedup)"`.
- Line 23: `# Per Dave's OQ4 decision`.
- Line 60: docstring `"per AC-OQ4"`.
- Line 67: docstring `"creates GitHub issue + sends Telegram notification per AC7/OQ4"`.
- Line 142: `"per AC7 and Dave's OQ4 decision"`.
- Line 162: `"(AC7, AC-OQ4)"`.
- Line 174: `# Check for existing open issue (AC-OQ4 dedup)`.
- Line 202: `# Create new issue (AC7)`.
- Line 242: `"per Dave's OQ4 decision (notify on final failure)"`.

---

## State Management (`publisher/state.py`)

Module docstring (lines 1-7): *"The frontmatter IS the state machine (Daedalus design decision). Publisher reads post status from frontmatter, writes back status/post_ids after publish. Ref: AC6 (status/post_ids written back), AC12 (main branch check)."*

### Public API (used by publisher.py)

- `parse_post_file(file_path) -> Optional[Post]` (line 30): regex-extracts frontmatter (`FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n?", re.MULTILINE)` line 27), `yaml.safe_load`s it, instantiates `Post(**frontmatter)`, sets `post._file_path`. Returns None on read/parse/validation error (logged).
- `write_post_status(file_path, post_id, status, post_ids=None, published_at=None)` (line 61): used by cron mode (AC6). Re-serializes frontmatter via `yaml.dump(..., default_flow_style=False, allow_unicode=True, sort_keys=False)`. **Merge semantics for `post_ids`**: existing dict is fetched, `.update(post_ids)` applied (lines 99-101) — additive, never deletes a key. Body content is preserved verbatim (line 112-113). The `post_id` parameter is unused in the body — appears to be vestigial.
- `write_ghl_post_result(file_path, status, ghl_post_id=None, error=None, published_at=None)` (line 124): used by GHL mode. Writes `status`, optionally `ghl_post_id`, `published_at`, `error`. **Clears `error` from frontmatter** when status != "failed" (line 167-169) — only error-clearing operation in either writer.
- `is_committed_on_main(file_path, repo_root) -> bool` (line 190): AC12 implementation. Runs `git log main -- <relpath>`; non-empty stdout ⇒ True. **Fail-open semantics** (line 217: comment `"On failure, fail open (allow publish) to avoid silent silencing."`) — exception path returns True. AC12 reference in docstring line 192.
- `scan_posts_for_brand(brand_dir, repo_root)` (line 220): scans `calendar/<YYYY>/<MM>/*.md` for **current month and next month only** (lines 228-236). Per file: AC12 main-branch check (skipped on miss with logged commit SHA from `git log -1 --format=%H`); `parse_post_file`; `status == "scheduled"` filter. AC-OQ2 reference in docstring line 222.

### Persistence format

- **Frontmatter is YAML, in-place in the .md file.** Round-trip via `yaml.safe_load` → mutate dict → `yaml.dump(..., sort_keys=False)`. Field order is preserved as best as PyYAML supports.
- Rate-limit state is JSON, separately, per the `models.py:RateLimitState.save` (atomic write-then-rename).

### Concurrency

- **No file locks** observed in `state.py` for frontmatter writes. Concurrent runs against the same .md file would race.
- Rate-limit JSON write is atomic at the rename boundary (models.py:273-275).

### State-reset semantics

- Frontmatter `error` is cleared by `write_ghl_post_result` when status is not "failed" (line 167-169). No other state is reset.
- Rate-limit window resets implicitly when `is_window_expired()` is True on the next `is_limited()` call (models.py:252-255).

### AC references in state.py

- Module docstring line 7: `"Ref: AC6 (status/post_ids written back), AC12 (main branch check)"`.
- `write_post_status` docstring line 69: `"AC6"`.
- `write_ghl_post_result` docstring line 132: `"(Step 5 / AC7)"`.
- `is_committed_on_main` docstring line 192: `"AC12"`.
- Inline comments at lines 91, 206, 214: `(AC6)`, `[AC12]`, `[AC12]`.
- `scan_posts_for_brand` docstring line 222: `"(AC-OQ2)"`.
- Inline comment line 247: `# AC12: only process files committed to main`.

---

## Cross-Cutting Patterns

1. **AC reference convention.** Follows Common Pattern: **CP-1 (AC Namespace Divergence)** — see Phase1_Common.md. Pass-01-specific evidence: every module-level docstring lists `Ref: AC<N>...` enumerating the ACs the file claims. Inline single-line comments tag specific decisions: `# AC5: ...`, `# AC6 ...`, `# AC-OQ4 ...`. Both AC namespaces appear: AC1-AC10 (AC2, AC3, AC4, AC5, AC6, AC7, AC8) and the broader namespace (AC11, AC12, AC13, AC14, AC16, AC-OQ1, AC-OQ2, AC-OQ3, AC-OQ4, AC-OQ6). **Confirms Phase 0 review note 1** — code references the broader namespace.
2. **Pydantic model pattern.** `BaseModel` subclasses with `Optional[X] = None` defaults, `@field_validator(...)` decorators (pydantic v2 style), no `extra=forbid`, no `frozen=True`. `from_yaml` classmethod on `Brand` does the YAML→dict→nested-models normalization manually (not via pydantic's own YAML hooks). (Connects to **CP-8 (Schema Field vs Code Validator Coverage Mismatch)** — see Phase1_Common.md.)
3. **Retry policy invocation.** Always: `publish_with_retry(publish_fn=lambda: adapter.publish(...), post_id=..., platform=..., github_token=..., github_repo=..., post_file_path=..., publish_at=...)`. Both cron and GHL modes use the same primitive. Adapters raise `PublishError`/`RateLimitError`/`PermanentError`; the primitive does the rest.
4. **State directory pattern.** Cron and GHL flows both compute `state_dir = brand_dir / ".state"` and `mkdir(parents=True, exist_ok=True)` (publisher.py:178, 326). Adapters receive `state_dir` in `__init__`. Rate-limit JSON files live at `state_dir/{platform}.json`. **The `.state/rate_limits/` subdirectory implied by the gitkeep is not used by `publisher/models.py`.**
5. **Frontmatter-as-state-machine.** Both modes mutate the .md file in place. The publisher does NOT commit/push; the workflow does (out of scope here). `[skip ci]` is mentioned in the publisher docstring (publisher.py:10) but is not enforced in the publisher code itself.
6. **Best-effort side effects + stats-dict surface.** Follows Common Pattern: **CP-6 (Stats-Dict + Best-Effort Side-Effect Convention)** — see Phase1_Common.md. Pass-01-specific evidence: Telegram notification + GitHub issue creation both swallow exceptions and log warnings (retry.py:235-276, 150-232). Frontmatter writeback failures are logged but do not abort the publisher (state.py:120-121, 185-186). `run_publisher` returns `{evaluated, published, deferred, skipped, failed}`; `run_ghl_publisher` returns `{evaluated, published, skipped, failed}` (no `deferred`).
7. **`Optional` defaults everywhere.** No model field is required-with-no-default unless it is mandatory at parse time. This permits gradual schema evolution (e.g., `ghl_post_id` added later without breaking existing posts).
8. **Telegram + GitHub-issue notification layering.** Follows Common Pattern: **CP-5 (Notification Layering)** — see Phase1_Common.md. Pass-01-specific evidence: `_send_telegram_notification` at retry.py:235-276 invoked from `_handle_final_failure` (retry.py:147), always paired with `_create_github_issue`. Triggers: `PermanentError` OR retry-exhaustion. Auth-check path bypasses retry.py and never sends Telegram.
9. **Two-gate workflow — publisher-side enforcement.** Follows Common Pattern: **CP-4 (Two-Gate Workflow Implementation)** — see Phase1_Common.md. Pass-01-specific evidence: Gate 1 = `status == "ready"` filter (publisher.py:210) + `is_committed_on_main` check (state.py — AC12 fail-open). Gate 2 = success path writes `status="ghl-pending"` via `write_ghl_post_result` even when `publish_at` is past-due (line 246: `is_immediate` computed but does not gate publish).
10. **Status enum drift (cron `scheduled` gate vs absent transition writer).** Follows Common Pattern: **CP-3 (Status-Lifecycle Drift Cluster)** — see Phase1_Common.md. Pass-01-specific evidence: `models.py:VALID_STATUSES` lists 8 values including `ghl-pending`; `validate_status` error message describes 5-state lifecycle. `run_publisher` requires `status == "scheduled"` but no code in this pass writes `ready → scheduled`.

---

## Unknowns / Ambiguities

1. **`scheduled` ↔ `ready` transition in cron mode** — `run_publisher` only processes `status == "scheduled"`, but no code in this pass writes `ready → scheduled`. Phase 0 workflow lists `draft → ready → ghl-pending → published`, omitting `scheduled` entirely, while `models.py:VALID_STATUSES` includes both. **Hypothesis: cron mode is a pre-GHL legacy path, currently not on the active workflow.** Pass 04 (schema) and Pass 06 (workflows) must reconcile.
2. **`MAX_RETRIES = 4` vs documented "3 attempts"** — `BACKOFF_DELAYS = [10, 30, 90]` plus `MAX_RETRIES = len(BACKOFF_DELAYS) + 1 = 4` total iterations of the retry loop. Module docstring says "3 attempts total"; comment line 25 says `# = 3 total attempts`. Code does 4. **Likely a bug or stale comment.** Flag for Pass 05 (tests).
3. **`PublishResult` model is dead code in this pass** — defined in `models.py:278-286` but not imported anywhere within `publisher/{publisher,retry,state}.py`. Pass 02/05 should confirm whether adapters or tests use it.
4. **Rate-limit state path** — `RateLimitState.save` writes `state_dir/{platform}.json`, but `brands/<brand>/.state/rate_limits/.gitkeep` exists in the repo. Pass 02 (adapters) must check whether `GHLAdapter` uses a different state path.
5. **`account_id` field on `Post`** vs `brand.ghl.accounts` lookup — `Post.account_id` (models.py:48) is documented as an override. Whether `GHLAdapter` consults the post-level override or always resolves via `brand.ghl.resolve_account_id(author, platform)` is a Pass 02 question.
6. **`extra` policy on pydantic models** — none declared. Unknown frontmatter fields silently survive `Post(**frontmatter)`. The strict schema validation that AC1 implies must therefore live elsewhere (Pass 03 — `validate-post.py`).
7. **`write_post_status`'s `post_id` parameter is unused** — vestigial signature. Phase 5/6 cleanup candidate.
8. **`status: "video-pending"`** — listed in `VALID_STATUSES` but no code in this pass produces or consumes it. Phase 2 HeyGen forward-pointer.
9. **Telegram bot credential provisioning** — env vars consumed at runtime (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`); how they're injected into the GHA runner (KV reference? raw secret?) is a Pass 06 question.
10. **`auth_check.yml` does NOT use Telegram** — failure path is GitHub issue with `credential-failure` + `agent:bob` (per Phase 0 note 7). The publish path uses Telegram + GitHub issue with `publish-failure` + `agent:bob`. **Confirmed by code in this pass** (retry.py:147 always calls both; auth-check path doesn't go through retry.py at all). Whether this asymmetry is intentional → Phase 0 Unknown #14, deferred to Pass 06.
