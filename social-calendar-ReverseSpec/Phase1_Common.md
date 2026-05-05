# Phase 1.5 — Reconciliation: Common Patterns

**Snapshot:** `67d061c`
**Method:** Patterns extracted from Phase 1 per-pass files (01–06) when the same behavior recurs in **2+ passes** AND is not already DRY in a shared layer. No intent inference; no improvement proposals. Drift dimensions and per-pass cites preserved verbatim.

---

## CP-1 — AC Namespace Divergence

**Definition.** Two AC numbering systems coexist in this repo with overlapping numbers but **different meanings** for AC1, AC2, AC5, AC6, AC7, AC8. `docs/AC_VERIFICATION_SUMMARY.md` (vintage 2026-03-27, issue-#2/"Vulcan") declares AC1–AC10. Code + workflow comments cite a broader namespace (AC11–AC16 + AC-OQ2/3/4/6) that is **not enumerated in any in-repo file**. AC# is therefore **not a stable identifier** across this repo's documentation surface vs its code-comment surface.

**Implementing passes.**
- **Pass 01** — module docstrings cite both namespaces (`publisher.py:33` lists AC3/AC4/AC5/AC6/AC7/AC11/AC12/AC16/AC-OQ2/AC-OQ4/AC-OQ6 + AC7-GHL); inline comments use broader-namespace tokens.
- **Pass 02** — `base.py` cites AC2/AC3/AC4/AC-OQ6; `instagram.py` cites AC14; `x_twitter.py` cites AC15; `ghl.py` cites AC2/AC3/AC4/AC6. AC18 implied for "draft" gating but never written.
- **Pass 03** — `validate-post.py` docstring cites AC1/AC5/AC8/AC11/AC-OQ2/AC-OQ3; AC8 means different things in `validate-brand.py` ("raw tokens") vs `validate-post.py` ("required fields, status, author/account resolution") — same token, different rules.
- **Pass 04** — schema cites AC1/AC5/AC6/AC7/AC11/AC-OQ3/AC-OQ6; `brand.yaml` cites AC8/AC14/AC16. None appear in `AC_VERIFICATION_SUMMARY.md`.
- **Pass 05** — `test_publisher_ghl_mode.py` cites AC6/AC7 (the only test file with AC tags); `test_ghl_adapter.py` cites only "issue #2".
- **Pass 06** — central reconciliation table built; the AC# semantics for AC1/AC2/AC5/AC6/AC7/AC8 differ between `AC_VERIFICATION_SUMMARY.md` and code/workflow YAML comments.

**Drift dimensions.**
- *Same number, different meaning:* AC1 (capability matrix vs schema validation); AC2 (list-accounts CLI vs auth_check); AC5 (delete-post CLI vs timezone enforcement); AC6 (env-var fallback vs commit-status-back); AC7 (multi-meaning: GHL adapter routing vs failure-issue creation vs "GitHub issue creation" in runbook); AC8 (Riley→schema vs raw-token detection vs brand-config/account resolution).
- *Doc-only ACs (broader namespace not in summary):* AC11, AC12, AC13, AC14, AC15, AC16, AC-OQ2, AC-OQ3, AC-OQ4, AC-OQ6.
- *Workflow YAML cites broader-namespace tokens unrelated to summary:* `validate-pr.yml` cites AC1/AC5/AC11/AC12/AC-OQ2/AC-OQ3 (6 tokens); `auth-check.yml` cites AC2/AC13; `publish.yml` cites AC6/AC7/AC8.
- *AC12 attribution gap:* cited in `validate-pr.yml` header but appears in NO script (Pass 03 + Pass 06).

**Reconciliation observations.**
- Source for the broader namespace lives outside this repo (presumed Daedalus issue thread; SOCIAL_CALENDAR_WORKFLOW §10 has 3 `<TBD>` issue-number placeholders, never filled).
- Stale CLI script citations in `AC_VERIFICATION_SUMMARY.md` (AC2–AC5 anchored to consolidated `ghl_social.py` subcommands) are doubly stale: scripts don't exist AND the AC numbers have been re-purposed in code comments.
- This pattern AMPLIFIES every other drift pattern — coverage claims, doc cross-references, and workflow gating cite ACs whose meaning depends on which file you read.

---

## CP-2 — Stale-Doc Script-Path References

**Definition.** Six script/test paths cited across repo docs do not exist on disk at snapshot. All 4 `ghl_social_*.py` CLIs were consolidated into `scripts/ghl_social.py` subcommands; `publish_posts.py` and `test_publish_posts.py` never existed at this snapshot. Approximately 24 individual cite-occurrences across 4 docs + 1 brand.yaml comment + 1 script error string.

**Stale paths.**
1. `scripts/ghl_social_list_accounts.py` → `ghl_social.py accounts`
2. `scripts/ghl_social_create_post.py` → `ghl_social.py create`
3. `scripts/ghl_social_list_posts.py` → `ghl_social.py posts`
4. `scripts/ghl_social_delete_post.py` → `ghl_social.py delete`
5. `scripts/publish_posts.py` (no current equivalent — publish path is `publisher.publisher` invoked by `publish.yml`)
6. `tests/test_publish_posts.py`

**Implementing passes.**
- **Pass 03** — confirms consolidation of (1)–(4) into `ghl_social.py`. Surfaces `validate-post.py:251` error string still saying "run ghl_social_list_accounts.py."
- **Pass 04** — `brands/secondring/brand.yaml` lines 24–25 instructs operator to run `ghl_social_list_accounts.py` (stale comment).
- **Pass 06** — quantifies: 6 stale paths across `AC_VERIFICATION_SUMMARY.md` (~15 cites), `DEVELOPER_GUIDE.md` (5+ cites), `GHL_SOCIAL_PLANNER_ARCHITECTURE.md` (line 99–100), `OPERATIONAL_RUNBOOK.md` (lines 113, 187, 198, 210, 279, 301).

**Drift dimensions.**
- All 3 stale-citing docs share author `[Bob — claude-sonnet-4-6] / Forge #2 Docs Phase` and pre-date the consolidation refactor.
- README (line 59) IS current — references `ghl_social.py` correctly. So drift is doc-author-cluster–specific, not repo-wide.
- Drift extends into runtime artifacts (script error string at `validate-post.py:251`; brand.yaml comment).

**Reconciliation observations.**
- Same root cause as CP-1: the docs were generated at a single Forge phase and never updated. The script paths and the AC numbers are co-stale.
- README's correctness suggests update happened by someone other than the original doc author; the bulk-doc set in `docs/` was untouched.

---

## CP-3 — Status-Lifecycle Drift Cluster

**Definition.** The post status state machine has at least three different shapes across this repo's surfaces. `models.py:VALID_STATUSES` (8 values), schema enum (7 values), and 3 docs disagree on whether `ghl-pending` is a valid state and which transition the publisher writes.

**Implementing passes.**
- **Pass 01** — `models.py` `VALID_STATUSES = {draft, ready, ghl-pending, scheduled, published, failed, deferred, video-pending}` (8 values). `validate_status` error message describes lifecycle as "draft → ready → scheduled → published | failed" — not exhaustive (missing ghl-pending, video-pending, deferred). Cron mode processes only `status == "scheduled"`; nothing in cron-mode code writes `ready → scheduled`.
- **Pass 03** — `validate-post.py` `VALID_STATUSES = {draft, ready, scheduled, published, failed, deferred, video-pending}` (7 values; **missing `ghl-pending`** vs models.py). `ghl_social.py posts --status` choices = `{scheduled, published, failed, draft}` (4 values, narrower).
- **Pass 04** — schema enum (line 36) `[draft, ready, scheduled, published, failed, deferred, video-pending]` (7 values, **no ghl-pending**); lifecycle declared as `draft → ready → scheduled → published | failed`.
- **Pass 05** — tests assert `status == ghl-pending` writeback (`test_writes_ghl_pending_status`, `test_publishes_ready_post_*_as_draft`). Tests treat `ghl-pending` as a real, expected status.
- **Pass 06** — README + SOCIAL_CALENDAR_WORKFLOW: 6-state `draft → ready → ghl-pending → scheduled → published | failed`. ARCHITECTURE.md (line 266): 5-state, omits `ghl-pending`. DEVELOPER_GUIDE: implies post-publisher status is `scheduled`.

**Drift dimensions.**
- *`ghl-pending` membership:* in models.py + tests + README + WORKFLOW; absent from schema enum + validate-post.py enum + ARCHITECTURE.md.
- *Cron-mode `scheduled` gate:* required by `run_publisher` (Pass 01) but no code in any pass writes `ready → scheduled`. Hypothesis (Pass 01): cron mode is pre-GHL legacy.
- *Workflow doc terminology:* "ghl-pending" used in WORKFLOW §10 as a desired/aspirational state; actual schema value is `scheduled` (Pass 04 calls this "stale workflow doc terminology").
- *Naming inconsistency on `Post.is_ready_to_publish`:* despite name, returns True only when `status == "scheduled"` — cron-mode-centric naming (Pass 01).

**Reconciliation observations.**
- The schema enum and validate-post.py agree (`ghl-pending` not valid); models.py + tests + README disagree (treat it as the canonical post-publisher status). Schema validation would REJECT the value the publisher writes.
- This is the cleanest example of doc surface vs code surface vs schema surface diverging on the same artifact.

---

## CP-4 — Two-Gate Workflow Implementation

**Definition.** The README's "two-gate" framing (Gate 1 = GitHub PR copy approval; Gate 2 = GHL Social Planner visual approval) is implemented across multiple files using different mechanisms — no single module owns the invariant.

**Implementing passes.**
- **Pass 01** — Gate 1 implementation: `run_ghl_publisher` only processes `status == "ready"` (publisher.py:210), and `state.py:is_committed_on_main` enforces "merged to main" (AC12 — fail-open semantics). Gate 2 implementation: success path writes `status="ghl-pending"` (publisher.py via `write_ghl_post_result`), never auto-publishes; even past-due `publish_at` lands as draft.
- **Pass 02** — Gate 2 wire-level: `GHLAdapter.publish` hardcodes `"status": "draft"` in the API payload (ghl.py:120). Inline comment: "Gate 2: land as draft for Dave's manual approval in GHL UI". No flag/parameter overrides this.
- **Pass 03** — Gate 1 implementation also includes `validate-pr.yml` (Job 1 + Job 2 fallback) running `validate-post.py` + `validate-brand.py` as the merge-blocking check.
- **Pass 04** — schema declares `status: ready` semantics ("merged to main and eligible for publisher pickup") — supports Gate 1 framing.
- **Pass 05** — tests assert Gate 1 (skip-non-ready: `test_skips_draft_posts`) and Gate 2 invariants (`test_payload_contains_scheduled_at_and_draft_status` for the wire payload; `test_publishes_ready_post_immediate_as_draft` for the past-due-still-drafts behavior).
- **Pass 06** — README owns the framing (line 11–26); WORKFLOW.md §10.1 says draft mode is "REQUIRED / not yet implemented" — yet code (Pass 02) DOES hardcode `status: "draft"`. Doc-vs-code drift on whether Gate 2 is "live."

**Drift dimensions.**
- *Where Gate 1 is enforced:* PR validation (validate-pr.yml + validate-post.py) AND publisher status gate (`status == "ready"`) AND `is_committed_on_main` check. Three layers, each independent.
- *Where Gate 2 is enforced:* hardcoded payload literal (`status: "draft"` in ghl.py:120) plus publisher status writeback (`ghl-pending`).
- *Doc-vs-code disagreement on Gate 2 liveness:* WORKFLOW §10.1 declares Gate 2 not yet implemented; ghl.py:120 hardcodes the draft literal; tests assert it.
- *Gate-bridging notifications:* Telegram (publish-time) + GitHub issue creation (failure-time) bridge the gates — see CP-5 + CP-6.

**Reconciliation observations.**
- Two-gate is a distributed invariant: PR validation, status enum, publisher state machine, and adapter payload literal each contribute. No single test or check covers the end-to-end invariant.
- WORKFLOW §10's "REQUIRED / not yet implemented" claim is contradicted by code — likely the doc was written before the code change.

---

## CP-5 — Notification Layering (Telegram + GitHub Issues)

**Definition.** Two notification mechanisms — Telegram and GitHub issue creation — are paired in failure handling but split asymmetrically across the publish vs auth-check flows. README + WORKFLOW describe Telegram for publish-time gating; ghl_social.py and adapters never touch Telegram.

**Implementing passes.**
- **Pass 01** — `_send_telegram_notification` defined at `retry.py:235-276`; called only from `_handle_final_failure` (retry.py:147), which fires on `PermanentError` OR retry-exhaustion. Always paired with `_create_github_issue` in same handler. Credentials read from env vars `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`. Best-effort: failures swallowed.
- **Pass 05** — zero `telegram` references in either test file. Telegram impl is unverified by tests despite being in retry.py.
- **Pass 06** — `publish.yml` injects `TELEGRAM_BOT_TOKEN` (secret) + `TELEGRAM_CHAT_ID` (var). `auth-check.yml` does NOT inject Telegram secrets — instead creates `[Auth Check Failed]` GitHub issue with `credential-failure` + `agent:bob` labels. README claims "Telegram notification: 'X posts pending approval in GHL'" (publish-time success event); WORKFLOW §10.2 says Telegram is "REQUIRED / not yet implemented"; OPERATIONAL_RUNBOOK §3 frames Telegram as failure-alerting (Phase 2).

**Drift dimensions.**
- *Telegram trigger semantics:* code (retry.py) fires Telegram on **failure** (paired with GitHub issue). README describes Telegram as **publish-time success** notification. WORKFLOW §10.2 claims **not implemented**. RUNBOOK §3 describes **failure alerting**. Four sources, three different semantics.
- *Auth-check vs publish asymmetry:* publish path uses Telegram + GitHub issue (`publish-failure` + `agent:bob` labels). Auth-check path uses GitHub issue ONLY (`credential-failure` + `agent:bob` labels). Asymmetry is structural — auth-check never enters retry.py.
- *Test coverage:* zero. Pass 05 confirms.

**Reconciliation observations.**
- The publisher CODE matches the runbook view (Telegram on failure, paired with GitHub issue). README's "X posts pending approval" success message is unimplemented.
- Coordination redundancy is a pattern: `_handle_final_failure` always fires both — never one without the other. Dedup on GitHub-issue side (title-equality match) but no dedup on Telegram side.

---

## CP-6 — Stats-Dict + Best-Effort Side-Effect Convention

**Definition.** Publisher orchestrators return stats dicts; side effects (Telegram, GitHub issues, frontmatter writeback, atomic state files) are best-effort with logged-and-swallowed failures.

**Implementing passes.**
- **Pass 01** — cron `run_publisher` returns `{evaluated, published, deferred, skipped, failed}` (5 keys). GHL `run_ghl_publisher` returns `{evaluated, published, skipped, failed}` (4 keys, **no `deferred`**). All three side-effect paths swallow exceptions: Telegram (retry.py:235-276), GitHub issues (retry.py:150-232), frontmatter writeback (state.py:120-121, 185-186). Rate-limit JSON write is atomic via write-then-rename (models.py:273-275).
- **Pass 05** — tests assert stats-dict shape: `stats["skipped"]`, `stats["published"]`, `stats["failed"]` (TestRunGhlPublisher) — confirms 3-key surface from outside.

**Drift dimensions.**
- *Cron vs GHL stats shape:* cron has `deferred`, GHL doesn't. `deferred` only meaningful when rate-limit gate is hit (cron-mode-only path).
- *Atomicity scope:* JSON state files atomic; frontmatter writeback NOT atomic (no file lock — Pass 01 notes concurrent runs would race).

**Reconciliation observations.**
- Pattern is repo-wide: every "outside the happy path" effect logs-and-continues. Failure-tolerance is the design, not the exception.

---

## CP-7 — Deprecated-Adapter Runtime Liveness

**Definition.** Five platform adapters (facebook, instagram, linkedin, gbp, x_twitter) are documented as deprecated in README but remain runtime-live for `auth_check` purposes. They are imported, registered, and invoked by `auth-check.yml`'s weekly run. Zero test coverage.

**Implementing passes.**
- **Pass 01** — `run_auth_check` (publisher.py:469-496) iterates `brand.credentials.__dict__` and instantiates adapters from `ADAPTER_REGISTRY`. Confirms deprecated adapters are reached via this path.
- **Pass 02** — confirmed runtime-live: imported via `publisher/adapters/__init__.py`; registered in `ADAPTER_REGISTRY` (`__init__.py:20-26`); instantiated by both `run_publisher` (cron mode) and `run_auth_check`. NOT instantiated by `run_ghl_publisher`. In-file deprecation markers inconsistent: 3 say "Phase 1 skeleton" (facebook/linkedin/gbp); 2 (instagram/x_twitter) carry no in-file marker. None say "deprecated" inline.
- **Pass 05** — zero references to deprecated adapter classes in tests. Confirmed gap.
- **Pass 06** — `auth-check.yml` injects `FACEBOOK_PAGE_ID`, `LINKEDIN_AUTHOR_URN`, `GBP_LOCATION_NAME`, `INSTAGRAM_USER_ID` env vars (lines 50–53) — needed by deprecated adapters' `auth_check()` methods. README line 153 says "GHL manages platform OAuth — no token rotation needed on our side" — soft drift vs auth-check.yml's per-platform env iteration.

**Drift dimensions.**
- *Doc deprecation vs runtime liveness:* README lists 5 as deprecated; code keeps them alive for auth-check.
- *Marker inconsistency:* "Phase 1 skeleton" (3) vs no marker (2) vs README "Deprecated" (5). No file uses literal "deprecated."
- *Test coverage:* 0 / 5 covered.
- *Per-adapter AC tags:* facebook AC3/AC4/AC13/AC14; instagram AC14/AC3/AC4; linkedin AC3/AC4/AC13; gbp AC3/AC4/AC13/AC-OQ6; x_twitter AC15/AC3/AC4/AC-OQ4/AC-OQ6 — all from broader namespace.

**Reconciliation observations.**
- "Deprecated by docs but live by runtime" is a discrete pattern: not pure dead code, not currently used for publishing, but exercised weekly via auth-check.
- Pattern intersects CP-1 (AC15 unique to x_twitter, AC14 unique to instagram — broader-namespace ACs anchored to deprecated code).

---

## CP-8 — Schema Field vs Code Validator Coverage Mismatch

**Definition.** The schema declares 15 fields (14 top-level + nested `creative`) but `validate-post.py` validates only a subset; some fields are validated nowhere. Schema vs models.py vs validate-post.py have parallel-but-not-equal field/enum coverage.

**Implementing passes.**
- **Pass 01** — `models.py` declares Pydantic `Post` with no `extra=forbid` / no `frozen=True`; unknown frontmatter fields silently survive parsing. `VALID_PLATFORMS`, `VALID_STATUSES`, `VALID_AUTHORS` constants; field validators only on platforms/status/author. No timezone validator on `publish_at` — comment line 41 says "validated by validate-post.py."
- **Pass 03** — `validate-post.py` enforces required fields (id/publish_at/platforms/status/brand/author), `id` regex, `publish_at` ISO+offset, platforms enum, status enum, author enum, ghl.accounts cross-validation, copy section headers, per-platform char limits. Does NOT validate `account_id`, `ghl_mode`, `campaign`, `tags`, `published_at`, `ghl_post_id`, `post_ids`, `error`, `creative` sub-fields. `validate-brand.py` does NOT check `ghl:` block at all.
- **Pass 04** — schema declares 15 fields with type/required/enum/pattern; `additionalProperties` policy NOT declared in schema (deferred to validate-post.py).

**Drift dimensions.**
- *Validated-everywhere fields:* id, publish_at, platforms, status, author.
- *Validated-only-in-schema fields:* `account_id`, `ghl_mode`, `campaign`, `tags`, `published_at` (publisher-written), `ghl_post_id` (publisher-written), `post_ids`, `error`, `creative.*`.
- *Validated-only-by-script (no schema rule):* none — validate-post.py adds cross-validation against brand.yaml's ghl.accounts, but that's not a schema field per se.
- *Enum disagreements:* status — schema 7 vs models.py 8 (CP-3); platforms — agreement (5 across all 3); author — agreement.
- *Validate-brand.py vs schema:* `validate-brand.py` doesn't validate `ghl.accounts` block at all; schema doesn't either; only `validate-post.py` cross-validates author→ghl.accounts (and silent-passes when block absent).

**Reconciliation observations.**
- The schema is a documentation artifact — no automated enforcement reads it. Validation is hand-coded in `validate-post.py`. Schema and validator are independently maintained.
- `additionalProperties` undeclared means new fields can be added to frontmatter without anyone failing. The strict schema validation that AC1 implies lives partly in the script and partly nowhere.

---

## CP-9 — Hardcoded Constants & Conventions

**Definition.** Several values are hardcoded in code rather than centralized in configuration: GHL API constants, per-platform rate-limit defaults, the `status="draft"` GHL payload literal, the `ghl-publisher` concurrency group name, the `cUgvqrKmBM4sAZvMH1JS` GHL_LOCATION_ID, character limits.

**Implementing passes.**
- **Pass 02** — `BASE_URL = "https://services.leadconnectorhq.com"` (ghl.py:40); `API_VERSION = "2021-07-28"` (ghl.py:41); `LINKEDIN_CHAR_LIMIT = 3000` (linkedin.py); `GBP_CHAR_LIMIT = 1500` (gbp.py); `X_CHAR_LIMIT = 280` (x_twitter.py). `status: "draft"` hardcoded in GHL payload (ghl.py:120). `LinkedIn-Version: 202401` header.
- **Pass 01** — `BACKOFF_DELAYS = [10, 30, 90]`, `MAX_RETRY_AFTER = 300`, `MAX_RETRIES = len(BACKOFF_DELAYS) + 1 = 4`, `BrandCadence.timezone` default `"America/Los_Angeles"`. `RateLimitState.DEFAULTS` ClassVar with per-platform limit/window pairs (linkedin 100/86400; facebook 200/3600; instagram 50/86400; x 500/2592000; gbp 1000/86400).
- **Pass 03** — `validate-post.py` per-platform char-limit dict (linkedin 3000, x 280, gbp 1500, facebook 63000, instagram 2200) duplicated from schema's `platform_limits` block.
- **Pass 04** — schema `platform_limits:` block (single source of truth claim, lines 168–175). `GHL_LOCATION_ID: cUgvqrKmBM4sAZvMH1JS` in `brands/secondring/brand.yaml` line 35.
- **Pass 06** — `concurrency.group: ghl-publisher` (publish.yml:33); auth-check cron `'0 9 * * 1'` (Monday 09:00 UTC). Phase 0 review claimed group `publisher` — actual `ghl-publisher`.

**Drift dimensions.**
- *Char-limit duplication:* schema declares them; `validate-post.py` re-declares them; deprecated adapters declare their own (`LINKEDIN_CHAR_LIMIT`, `GBP_CHAR_LIMIT`, `X_CHAR_LIMIT`). Three locations, currently consistent.
- *Rate-limit defaults:* declared once in `models.py` ClassVar — DRY here, not duplicated. (Counter-example to the pattern.)
- *Location ID:* lives in brand.yaml AND can be overridden by env (`GHL_LOCATION_ID` env var wins per ghl.py:69). Two sources, env-first.
- *Retry comment vs code:* `MAX_RETRIES` computes 4; comment + docstring say "3 attempts total" (Pass 01 unknown #2).

**Reconciliation observations.**
- Char-limit triplication is the most material drift risk: change schema and 2 other places must follow.
- Most other constants are localized cleanly; the pattern is "many constants, mostly DRY each in their own home, but char-limits are not."

---

## CP-10 — Empty Phase-2 / Forward-Pointer Placeholders

**Definition.** Multiple zero-content placeholders point at deferred Phase 2 (HeyGen) or unfinished Phase 1 work, without explicit in-repo documentation of what they're for.

**Implementing passes.**
- **Pass 04** — `templates/.gitkeep` (0 bytes, no README mention); `campaigns/spring-launch-2026/.gitkeep` (0 bytes, no post references this slug; VP posts use `q2-2026-*` slugs); `avatar_id: null` in both brand.yaml files; schema `creative.type` enum includes `heygen`; schema `creative.video_url` annotated "Written by publisher (Phase 2)"; schema `status` enum includes `video-pending` ("HeyGen not complete (Phase 2)"). 6 unfilled `<account_id>` placeholders in `brands/secondring/brand.yaml`. `brands/velocitypoint/brand.yaml` has NO `ghl:` block at all despite all 3 VP posts having `ghl_mode: true`.
- **Pass 06** — `SOCIAL_CALENDAR_WORKFLOW.md §10` lists 3 `<TBD>` issue numbers for "Open Technical Work" (10.1 GHL Draft Mode, 10.2 Telegram, 10.3 Status Polling) — never resolved. `auth_check.yml` Azure Login conditional `vars.AZURE_CLIENT_ID != ''` — Phase 2 KV path not yet exercised. `.gitignore` `.config/` entry for xurl — no current workflow writes it.

**Drift dimensions.**
- *Forward-pointer specificity:* explicit (avatar_id null + comment "Phase 2 — HeyGen") vs implicit (empty templates/ and campaigns/spring-launch-2026/ with no comment).
- *Launch-blocker shape inconsistency:* secondring has 6 placeholders; velocitypoint has 0 placeholders but only because the `ghl:` block is absent — yet VP posts ARE GHL-mode. The "true" launch-blocker count is 6 + (full ghl: block missing for VP) — inconsistent across brands.
- *TBD issue references:* 3 in WORKFLOW §10, never filled.

**Reconciliation observations.**
- Phase 2 forward-pointers are scattered across schema, brand.yaml, models.py, gitignore, and docs — no single inventory. Some are labeled (avatar_id, video-pending), most are not.
- The `<TBD>` issue numbers in WORKFLOW §10 + the missing-but-needed `ghl:` block for VP both indicate live work-in-progress that the snapshot captures mid-stride.

---

## CP-11 — Cross-Spec GHL Convention (Cross-Spec Marker)

**Definition.** This is NOT a within-repo recurring pattern; recorded here per Phase 1.5 cross-spec instructions. The same GHL HTTP convention — `Authorization: Bearer <token>` + `Version: 2021-07-28` header against `https://services.leadconnectorhq.com` — appears in this repo, in `RP` (per Phase 0 cross-spec note), and in `sr-ops-tools` (Phase 0 C7 marker). Pass 02 confirms identical convention here (ghl.py:305-311).

**Implementing pass.**
- **Pass 02** — header construction in `_request` (ghl.py:305-311). Bearer from `GHL_API_KEY` env var. Cross-references RP and sr-ops-tools per Phase 0 markers.
- **Pass 04** — brand.yaml `cUgvqrKmBM4sAZvMH1JS` location-id matches the value referenced cross-repo per sr-ops-tools Pass 04.

**Reconciliation observations.**
- Treat as a stable cross-spec contract worth tracking when the GHL API version changes; not actionable within this Phase 1.5 reconciliation.

---

## Pattern density vs sr-google-ads

This repo's Phase 1 finding density is materially higher than sr-google-ads's, driven primarily by **CP-1 (AC namespace divergence)** which amplifies every other drift pattern. CP-2 (stale script paths) and CP-3 (status-lifecycle drift) are large because doc/code drift is doc-author-cluster–specific and unresolved. CP-7 (deprecated-but-live adapters) is a structural pattern with few cross-spec equivalents. The two-gate workflow (CP-4) is distinctive to social-calendar.
