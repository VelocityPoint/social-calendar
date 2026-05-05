# Phase 4 — Gap Analysis

**Snapshot:** `67d061c` (2026-04-26)
**Method:** Each finding traces to specific Phase 1 / Phase 1.5 / Phase 2 / Phase 3 evidence. Severity is High / Medium / Low. **No fix proposals — that is Phase 5.**

**Status posture.** Repo is post-MVP, pre-real-traffic. Campaign 1 has not yet run. velocitypoint brand.yaml is missing the entire `ghl:` block. Highs that block first publish are most material. Findings concerning behaviour that "would matter if X were ever exercised" are scoped accordingly.

**Categories.**
- **S1** — Missing Features (capabilities Phase 2 / Phase 3 imply but Phase 1 evidence shows are not implemented)
- **S2** — Undefined Behaviour (code paths whose effect at runtime is ambiguous, contradicted by evidence, or outright unreachable)
- **S3** — Inconsistencies (the same fact stated differently across two or more sites)
- **S4** — Risks (security / reliability / operational / compliance / pre-launch hazards)
- **S5** — Technical Debt (cluster-scale and structural)

---

## S1 — Missing Features

### S1.1 — I-11 violated: AC identifier namespace not globally unique
- **What.** Per Phase 3 I-11, AC identifiers MUST be globally unique within the repo. They are not. Two parallel spec sources (Vulcan = issue #2, Daedalus = un-numbered) collide on AC1, AC2, AC5, AC6, AC7, AC8 — same number, different meanings. The "globally unique AC namespace" capability the convention promises does not exist.
- **Why we know.** Phase 1.5 CP-1 enumerates the collisions across `AC_VERIFICATION_SUMMARY.md` (AC1–AC10) and the broader namespace AC11–AC16 + AC-OQ2/3/4/6 found only in code/workflow YAML. Phase 3 §4.5 + I-11 explicitly call this out as an unmet invariant. Phase 2 Group B + Sp.A confirm the divergence as accidental cross-spec collision, not intentional convention.
- **Severity.** Medium-High.
- **Trace.** `Phase1_Common.md` CP-1; `Phase3_Spec_Reviewed.md` §4.5, I-11; `Phase2_Intent_Reviewed.md` Sp.A, Group B.2. Cite sites: `publisher.py:33`, `validate-post.py` docstring, `validate-pr.yml` header, `auth-check.yml` header, `publish.yml` header, `OPERATIONAL_RUNBOOK.md` §AC tables.
- **Notes.** This is the amplifier finding — every "AC<n> is covered" / "AC<n> gates this workflow" claim depends on which doc you read. Filed once per the prompt.

### S1.2 — I-12 violated: status enum not canonical across schema, models, validator, tests
- **What.** Per Phase 3 I-12, the status enum MUST be canonical across schema, models, validator, and tests. It is not. `models.py:VALID_STATUSES` includes `ghl-pending` (8 values); `schemas/post.schema.yaml` and `validate-post.py` do not (7 values, no `ghl-pending`). Tests assert publisher writes `ghl-pending`. Schema validation would reject the value the publisher writes.
- **Why we know.** Phase 1.5 CP-3 enumerates four status-shape sites with three distinct shapes. Phase 1 Pass 01 / 03 / 04 / 05 cite the disagreement directly. Phase 3 §4.4 + I-12 declare the invariant and flag the violation.
- **Severity.** High. (See also S4.2 — runs as a reliability risk.)
- **Trace.** `Phase1_Common.md` CP-3; `Phase3_Spec_Reviewed.md` §4.4, I-12; `Phase2_Intent_Reviewed.md` Sp.B; `models.py:VALID_STATUSES`, `schemas/post.schema.yaml:36`, `validate-post.py:VALID_STATUSES`, `tests/test_publisher_ghl_mode.py::test_writes_ghl_pending_status`.

### S1.3 — velocitypoint `brand.yaml` missing entire `ghl:` block (launch blocker)
- **What.** `brands/velocitypoint/brand.yaml` has no `ghl:` block (no `location_id`, no `accounts` map). All 3 VP posts at snapshot declare `ghl_mode: true`. Publisher path for VP posts hits `getattr(brand, "ghl", None) → None → _no_ghl_config_returns_early`. Posts silently no-op: 0 published, 0 failed, no error surfaced.
- **Why we know.** Phase 1 Pass 04 unknown #6; Phase 1 Pass 05 has `test_no_ghl_config_returns_early` directly asserting the silent-no-op behavior. Phase 2 Sp.J flags both staging-intent (Medium) and silent-no-op consequence (High). Phase 3 §4.11 (forward-pointer hygiene) + I-13 (credentials must resolve from secret store) bracket this.
- **Severity.** High (launch blocker — first VP publish fails silently).
- **Trace.** `Phase2_Intent_Reviewed.md` Sp.J; `Phase1_Compacted.md` Pass 04 unknown #6 line 417; test `tests/test_publisher_ghl_mode.py::test_no_ghl_config_returns_early`; `brands/velocitypoint/brand.yaml` (no ghl block); 3 VP posts at `brands/velocitypoint/calendar/2026/q2-2026-*.md` (`ghl_mode: true`).
- **Notes.** Tied with S1.4 as the "Campaign 1 won't publish" finding pair. Test asserts the no-op as correct rather than flagging it — the failure mode is normalised.

### S1.4 — secondring `brand.yaml` has 6 unfilled `<account_id>` placeholders (launch blocker)
- **What.** `brands/secondring/brand.yaml` contains 6 unfilled `<account_id>` placeholders under `ghl.accounts` (4 under `dave`, 2 under `velocitypoint`). Until populated, account resolution will return placeholder strings to the GHL API, producing publish failures (or accepted-but-mis-routed posts).
- **Why we know.** Phase 1 Pass 04 finding #10 (line 425) counts placeholders directly. Phase 1.5 CP-10 includes them in the forward-pointer cluster. Phase 3 §4.11 (forward-pointer hygiene) + I-13 cover this in spirit.
- **Severity.** High (launch blocker — first SR publish on any account holding a `<account_id>` placeholder fails or mis-routes).
- **Trace.** `Phase1_Compacted.md` Pass 04 #10 line 425; `Phase1_Common.md` CP-10; `brands/secondring/brand.yaml` `ghl.accounts` map.
- **Notes.** No automated check enforces "placeholders must be filled before publish." `validate-brand.py` doesn't validate `ghl:` block at all (Pass 03).

### S1.5 — AC12 cited in workflow header but implemented in no script
- **What.** `validate-pr.yml` header cites AC12 ("ensures only valid docs reach main") but no script in the repo carries an `AC12` tag. `state.py:is_committed_on_main` is the obvious implementation candidate but is not tagged AC12 anywhere.
- **Why we know.** Phase 1.5 CP-1 calls this out explicitly ("AC12 attribution gap"). Phase 1 Pass 03 + Pass 06 confirm. Phase 2 Sp.D treats this as placeholder for future wiring (Medium confidence).
- **Severity.** Low-Medium.
- **Trace.** `Phase1_Common.md` CP-1; `Phase2_Intent_Reviewed.md` Sp.D; `validate-pr.yml` header; `state.py:is_committed_on_main`.

### S1.6 — Empty `templates/` and `campaigns/spring-launch-2026/` directories
- **What.** `templates/.gitkeep` (0 bytes) and `campaigns/spring-launch-2026/.gitkeep` (0 bytes) exist with no README mention, no doc reference, no code reference, no Phase-2 label. No post at snapshot uses the `spring-launch-2026` slug; the 3 VP posts use `q2-2026-*`.
- **Why we know.** Phase 1.5 CP-10. Phase 1 Pass 04 unknown #1 + #2. Phase 2 Phase-2-deferred section explicitly leaves this unresolved (3 readings: forward-pointer, vestigial, oversight).
- **Severity.** Low.
- **Trace.** `Phase1_Common.md` CP-10; `Phase2_Intent_Reviewed.md` "What Phase 2 deliberately leaves unresolved" #5; `templates/.gitkeep`; `campaigns/spring-launch-2026/.gitkeep`.
- **Notes.** Phase 3 §4.11 says forward-pointers SHOULD be labelled in-place; these are not.

### S1.7 — Published-status sync absent (lifecycle never closes)
- **What.** Publisher writes `ghl-pending` on success but never `published`. No code path detects GHL fire-time. The lifecycle stops at `ghl-pending` for all posts after Gate 2; there is no transition to `published`.
- **Why we know.** Phase 1 Pass 01 + Pass 05 (no test for `ghl-pending → published`). Phase 2 E.5 + WORKFLOW §10.3 explicitly note this as not-implemented. Phase 3 §3.2 Boundaries notes it as "currently absent (deferred work)."
- **Severity.** Low (Phase 2 deferred and explicitly intent-flagged; not a Phase 4 surprise — but recorded for completeness).
- **Trace.** `Phase1_Compacted.md` Pass 01 status writeback evidence, Pass 05 line 560; `Phase2_Intent_Reviewed.md` E.5; `Phase3_Spec_Reviewed.md` §3.2 Boundaries.

### S1.8 — Telegram-on-success notification (Gate-bridge) not implemented
- **What.** README + WORKFLOW §10.2 describe a Gate-bridging Telegram notification ("X posts pending approval in GHL") on publish-time success. Code only fires Telegram on failure (`retry.py:_handle_final_failure`). The promised success-path notification does not exist.
- **Why we know.** Phase 1.5 CP-5 lists three semantically different Telegram framings across docs vs one in code (failure-only). Phase 2 E.1 / E.5 / E.6 confirm.
- **Severity.** Low-Medium (operator UX; not a publish-correctness gap).
- **Trace.** `Phase1_Common.md` CP-5; `Phase2_Intent_Reviewed.md` Group E; `retry.py:235-276`, `retry.py:147`; README lines 11-26; WORKFLOW §10.2.

### S1.9 — No "abort Gate 2" path / no `cancelled` status
- **What.** If Dave decides not to publish a post in GHL and deletes the GHL draft, the post-document on main remains at `ghl-pending` indefinitely. No `cancelled` status in the schema enum, no detection of GHL-side delete, no writeback path.
- **Why we know.** Phase 2 Sp.A.5 / A.5 Missing Intent. Phase 3 §3.2 Boundaries acknowledges lifecycle closure absent.
- **Severity.** Low (a stale post-document is a hygiene issue, not a publish bug).
- **Trace.** `Phase2_Intent_Reviewed.md` Group A.5; schema enum (no `cancelled`).

### S1.10 — No automated AC-coverage check
- **What.** `AC_VERIFICATION_SUMMARY.md` is hand-curated. No CI step verifies that every AC<n> cite in code maps back to a declared AC, or that every declared AC has a test. Coverage drift is detectable only by manual audit.
- **Why we know.** Phase 2 B.6. Phase 1 Pass 05 confirms uneven test coverage of ACs (4 covered of 17 cited tokens — 23.5%).
- **Severity.** Medium.
- **Trace.** `Phase2_Intent_Reviewed.md` B.6; `Phase1_Compacted.md` Pass 05 line 598. See also S2.7 (the same data).

---

## S2 — Undefined Behaviour

### S2.1 — Cron-mode publisher gates on `status == "scheduled"` but no code writes that transition
- **What.** `publisher.run_publisher` (cron mode) processes only `status == "scheduled"`. No code in this repo writes `ready → scheduled`. The cron-mode path is therefore unreachable from any post originating in this repo.
- **Why we know.** Phase 1 Pass 01 explicitly: "Cron mode processes only `status == "scheduled"`; nothing in cron-mode code writes `ready → scheduled`." Phase 2 "What Phase 2 deliberately leaves unresolved" #4: cron-mode aliveness undetermined.
- **Severity.** Medium (dead code on a Tier-1 path is undefined behaviour even if currently no-op).
- **Trace.** `Phase1_Common.md` CP-3; `Phase1_Compacted.md` Pass 01 cron-mode evidence; `publisher/publisher.py:run_publisher`.

### S2.2 — Deprecated adapters' `publish` methods unreachable from `--mode ghl` but defined
- **What.** 5 deprecated adapters (facebook, instagram, linkedin, gbp, x_twitter) define `publish` methods. `run_ghl_publisher` does not invoke them. `run_publisher` (cron mode) would, but cron mode is itself unreachable (S2.1). The `publish` methods on these 5 are dead code.
- **Why we know.** Phase 1.5 CP-7. Phase 1 Pass 02 confirms registry instantiation by `run_publisher` only, not `run_ghl_publisher`.
- **Severity.** Low-Medium.
- **Trace.** `Phase1_Common.md` CP-7; `publisher/adapters/__init__.py:20-26`; `publisher/publisher.py:run_ghl_publisher` (no per-platform adapter dispatch).

### S2.3 — `auth-check` invokes deprecated adapters' `auth_check` — value uncertain
- **What.** The weekly `auth-check.yml` workflow probes per-platform credentials via the 5 deprecated adapters. README line 153 claims "GHL manages platform OAuth — no token rotation needed on our side." If GHL owns the token health, the per-platform probe's value is unclear; if not, the README is wrong.
- **Why we know.** Phase 1.5 CP-7 drift dimension. Phase 2 C.1 names two competing readings (intentional defense-in-depth vs leftover scaffolding) and lands "intentional preservation" at Medium confidence — the question is genuinely undetermined.
- **Severity.** Low-Medium.
- **Trace.** `Phase1_Common.md` CP-7; `Phase2_Intent_Reviewed.md` Group C.1; `auth-check.yml`; README line 153.

### S2.4 — `MAX_RETRIES = 4` vs docstring "3 attempts total"
- **What.** `retry.py` declares `BACKOFF_DELAYS = [10, 30, 90]` and `MAX_RETRIES = len(BACKOFF_DELAYS) + 1 = 4`. The module docstring and inline comment line 25 say "3 total attempts." Behaviour is "1 initial + 3 backoff retries." An operator reading `MAX_RETRIES = 4` and the docstring "3 attempts" gets contradictory mental models.
- **Why we know.** Phase 1.5 CP-9. Phase 1 Pass 01 unknown #2. Phase 2 Sp.F frames the convention-mismatch as the intent question.
- **Severity.** Low-Medium.
- **Trace.** `Phase1_Common.md` CP-9; `Phase2_Intent_Reviewed.md` Sp.F; `retry.py` constants block.

### S2.5 — `RateLimitState.save` writes to `state_dir/{platform}.json`, not `.state/rate_limits/{platform}.json`
- **What.** Both publisher modes compute `state_dir = brand_dir / ".state"` and write rate-limit JSON at `state_dir/{platform}.json`. The `.gitkeep` file lives at `brands/<brand>/.state/rate_limits/.gitkeep`, implying a deeper layout. The placeholder directory is never written to. State is written one level shallower than the placeholder anticipates.
- **Why we know.** Phase 1 Pass 01 cross-cutting note #4 (line 27 of Compacted), Pass 04 #4 (line 39).
- **Severity.** Medium-High (silent-data-loss risk if any reader expects the deeper layout — see S4.4).
- **Trace.** `Phase1_Compacted.md` Pass 01 lines 27, 39; `Phase2_Intent_Reviewed.md` Sp.G; `publisher/publisher.py:178, 326`; `publisher/models.py:RateLimitState.save`.

### S2.6 — `validate-post.py:251` references non-existent script in error message
- **What.** `validate-post.py:251` emits an error string suggesting the operator run `ghl_social_list_accounts.py`. That script was consolidated into `scripts/ghl_social.py accounts` and no longer exists on disk.
- **Why we know.** Phase 1.5 CP-2. Phase 1 Pass 03 cite directly.
- **Severity.** Low.
- **Trace.** `Phase1_Common.md` CP-2; `validate-post.py:251`.

### S2.7 — Test AC coverage is 23.5% — half the AC surface unverified
- **What.** Phase 1 Pass 05 measures: 4 ACs covered (AC2, AC3, AC6, AC7) of 10 in-scope-for-pytest = 40% direct, 60% with partials. Of all 17 AC tokens cited across code: **23.5% direct.** Behaviour cited as "satisfying AC<n>" is mostly unverified by automated tests. This is undefined behaviour in the sense that the spec-claim and the test-claim do not match.
- **Why we know.** Phase 1 Pass 05 line 598; line 652 lists uncovered ACs (AC4, AC8, AC11–16, AC-OQ4, AC-OQ6).
- **Severity.** Medium.
- **Trace.** `Phase1_Compacted.md` Pass 05 lines 598, 652.

### S2.8 — Pre-existing Pydantic v2 `RateLimitState` bug bypassed in tests
- **What.** `TestPublish` docstring: "patch check_rate_limit/increment_rate_limit to bypass RateLimitState (pre-existing Pydantic v2 issue in models.py)." A bug exists in `models.py:RateLimitState` that the tests intentionally route around. Bug location, severity, and ticket are undocumented.
- **Why we know.** Phase 1 Pass 05 line 447, line 654.
- **Severity.** Medium (any production exercise of `RateLimitState` would hit the bug; tests don't catch it).
- **Trace.** `Phase1_Compacted.md` Pass 05 lines 447, 654; `tests/test_ghl_adapter.py::TestPublish` docstring; `publisher/models.py:RateLimitState`.

---

## S3 — Inconsistencies

### S3.1 — AC namespace divergence (canonical inconsistency cluster)
- **What.** Six AC numbers (AC1, AC2, AC5, AC6, AC7, AC8) carry different meanings across `AC_VERIFICATION_SUMMARY.md` vs code-comment / workflow YAML cites. AC8 specifically means "raw-token detection" in `validate-brand.py` and "required fields, status, author/account resolution" in `validate-post.py` — same script-author intent, different rules.
- **Why we know.** Phase 1.5 CP-1. Phase 1 Pass 03 + Pass 06 catalogue. Phase 2 Group B / Sp.A.
- **Severity.** Medium-High. (Filed once per prompt instruction; this is the same finding as S1.1 viewed as inconsistency.)
- **Trace.** `Phase1_Common.md` CP-1; same cite sites as S1.1.

### S3.2 — 24 stale script-path citations across 4 docs
- **What.** Six script/test paths cited in repo docs do not exist on disk: `scripts/ghl_social_list_accounts.py`, `scripts/ghl_social_create_post.py`, `scripts/ghl_social_list_posts.py`, `scripts/ghl_social_delete_post.py`, `scripts/publish_posts.py`, `tests/test_publish_posts.py`. Approximately 24 individual citation occurrences across `AC_VERIFICATION_SUMMARY.md` (~15), `DEVELOPER_GUIDE.md` (5+), `GHL_SOCIAL_PLANNER_ARCHITECTURE.md` (line 99–100), `OPERATIONAL_RUNBOOK.md` (lines 113, 187, 198, 210, 279, 301), plus `brands/secondring/brand.yaml` lines 24–25 and a runtime error string at `validate-post.py:251`.
- **Why we know.** Phase 1.5 CP-2.
- **Severity.** Medium.
- **Trace.** `Phase1_Common.md` CP-2.
- **Notes.** README is correct (line 59 references `ghl_social.py` properly). Drift is doc-author-cluster–specific (the Bob/Forge batch).

### S3.3 — Status terminology drift: `scheduled` (schema) vs `ghl-pending` (workflow doc + publisher writeback)
- **What.** Schema enum has `scheduled` but no `ghl-pending`. Publisher writes `ghl-pending` on success. WORKFLOW.md uses `ghl-pending` to describe post-publisher state. Three sources, two enum shapes.
- **Why we know.** Phase 1.5 CP-3.
- **Severity.** Medium. (Cross-ref to S1.2 / S4.2 — the High-severity bug-in-waiting and invariant violation are filed separately.)
- **Trace.** `Phase1_Common.md` CP-3; `schemas/post.schema.yaml:36`; SOCIAL_CALENDAR_WORKFLOW.md.

### S3.4 — SR post `author: davelawler-vp` violates schema enum
- **What.** Schema declares `author` enum `[dave, velocitypoint]`. `brands/secondring/calendar/2026/04/.../2026-04-01-never-miss-a-call.md` line 12 sets `author: davelawler-vp`. That post has `ghl_mode: false`. Either `validate-post.py` softens the enum check when `ghl_mode: false` (Pass 03 unresolved) or the post would fail validation if validated today.
- **Why we know.** Phase 1 Pass 04 unknown #4 (line 413).
- **Severity.** Low (ghl_mode-false post is on the legacy direct-adapter path which is itself unreachable per S2.2 + S2.1).
- **Trace.** `Phase1_Compacted.md` Pass 04 #4 line 413; `schemas/post.schema.yaml:59`; SR post file.

### S3.5 — Publisher state-dir vs `.state/rate_limits/` placeholder mismatch
- **What.** Code writes `state_dir/{platform}.json` (under `brand_dir/.state/`). Placeholder gitkeep is at `brand_dir/.state/rate_limits/.gitkeep`. Two different layouts; only the shallower (code) one is exercised.
- **Why we know.** Phase 1 Pass 01 cross-cutting #4. (Same evidence as S2.5 — filed here as inconsistency between two placeholder/code layouts.)
- **Severity.** Medium.
- **Trace.** `Phase1_Compacted.md` line 27; `Phase2_Intent_Reviewed.md` Sp.G.

### S3.6 — Concurrency group: `ghl-publisher` (workflow) vs `publisher` (Phase 0 review claim)
- **What.** `publish.yml:33` uses `concurrency.group: ghl-publisher`. Phase 0 review documented the group as `publisher`. Phase 0 was wrong; the actual group is `ghl-publisher`. This is a doc-vs-actual drift recorded in the Phase 0 review pass.
- **Why we know.** Phase 1.5 CP-9. Phase 1 Pass 06 line 198 ("Phase 0 review claimed group `publisher` — actual `ghl-publisher`").
- **Severity.** Low.
- **Trace.** `Phase1_Common.md` CP-9; `publish.yml:33`.

### S3.7 — README claims AC1–AC14 but canonical AC summary covers AC1–AC10
- **What.** README quotes (per Phase 0) cover AC1–AC14. `AC_VERIFICATION_SUMMARY.md` enumerates AC1–AC10 only. AC11–AC14 are part of the broader namespace that lives nowhere in `docs/`.
- **Why we know.** Phase 1.5 CP-1 reconciliation observations. Phase 1 Pass 06 reconciliation table.
- **Severity.** Medium (sub-finding of S1.1, but separately listed because it's a README-vs-summary doc-specific drift).
- **Trace.** `Phase1_Common.md` CP-1.

### S3.8 — 3 `<TBD>` issue-number placeholders in `SOCIAL_CALENDAR_WORKFLOW.md` §10
- **What.** WORKFLOW.md §10 lines 256, 262, 268 reference `social-calendar#<TBD>` for three Open Technical Work items (10.1 GHL Draft Mode, 10.2 Telegram, 10.3 Status Polling). Never filled. Daedalus issue numbers were planned but never recorded.
- **Why we know.** Phase 1.5 CP-10. Phase 1 Pass 06 line 920, 923.
- **Severity.** Low.
- **Trace.** `Phase1_Common.md` CP-10; SOCIAL_CALENDAR_WORKFLOW.md §10.

### S3.9 — velocitypoint `brand.yaml` has no `ghl:` block but VP posts use `ghl_mode: true`
- **What.** Same as S1.3 viewed as inconsistency: brand-config and post-frontmatter disagree about whether VP is GHL-mode. (Filed once per prompt; cross-link only.)
- **Why we know.** Phase 1 Pass 04 unknown #6 (line 417).
- **Severity.** High (cross-ref S1.3).
- **Trace.** S1.3.

### S3.10 — Adapter deprecation markers inconsistent
- **What.** Of 5 deprecated adapters: 3 (facebook/linkedin/gbp) carry "Phase 1 skeleton" markers; 2 (instagram/x_twitter) carry no in-file marker; README lists all 5 as "deprecated"; no file uses the literal "deprecated."
- **Why we know.** Phase 1.5 CP-7 drift dimension. Phase 1 Pass 02.
- **Severity.** Low.
- **Trace.** `Phase1_Common.md` CP-7.

### S3.11 — `ghl-pending` in publisher state machine but absent from schema enum
- **What.** Same root as S1.2 / S3.3 viewed at the artifact level: schema's status enum literally does not include `ghl-pending`; publisher / models.py / tests treat it as canonical.
- **Why we know.** Phase 1.5 CP-3. (Filed once per prompt as inconsistency surface; the latent-bug version is S4.2.)
- **Severity.** High (cross-ref S1.2, S4.2).
- **Trace.** `Phase1_Common.md` CP-3.

### S3.12 — Schema-vs-validator field-coverage mismatch
- **What.** Schema declares 15 fields + nested `creative.*`. `validate-post.py` validates ~6 fields (id, publish_at, platforms, status, author, plus per-section copy + character limits). Fields validated only-in-schema (no script enforcement): `account_id`, `ghl_mode`, `campaign`, `tags`, `published_at`, `ghl_post_id`, `post_ids`, `error`, `creative.*`. `additionalProperties` policy is undeclared in schema and unenforced in validator. Schema is documentation; enforcement is hand-coded; the two are independently maintained.
- **Why we know.** Phase 1.5 CP-8.
- **Severity.** Medium.
- **Trace.** `Phase1_Common.md` CP-8; `Phase2_Intent_Reviewed.md` Group F / CP-8.

### S3.13 — Test AC linkage inconsistent (publisher tests cite ACs; adapter tests don't)
- **What.** `test_publisher_ghl_mode.py` cites AC6, AC7 in test names/docstrings. `test_ghl_adapter.py` cites only "issue #2" — no per-test AC tags. Two adjacent test files use two different traceability conventions.
- **Why we know.** Phase 1.5 CP-1 Pass 05 evidence. Phase 1 Pass 05.
- **Severity.** Low.
- **Trace.** `Phase1_Common.md` CP-1 Pass 05 row.

### S3.14 — Stats-dict shape: cron has `deferred`, GHL doesn't
- **What.** Cron `run_publisher` returns 5-key dict including `deferred`. `run_ghl_publisher` returns 4-key dict (no `deferred`). `deferred` is only meaningful when rate-limit gate hits, which only happens in cron-mode-only path. Inconsistent surface for the two callers.
- **Why we know.** Phase 1.5 CP-6. Phase 1 Pass 01 + Pass 05.
- **Severity.** Low.
- **Trace.** `Phase1_Common.md` CP-6.

### S3.15 — Char-limit triplication (schema + validator + 3 deprecated adapters)
- **What.** Per-platform character limits declared in schema's `platform_limits`, again in `validate-post.py`'s per-platform char-limit dict, again in 3 deprecated adapters (`LINKEDIN_CHAR_LIMIT`, `GBP_CHAR_LIMIT`, `X_CHAR_LIMIT`). Currently consistent. Three sources, no canonical enforcement of consistency.
- **Why we know.** Phase 1.5 CP-9. Phase 1 Pass 02 + Pass 03 + Pass 04.
- **Severity.** Medium (silent drift on next limit change).
- **Trace.** `Phase1_Common.md` CP-9.

---

## S4 — Risks

### S4.1 — Security: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` env-var only, not KV-resolved
- **What.** All other credentials follow `kv-<brand>-<platform>-<suffix>` resolution through Azure Key Vault. Telegram credentials are read directly from env vars in the workflow runtime; provisioning path (raw secret vs KV-bridge) is not visible in this repo. Telegram token is the operator-notification bus credential — leaked, an attacker can spoof Dave's failure-alert channel.
- **Why we know.** Phase 1.5 CP-5. Phase 1 Pass 01 line 113. Phase 1 Pass 06 line 693 (secret inventory). Phase 1 Pass 01 unknown #9 (line 44 of Compacted).
- **Severity.** Medium (Telegram is a low-blast-radius channel; not on the publish path).
- **Trace.** `Phase1_Common.md` CP-5; `retry.py:235-276`; `publish.yml` env block.

### S4.2 — Reliability: schema rejects `ghl-pending` at PR time but publisher writes it at runtime
- **What.** Validation surface (PR-time `validate-post.py`) and writeback surface (post-publish `_write_ghl_post_result`) do not temporally overlap. A `ghl-pending` post that is ever re-validated (e.g., a doc edit on an already-published post) would fail the gate. The bug is latent because no current workflow re-runs validation against a post in `ghl-pending`. **This is a bug-in-waiting if validation scope is ever extended.**
- **Why we know.** Phase 1.5 CP-3. Phase 2 Sp.B (Medium confidence on latency, High confidence on rejection-if-tested). Phase 3 §4.4 + I-12 declare canonicalization required.
- **Severity.** High (the latency hides the bug; first time a `ghl-pending` post is touched in a PR, validation fails).
- **Trace.** `Phase2_Intent_Reviewed.md` Sp.B; `Phase1_Common.md` CP-3.

### S4.3 — Reliability: `MAX_RETRIES` off-by-one (operator-mental-model)
- **What.** Same as S2.4 viewed as risk: an operator reading docs ("3 attempts") and reading runtime logs ("attempt 4 failed") doesn't know whether the publisher quit early, ran past spec, or matches the spec. Mis-diagnosis risk during incident response.
- **Why we know.** Phase 1.5 CP-9. Phase 2 Sp.F.
- **Severity.** Low-Medium.
- **Trace.** Same as S2.4.

### S4.4 — Reliability: `RateLimitState` writes to wrong path → silent persistence loss
- **What.** Same as S2.5 viewed as risk. Code writes `state_dir/{platform}.json`; gitkeep anticipates `state_dir/rate_limits/{platform}.json`. If any external tooling, backup script, or new code reads from the deeper path, it misses the actual state. State *does* persist between runs (because `RateLimitState.save` and `.load` agree on the shallower path), but the placeholder discrepancy is a foot-gun for any future code that consults the gitkeep'd location.
- **Why we know.** Phase 1.5 implicit (Pass 01 #4 + Pass 04 #4). Phase 2 Sp.G.
- **Severity.** Medium-High (silent data loss is the prompt-flagged severity for this finding).
- **Trace.** Same as S2.5.

### S4.5 — Reliability: half the lifecycle untested (`ghl-pending → published` transition)
- **What.** Tests cover `ready → ghl-pending` (success) and `ready → failed` (failure). No test covers `ghl-pending → published` because that transition isn't implemented (S1.7). When polling IS implemented, there is no harness ready.
- **Why we know.** Phase 1 Pass 05 line 560.
- **Severity.** Medium.
- **Trace.** `Phase1_Compacted.md` Pass 05 line 560; `tests/test_publisher_ghl_mode.py`.

### S4.6 — Reliability: idempotency on re-publish not asserted by any test
- **What.** Phase 3 I-6 requires replay protection: re-running publish over a post in `ghl-pending` MUST NOT create a duplicate draft. No test asserts this directly. Mechanism (the publisher refuses non-`ready` posts) is correct on inspection but unverified.
- **Why we know.** Phase 3 I-6 + §4.2. Phase 1 Pass 05 (no `test_replay` / `test_idempotent` test in scope).
- **Severity.** Medium.
- **Trace.** `Phase3_Spec_Reviewed.md` I-6, §4.2; `Phase1_Compacted.md` Pass 05.

### S4.7 — Operational: failure mode ambiguous when Telegram OR GitHub-issue creation fails
- **What.** `retry.py:_handle_final_failure` fires both Telegram and GitHub-issue. Both are best-effort; failures are swallowed (logged-only). If Telegram is down, Dave never sees the alert; if GitHub-issue creation fails, the work item never appears. Both failing simultaneously means the publish-failure goes silent in both surfaces.
- **Why we know.** Phase 1.5 CP-5 + CP-6. Phase 3 I-9 + I-14 (paired escalation + best-effort side-effect).
- **Severity.** Medium.
- **Trace.** `Phase1_Common.md` CP-5, CP-6; `Phase3_Spec_Reviewed.md` I-9, I-14; `retry.py:_handle_final_failure`.
- **Notes.** Phase 3 declares the pairing as invariant; the spec doesn't require detection of *paired-side-effect-failure* — that's an observability gap.

### S4.8 — Operational: 5 deprecated adapters runtime-live cost weekly OIDC + KV resolution time
- **What.** Every Monday 09:00 UTC, `auth-check.yml` instantiates 5 deprecated adapters. Each calls `_get_credential` → KV reference resolution. If GHL truly handles all OAuth (per README line 153), this work is wasted.
- **Why we know.** Phase 1.5 CP-7. Phase 1 Pass 06 lines 50–53 (per-platform env injection).
- **Severity.** Low-Medium.
- **Trace.** `Phase1_Common.md` CP-7.

### S4.9 — Compliance: per-platform char limits enforced at PR time only — schema-drift exposure
- **What.** Per-platform char limits enforced in `validate-post.py` at PR time. Schema declares them. No publish-time recheck. Three declaration sites (S3.15) currently agree; if any drifts, posts may pass PR-time and exceed at publish-time → API rejection.
- **Why we know.** Phase 3 §4.7. Phase 1.5 CP-9.
- **Severity.** Low-Medium.
- **Trace.** `Phase3_Spec_Reviewed.md` §4.7; `Phase1_Common.md` CP-9.

### S4.10 — Pre-launch: secondring 6 unfilled `<account_id>` + velocitypoint missing `ghl:` block — first publish will fail
- **What.** Composite of S1.3 + S1.4 viewed as the launch hazard. Campaign 1 has not yet run. The first VP publish hits silent-no-op (S1.3); the first SR publish on any account with `<account_id>` placeholder hits API rejection or mis-routing (S1.4). Either path: Campaign 1 fails on attempt 1.
- **Why we know.** Same evidence as S1.3 + S1.4.
- **Severity.** High.
- **Trace.** S1.3 + S1.4.

### S4.11 — Reliability: `RateLimitState` Pydantic v2 bug bypassed in tests, would activate in production
- **What.** Same as S2.8 viewed as risk: tests patch around a known `RateLimitState` Pydantic v2 bug. Bug location undocumented. Any production exercise of un-patched `RateLimitState` may behave unexpectedly. Cron mode (S2.1) would hit it but is itself unreachable; rate-limit accounting in `--mode ghl` may or may not exercise the bug — undetermined.
- **Why we know.** Phase 1 Pass 05 lines 447, 654.
- **Severity.** Medium.
- **Trace.** Same as S2.8.

### S4.12 — Operational: `agent:bob` consumer automation external to repo — failure-handling lifecycle outside repo control
- **What.** Failure paths create GitHub issues with `agent:bob` label expecting external automation to triage. If that automation is offline or misconfigured, work-items pile up unactioned. Repo has no fallback.
- **Why we know.** Phase 2 D.3 + Group H. Phase 3 §7 (out of scope).
- **Severity.** Low (matches Phase 3 OOS scoping; recorded for completeness).
- **Trace.** `Phase2_Intent_Reviewed.md` D.3; `Phase3_Spec_Reviewed.md` §7.

---

## S5 — Technical Debt

### S5.1 — AC namespace divergence cluster (CP-1)
- **What.** The single most amplifying debt finding. Two parallel AC namespaces (Vulcan + Daedalus) collide on 6 AC numbers; broader namespace lives only in code/comments; no in-repo enumeration of the broader namespace exists. Every AC-anchored claim depends on which doc you read.
- **Why we know.** Phase 1.5 CP-1; Phase 2 Group B + Sp.A.
- **Severity.** Medium-High (cluster).
- **Trace.** Same as S1.1.

### S5.2 — Stale-doc cluster (CP-2)
- **What.** 24 stale citations across 4 docs (`AC_VERIFICATION_SUMMARY.md`, `DEVELOPER_GUIDE.md`, `GHL_SOCIAL_PLANNER_ARCHITECTURE.md`, `OPERATIONAL_RUNBOOK.md`) plus brand.yaml comment + runtime error string. All from a single doc-author-cluster (Bob/Forge phase) that pre-dates the script consolidation refactor.
- **Why we know.** Phase 1.5 CP-2.
- **Severity.** Medium.
- **Trace.** Same as S3.2.

### S5.3 — Status-lifecycle drift cluster (CP-3)
- **What.** 4 surfaces (schema, models.py, validate-post.py, docs) disagree on the status enum shape. `ghl-pending` is canonical to publisher + tests but absent from schema + validator.
- **Why we know.** Phase 1.5 CP-3.
- **Severity.** High (cluster — same root as S1.2 / S4.2).
- **Trace.** Same as S1.2.

### S5.4 — Deprecated-but-runtime-live adapters (CP-7)
- **What.** 5 adapters that the README calls "deprecated" remain in `ADAPTER_REGISTRY`, are imported by `__init__.py`, and are instantiated weekly by `auth-check.yml`. Their `publish` methods are dead code. Their `auth_check` methods are live but their value is contested (S2.3).
- **Why we know.** Phase 1.5 CP-7.
- **Severity.** Low-Medium (recorded as cluster debt).
- **Trace.** Same as S2.2.

### S5.5 — Schema-vs-validator coverage cluster (CP-8)
- **What.** Schema declares 15 fields; validator validates ~6. Schema is documentation only; no automated reader consumes it. `additionalProperties` policy gap means new fields can be added without anyone failing.
- **Why we know.** Phase 1.5 CP-8.
- **Severity.** Medium.
- **Trace.** Same as S3.12.

### S5.6 — Hardcoded constants cluster (CP-9)
- **What.** Char limits triplicated; `MAX_RETRIES` count-convention split; `ghl-publisher` group name vs Phase 0 review claim; `cUgvqrKmBM4sAZvMH1JS` location-id literal in brand.yaml + cross-spec marker.
- **Why we know.** Phase 1.5 CP-9.
- **Severity.** Medium.
- **Trace.** `Phase1_Common.md` CP-9.

### S5.7 — Notification layering cluster (CP-5)
- **What.** Three different framings of Telegram intent (publish-success, gate-bridge, failure-alerting) across README / WORKFLOW / RUNBOOK. Code does failure-only. Auth-check vs publish asymmetry (GitHub-issue alone vs paired Telegram+issue) is structural but undocumented.
- **Why we know.** Phase 1.5 CP-5; Phase 2 Group E.
- **Severity.** Medium.
- **Trace.** Same as S1.8.

### S5.8 — No `conftest.py` — test helpers duplicated across files
- **What.** `tests/__init__.py` is a 1-line marker. No `conftest.py` exists. `make_post`, `make_brand`, `_make_brand_and_post` etc. are duplicated across `test_ghl_adapter.py` and `test_publisher_ghl_mode.py`. Common fixture extraction has not happened.
- **Why we know.** Phase 1 Pass 05 lines 433, 630.
- **Severity.** Low.
- **Trace.** `Phase1_Compacted.md` Pass 05 lines 433, 630.

### S5.9 — Pre-existing Pydantic v2 `RateLimitState` bug acknowledged in test docstring
- **What.** Same as S2.8 / S4.11 viewed as debt: a known bug exists in `models.py:RateLimitState`; tests patch around it; ticket / location undocumented. The bug is a debt entry that has already cost test ergonomics.
- **Why we know.** Phase 1 Pass 05 lines 447, 654.
- **Severity.** Medium.
- **Trace.** Same as S2.8.

### S5.10 — `python-frontmatter` dependency usage scope unverified
- **What.** `publisher/requirements.txt` lists `python-frontmatter>=1.1.0`. Phase 0 noted only PyYAML, Requests, Pydantic. Whether `python-frontmatter` is used in tested paths or only legacy paths is not visible from the snapshot.
- **Why we know.** Phase 1 Pass 06 line 1072 + line 1067.
- **Severity.** Low.
- **Trace.** `Phase1_Compacted.md` Pass 06 lines 1067, 1072.

### S5.11 — Two-gate invariant encoded across 4 layers (no single source of truth)
- **What.** Phase 3 §4.1 declares the two-gate invariant is encoded REDUNDANTLY across (1) schema status enum, (2) pre-merge schema validation, (3) publisher state-machine `status==ready` gate, (4) adapter wire-payload `status: draft` literal. The redundancy IS the design (defense-in-depth). But: no single artifact declares "this is the two-gate invariant"; no test asserts the end-to-end invariant. A new contributor cannot find one place to read or change the invariant.
- **Why we know.** Phase 1.5 CP-4. Phase 3 §4.1 explicitly. Phase 2 CP-4 inference.
- **Severity.** Medium (debt, not bug — the spec marks the redundancy as intentional).
- **Trace.** `Phase1_Common.md` CP-4; `Phase3_Spec_Reviewed.md` §4.1.

---

## Severity Rollup

| Severity | Count |
|---|---|
| **High** | 7 |
| **Medium-High** | 3 |
| **Medium** | 18 |
| **Low-Medium** | 7 |
| **Low** | 9 |
| **Total** | **44** |

By section:

| Section | Count |
|---|---|
| S1 — Missing Features | 10 |
| S2 — Undefined Behaviour | 8 |
| S3 — Inconsistencies | 15 |
| S4 — Risks | 12 |
| S5 — Technical Debt | 11 |

(S1+S2+S3+S4+S5 = 56 finding-listings; 44 unique findings — some are filed once and cross-referenced from sibling sections per prompt instruction.)

---

## Top 5 (most material to "first publish doesn't fail")

1. **S1.3 / S4.10 — velocitypoint `brand.yaml` missing entire `ghl:` block.** First VP publish hits silent-no-op via `test_no_ghl_config_returns_early`. **High.** Pre-launch blocker.
2. **S1.4 / S4.10 — secondring 6 unfilled `<account_id>` placeholders.** First SR publish on any of those 6 accounts API-rejects or mis-routes. **High.** Pre-launch blocker.
3. **S1.2 / S4.2 / S3.11 — Schema-vs-publisher status mismatch (`ghl-pending`).** Bug-in-waiting: validation surface and writeback surface don't temporally overlap today, but any future doc-edit on a `ghl-pending` post triggers PR-time validation failure. **High.**
4. **S2.5 / S4.4 — `RateLimitState` writes to wrong path (silent data loss surface).** Code-vs-placeholder mismatch on rate-limit JSON file location. **Medium-High.**
5. **S1.1 / S3.1 / S5.1 — AC namespace divergence (CP-1).** The cross-cutting amplifier. Every "this is covered by AC<n>" claim has uncertain meaning. **Medium-High.**
