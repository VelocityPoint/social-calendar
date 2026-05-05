# Phase 1 — Pass 06 — Docs + Workflows + Build/CI

**Snapshot:** `67d061c`
**Files in scope:** 7 docs (README + 6 in `docs/`), 3 workflows, `dependabot.yml`, `publisher/requirements.txt`, `.gitignore`

---

### Docs

#### `README.md` (181 lines)

**Section structure (top-level `##`):**
- `social-calendar` (title block)
- `## How It Works — Two Gates`
- `## Repo Structure`
- `## Post Document Format` (with `### Post Status Lifecycle`)
- `## Validate a Post Locally`
- `## Run Publisher Locally`
- `## Platform Notes` (with `### GHL Social Planner (primary)`, `### Instagram`, `### Google Business Profile`)
- `## Adding a New Brand`
- `## Related`

**Substantive content this doc owns:**
- Two-gate workflow summary (line 11–26): Gate 1 = GitHub PR copy approval; Gate 2 = GHL Social Planner visual approval. After merge, "Dave receives a Telegram notification: 'X posts pending approval in GHL'" (line 22).
- **Post status lifecycle table** (lines 102–113): `draft → ready → ghl-pending → scheduled → published` (plus `failed`). Owns the canonical 6-state enum.
- **Required GitHub Actions secrets table** (lines 138–146): `GHL_API_KEY`, `GHL_LOCATION_ID`, `GITHUB_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Owns the secret inventory.
- Repo structure tree (lines 32–75).
- Adding-a-new-brand procedure (lines 163–169).

**AC references:** None. README does not cite ACs.

**Cross-references:**
- `docs/SOCIAL_CALENDAR_WORKFLOW.md` — line 26, 175.
- `docs/GHL_SOCIAL_PLANNER_ARCHITECTURE.md` — line 176.
- `Core_Business#222` — line 177.
- Issues `#13`, `#14`, `#15` — line 178–180 ("GHL draft gate", "Telegram notification", "Published status sync").

**Stale-doc indicators:**
- Line 59 lists `scripts/ghl_social.py` (consolidated CLI) — **matches snapshot**. README is current here, unlike AC_VERIFICATION_SUMMARY.
- Lists 5 deprecated adapters (lines 50–54) consistent with code.
- Line 153: "GHL manages platform OAuth — no token rotation needed on our side" — but `auth-check.yml` still iterates per-platform IDs (FACEBOOK_PAGE_ID etc.). **Soft drift** — Pass 02 territory.

---

#### `docs/AC_VERIFICATION_SUMMARY.md` (328 lines)

**Section structure:**
- Header block (issue #2, "Bob — Forge Documentation Phase", date 2026-03-27)
- `## AC Status Summary` (table)
- `## AC-by-AC Detail` with `### AC1` … `### AC10`
- `## Known Limitations and Non-Blocking Items` (W1/W2/W3 + design limitations)
- `## Remaining Work Timeline`
- `## Build Deliverable Inventory`

**Canonical AC list per this doc — AC1 through AC10 only.** Status from line 13–23 table:

| AC | Description | Status |
|----|-------------|--------|
| AC1 | Capability matrix | PASS |
| AC2 | `ghl_social_list_accounts.py` | PASS |
| AC3 | `ghl_social_create_post.py` with dry-run | PASS |
| AC4 | `ghl_social_list_posts.py` | PASS |
| AC5 | `ghl_social_delete_post.py` with dry-run | PASS |
| AC6 | `--location-id`/`--api-key` env-var fallback | PASS |
| AC7 | GHL adapter routes through GHL API | PASS |
| AC8 | Riley post → schema → publishable | PASS (unit) |
| AC9 | End-to-end test (live) | BLOCKED (no accounts connected) |
| AC10 | Tests + production docs | PARTIAL |

**Total AC-summary count: 10.**

**Stale references — scripts cited that don't exist at snapshot:**
1. `scripts/ghl_social_list_accounts.py` (lines 17, 51, 66, 154, 161, 230, 319) — **does not exist**; functionality moved into `scripts/ghl_social.py accounts`.
2. `scripts/ghl_social_create_post.py` (lines 18, 75, 80, 154, 162, 236, 319) — **does not exist**; moved to `scripts/ghl_social.py create`.
3. `scripts/ghl_social_list_posts.py` (lines 19, 107, 112, 154, 163, 242, 319) — **does not exist**; moved to `scripts/ghl_social.py list`.
4. `scripts/ghl_social_delete_post.py` (lines 20, 129, 134, 154, 164, 245, 319) — **does not exist**; moved to `scripts/ghl_social.py delete`.
5. `scripts/publish_posts.py` (line 180) — **does not exist** (also referenced in DEVELOPER_GUIDE).

**5 distinct script paths in AC summary, 0 of them resolve at snapshot.** All 4 CLI tools were consolidated into `scripts/ghl_social.py` (363 LOC) per Phase 0 review note 2.

**AC line cites preserve specifics:**
- AC2: "`--api-key` defaults to `$GHL_API_KEY` env var" (line 57). "Exits with clear error if neither location-id nor env var is provided" (line 58).
- AC3: "Live mode requires interactive confirmation (prevents accidents)" (line 86). "`--image-url` adds `mediaUrls` to payload → `type: image`" (line 86).
- AC4: "Uses `POST /social-media-posting/{locationId}/posts/list` (correct — GET would not support body filters)" (line 117).
- AC5: "Live mode requires typing the post ID to confirm (intentional friction)" (line 138).
- AC7: "Known non-blocking issue (W1): Double `increment_rate_limit()` call in `ghl.py` + `publisher.py` — rate limits counted 2x" (line 188).
- AC9: "[SR] Sales sub-account has 0 social accounts connected (per Dave's answer to Q2 in issue #2: 'build first, test once accounts are connected')" (line 224).
- AC10: "65 unit tests total (47 adapter + 18 publisher GHL mode) — all mocked, no live GHL needed" (line 259). 47 + 18 = 65 — matches Pass 0 LOC observation.

**Cross-references:** `GHL_SOCIAL_PLANNER_ARCHITECTURE.md`, `DEVELOPER_GUIDE.md`, `OPERATIONAL_RUNBOOK.md`, `RILEY_HANDOFF_SPEC.md` (lines 263–267 of AC summary). PRs #3/#4/#5/#6/#8/#9 cited as build deliverables (lines 317–323).

**Stale-doc indicators:** date 2026-03-27 (line 6) — pre-dates the consolidation refactor. The whole doc is a historical "snapshot at PRs #3-#9 merged" record; never updated to reflect the script consolidation.

---

#### `docs/DEVELOPER_GUIDE.md` (560 lines)

**Section structure:**
- `## 1. How the System Works` (with "The Key Insight: Merge = Publish Approval", "Why GHL Instead of Direct Platform APIs?")
- `## 2. Repository Layout`
- `## 3. Step-by-Step Post Creation Workflow` (Steps 1–5)
- `## 4. Local Development Setup`
- `## 5. CLI Tools Reference`
- `## 6. Understanding the Code` (per-file walkthroughs)
- `## 7. Debugging Common Issues` (5 scenarios)
- `## 8. Testing Procedures`
- `## 9. Adding a New Platform`
- `## 10. Adding a New Brand`

**Substantive content this doc owns:**
- Per-file code walkthroughs for `ghl.py`, `retry.py`, `state.py`, `models.py` (lines 276–352).
- Error hierarchy diagram (lines 308–314): `Exception → PublishError → RateLimitError`; `Exception → PermanentError → GHLError`.
- **`RateLimitState.DEFAULTS` ClassVar quirk note** (lines 349–352) — Pydantic-specific guidance not in any other doc.
- 5-row "PR schema check fails" debugging table (lines 419–426).

**AC references:** None — guide doesn't cite AC numbers.

**Cross-references:** issue #2 (line 3); architecture/workflow docs not linked from body.

**Stale-doc indicators:**
- Lines 56–69 list **`scripts/publish_posts.py`** (described as "PR #7, superseded by publisher.py --mode ghl") — file does not exist at snapshot.
- Lines 57–60 list 4 separate `ghl_social_*.py` CLI scripts — none exist at snapshot. Same drift as AC summary.
- Line 65: `tests/test_publish_posts.py` — file does not exist at snapshot. Tree shows only `test_ghl_adapter.py` (532 LOC) + `test_publisher_ghl_mode.py` (410 LOC) per Phase 0.
- Line 69: duplicate entry for `test_publisher_ghl_mode.py` — listed twice within the same tree block (cosmetic but indicates copy-paste error).

---

#### `docs/GHL_SOCIAL_PLANNER_ARCHITECTURE.md` (445 lines) — "Daedalus design"

**Section structure:**
- `## 1. System Overview`
- `## 2. Pipeline Overview`
- `## 3. Component Interactions and Dependencies` (Component Map / Dependency Chain / Auth Surfaces)
- `## 4. Data Flow Diagrams` (Happy / Failure / Validation)
- `## 5. Post Document Schema (v1.1)`
- `## 6. Brand Configuration`
- `## 7. GitHub Actions Workflows`
- `## 8. GHL API Reference` (with Platform Support Matrix + Rate Limits)
- `## 9. Failure Modes and Recovery`
- `## 10. Known Limitations (Phase 1)`
- `## 11. Phase 2 Roadmap`

**Substantive content this doc owns:**
- The single ASCII pipeline diagram (lines 23–81) showing Riley → PR → publish.yml → publisher → GHLAdapter → GHL → platforms.
- **GHL endpoint table** (lines 343–349) — 5 endpoints: create POST, get GET, list POST (`/posts/list`), delete DELETE, accounts GET. Authoritative.
- **Platform support matrix with TikTok row** (lines 357–364) — only place TikTok is in the support matrix.
- Rate limits table (line 366–373): GHL per-account; LinkedIn ~100/day; Instagram ~50/24h; Facebook ~200/hour.
- **Retry policy:** "3 attempts, backoff delays: 10s → 30s → 90s. 429 responses honor `Retry-After` header (capped at 300s)" (line 375).
- 9-row failure scenarios table (lines 383–393).
- Status lifecycle: `draft → ready → scheduled → published` + `failed` (line 266) — **does NOT include `ghl-pending`**, conflicting with README and SOCIAL_CALENDAR_WORKFLOW.

**AC references:** Line 196 mentions "(Optional) Create GitHub issue for persistent failure (AC7)" — only AC ref in body.

**Cross-references:** issue #2 (line 3); `OPERATIONAL_RUNBOOK.md` (line 422).

**Stale-doc indicators:**
- Line 99: `scripts/publish_posts.py` "Called by GitHub Actions" — does not exist at snapshot.
- Line 100: `scripts/ghl_social_*.py` — 4 separate CLIs, none exist.
- Line 266 status diagram **omits `ghl-pending`** — README + WORKFLOW doc include it. Spec drift between docs.
- Line 4 says "v1.0 — as-built post Forge pipeline (PRs #3, #4, #5, #6, #8)" — same vintage as AC summary; pre-consolidation refactor.

---

#### `docs/OPERATIONAL_RUNBOOK.md` (361 lines)

**Section structure:**
- `## 1. System Health Overview`
- `## 2. Monitoring Setup`
- `## 3. Alerting Setup`
- `## 4. Incident Response Procedures` (P0/P1/P2/P3)
- `## 5. Social Account Connection Troubleshooting`
- `## 6. API Key Rotation Procedures`
- `## 7. Going Live Checklist (First-Time Setup)`
- `## 8. Scheduled Maintenance`
- `## 9. Contact and Escalation`

**Substantive content this doc owns:**
- P0/P1/P2/P3 incident-response runbooks (lines 96–203) — only doc with this.
- **API key rotation procedure** (lines 245–288) — required scopes: `social-media-posting.read`, `social-media-posting.write`.
- Going-live checklist (lines 291–322).
- Platform OAuth token-lifetime table (lines 235–241): Facebook 60d auto-refresh, LinkedIn 60d, Twitter "Most fragile".
- Contact/escalation table (lines 350–356): "GHL API changes / breakage | Bob (GHL specialist) via Telegram".

**AC references:** Line 74 "The `retry.py` module has hooks for GitHub issue creation on persistent failures (`AC7`)" — only AC cite.

**Cross-references:** issue #2.

**Stale-doc indicators:**
- Lines 113, 210, 279, 301: invokes `python scripts/ghl_social_list_accounts.py` — script does not exist at snapshot.
- Line 187: `ghl_social_delete_post.py` — does not exist.
- Line 198: same.
- Line 90 calls out a Phase-2 plan: "Telegram notification to Dave on `status: failed` posts (via `retry.py` GitHub issue creation + issue-to-Telegram bridge)" — note this contradicts SOCIAL_CALENDAR_WORKFLOW which describes Telegram as a *publish-success* notification, not a failure bridge.

---

#### `docs/RILEY_HANDOFF_SPEC.md` (490 lines)

**Section structure:**
- `## 1. Riley's Role in the Pipeline`
- `## 2. PR-Driven Workflow`
- `## 3. File Location and Naming`
- `## 4. Required Frontmatter` (incl. "Fields Riley must NEVER set")
- `## 5. Post Body (Copy)`
- `## 6. Schema Validation Rules`
- `## 7. Sample Post Templates by Platform` (LinkedIn / Facebook / Instagram / GBP / X)
- `## 8. Batch Post Generation Guidelines`
- `## 9. Review and Approval Process`
- `## 10. Common Mistakes to Avoid`

**Substantive content this doc owns:**
- **Per-platform character limits table** (lines 217–223): linkedin 3,000; facebook 63,000; instagram 2,200; gbp 1,500; x 280. Authoritative for the schema.
- 5 full sample post templates with tone notes (lines 234–384).
- "Fields Riley must NEVER set" table (lines 130–137): `status: ready`, `ghl_post_id`, `published_at`, `error`, `account_id`.
- Common mistakes table (lines 476–485).

**AC references:** None — Riley spec doesn't cite ACs.

**Cross-references:** issue #2 (line 3).

**Stale-doc indicators:**
- Author values cited as `dave` or `velocitypoint` (lines 124, 213) — consistent with brand.yaml (cross-checked at Phase 0).
- Line 226: notes "this check is a **warning**, not a failure, if `brand.yaml` doesn't yet have real account IDs (during bootstrap)" — Pass 03 should verify against `validate-post.py`.
- Status values used: only `draft` (Riley sets) and `ready` (Dave sets); doesn't go beyond. Consistent with README + WORKFLOW.

---

#### `docs/SOCIAL_CALENDAR_WORKFLOW.md` (274 lines)

**Section structure:**
- `## 1. The Two Gates`
- `## 2. Full Pipeline (All Stages)` (Stages 1–5)
- `## 3. Status Lifecycle (Updated)`
- `## 4. What Each Role Does` (Riley / Bob / Dave)
- `## 5. File Conventions`
- `## 6. PR Format (Standard)`
- `## 7. Review Checklist` (Gate 1 + Gate 2)
- `## 8. Cadence & Volume`
- `## 9. Resale Product Notes`
- `## 10. Open Technical Work` (10.1 GHL Draft Mode, 10.2 Telegram, 10.3 Status Polling)

**Substantive content this doc owns:**
- **Canonical 5-stage pipeline** (lines 30–70). Owns the formalized version.
- **Status lifecycle including `ghl-pending`** (lines 76–93): `draft → ready → ghl-pending → scheduled → published`. The single source-of-truth for the 6-state machine.
- Per-platform target cadence table (lines 218–223).
- **§10 "Open Technical Work" section** (lines 250–268) — three open items:
  - 10.1 GHL Draft Mode (REQUIRED): "Current behavior: Publisher creates posts in GHL as `scheduled` (auto-fires). Required behavior: Publisher creates posts as GHL drafts" — Phase 1 does NOT yet have draft mode at this snapshot per this doc.
  - 10.2 Telegram Notification (REQUIRED): "Current behavior: No notification after publisher runs. Required behavior: After publisher creates GHL drafts, send Dave a Telegram message".
  - 10.3 Status Polling / Webhook (NICE-TO-HAVE): "Publisher doesn't know when GHL actually fires the post."
- Author note "Formalized by Bob — 2026-04-02" (line 273) — postdates AC_VERIFICATION_SUMMARY by 6 days.

**AC references:** Phase 0 review note 8 confirms: **none.** AC mapping lives in AC_VERIFICATION_SUMMARY only. Verified.

**Cross-references:** None to other docs in body. References issues `social-calendar#<TBD>` (lines 256, 262, 268) — placeholders never filled in.

**Stale-doc indicators:**
- Lines 256, 262, 268: three `<TBD>` issue numbers — placeholders never resolved in this snapshot. This is Daedalus issue tracking that didn't make it back into the doc.
- §10 implies the publisher does NOT yet send Telegram and does NOT yet create drafts — needs Pass 01 corroboration. README (line 22) and `publish.yml` (line 87 — `TELEGRAM_BOT_TOKEN` env-set) suggest Telegram wiring is at least *partially* in place. **Doc-vs-code drift.**

---

### Workflows

#### `.github/workflows/auth-check.yml` (71 lines)

**Triggers (lines 7–10):**
- `schedule: cron: '0 9 * * 1'` — Monday 09:00 UTC weekly.
- `workflow_dispatch:` — manual.

**Permissions (lines 17–20):** `contents: read`, `issues: write`, `id-token: write` (OIDC).

**Environment:** `production` (line 15) — gates secrets.

**Steps:**
1. `actions/checkout@v6` (line 23).
2. **Azure Login (OIDC)** (lines 25–31) — conditional on `vars.AZURE_CLIENT_ID != ''`. Uses `client-id` / `tenant-id` / `subscription-id` repo vars.
3. `actions/setup-python@v6` Python 3.12 with pip cache (lines 33–37).
4. `pip install -r publisher/requirements.txt` (line 40).
5. **Run auth check (all brands)** (lines 42–54):
   ```yaml
   python -m publisher.publisher --auth-check --brand all
   ```
   With env: `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `AZURE_KEY_VAULT_NAME`, `FACEBOOK_PAGE_ID`, `LINKEDIN_AUTHOR_URN`, `GBP_LOCATION_NAME`, `INSTAGRAM_USER_ID`. **`continue-on-error: true`** — failure here does NOT fail the run; instead Step 6 catches the outcome.
6. **Create issue on auth failure** (lines 56–71):
   ```yaml
   if: steps.auth_check.outcome == 'failure'
   ...
   gh issue create --repo "${{ github.repository }}" \
     --title "[Auth Check Failed] Weekly credential check $(date -u +%Y-%m-%d)" \
     --body "..." \
     --label "credential-failure" \
     --label "agent:bob"
   ```

**AC refs in YAML comments (lines 3–5):** "AC2: Weekly credential health check across all brands and platforms. Creates a GitHub issue if any token is within 7 days of expiry or fails auth. Ref: AC2 (auth_check), AC13 (token refresh warning)".

**Failure surface:**
- Auth-check Python step: marked `continue-on-error: true` — never reds the workflow itself.
- The issue-creation step is the alert mechanism. Issue uses labels `credential-failure` + `agent:bob`. **No Telegram notification.** (Phase 0 note 7 confirmed.)

**Token-expiry-warning logic (AC2 + AC13):** delegated to `publisher.publisher --auth-check`. The 7-day window cited in YAML comment is implemented inside the publisher (Pass 01 surface), not in the workflow.

**Brand iteration logic:** `--brand all` (single invocation). The Python entry point handles brand iteration internally; the workflow does not loop or matrix over brands.

---

#### `.github/workflows/publish.yml` (129 lines)

**Triggers (lines 10–29):**
- `push: branches: [main]` with `paths: brands/**/calendar/**/*.md` (line 14).
- `workflow_dispatch:` with inputs `brand` (default `"all"`), `dry_run` (boolean default false), `files` (newline-separated, default empty).

**Concurrency (lines 32–34):**
```yaml
concurrency:
  group: ghl-publisher
  cancel-in-progress: false
```
Serializes runs (no overlap). Phase 0 review noted "concurrency group `publisher`" — actual value is `ghl-publisher`.

**Permissions (lines 36–38):** `contents: write` (commit status updates back, comment cites AC6); `issues: write` (failure issues, comment cites AC7).

**Loop guard (line 45):** `if: "!contains(github.event.head_commit.message, '[skip ci]')"` — skips publisher status commits.

**Steps:**
1. **Checkout with `fetch-depth: 2`** (lines 48–52) — enough for `git diff HEAD~1 HEAD`.
2. Setup Python 3.12 + pip cache (lines 54–58).
3. `pip install -r publisher/requirements.txt` (line 61).
4. Configure git identity `github-actions[bot]` (lines 63–66).
5. **Identify changed files** (lines 68–77, push trigger only):
   ```bash
   FILES=$(git diff --name-only HEAD~1 HEAD -- "brands/**/calendar/**/*.md" || true)
   ```
   Output passed via `$GITHUB_OUTPUT` heredoc.
6. **Publish ready posts (push trigger)** (lines 79–93): runs `python -m publisher.publisher --mode ghl --brand all --files "${{ steps.changed.outputs.files }}"`. Env injects `GHL_API_KEY`, `GHL_LOCATION_ID`, `ASSETS_BASE_URL`, `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, **`TELEGRAM_BOT_TOKEN`** (secret), **`TELEGRAM_CHAT_ID`** (var) — Telegram wiring lands here at workflow level.
7. **Publish ready posts (manual trigger)** (lines 95–118): same env, plus inputs flag handling (`--dry-run` if `inputs.dry_run==true`, `--files "${{ inputs.files }}"` if non-empty). Uses `EXTRA_ARGS` and `FILES_ARG` shell-var concatenation (W2/W3 from AC_VERIFICATION_SUMMARY).
8. **Commit status updates** (lines 120–128):
   ```bash
   git add brands/
   if ! git diff --staged --quiet; then
     git commit -m "chore: record GHL publish status [skip ci]"
     git push
   ```

**AC refs in YAML comments (lines 3–5):** "Vulcan design spec (issue #2), AC7 (GHL adapter integration), AC6 (commit status back), AC8 (brand config / account resolution)". Inline: `# Commit status updates back to repo (AC6)` (line 37); `# Create failure issues (AC7)` (line 38).

**Brand discovery:** Workflow always passes `--brand all` on push trigger (line 92); on manual trigger, uses `${{ inputs.brand }}` which defaults to `"all"`. **Brand iteration is delegated to the publisher.** Workflow does not enumerate brands.

**Failure recovery / partial-publish state:** Step 8's commit-back is best-effort: if the python step succeeded for some posts and failed for others, the publisher itself writes per-post status to frontmatter (per architecture doc), and the commit step picks up whatever was written. The workflow does not re-try the python step.

**Commit-status-back to PR (AC6):** Implemented as a post-publish git commit (not as GitHub commit-status API). Uses `[skip ci]` to break the publish→commit→publish loop.

---

#### `.github/workflows/validate-pr.yml` (114 lines)

**Triggers (lines 8–13):**
- `pull_request: branches: [main]` with `paths: brands/**/calendar/**/*.md`, `brands/**/brand.yaml`.

**Permissions:** None declared (defaults to read).

**Jobs — TWO of them:**

**Job 1: `validate-posts` (lines 16–65)** — gated by `if: "contains(join(github.event.pull_request.changed_files.*.filename, ','), 'calendar/')"`.

Steps:
1. Checkout with `fetch-depth: 0` (lines 21–23).
2. setup-python 3.12 (lines 25–28).
3. `pip install pyyaml pydantic` (line 31). **Note: bypasses `publisher/requirements.txt` — installs only 2 deps.**
4. **Validate changed post files** (lines 33–49): `git diff --name-only origin/${{ github.base_ref }}...HEAD | grep 'brands/.*/calendar/.*\.md'` → `xargs python scripts/validate-post.py`.
5. **Validate changed brand configs** (lines 51–65): same diff pattern with `'brands/.*/brand\.yaml'` → `xargs python scripts/validate-brand.py`.

**Job 2: `validate-posts-fallback` (lines 67–113)** — no `if:` guard, so it runs unconditionally on any matching PR.

Steps mirror Job 1 but use a `while read` loop instead of `xargs`, with a `FAILED=0` accumulator and explicit `exit 1` on any per-file failure (lines 99–110). Functionally a defensive duplicate of Job 1.

**AC refs in YAML comments (lines 3–6):** "AC1 (schema validation), AC5 (timezone in publish_at), AC11 (copy sections), AC12 (ensures only valid docs reach main), AC-OQ2 (path structure), AC-OQ3 (multi-section)". **Six ACs cited.** AC11, AC12, AC-OQ2, AC-OQ3 — all from the broader namespace not in AC_VERIFICATION_SUMMARY.

**Block-merge mechanism:** `xargs python scripts/validate-post.py` exits non-zero on any failure (Job 1) → step fails → required PR check fails → branch protection blocks merge. (Branch protection itself not in repo; assumed.)

**Job 1 vs Job 2 note:** Job 1's `if:` guard depends on `github.event.pull_request.changed_files.*.filename`, which is **not always populated** — Job 2 is the safety net. Both run; Job 2 always validates regardless. This is duplicative work (same `git diff` + same `validate-post.py`) but eliminates the gap if Job 1's `if:` evaluates false.

---

### Build/CI Plumbing

#### `.github/dependabot.yml` (28 lines)

**Ecosystems (Phase 0 said "pip + github-actions" — confirmed):**
- `github-actions` (lines 10–17): weekly, max 10 PRs, `update-types: ["patch", "minor"]` grouped as `actions-patch-and-minor`.
- `pip` (lines 19–28): weekly, max 10 PRs, same group strategy as `pip-patch-and-minor`.

**Major-version policy:** Comment lines 4–5 + 27 — major bumps land as separate PRs (default behavior, no `ignore` clause).

**Auto-generated marker:** Line 1 — "Auto-generated by scripts/setup-dependabot.sh — see dave/setup-dependabot PRs." Cross-spec note: `scripts/setup-dependabot.sh` is not in this repo; it is centrally maintained.

#### `publisher/requirements.txt` (4 lines)

```
pyyaml>=6.0.3
pydantic>=2.13.3
python-frontmatter>=1.1.0
requests>=2.33.1
```

Phase 0 said "PyYAML, Requests" + "Pydantic v2.13.3+" — confirmed plus `python-frontmatter>=1.1.0` (not previously called out).

#### `.gitignore` (28 lines, top-level)

Sections: Python (`__pycache__/`, `*.py[cod]`, `*.egg-info/`, `.venv/`, `venv/`, `dist/`, `build/`); Environment/secrets (`.env`, `*.env`, `*.json.tmp`); xurl config (`.config/`); macOS (`.DS_Store`); IDE (`.vscode/`, `.idea/`); Publisher logs (`*.log`).

**Phase 0 finding confirmed:** `.pytest_cache/` is **NOT** in this `.gitignore`. (Phase 0 review note 5: works only because pytest auto-writes its own `.pytest_cache/.gitignore`.)

**Notable inclusion:** `.config/` (line 16) — comment "xurl config (written by workflow, not committed)" confirms the X-config / `xurl` mechanism is workflow-runtime-generated. Cross-ref Pass 02 unknown #3.

---

### AC Namespace Reconciliation

This is THE central Pass 06 finding.

**Two AC namespaces coexist in this snapshot:**

**Namespace A — `AC_VERIFICATION_SUMMARY.md` (10 ACs):** AC1 through AC10. Documented status table at lines 13–23 of that doc. Vintage 2026-03-27. Tied to issue #2 ("Vulcan").

| AC | Doc claim | Cited in |
|----|-----------|----------|
| AC1 | Capability matrix | summary; `validate-pr.yml` (line 5: "AC1 (schema validation)") — **note conflicting meaning**: summary says capability-matrix, workflow says schema-validation. |
| AC2 | `ghl_social_list_accounts.py` | summary; `auth-check.yml` (line 5: "AC2 (auth_check)") — **conflicting meaning** again: summary says list-accounts CLI, workflow says auth-check. |
| AC3 | `ghl_social_create_post.py` | summary only |
| AC4 | `ghl_social_list_posts.py` | summary only |
| AC5 | `ghl_social_delete_post.py` | summary; `validate-pr.yml` (line 5: "AC5 (timezone in publish_at)") — **conflicting meaning**. |
| AC6 | env-var fallback on CLIs | summary; `publish.yml` (line 4: "AC6 (commit status back)") — **conflicting meaning**. |
| AC7 | GHL adapter routes through GHL API | summary; `publish.yml` (line 4: "AC7 (GHL adapter integration)") + `OPERATIONAL_RUNBOOK.md` line 74 ("AC7 — GitHub issue creation"); `architecture.md` line 196 — **two-three different uses.** |
| AC8 | Riley post → schema → publishable | summary; `publish.yml` (line 4: "AC8 (brand config / account resolution)") — **conflicting meaning.** |
| AC9 | Live E2E test | summary only |
| AC10 | Tests + production docs | summary only |

**Namespace B — code/workflow YAML comments (broader, AC1-AC16 + AC-OQ):** workflows alone reference AC1, AC2, AC5, AC6, AC7, AC8, AC11, AC12, AC13, AC-OQ2, AC-OQ3. Per Phase 0, code adds AC14, AC16, AC-OQ4, AC-OQ6. **Not enumerated in any in-repo doc.**

**Reconciliation outcome:**
- The **canonical AC count from `AC_VERIFICATION_SUMMARY.md` is 10** (AC1-AC10).
- The two namespaces share AC numbers but assign **different meanings** to AC1, AC2, AC5, AC6, AC7, AC8 (verified via cross-cite above).
- The broader namespace (AC11-AC16, AC-OQ2/3/4/6) appears **only** in code + workflow comments. No in-repo doc enumerates it. Source-of-truth lives outside this repo (likely Vulcan/Daedalus issue threads, possibly cross-repo).
- The 4 stale CLI script citations in AC_VERIFICATION_SUMMARY (AC2-AC5) are doubly stale: scripts don't exist, and the AC numbers have been re-purposed in code comments.

**Concrete reconciliation table (best effort from in-repo evidence):**

| AC# | Code/workflow meaning | AC_VERIFICATION_SUMMARY meaning | Same? |
|-----|----------------------|--------------------------------|-------|
| AC1 | schema validation (`validate-pr.yml`) | capability matrix | NO |
| AC2 | auth_check / weekly (`auth-check.yml`) | list-accounts CLI | NO |
| AC3 | (not in workflows) | create-post CLI | n/a |
| AC4 | (not in workflows) | list-posts CLI | n/a |
| AC5 | timezone in publish_at (`validate-pr.yml`) | delete-post CLI | NO |
| AC6 | commit status back (`publish.yml`) | env-var fallback on CLIs | NO |
| AC7 | GHL adapter integration / failure issues (`publish.yml`, runbook) | GHL adapter routes through GHL | **partial overlap** |
| AC8 | brand config / account resolution (`publish.yml`) | Riley post → schema → publishable | NO (different angle) |
| AC9 | (not in workflows) | live E2E test | n/a |
| AC10 | (not in workflows) | tests + production docs | n/a |
| AC11 | copy sections (`validate-pr.yml`) | n/a | doc-only |
| AC12 | only-valid-docs-to-main (`validate-pr.yml`) | n/a | doc-only |
| AC13 | token refresh warning (`auth-check.yml`) | n/a | doc-only |
| AC-OQ2 | path structure (`validate-pr.yml`) | n/a | doc-only |
| AC-OQ3 | multi-section (`validate-pr.yml`) | n/a | doc-only |

**The two AC namespaces are NOT the same list with extensions — they are different specs that happen to share AC1-AC10 numbering.** AC_VERIFICATION_SUMMARY is the issue-#2 ("Vulcan") spec; the broader namespace appears to be a "Daedalus"-era spec where AC numbers were reassigned. No reconciliation document exists in-repo.

---

## Cross-Cutting Patterns

### Pattern P06-A: AC-namespace divergence (THE central finding)
Follows Common Pattern: **CP-1 (AC Namespace Divergence)** — see Phase1_Common.md. Pass-06-specific evidence: two AC numbering systems coexist with overlapping numbers but **different meanings** for AC1, AC2, AC5, AC6, AC7, AC8. `AC_VERIFICATION_SUMMARY.md` (10 ACs) is the issue-#2 documented spec. Code + workflow comments reference a broader namespace (AC11-AC16 + AC-OQ2/3/4/6) that is not enumerated in any in-repo file. Source for the broader namespace is external (presumed Daedalus issue thread). The reconciliation table at "AC Namespace Reconciliation" above is the authoritative cross-cite for this pass.

### Pattern P06-B: Doc-vs-code drift on script consolidation
Follows Common Pattern: **CP-2 (Stale-Doc Script-Path References)** — see Phase1_Common.md. Pass-06-specific evidence: three docs (AC_VERIFICATION_SUMMARY, DEVELOPER_GUIDE, GHL_SOCIAL_PLANNER_ARCHITECTURE) reference 4 separate `ghl_social_*.py` scripts + `publish_posts.py` + `test_publish_posts.py`. **None of these 6 file paths exist at snapshot.** The snapshot has consolidated `scripts/ghl_social.py` (363 LOC). Drift count: **6 stale script paths across 3 docs + runbook, ~24 individual cite occurrences** (AC summary alone has ~15 stale cites). All 3 docs share the same author (`[Bob - claude-sonnet-4-6] — Forge #2 Docs Phase`) and pre-date the consolidation refactor. None were updated. README is current — drift is doc-author-cluster-specific.

### Pattern P06-C: Status-lifecycle drift between docs
Follows Common Pattern: **CP-3 (Status-Lifecycle Drift Cluster)** — see Phase1_Common.md. Pass-06-specific evidence:
- README + SOCIAL_CALENDAR_WORKFLOW: `draft → ready → ghl-pending → scheduled → published` (+ `failed`) — 6 states.
- GHL_SOCIAL_PLANNER_ARCHITECTURE.md (line 266): `draft → ready → scheduled → published` (+ `failed`) — 5 states, **omits `ghl-pending`**.
- DEVELOPER_GUIDE: status table (lines 320–329) implies success-path goes straight to `scheduled` after publisher run — **closer to architecture's view** than to README's. Conflict not flagged in any doc.

### Pattern P06-D: Workflow ↔ AC mapping
Connects to **CP-1 (AC Namespace Divergence)** — see Phase1_Common.md. Pass-06-specific evidence:

| Workflow | ACs cited (YAML comments) |
|----------|---------------------------|
| `auth-check.yml` | AC2, AC13 |
| `publish.yml` | AC6, AC7, AC8 (+ "Vulcan design spec / issue #2") |
| `validate-pr.yml` | AC1, AC5, AC11, AC12, AC-OQ2, AC-OQ3 |

11 distinct AC tokens cited in workflows. Of these: 3 (AC11, AC12, AC13) + 2 (AC-OQ2, AC-OQ3) = 5 tokens are NOT in AC_VERIFICATION_SUMMARY.

### Pattern P06-E: Two-job CI defensive pattern (validate-pr.yml)
Connects to **CP-4 (Two-Gate Workflow Implementation)** — see Phase1_Common.md (Gate 1 CI implementation). Pass-06-specific evidence: Job 1 (`validate-posts`) has an `if:` guard on `pull_request.changed_files.*.filename` (which can be empty). Job 2 (`validate-posts-fallback`) has no guard. Both run the same validation against the same diff. This is intentional belt-and-suspenders; the cost is duplicate compute on every PR. Worth noting because Phase 0 didn't catch the duplicate-validation pattern.

### Pattern P06-F: Telegram wiring asymmetry
Follows Common Pattern: **CP-5 (Notification Layering)** — see Phase1_Common.md. Pass-06-specific evidence:
- `publish.yml` injects `TELEGRAM_BOT_TOKEN` (secret) + `TELEGRAM_CHAT_ID` (var) into the publisher env (lines 87–88, 103–104).
- `auth-check.yml` does NOT inject Telegram secrets; on failure it creates a GitHub issue (`credential-failure` + `agent:bob` labels).
- README + WORKFLOW doc describe Telegram for "X posts pending approval" (publish-time event).
- OPERATIONAL_RUNBOOK §3 describes Telegram for failure alerting (Phase 2 plan).
- WORKFLOW §10.2 says Telegram "REQUIRED" / "Current behavior: No notification" — implies not yet implemented at this snapshot.

The publisher receives Telegram credentials from `publish.yml`. Pass 01 confirmed `publisher.py` invokes Telegram via `retry.py:_send_telegram_notification` on final failure (paired with GitHub issue creation).

### Pattern P06-G: `auth-check.yml` carries deprecated-platform env vars
Follows Common Pattern: **CP-7 (Deprecated-Adapter Runtime Liveness)** — see Phase1_Common.md. Pass-06-specific evidence: `FACEBOOK_PAGE_ID`, `LINKEDIN_AUTHOR_URN`, `GBP_LOCATION_NAME`, `INSTAGRAM_USER_ID` are still injected (lines 50–53). These are needed by the deprecated platform adapters' `auth_check()` methods. README line 153 says "GHL manages platform OAuth — no token rotation needed on our side" — soft drift vs auth-check.yml's per-platform env iteration.

### Pattern P06-H: Empty / forward-pointer placeholders + TBD issue numbers
Follows Common Pattern: **CP-10 (Empty Phase-2 / Forward-Pointer Placeholders)** — see Phase1_Common.md. Pass-06-specific evidence: `SOCIAL_CALENDAR_WORKFLOW.md §10` lists 3 `<TBD>` issue numbers for "Open Technical Work" (10.1 GHL Draft Mode, 10.2 Telegram, 10.3 Status Polling) — never resolved. `auth_check.yml` Azure Login conditional `vars.AZURE_CLIENT_ID != ''` — Phase 2 KV path not yet exercised. `.gitignore` `.config/` entry for xurl — no current workflow writes it. `scripts/setup-dependabot.sh` cited in `dependabot.yml` line 1 but does not exist in this repo.

### Pattern P06-I: Hardcoded constants & conventions
Follows Common Pattern: **CP-9 (Hardcoded Constants & Conventions)** — see Phase1_Common.md. Pass-06-specific evidence: `concurrency.group: ghl-publisher` (publish.yml:33); auth-check cron `'0 9 * * 1'` (Monday 09:00 UTC); Phase 0 review claimed group `publisher` — actual `ghl-publisher` (minor Phase 0 correction).

---

## Unknowns / Ambiguities

1. **Source of the broader AC namespace (AC11-AC16, AC-OQ2/3/4/6).** Not in any in-repo file. Likely Daedalus issue / cross-repo. Pass 06 cannot resolve without external sources.
2. **Daedalus issue number.** Phase 0 review noted unknown. Not surfaced in any doc read in this pass — `<TBD>` placeholders in SOCIAL_CALENDAR_WORKFLOW.md §10 (lines 256, 262, 268).
3. **Telegram impl location at snapshot.** WORKFLOW.md §10.2 says "no notification"; `publish.yml` injects Telegram secrets; README claims Telegram notification fires. Three sources, three states. → Pass 01 (grep `telegram` in `publisher.py`).
4. **`ghl-pending` status in code.** Two of three docs include it; architecture doc omits it. Pass 04 (schema enum) + Pass 01 (publisher state machine) must reconcile — does the schema permit `ghl-pending`?
5. **AC1/AC2/AC5/AC6/AC7/AC8 dual-meaning.** Resolved at the documentation level: the two namespaces are different specs. Whether to treat doc-spec or code-spec as canonical is a Phase 2/3 decision; Pass 06 records both.
6. **`auth-check.yml`'s 7-day expiry-warning logic** is in the YAML comment but the implementation lives in `publisher.publisher --auth-check`. → Pass 01.
7. **`publish.yml --files` shell concatenation (W2/W3).** Lines 110–113 use bash variable concatenation that AC summary calls out as fragile. Edge case observed but never reproduced.
8. **`scripts/setup-dependabot.sh`** referenced in `dependabot.yml` line 1 — file does not exist in this repo. External tooling, cross-spec to a "dave/setup-dependabot" pattern (likely repo-template tooling).
9. **`.config/` gitignore entry for xurl** (`.gitignore` line 16) — confirms xurl config is workflow-written but no workflow in this snapshot writes `.config/`. Either dead gitignore entry or a flow not yet exercised at this snapshot. → Pass 02.
10. **Phase 0 review claim of `concurrency group: publisher`** — actual value is `ghl-publisher` (`publish.yml` line 33). Minor Phase 0 correction.
