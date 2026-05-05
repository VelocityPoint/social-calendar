# Phase 0 — Scope Inventory (Reviewed)

## Review Notes

This is a corrected version of `Phase0_Scope.md`. Findings from review against the snapshot:

**Major corrections:**
1. **AC namespace conflict.** Original cited "AC1-AC14" everywhere. Reality: TWO AC namespaces coexist.
   - `docs/AC_VERIFICATION_SUMMARY.md` defines **AC1-AC10** (issue #2 — GHL Social Planner work, dated 2026-03-27).
   - Code/workflow comments reference a broader namespace including **AC11, AC12, AC13, AC14, AC16, AC-OQ2, AC-OQ3, AC-OQ4, AC-OQ6** (e.g., `validate-pr.yml`, `publisher/models.py`, `publisher/state.py`, `scripts/validate-post.py`). Source: an earlier/companion spec, NOT the AC summary doc. Pass 06 must reconcile.
2. **AC summary references scripts that don't exist in the repo at snapshot.** `AC_VERIFICATION_SUMMARY.md` cites `scripts/ghl_social_list_accounts.py`, `ghl_social_create_post.py`, `ghl_social_list_posts.py`, `ghl_social_delete_post.py`, and `scripts/publish_posts.py`. Actual `scripts/` at snapshot has only **3 files**: `ghl_social.py` (363 LOC), `validate-brand.py`, `validate-post.py`. The AC doc is stale relative to a refactor that consolidated 4 CLIs into one. This is a Pass 03 + Pass 06 finding.
3. **Five non-GHL platform adapters are explicitly DEPRECATED** per README, not "live platform implementations." README says: "GHL handles Meta OAuth" and labels facebook/instagram/linkedin/x_twitter/gbp as "Deprecated." Phase 1 should treat them as legacy/dead code, not Phase-1 surface.
4. **LOC totals were off.** Recomputed via `wc -l`:
   - Publisher core (`publisher/{publisher,models,retry,state,__init__}.py`): **1,438** (matches original by coincidence, but only because `__init__.py` is 1 line).
   - Adapters (`publisher/adapters/*.py`, all 8 files): **1,338** (original said ~722; off by ~600 — original undercounted the deprecated adapters significantly).
   - Scripts (`scripts/*.py`): **858**. Tests: **942**. Workflows: **312**.
   - Total Python: **4,888 LOC** (not 4,576). Differs because adapters were undercounted.
5. **`.pytest_cache/` status.** It exists locally on disk (CACHEDIR.TAG present) but is NOT committed (`find` excluded it; not in repo file listing). It is also NOT listed in `.gitignore` — works only because pytest writes its own `.pytest_cache/.gitignore`. Phase 0's "is it gitignored or accidentally committed?" framing was wrong; the answer is "neither at root, but auto-ignored by pytest's local file."
6. **Brand listing in Component Map omitted `gitkeep` placeholders accurately** — both `templates/.gitkeep` and `campaigns/spring-launch-2026/.gitkeep` are 1-line empty files. Confirmed.
7. **`auth-check.yml` brief peek.** It does Azure OIDC login → installs Python 3.12 → runs `python -m publisher.publisher --auth-check --brand all` → on failure creates a GitHub issue with labels `credential-failure` + `agent:bob`. NOT calling `scripts/ghl_social.py --check` as Phase 0 speculated. Telegram is NOT used here — the alert is a GitHub issue.
8. **`SOCIAL_CALENDAR_WORKFLOW.md` confirmed** — covers the formalized two-gate workflow but does NOT cross-reference AC numbers. AC mapping lives in `AC_VERIFICATION_SUMMARY.md`.

**Style/scope fixes:**
- Original creeps into Phase 2 territory by speculating "the publisher likely shells out to xurl" and "5 platform adapters may be unused at runtime." Demoted these from speculation to "REVIEW" markers.
- Original's "most spec'd repo we've reverse-spec'd" / "most rigorous test surface" judgements moved out of Phase 0 prose (qualitative, not Phase 0's job).
- Cross-spec cross-references kept; flagged where unverifiable from this repo alone.

**Couldn't verify from this repo (Phase 1 must resolve):**
- `Core_Business#222` exists (claimed in README); cross-repo, not checkable here.
- Vulcan = issue #2 (verified — AC summary cites `social-calendar#2`). Daedalus issue number unknown; not in any in-repo file I read.
- Whether `publisher.py` runs in a Function App or only in GitHub Actions (only `publish.yml` invocation seen; no Azure Function code in repo, so likely GHA-only).

---

# Phase 0 — Scope Inventory

**Project:** social-calendar (GitHub-native social media content calendar and publisher for VelocityPoint)
**Repository:** `VelocityPoint/social-calendar`
**Snapshot:** `67d061c` (2026-04-26) — `Merge pull request #24 from VelocityPoint/dependabot/pip/pydantic-gte-2.13.3`
**Branch at snapshot:** `main`
**Total source size:** **4,888 LOC Python** (publisher core 1,438 + adapters 1,338 + scripts 858 + tests 942 + adapters/__init__ 29 + publisher/__init__ 1) + 3 GitHub Actions workflows (312 lines) + 7 markdown docs + 2 brand YAMLs + 4 calendar markdown posts + 1 schema YAML + 1 dependabot YAML + 1 requirements.txt

---

## Provenance & Context

social-calendar is the **organic-social-media bookend** to the paid-ads `sr-google-ads` repo. Closes the marketing surface:

- **Paid path (sr-google-ads)**: ad impressions → click → `/waitlist` → Stripe → Function → Google Ads conversion-import
- **Organic path (this repo)**: scheduled markdown post → 2-gate approval → GHL Social Planner draft → operator-scheduled fire → multi-platform publish

**Originating issue:** `Core_Business#222` (per README — cross-repo, not verified from this repo).
**Active phase:** Phase 1 (GHL Social Planner integration).
**Phase 2** (HeyGen avatar integration) deferred — see `avatar_id: null` in brand configs.

**Two named design specs** referenced in code/comments:
- **Vulcan** = `social-calendar#2` — publisher architecture (verified via AC summary cross-link)
- **Daedalus** — GHL Social Planner integration; issue number not surfaced in any in-repo file. REVIEW (Phase 1).

**AC namespaces — TWO of them, not reconciled in-repo:**
- **`docs/AC_VERIFICATION_SUMMARY.md` (canonical doc):** AC1-AC10. Status table shows 8 PASS, 1 BLOCKED (AC9 — live E2E pending account connection), 1 PARTIAL (AC10 — docs).
- **Code + workflow comments:** reference a broader/older namespace including AC11, AC12, AC13, AC14, AC16, plus AC-OQ2, AC-OQ3, AC-OQ4, AC-OQ6. Examples: `validate-pr.yml` cites AC1, AC5, AC11, AC12, AC-OQ2, AC-OQ3; `auth-check.yml` cites AC2, AC13; `publisher/models.py` cites AC1, AC6, AC8, AC13, AC14, AC16; `publisher/publisher.py` cites AC3-AC7, AC11, AC12, AC16, AC-OQ2/4/6.
- **Implication:** the codebase was built against a wider AC list than `AC_VERIFICATION_SUMMARY.md` documents. Pass 06 must locate or reconstruct the source-of-truth list.

**Cross-spec relevance:**
- **`sr-ops-tools`**: shares GHL automation surface (Phase 1.5 C7 cross-spec marker — same Bearer + version-2021-07-28 GHL pattern likely repeated)
- **`sr-azure-infra`**: brand.yaml uses Key Vault secret-name pattern (`kv-secondring-facebook-token`); credentials resolution is via secret-store lookup at runtime
- **`sr-google-ads`**: shares the "single source + manual sync" pattern shape (no shared code in this repo)
- **`Core_Business#222`**: parent strategic issue (out of repo)

**Notable architectural choices (observed, not interpreted):**
- **Two-gate human-in-the-loop**: posts land as DRAFTS in GHL, not auto-fired. Per README + `SOCIAL_CALENDAR_WORKFLOW.md`.
- **Telegram notification** wired into the publish flow (per README + workflow doc Stage 3) — NOT visible in `auth-check.yml` (which uses GitHub issues instead). Phase 1 must locate Telegram impl in `publisher.py`.
- **942-LOC test suite** across 2 test files. `.pytest_cache/` exists locally (untracked) — tests run.

---

## Operational Surface

```
Author lifecycle (per README + SOCIAL_CALENDAR_WORKFLOW.md):
  Riley:  drafts post in brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-slug.md (status: draft)
  Riley:  opens GitHub PR
    → validate-pr.yml runs scripts/validate-post.py + scripts/validate-brand.py
      (refs: AC1 schema, AC5 timezone, AC11 copy sections, AC12 main-branch, AC-OQ2/3)
    → Dave reads copy in GitHub diff, sets `status: ready`, merges (Gate 1)
  Merge:
    → publish.yml runs publisher/publisher.py
    → Publisher creates post in GHL Social Planner as DRAFT
    → Writes back status: ghl-pending + ghl_post_id to the .md file
    → Sends Telegram notification (impl location: REVIEW, Pass 01)
  Dave (Gate 2 — visual approval):
    → opens GHL Social Planner, reviews previews, clicks Schedule
    → GHL fires each post at its publish_at time
    → publisher detects success → writes back status: published + published_at
  Weekly:
    → auth-check.yml (cron Mon 09:00 UTC) runs
      `python -m publisher.publisher --auth-check --brand all` via Azure OIDC.
      On failure: creates GitHub issue with label credential-failure + agent:bob.
      (refs: AC2 auth_check, AC13 token refresh)

Out-of-band tools (scripts/):
  scripts/ghl_social.py      (363 LOC) — operator CLI for GHL Social Planner
                                          (consolidates accounts/posts/create/delete)
  scripts/validate-brand.py  (170 LOC) — schema check on brands/<brand>/brand.yaml
  scripts/validate-post.py   (325 LOC) — schema check on calendar markdown posts
```

**Brands at snapshot:** 2 — `secondring` (Second Ring), `velocitypoint` (Velocity Point). Each has its own `.state/`, `assets/`, `brand.yaml`, `calendar/` subtree.

**Platforms supported per schema:** 5 — `facebook`, `linkedin`, `gbp` (Google Business Profile), `x` (Twitter), `instagram`. Plus a 6th adapter (`ghl.py`) which is the active publishing channel; the 5 platform-specific adapters are **marked deprecated in the README** (GHL now handles Meta OAuth and platform routing).

---

## Component Map

| # | Component | Path | Apparent Role | LOC |
|---|-----------|------|---------------|----:|
| C1 | **Publisher core engine** | `publisher/{publisher,models,retry,state,__init__}.py` | YAML→pydantic→adapter dispatch + retry + per-brand rate-limit state | 1,438 |
| C2 | **Platform adapters** | `publisher/adapters/{__init__,base,facebook,gbp,ghl,instagram,linkedin,x_twitter}.py` (8 files) | `ghl.py` (341 LOC) is active; `base.py` (142) declares interface; the 5 platform adapters (facebook 126, gbp 146, instagram 167, linkedin 183, x_twitter 204 = 826) are marked deprecated in README | 1,338 |
| C3 | **Operator scripts** | `scripts/{ghl_social,validate-brand,validate-post}.py` | 3 scripts: `ghl_social.py` is operator-only consolidated GHL CLI; `validate-*` are CI gates | 858 |
| C4 | **Brand + calendar + campaign content** | `brands/{secondring,velocitypoint}/{brand.yaml,calendar/YYYY/MM/*.md,assets/.gitkeep,.state/rate_limits/.gitkeep}`, `campaigns/spring-launch-2026/.gitkeep`, `templates/.gitkeep` | Per-brand configs + 4 scheduled posts (1 SR + 3 VP) + empty placeholder dirs | n/a |
| C5 | **Schema** | `schemas/post.schema.yaml` | The post document schema (v1.1 per file) | n/a |
| C6 | **Test suite** | `tests/{__init__,test_ghl_adapter,test_publisher_ghl_mode}.py` | pytest suite | 942 |
| C7 | **GitHub Actions workflows** | `.github/workflows/{auth-check,publish,validate-pr}.yml` | 3 workflows: weekly auth check (71), publish on merge (128), PR validation (113) | 312 |
| C8 | **Documentation** | `README.md`, `docs/{AC_VERIFICATION_SUMMARY,DEVELOPER_GUIDE,GHL_SOCIAL_PLANNER_ARCHITECTURE,OPERATIONAL_RUNBOOK,RILEY_HANDOFF_SPEC,SOCIAL_CALENDAR_WORKFLOW}.md` | README + 6 docs | n/a |
| C9 | **Build / CI plumbing** | `publisher/requirements.txt`, `.github/dependabot.yml`, `.gitignore` | Python deps + dependabot (pip + github-actions) | n/a |

---

## File Classification

### Entry Points
- `publisher/publisher.py` (605 LOC) — main entry, invoked by `publish.yml` (publish path) and `auth-check.yml` (`--auth-check --brand all`)
- `scripts/ghl_social.py` (363 LOC) — operator CLI for GHL Social Planner ops
- `scripts/validate-brand.py` (170 LOC) — CI gate
- `scripts/validate-post.py` (325 LOC) — CI gate
- `.github/workflows/{auth-check,publish,validate-pr}.yml` — CI entry points

### Library / shared
- `publisher/models.py` (286) — pydantic models (Post, Brand, GHLConfig, RateLimitState, etc.)
- `publisher/retry.py` (276) — retry primitive (10s/30s/90s backoff per README)
- `publisher/state.py` (270) — frontmatter read/write + main-branch check (AC12)
- `publisher/adapters/base.py` (142) — abstract adapter interface
- `publisher/adapters/ghl.py` (341) — active GHL Social Planner adapter
- `publisher/adapters/{facebook,gbp,instagram,linkedin,x_twitter}.py` — 5 deprecated platform adapters per README

### Tests
- `tests/test_ghl_adapter.py` (532)
- `tests/test_publisher_ghl_mode.py` (410)
- `tests/__init__.py` (0)

### Configuration
- `brands/secondring/brand.yaml`, `brands/velocitypoint/brand.yaml`
- `schemas/post.schema.yaml`
- `publisher/requirements.txt`
- `.github/dependabot.yml`
- `.gitignore`

### Documentation
- `README.md` — project overview + two-gate workflow
- `docs/AC_VERIFICATION_SUMMARY.md` — AC1-AC10 verification (issue #2 spec; references some scripts not in current repo — see Review Note 2)
- `docs/DEVELOPER_GUIDE.md`
- `docs/GHL_SOCIAL_PLANNER_ARCHITECTURE.md` — Daedalus design (GHL integration)
- `docs/OPERATIONAL_RUNBOOK.md`
- `docs/RILEY_HANDOFF_SPEC.md` — Riley-specific spec
- `docs/SOCIAL_CALENDAR_WORKFLOW.md` — formalized 5-stage workflow (does NOT cross-reference AC numbers)

### Content (data, not code)
- `brands/secondring/calendar/2026/04/2026-04-01-never-miss-a-call.md` (1 SR post)
- `brands/velocitypoint/calendar/2026/04/2026-04-07-linkedin-ai-for-service-business.md`
- `brands/velocitypoint/calendar/2026/04/2026-04-09-facebook-never-miss-a-call.md`
- `brands/velocitypoint/calendar/2026/04/2026-04-11-instagram-ai-receptionist.md` (3 VP posts)
- `templates/.gitkeep` (empty 1-line placeholder)
- `campaigns/spring-launch-2026/.gitkeep` (empty 1-line placeholder)
- `brands/{secondring,velocitypoint}/{assets/,.state/rate_limits/}/.gitkeep` (4 empty placeholders)

### Infrastructure as Code
**None in repo.** Infra (Key Vault, etc.) lives in `sr-azure-infra`. The Key Vault secret names referenced in `brand.yaml` are provisioned externally.

### Unknown / REVIEW
- `templates/` is empty (just `.gitkeep`). Phase 1 Pass 04 should resolve intent.
- `campaigns/spring-launch-2026/` is empty. Same question.
- AC namespace conflict (AC1-AC10 vs AC1-AC16+OQ). Pass 06 must reconcile.
- Whether the 5 deprecated platform adapters are reachable at runtime, or pure dead code. Pass 02.
- `auth-check.yml` env vars include `FACEBOOK_PAGE_ID`, `LINKEDIN_AUTHOR_URN`, `GBP_LOCATION_NAME`, `INSTAGRAM_USER_ID` — implying the deprecated adapters' `auth_check` methods are still invoked. Confirms the adapters are not entirely dead; Pass 02 must clarify the active surface.

---

## Dependency Signals

### Cross-component (within repo)
- **C2 (adapters) → C1 (engine)**: adapters inherit `publisher/adapters/base.py`; dispatched by `publisher/publisher.py`.
- **C1 → C5 (schema)**: `publisher/models.py` mirrors schema structure (cited in models docstring).
- **C3 (scripts) → C1 + C5**: `validate-post.py` consumes the schema; `validate-brand.py` consumes brand schema (defined in models too).
- **C7 (workflows) → C3 + C1**: `validate-pr.yml` invokes scripts; `publish.yml` invokes `publisher.publisher`; `auth-check.yml` invokes `publisher.publisher --auth-check`.
- **C6 (tests) → C1 + C2**: tests verify publisher behavior + GHL adapter.
- **C4 (content) → C5 (schema)**: each calendar markdown post must validate against the post schema.

### External dependencies
- **GoHighLevel Social Planner API** — primary integration (Phase 1 focus per README)
- **Facebook Graph API** + **Instagram Graph API** (shared Meta credentials per AC14 — but README says Meta OAuth now handled by GHL; reconcile in Pass 02)
- **LinkedIn API** (deprecated adapter)
- **Google Business Profile API** (deprecated `gbp` adapter)
- **X (Twitter) API** — `x_twitter.py` (deprecated); brand.yaml comment mentions `xurl config JSON` for `kv-secondring-x-config`. REVIEW (Pass 02): whether `xurl` is shelled out or just a credential format
- **Telegram Bot API** — for Dave's notification (per README + workflow doc); impl location not yet identified. Pass 01.
- **HeyGen** — Phase 2 deferred (`avatar_id: null` in brand configs)
- **Azure Key Vault** — secret store; `kv-secondring-*` and `kv-velocitypoint-*` secret names referenced. Resolution via Azure OIDC in workflows (`AZURE_KEY_VAULT_NAME` env var).
- **Pydantic v2.13.3+** (per recent dependabot bump)
- **PyYAML, Requests** (per `publisher/requirements.txt`)

### Cross-repo
- **`Core_Business`** — parent strategic issue (#222) lives there
- **`sr-azure-infra`** — provisions Key Vault entries
- **`sr-ops-tools`** — sibling Python operational layer; potentially shares GHL helpers
- **`vp-cms` / `Product-SecondRing`** — design specs may live in sibling repos; Phase 0 doesn't resolve

---

## Phase 1 Extraction Plan

The codebase has 9 logical components; **split-file layout** with **6 passes**:

| Pass | Title | Inputs | Approx LOC | Notes |
|------|-------|--------|----------:|-------|
| 01 | Publisher Core Engine | `publisher/{publisher,models,retry,state,__init__}.py` | 1,438 | Largest pass. `publisher.py` (605) is the orchestrator; `models.py` + `retry.py` + `state.py` are the supporting primitives. **Resolves:** Telegram impl location; `--auth-check` flow; `--mode ghl` semantics; AC11/AC12/AC16 in-code references. |
| 02 | Platform Adapters | `publisher/adapters/*.py` (8 files: base + ghl + 5 deprecated + __init__) | 1,338 | Adapter pattern. **Resolves:** which deprecated adapters are still reached by `auth-check.yml`; xurl/X-config question; whether deprecated adapters can be deleted or remain for `auth_check` method only. |
| 03 | Operator Scripts | `scripts/{ghl_social,validate-brand,validate-post}.py` | 858 | 3 scripts. `validate-*` are CI gates; `ghl_social.py` is the consolidated operator CLI. **Resolves:** the AC summary's references to 4 separate `ghl_social_*.py` files (history vs current). |
| 04 | Schema + Brand + Calendar Content | `schemas/post.schema.yaml`, 2× `brands/<brand>/brand.yaml`, 4× calendar posts, `campaigns/spring-launch-2026/`, `templates/` | n/a (YAML + markdown) | The declarative surface. **Resolves:** schema `status` enum state machine (`draft → ready → ghl-pending → published?`); empty `templates/` and `campaigns/` intent; `account_ids must be filled in before publishing goes live` launch-blocker. |
| 05 | Test Suite | `tests/{test_ghl_adapter,test_publisher_ghl_mode}.py` (+ `__init__.py`) | 942 | Map test scenarios to ACs. |
| 06 | Docs + Workflows + Build/CI | All 6 docs in `docs/`, `README.md`, 3 workflows in `.github/workflows/`, `.github/dependabot.yml`, `publisher/requirements.txt`, `.gitignore` | 312 (workflows) + n/a (docs) | The runbook + automation surface. **Resolves:** AC namespace reconciliation (AC1-AC10 vs AC1-AC16+OQ); workflow trigger mapping; whether `AC_VERIFICATION_SUMMARY.md`'s stale script references should be updated. |

**Cross-cutting concerns** to expect Phase 1.5 to surface:
- **AC-mapping master table** — must reconcile two AC namespaces
- **GHL API client pattern** — same Bearer + version-2021-07-28 as RP/sr-ops-tools (cross-spec C7 marker)
- **Key Vault secret-name pattern** — brand.yaml references KV secret names; cross-spec to sr-azure-infra
- **Adapter interface conformance** — `base.py` interface; do all 6 platform adapters honor it even though 5 are deprecated?
- **Pydantic-validation pattern** — schema + models alignment
- **Retry policy pattern** — `publisher/retry.py` 276-LOC primitive; document semantics
- **State directory pattern** — `.state/rate_limits/` per brand
- **Two-gate workflow pattern** — distinctive; document the GitHub gate ↔ GHL gate handoff

---

## Out of Scope

- **GoHighLevel API internals** — black-box dependency
- **Facebook / Instagram / LinkedIn / X / GBP API internals** — black-box (and adapters deprecated anyway)
- **Telegram Bot API internals** — black-box (impl wiring IS in scope; API surface is not)
- **HeyGen** — out-of-phase (Phase 2 deferred)
- **Azure Key Vault internals** — provisioned in sr-azure-infra
- **Vulcan + Daedalus design spec contents** — referenced but live in cross-repo issue tracker
- **Riley's authoring tooling** — this repo is the publisher, not the author
- **`Core_Business#222`** — parent strategic issue, out of scope

---

## Unknowns / Ambiguities (each has a Phase 1 pass that resolves it)

1. **`templates/` and `campaigns/spring-launch-2026/` empty at snapshot** — placeholders for what? → Pass 04.
2. **Telegram notification impl location** — README + workflow doc cite it; `auth-check.yml` doesn't use it (it uses GitHub issues). → Pass 01 (grep `telegram` in `publisher.py`).
3. **`xurl config JSON` for X (Twitter)** — brand.yaml notes `kv-secondring-x-config` is "xurl config JSON." Does the X adapter shell out to `xurl`, or just consume the JSON? → Pass 02.
4. **5 deprecated adapters' runtime status** — README says deprecated, but `auth-check.yml` env vars suggest their `auth_check` methods are still called. → Pass 02.
5. **AC namespace reconciliation** — AC_VERIFICATION_SUMMARY documents AC1-AC10; code references AC11-AC16 + AC-OQ2/3/4/6. → Pass 06.
6. **`AC_VERIFICATION_SUMMARY.md` stale script references** — cites 4 separate `ghl_social_*.py` scripts; only consolidated `ghl_social.py` exists. → Pass 03 + Pass 06.
7. **Telegram bot credentials** — env-var name, KV secret name, or hardcoded? → Pass 01 (publisher) or Pass 06 (workflows).
8. **GHL_LOCATION_ID `cUgvqrKmBM4sAZvMH1JS`** — visible in brand.yaml comment. Cross-ref to `sr-ops-tools` Pass 04 (referenced same ID). → Pass 04.
9. **`account_ids must be filled in before publishing goes live`** (per brand.yaml comment) — same launch-blocker pattern as sr-google-ads. Which fields? → Pass 04.
10. **`status` field full state machine** — schema (Pass 04) defines it; workflow doc shows `draft → ready → ghl-pending → published`. Confirm against schema enum.
11. **Vulcan vs Daedalus spec scope** — Vulcan = `social-calendar#2`. Daedalus issue number REVIEW. → Pass 06.
12. **Phase 2 indicators** — `avatar_id: null` (HeyGen), empty `templates/`, empty `campaigns/`. Forward-pointers; record as observed-empty.
13. **`.pytest_cache/` not in `.gitignore`** — works only because pytest auto-writes its own `.pytest_cache/.gitignore`. Recommend Pass 06 flag for hardening (add explicit entry to root `.gitignore`).
14. **`auth-check.yml` Telegram absence** — failure path is GitHub issue, not Telegram. Inconsistent with publish-path Telegram notification? → Pass 06 (intentional or oversight).
