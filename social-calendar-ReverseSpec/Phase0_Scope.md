# Phase 0 — Scope Inventory

**Project:** social-calendar (GitHub-native social media content calendar and publisher for VelocityPoint)
**Repository:** `VelocityPoint/social-calendar`
**Snapshot:** `67d061c` (2026-04-26) — `Merge pull request #24 from VelocityPoint/dependabot/pip/pydantic-gte-2.13.3`
**Branch at snapshot:** `main` (caught up via fast-forward)
**Total source size:** **4,576 LOC Python** (publisher 1,667 + adapters ~720 + scripts 858 + tests 942) + 3 GitHub Actions workflows + 6 markdown docs + 2 brand YAMLs + 4 calendar markdown posts + 1 schema YAML

---

## Provenance & Context

social-calendar is the **organic-social-media bookend** to the paid-ads `sr-google-ads` repo (just reverse-spec'd). Closes the marketing surface:

- **Paid path (sr-google-ads)**: ad impressions → click → `/waitlist` → Stripe → Function → Google Ads conversion-import
- **Organic path (this repo)**: scheduled markdown post → 2-gate approval → GHL Social Planner draft → operator-scheduled fire → multi-platform publish

**Originating issue:** `Core_Business#222` (per README). **Active phase:** Phase 1 (GHL Social Planner integration). **Phase 2** (HeyGen avatar integration) deferred — see `avatar_id: null` in brand configs.

**Two named design specs** referenced in code comments:
- **Vulcan design spec** (issue #2 in this repo) — publisher architecture
- **Daedalus design spec** — GHL Social Planner integration, account resolution

The repo follows an unusually formal **AC-driven** workflow: code comments reference acceptance criteria AC1-AC14 throughout. This is the most spec'd repo we've reverse-spec'd; Phase 1 should record the AC↔code mapping faithfully.

**Cross-spec relevance:**
- **`sr-ops-tools`**: shares GHL automation surface (Phase 1.5 C7 cross-spec marker — same Bearer + version-2021-07-28 GHL pattern likely repeated)
- **`sr-azure-infra`**: brand.yaml uses Key Vault secret-name pattern (`kv-secondring-facebook-token`); credentials resolution is via secret-store lookup at runtime
- **`sr-google-ads`**: cross-spec `gclid-capture.js`-style sync-with-vp-cms is similar in shape (single source + manual sync), not present here but the pattern is recognizable
- **`Core_Business#222`**: parent strategic issue (out of repo)

**Notable architectural choices:**
- **Human-in-the-loop pattern**: posts land as DRAFTS in GHL, not auto-fired. Operator must visually approve in GHL Social Planner before scheduling. This is distinctive in VP tooling (other operational scripts don't have a two-stage approval surface).
- **Telegram notification** wired into the publish flow (per README "Dave receives a Telegram notification: 'X posts pending approval in GHL'") — Phase 1 should locate the implementation.
- **Real test suite** (942 LOC across 2 test files) — unusually high coverage for a small VP repo. `.pytest_cache` present at snapshot, suggesting tests run regularly.

---

## Operational Surface

```
Author lifecycle (per README):
  Riley:  drafts post in brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-slug.md
  Riley:  opens GitHub PR
    → validate-pr.yml runs scripts/validate-post.py + scripts/validate-brand.py (AC1, AC5, AC11)
    → Dave reads copy in GitHub diff, sets `status: ready`, merges
  Merge:
    → publish.yml runs publisher/publisher.py
    → Publisher creates GHL Social Planner draft per platform per brand (AC7, AC6, AC8)
    → Dave receives Telegram notification
  Dave (visual approval):
    → opens GHL Social Planner, reviews previews, clicks Schedule
    → GHL fires each post at its publish_at time
  Weekly:
    → auth-check.yml (AC2, AC13) probes credentials, opens GitHub issue if any token within 7 days of expiry

Out-of-band tools:
  scripts/ghl_social.py         — operator helpers for GHL Social Planner interactions
  scripts/validate-brand.py     — schema check on brands/<brand>/brand.yaml
  scripts/validate-post.py      — schema check on calendar markdown posts
```

**Brands at snapshot:** 2 — `secondring` (Second Ring), `velocitypoint` (Velocity Point). Each has its own `.state/`, `assets/`, `brand.yaml`, and `calendar/` subtree.

**Platforms supported per schema:** 5 — `facebook`, `linkedin`, `gbp` (Google Business Profile), `x` (Twitter), `instagram`. Plus a 6th adapter (`ghl.py`) which is the **publishing channel** (not a destination platform — GHL routes to the actual platforms once Dave schedules).

---

## Component Map

| # | Component | Path | Apparent Role | LOC |
|---|-----------|------|---------------|----:|
| C1 | **Publisher core engine** | `publisher/{publisher,models,retry,state,__init__}.py` | YAML→pydantic→adapter dispatch + retry + per-brand rate-limit state | ~1,438 |
| C2 | **Platform adapters** | `publisher/adapters/{__init__,base,facebook,gbp,ghl,instagram,linkedin,x_twitter}.py` | One adapter per platform; base.py likely declares the interface | ~722 |
| C3 | **Operator scripts** | `scripts/{ghl_social,validate-brand,validate-post}.py` | Operator-invoked CLI helpers — GHL Social helpers + 2 validators | ~858 |
| C4 | **Brand + calendar + campaign content** | `brands/{secondring,velocitypoint}/{brand.yaml,calendar/YYYY/MM/*.md,assets/,.state/}`, `campaigns/spring-launch-2026/`, `templates/` | Per-brand configs + scheduled posts as markdown files + state directories for rate-limiting | n/a |
| C5 | **Schema** | `schemas/post.schema.yaml` | The post document schema (v1.1 per file) | n/a |
| C6 | **Test suite** | `tests/{test_ghl_adapter,test_publisher_ghl_mode}.py` (+ `__init__.py`) | Real pytest test suite — 942 LOC | ~942 |
| C7 | **GitHub Actions workflows** | `.github/workflows/{auth-check,publish,validate-pr}.yml` | 3 workflows: weekly auth check, publish on merge, PR validation | ~312 (3 yaml) |
| C8 | **Documentation** | `README.md`, `docs/{AC_VERIFICATION_SUMMARY,DEVELOPER_GUIDE,GHL_SOCIAL_PLANNER_ARCHITECTURE,OPERATIONAL_RUNBOOK,RILEY_HANDOFF_SPEC,SOCIAL_CALENDAR_WORKFLOW}.md` | README + 6 docs spanning architecture, runbook, AC verification, developer guide, handoff spec, workflow | n/a |
| C9 | **Build / CI plumbing** | `publisher/requirements.txt`, `.github/dependabot.yml` | Python deps + dependabot covering pip + github-actions (per recent commits) | n/a |

---

## File Classification

### Entry Points
- `publisher/publisher.py` (605 LOC) — main entry for `publish.yml` workflow
- `scripts/ghl_social.py` (363 LOC) — operator CLI for GHL Social Planner ops
- `scripts/validate-brand.py` (170 LOC) — operator CLI / CI gate
- `scripts/validate-post.py` (325 LOC) — operator CLI / CI gate
- `.github/workflows/{auth-check,publish,validate-pr}.yml` — CI entry points

### Library / shared
- `publisher/models.py` (286 LOC) — pydantic models (post, brand, etc.)
- `publisher/retry.py` (276 LOC) — retry primitive
- `publisher/state.py` (270 LOC) — state management (rate limits, etc.)
- `publisher/adapters/base.py` — base interface for adapters
- `publisher/adapters/{facebook,gbp,ghl,instagram,linkedin,x_twitter}.py` — 6 platform implementations

### Tests
- `tests/test_ghl_adapter.py` (532 LOC)
- `tests/test_publisher_ghl_mode.py` (410 LOC)

### Configuration
- `brands/secondring/brand.yaml`, `brands/velocitypoint/brand.yaml` — per-brand config
- `schemas/post.schema.yaml` — schema document
- `publisher/requirements.txt`
- `.github/dependabot.yml`

### Documentation
- `README.md` — project overview + two-gate workflow
- `docs/AC_VERIFICATION_SUMMARY.md` — AC-by-AC verification status
- `docs/DEVELOPER_GUIDE.md` — developer-facing setup
- `docs/GHL_SOCIAL_PLANNER_ARCHITECTURE.md` — Daedalus design (GHL integration)
- `docs/OPERATIONAL_RUNBOOK.md` — operator runbook
- `docs/RILEY_HANDOFF_SPEC.md` — Riley-specific spec
- `docs/SOCIAL_CALENDAR_WORKFLOW.md` — formalized workflow

### Content (data, not code)
- `brands/secondring/calendar/2026/04/2026-04-01-never-miss-a-call.md` (1 post)
- `brands/velocitypoint/calendar/2026/04/{2026-04-07-linkedin-ai-for-service-business,2026-04-09-facebook-never-miss-a-call,2026-04-11-instagram-ai-receptionist}.md` (3 posts)
- `templates/.gitkeep` — template directory present but empty
- `campaigns/spring-launch-2026/.gitkeep` — campaign directory present but empty
- `brands/<brand>/{assets/,.state/rate_limits/}.gitkeep` — placeholder dirs

### Infrastructure as Code
**None in repo.** Infrastructure (key vault, function apps, etc.) lives in `sr-azure-infra` (already reverse-spec'd). The Key Vault secret names referenced by `brand.yaml` are provisioned externally.

### Unknown / REVIEW
- `templates/` is empty (just `.gitkeep`). What's intended to live there? Pass 04 should resolve.
- `campaigns/spring-launch-2026/` is empty. Same question.
- `.pytest_cache/` is in the file listing — verify it's git-ignored vs accidentally committed. Pass 06.
- The 6 docs collectively are substantial. Phase 0 cites them but doesn't deep-read; Pass 06 owns.

---

## Dependency Signals

### Cross-component (within repo)
- **C2 (adapters) → C1 (engine)**: adapters likely inherit from `publisher/adapters/base.py` and are dispatched by `publisher/publisher.py`.
- **C1 → C5 (schema)**: `publisher/models.py` likely mirrors the schema structure.
- **C3 (scripts) → C1 + C5**: `validate-post.py` consumes the schema; `validate-brand.py` consumes brand schema (likely defined in models too).
- **C7 (workflows) → C3 + C1**: `validate-pr.yml` invokes scripts; `publish.yml` invokes `publisher/publisher.py`.
- **C6 (tests) → C1 + C2**: tests verify publisher behavior + GHL adapter specifically.
- **C4 (content) → C5 (schema)**: each calendar markdown post must validate against the post schema.

### External dependencies
- **GoHighLevel Social Planner API** — primary integration (Phase 1 focus per README). Same Bearer + version-2021-07-28 pattern as RP/sr-ops-tools.
- **Facebook Graph API** + **Instagram Graph API** (shared Meta credentials per AC14)
- **LinkedIn API**
- **Google Business Profile API** (`gbp` adapter)
- **X (Twitter) API** — `x_twitter.py` adapter; brand.yaml says `kv-secondring-x-config` is "xurl config JSON" (likely the `xurl` CLI tool)
- **Telegram Bot API** — for Dave's notification (per README); Phase 1 should locate
- **HeyGen** — Phase 2 deferred (`avatar_id: null` in brand configs)
- **Azure Key Vault** — secret store; `kv-secondring-*` and `kv-velocitypoint-*` secret names referenced in brand.yaml
- **Pydantic v2.13.3+** (per recent dependabot bump)
- **PyYAML 6.0.3+**
- **Requests 2.33.1+**

### Cross-repo
- **`Core_Business`** — parent strategic issue (#222) lives there
- **`sr-azure-infra`** — provisions Key Vault entries + Function infrastructure (if publisher.py runs in a Function App; Phase 1 confirms)
- **`sr-ops-tools`** — sibling Python operational layer; potentially shares GHL helpers
- **`vp-cms` / `Product-SecondRing`** — design specs for Vulcan + Daedalus may live in sibling repos; Phase 0 doesn't resolve

---

## Phase 1 Extraction Plan

The codebase has 9 logical components; using **split-file layout** with **6 passes**:

| Pass | Title | Inputs | Approx LOC | Notes |
|------|-------|--------|----------:|-------|
| 01 | Publisher Core Engine | `publisher/{publisher,models,retry,state,__init__}.py` | ~1,438 | The biggest pass. publisher.py (605 LOC) is the orchestrator; models.py + retry.py + state.py are the supporting primitives. Map AC↔code references throughout. |
| 02 | Platform Adapters | `publisher/adapters/*.py` (8 files: base + 6 platforms + ghl + __init__) | ~722 | Adapter pattern. Compare each platform's auth, post-shape, and error handling. Resolve the GHL-as-publishing-channel-vs-platform distinction. |
| 03 | Operator Scripts | `scripts/{ghl_social,validate-brand,validate-post}.py` | ~858 | 3 scripts. validate-* are CI gates; ghl_social.py is operator-only. Pass 03 should resolve `templates/` and `campaigns/` empty-dir questions. |
| 04 | Schema + Brand + Calendar Content | `schemas/post.schema.yaml`, `brands/<brand>/brand.yaml` (×2), `brands/<brand>/calendar/2026/04/*.md` (×4), `campaigns/spring-launch-2026/`, `templates/` | n/a (YAML + markdown) | The declarative surface. Pass 04 documents the schema authoritatively + the 4 actual posts at snapshot + the empty placeholder dirs. |
| 05 | Test Suite | `tests/{test_ghl_adapter,test_publisher_ghl_mode}.py` + `__init__.py` | ~942 | The most rigorous test surface in any VP repo we've reverse-spec'd. Map test scenarios to ACs (AC1-AC14). |
| 06 | Docs + Workflows + Build/CI | All 6 docs in `docs/`, `README.md`, 3 workflows in `.github/workflows/`, `.github/dependabot.yml`, `publisher/requirements.txt` | n/a | The runbook + automation surface. Pass 06 should resolve the AC list (canonicalize from `AC_VERIFICATION_SUMMARY.md`) and document the 3 workflow triggers + their AC references. |

**Cross-cutting concerns** to expect Phase 1.5 to surface (predicted):
- **AC-mapping pattern** — code comments reference AC1-AC14. Phase 1.5 should produce a master AC table.
- **GHL API client pattern** — same Bearer + version-2021-07-28 as RP/sr-ops-tools (cross-spec C7 marker)
- **Key Vault secret-name pattern** — brand.yaml references KV secret names; cross-spec to sr-azure-infra
- **Per-platform adapter consistency** — base.py interface; do all 6 platform adapters honor it?
- **Pydantic-validation pattern** — schema + models likely well-aligned
- **Retry policy pattern** — `publisher/retry.py` is a dedicated 276-LOC primitive; document its semantics
- **State directory pattern** — `.state/rate_limits/` per brand; document the rate-limit primitive
- **Two-gate workflow pattern** — distinctive; document the GitHub gate ↔ GHL gate handoff

---

## Out of Scope

- **GoHighLevel API internals** — black-box dependency
- **Facebook / Instagram / LinkedIn / X / GBP API internals** — black-box
- **Telegram Bot API internals** — black-box
- **HeyGen** — out-of-phase (Phase 2 deferred)
- **Azure Key Vault internals** — provisioned in sr-azure-infra
- **Vulcan + Daedalus design specs** — referenced but live in cross-repo issue tracker, not this repo
- **Riley's authoring process** — Riley is the author; this repo is the publisher. The author's tooling (e.g., copywriting prompts, brand-voice guides) lives in `Product-SecondRing` or similar
- **`Core_Business#222`** — parent strategic issue, out of scope
- **`.pytest_cache/`** — build artifact (verify gitignore in Pass 06)

---

## Unknowns / Ambiguities

1. **`templates/` and `campaigns/spring-launch-2026/` are empty** at snapshot (just `.gitkeep`). Are they intentional placeholders for Phase 2, or evidence that templates/campaigns features were planned but not implemented? Pass 04 + Pass 06 should resolve.

2. **Telegram notification implementation** — README cites it; not visible in file listing. Pass 01 should grep for `telegram` / `bot` in publisher.py.

3. **`xurl config JSON` for X (Twitter)** — brand.yaml notes `kv-secondring-x-config` is "xurl config JSON." `xurl` is a CLI tool from Twitter; the publisher likely shells out to it. Pass 02 (X adapter) should confirm.

4. **GHL adapter as publishing channel** — `publisher/adapters/ghl.py` is the channel that creates DRAFTS in GHL; the 5 platform adapters (facebook/linkedin/gbp/x/instagram) may be unused at runtime in Phase 1, since GHL handles the actual platform publishing. Pass 02 must resolve which adapters are live in Phase 1 vs Phase 2.

5. **AC list canonical source** — code comments reference AC1-AC14; `docs/AC_VERIFICATION_SUMMARY.md` likely lists them. Pass 06 should canonicalize.

6. **`auth-check.yml` is 71 lines** — Pass 06 should document what credentials are checked and how (presumably calling adapters' auth-probe methods or running `scripts/ghl_social.py --check`).

7. **Telegram bot credentials** — if Telegram is wired in, where do creds come from? Probably env vars in the workflow; Pass 06 should locate.

8. **GHL_LOCATION_ID `cUgvqrKmBM4sAZvMH1JS`** — visible in brand.yaml comment. Cross-ref to `sr-ops-tools` Pass 04 (which referenced the same `cUgvqrKmBM4sAZvMH1JS` for SR location). This is a hardcoded VP-internal reference; document and cross-spec to confirm consistency.

9. **`account_ids must be filled in before publishing goes live`** (per brand.yaml comment) — same launch-blocker pattern as sr-google-ads STATUS.md's "outstanding tasks." Pass 04 should document which brand.yaml fields are unfilled.

10. **`status: ready` field semantics** — README cites `status: ready` as the gate-1 approval marker, set by Dave. The schema (Pass 04) should define this enum's full state machine (draft → ready → published?).

11. **Vulcan vs Daedalus spec scope** — Vulcan is publisher architecture (issue #2 in this repo); Daedalus is GHL integration (issue ?). Pass 02 + Pass 06 should disambiguate when each applies.

12. **Phase 2 indicators** — `avatar_id: null` (HeyGen), empty `templates/`, empty `campaigns/`. These are forward-pointers but Phase 1 records them as observed-empty.
