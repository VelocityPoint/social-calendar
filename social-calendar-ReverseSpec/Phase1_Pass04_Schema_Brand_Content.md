# Phase 1 — Pass 04 — Schema + Brand + Calendar Content

**Snapshot:** `67d061c`
**Files in scope (9):** `schemas/post.schema.yaml`, 2× `brand.yaml`, 4× calendar markdown posts, 2× `.gitkeep` placeholders.

---

## Post Schema

**File:** `schemas/post.schema.yaml`
**Schema version:** `"1.1"` (line 5).
**Header comment (lines 1–3):** "Used by scripts/validate-post.py (AC1) and validate-pr.yml workflow / Every field is documented with type, required/optional, and constraints".

### Field inventory — 14 top-level fields under `fields:`

| # | Field | Type | Req? | Constraint | Description (verbatim, abbrev.) | AC ref |
|---|-------|------|------|------------|---------------------------------|--------|
| 1 | `id` | string | required | pattern `^\d{4}-\d{2}-\d{2}-.+$` | "Unique post identifier. Format: YYYY-MM-DD-<slug>." | (header AC1) |
| 2 | `publish_at` | string | required | pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$` | ISO 8601 datetime with timezone offset. | **AC5** ("Bare datetime (no offset) fails validation per AC5") |
| 3 | `platforms` | list[string] | required | enum `[facebook, linkedin, gbp, x, instagram]`; `min_items: 1` | "Non-empty list of target platforms." | — |
| 4 | `status` | string | required | enum (7 values, see below) | "Current lifecycle status of the post." | AC7 (failed→issue), AC-OQ6 (deferred) |
| 5 | `brand` | string | required | pattern `^[a-z][a-z0-9-]*$` | "Brand slug matching a directory under brands/." | — |
| 6 | `author` | string | required | enum `[dave, velocitypoint]` | "Author identifier mapping to a GHL social account via brand.yaml → ghl.accounts." | — |
| 7 | `account_id` | string | optional | — | "GHL account ID override. If omitted, resolved from brand.yaml ghl.accounts[author][platform]." | — |
| 8 | `ghl_mode` | boolean | optional | default `true` | "When true (default), post is published via the GHL Social Planner adapter." | — |
| 9 | `campaign` | string | optional | — | "Campaign slug from campaigns/ directory." | — |
| 10 | `tags` | list[string] | optional | — | "Content tags for filtering and reporting." | — |
| 11 | `published_at` | string | optional | pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` (UTC `Z` only) | "ISO 8601 UTC timestamp written by publisher after successful publish." | **AC6** (header comment line 100) |
| 12 | `ghl_post_id` | string | optional | — | "GHL Social Planner post ID written by publisher after successful createPost call." | — |
| 13 | `post_ids` | object | optional | — | "Platform post IDs written by publisher. One key per published platform." | — |
| 14 | `error` | string | optional | — | "Last error message if status=failed. Written by publisher." | — |

Plus a 15th nested-object field:

| 15 | `creative` | list of objects | optional | sub-fields below | "Optional list of creative assets (images, videos)." | — |

`creative[*]` sub-fields: `type` (required, enum `[image, video, heygen]`), `path` (optional, "Relative path to asset file under brands/<brand>/assets/"), `url` (optional), `video_url` (optional, "Azure Blob URL for rendered video. Written by publisher (Phase 2)"), `platforms` (optional, enum `[facebook, linkedin, gbp, x, instagram]`).

**Total field count:** **15** (14 top-level + nested `creative` object).

### Status enum + state machine

Enum (line 36): `[draft, ready, scheduled, published, failed, deferred, video-pending]` — **7 values**.

Per-state semantics (verbatim from `notes:` lines 37–44):
- `draft` — "work-in-progress, not yet ready for publishing gate"
- `ready` — "merged to main and eligible for the publisher to pick up"
- `scheduled` — "createPost succeeded; GHL holds post until publish_at"
- `published` — "GHL confirmed the post is live on all targeted platforms"
- `failed` — "all retries exhausted; error field populated; GitHub issue created per AC7"
- `deferred` — "rate-limited; no issue; retried next run per AC-OQ6"
- `video-pending` — "HeyGen not complete (Phase 2)"

Lifecycle (line 45, verbatim): `draft → ready → scheduled → published | failed`. (Phase 0 Unknown #10 — workflow doc said `draft → ready → ghl-pending → published`; **`ghl-pending` is NOT a valid enum value**; the schema uses `scheduled` instead. Workflow doc terminology is stale.)

### Per-platform character limits (AC11 candidate)

`platform_limits:` block (lines 168–175):
```
linkedin:  3000
x:          280
gbp:       1500
facebook: 63000
instagram: 2200
```
Source comment (line 169): "Source: GHL Social Planner docs + platform native limits".

### Copy section headers (AC11, AC-OQ3)

`copy_section_headers:` block (lines 177–183):
```
linkedin:  "LinkedIn Version"
facebook:  "Facebook Version"
x:         "X Version"
gbp:       "Google Business Profile Version"
instagram: "Instagram Version"
```
Comment (line 177): "Copy section headers (extracted by publisher per AC11, OQ3)".

### `additionalProperties` policy

**UNKNOWN — not declared.** This file is a hand-rolled YAML schema description (not JSON Schema), and there is no explicit `additionalProperties` key. Whether unknown keys in a post markdown are allowed/rejected is determined by `scripts/validate-post.py` (Pass 03 surface), not by this file.

### `ghl_mode_notes` block (lines 186–191) — verbatim

- "author must resolve in brand.yaml → ghl.accounts[author][platform]"
- "publish_at must include timezone offset (ISO 8601 with +HH:MM or Z)"
- "status must be 'ready' for publisher to pick up the post"
- "account_id is optional override; normally resolved from brand config"
- "ghl_post_id is set by publisher after successful createPost — do not set manually"

### `author` enum vs actual usage — discrepancy

Schema enum is `[dave, velocitypoint]` (line 59). The lone secondring post (`2026-04-01-never-miss-a-call.md` line 12) sets `author: davelawler-vp` — **not in the enum**. That post has `ghl_mode: false` (line 13), and the schema notes (line 62) say "In GHL mode (ghl_mode: true), this field is REQUIRED and must resolve to a GHL account" — implying enum enforcement may be GHL-mode-conditional, but the schema declaration itself does not condition the enum on `ghl_mode`. Treat as observed inconsistency between schema and content. (See Unknowns.)

---

## Brand Configs

### `brands/secondring/brand.yaml`

Top-level keys (7): `brand_name`, `avatar_id`, `credentials`, `ghl`, `cadence`, `pillars`, `voice`.

- `brand_name: "Second Ring"` (line 7).
- `avatar_id: null` (line 8) — comment: "HeyGen avatar ID (Phase 2 — set when HeyGen integration is ready)". Phase 2 placeholder confirmed.
- File header comment (lines 2–6): "Ref: AC8 (brand config schema), AC14 (Instagram shares Facebook credential) / IMPORTANT: credentials values are Key Vault secret NAMES, not raw tokens. The publisher resolves these names against Azure Key Vault or environment variables."

**`credentials:` (lines 12–17):** 5 platform keys, all KV-secret-name values.

| Platform   | KV secret name                      | Notes                              |
|------------|-------------------------------------|------------------------------------|
| facebook   | `kv-secondring-facebook-token`      | —                                  |
| instagram  | `kv-secondring-facebook-token`      | **Shared with facebook (AC14)** — comment line 14 verbatim: "Shared Meta app creds (AC14)" |
| linkedin   | `kv-secondring-linkedin-token`      | —                                  |
| gbp        | `kv-secondring-gbp-credentials`     | —                                  |
| x          | `kv-secondring-x-config`            | inline comment "xurl config JSON"  |

**`ghl:` block (lines 34–44):**
- `location_id: cUgvqrKmBM4sAZvMH1JS` (comment: `[SR] Sales production sub-account`).
- `accounts:` — two authors: `dave` (4 platforms: linkedin, facebook, instagram, google_business) and `velocitypoint` (2 platforms: linkedin, facebook).
- **Every `account_id` value is the literal placeholder string `"<account_id>"`** — count = **6** (4 under `dave` + 2 under `velocitypoint`).
- Header comment (lines 19–33) explicitly: "account_ids must be filled in before publishing goes live" + discovery instructions citing `scripts/ghl_social_list_accounts.py` (script that **does not exist** at snapshot per Phase 0 Review Note 2; current consolidated CLI is `scripts/ghl_social.py`).

**Launch blockers (Phase 0 Unknown #9):** **6 unfilled `<account_id>` placeholders in secondring** — all `ghl.accounts[author][platform]` slots.

**`cadence:` block (lines 47–78):** 5 platforms (linkedin, facebook, instagram, x, gbp), each with `posts_per_week`, `preferred_times` (list of HH:MM strings), `timezone` (all `America/Los_Angeles`).

**`pillars:` (lines 81–87):** 6 content topics.

**`voice:` (lines 90–97):** `tone`, `avoid` (list of 3), `cta_style`. Comment (line 89): "Brand voice guidelines (used by content generation in Phase 2)".

### `brands/velocitypoint/brand.yaml`

Top-level keys (5): `brand_name`, `avatar_id`, `credentials`, `cadence`, `pillars`. **No `ghl:` block. No `voice:` block.**

- `brand_name: "Velocity Point"` (line 4).
- `avatar_id: null` (line 5) — Phase 2 placeholder.
- Header comment (line 2): "Ref: AC8, AC16 (multi-brand)".

**`credentials:` (lines 7–9):** **2 platform keys** — `linkedin: kv-velocitypoint-linkedin-token`, `x: kv-velocitypoint-x-config`. No facebook, instagram, or gbp entries.

**`cadence:`:** 2 platforms (linkedin, x). All `America/Los_Angeles`.

**`pillars:`:** 4 topics.

**Launch blockers (account_ids):** **0 unfilled placeholders** — but only because **no `ghl:` block exists at all**. Per the secondring header comment line 32–33: "Posts for non-GHL brands omit this block entirely — missing ghl: is valid and non-GHL posts pass validation without it." Yet **all 3 velocitypoint posts at snapshot have `ghl_mode: true`** — implying VP posts targeting GHL would fail account resolution because there is no `ghl.accounts` map. **Inconsistency** (see Unknowns).

### Brand-config differences (secondring vs velocitypoint)

| Aspect                  | secondring                        | velocitypoint                  |
|-------------------------|-----------------------------------|--------------------------------|
| Top-level keys          | 7                                 | 5                              |
| `credentials` platforms | 5 (fb, ig, li, gbp, x)            | 2 (li, x)                      |
| `ghl:` block            | Present, 6 unfilled `<account_id>` placeholders | **Absent**       |
| `cadence:` platforms    | 5                                 | 2                              |
| `pillars:` count        | 6                                 | 4                              |
| `voice:` block          | Present (tone, avoid, cta_style)  | **Absent**                     |
| Instagram=Facebook KV share (AC14) | Yes (`kv-secondring-facebook-token` reused) | N/A (no IG, no FB) |
| `avatar_id`             | `null` (Phase 2)                  | `null` (Phase 2)               |
| AC refs in header       | AC8, AC14                         | AC8, AC16                      |

---

## Calendar Posts

### Frontmatter field usage (pattern across 4 posts)

| Field         | SR 04-01 | VP 04-07 | VP 04-09 | VP 04-11 |
|---------------|:--------:|:--------:|:--------:|:--------:|
| `id`          | yes      | yes      | yes      | yes      |
| `publish_at`  | yes      | yes      | yes      | yes      |
| `platforms`   | yes (5)  | yes (1)  | yes (1)  | yes (1)  |
| `status`      | `scheduled` | `ready` | `ready` | `ready` |
| `brand`       | secondring | velocitypoint | velocitypoint | velocitypoint |
| `author`      | `davelawler-vp` (off-enum) | `dave` | `dave` | `dave` |
| `ghl_mode`    | `false`  | `true`   | `true`   | `true`   |
| `tags`        | yes (3)  | yes (4)  | yes (4)  | yes (4)  |
| `campaign`    | —        | `q2-2026-thought-leadership` | `q2-2026-second-ring-outreach` | `q2-2026-second-ring-outreach` |
| `creative`    | —        | —        | —        | yes (1 image, instagram-targeted) |
| `account_id`/`published_at`/`ghl_post_id`/`post_ids`/`error` | — | — | — | — |

**Status field at snapshot:** SR post = `scheduled` (already past Gate 1 + GHL createPost). All 3 VP posts = `ready` (past Gate 1, awaiting publisher pickup).

**Platforms targeted (union across the 4 posts):** linkedin, facebook, x, gbp, instagram — **all 5 schema platforms appear**, but only via the SR multi-platform post. The 3 VP posts each target exactly one platform (linkedin, facebook, instagram respectively).

**publish_at timestamps:**
- SR `2026-04-01-never-miss-a-call`: `2026-04-01T09:00:00-07:00` (PDT)
- VP `2026-04-07-linkedin-ai-for-service-business`: `2026-04-07T09:00:00-07:00`
- VP `2026-04-09-facebook-never-miss-a-call`: `2026-04-09T10:00:00-07:00`
- VP `2026-04-11-instagram-ai-receptionist`: `2026-04-11T10:00:00-07:00`

All 4 posts use **`-07:00`** offset (Pacific Daylight Time / America/Los_Angeles), matching the cadence-block timezone in both brand.yaml files.

### Body — first 3 lines + char count per post

**SR `2026-04-01-never-miss-a-call.md`** (5 platforms — has all 5 copy sections "LinkedIn Version", "Facebook Version", "X Version", "Google Business Profile Version", "Instagram Version" matching `copy_section_headers` exactly):

First 3 lines after frontmatter (lines 20–22):
```
# LinkedIn Version

Every missed call is a missed customer.
```
Body length (lines 19–69, post-frontmatter): **~2,160 characters** across all 5 sections combined (file shown ends at line 69, no terminating newline shown). LinkedIn section ~512 chars; Facebook ~520; X ~221; GBP ~310; Instagram ~244 — all within `platform_limits`.

**VP `2026-04-07-linkedin-ai-for-service-business.md`** (linkedin only, has only "# LinkedIn Version"):

First 3 lines after frontmatter (lines 18–20):
```
# LinkedIn Version

Most small service businesses are leaving money on the table — not because of bad service, but because of bad infrastructure.
```
Body (lines 17–35): **~1,068 characters**. Within linkedin limit (3000).

**VP `2026-04-09-facebook-never-miss-a-call.md`** (facebook only, has only "# Facebook Version"):

First 3 lines after frontmatter (lines 18–20):
```
# Facebook Version

Quick question for any service business owner reading this:
```
Body (lines 17–41): **~1,332 characters**. Within facebook limit (63000).

**VP `2026-04-11-instagram-ai-receptionist.md`** (instagram only, has "# Instagram Version" + hashtags):

First 3 lines after frontmatter (lines 23–25):
```
# Instagram Version

The call you missed while you were on a job just became your competitor's customer.
```
Body (lines 22–31): **~340 characters** including hashtag line. Within instagram limit (2200).

### Per-platform copy-header pattern

Posts with **multiple `platforms:`** include one `# <Platform> Version` heading per platform (SR post: 5 sections). Single-platform VP posts have a single matching heading. Headings match `schemas/post.schema.yaml` `copy_section_headers` block verbatim. Consistent with AC11 / AC-OQ3 extraction-by-header.

---

## Empty Placeholders

### `templates/.gitkeep`

- File size: **0 bytes** (verified via `wc -c`). Read tool reports "the file has 1 lines" but the file content is empty (single trailing or no newline; 0 bytes of content).
- README.md: **no mention** of `templates/` (verified via Grep — "No matches found" for pattern `templates|campaigns/spring-launch`).
- Phase 0 Review Note 6 confirms: "both `templates/.gitkeep` and `campaigns/spring-launch-2026/.gitkeep` are 1-line empty files".
- **Intent: UNKNOWN.** No README explanation. Phase 0 Unknown #1 ("placeholders for what?") is **NOT resolved by this file or README**. The directory exists as a forward-pointer but is not referenced anywhere in code, schema, or docs at snapshot.

### `campaigns/spring-launch-2026/.gitkeep`

- File size: **0 bytes**.
- Directory name suggests intent ("spring-launch-2026") aligned with the `campaign:` schema field (line 88–91), but **no post at snapshot references this campaign slug**. The 3 VP posts use campaigns `q2-2026-thought-leadership` and `q2-2026-second-ring-outreach`; none use `spring-launch-2026`.
- README.md: **no mention** (per Grep above).
- **Intent: UNKNOWN.** Same as `templates/`.

---

## Cross-Cutting Patterns

1. **Schema field convention** — hand-rolled YAML schema (NOT JSON Schema). Each field declared with `type:`, `required:`, optional `pattern:` / `enum:` / `min_items:` / `default:`, plus `description:` and free-form `notes:` list. Publisher-written fields (`published_at`, `ghl_post_id`, `post_ids`, `error`, `creative[*].video_url`) are flagged in their `notes:` with "Set by publisher — do not set manually". Cross-referenced AC numbers (AC1, AC5, AC6, AC7, AC11, AC14, AC-OQ3, AC-OQ6) appear in field notes. Connects to **CP-8 (Schema Field vs Code Validator Coverage Mismatch)** — see Phase1_Common.md.

2. **KV-secret-name pattern** (cross-spec to `sr-azure-infra`) — values in `credentials:` block follow `kv-<brand>-<platform>-{token|credentials|config}` naming. Forms observed:
   - `kv-secondring-facebook-token` (used twice — AC14 reuse for instagram)
   - `kv-secondring-linkedin-token`, `kv-velocitypoint-linkedin-token`
   - `kv-secondring-gbp-credentials` (note: `-credentials` suffix, not `-token`)
   - `kv-secondring-x-config`, `kv-velocitypoint-x-config` (`-config` suffix; comment says "xurl config JSON" — Phase 0 Unknown #3, deferred to Pass 02)
   Pattern: 3-segment `kv-<brand>-<platform>` prefix + suffix that reflects credential shape (`token` for OAuth tokens, `credentials` for richer JSON, `config` for xurl/x config blob).

3. **Calendar markdown frontmatter pattern** (4 posts) — YAML frontmatter delimited by `---` on lines 1 and N. Required-by-schema fields (`id`, `publish_at`, `platforms`, `status`, `brand`, `author`) present in all 4. `ghl_mode` explicitly set in all 4 (3× `true`, 1× `false`); schema default is `true` so explicit `false` is the only one that materially overrides. Body uses `# <Platform> Version` headings matching `copy_section_headers` exactly — one heading per `platforms:` entry. `creative:` field with relative path under `assets/` used only on the IG post (1/4).

4. **Per-platform character-limit convention** — single source-of-truth claim in `schemas/post.schema.yaml` `platform_limits:` block. Limits range from 280 (X) to 63000 (Facebook). All 4 observed posts comply. Header comment cites "GHL Social Planner docs + platform native limits". This is the AC11-tagged surface enforced by `scripts/validate-post.py` (Pass 03). Connects to **CP-9 (Hardcoded Constants & Conventions)** — see Phase1_Common.md (char limits triplicated across schema, validate-post.py, deprecated adapters).

5. **Phase 2 forward-pointer pattern.** Follows Common Pattern: **CP-10 (Empty Phase-2 / Forward-Pointer Placeholders)** — see Phase1_Common.md. Pass-04-specific evidence: `avatar_id: null` in both brand.yaml files; schema `creative.type` enum includes `heygen`; schema `creative.video_url` is "Written by publisher (Phase 2)"; schema `status` enum includes `video-pending` ("HeyGen not complete (Phase 2)"). The empty `templates/` and `campaigns/spring-launch-2026/` are unlabeled forward-pointers (no in-repo description). 6 unfilled `<account_id>` placeholders in secondring + entirely-absent `ghl:` block in velocitypoint despite VP posts being `ghl_mode: true`.

6. **Two-namespace AC referencing inside this file-scope.** Follows Common Pattern: **CP-1 (AC Namespace Divergence)** — see Phase1_Common.md. Pass-04-specific evidence: schema cites AC1 (header), AC5 (publish_at), AC6 (published_at), AC7 (failed→issue), AC11 (copy headers), AC-OQ3, AC-OQ6 (deferred). brand.yaml cites AC8, AC14, AC16. None of these appear in `docs/AC_VERIFICATION_SUMMARY.md` (which documents AC1–AC10 only).

7. **Status enum drift inside the schema file.** Follows Common Pattern: **CP-3 (Status-Lifecycle Drift Cluster)** — see Phase1_Common.md. Pass-04-specific evidence: schema enum (line 36) `[draft, ready, scheduled, published, failed, deferred, video-pending]` (7 values, **no `ghl-pending`**). Lifecycle declared as `draft → ready → scheduled → published | failed`. Workflow doc cites `ghl-pending`; schema does not — the schema would REJECT the value the publisher writes.

8. **Stale brand.yaml comment.** Follows Common Pattern: **CP-2 (Stale-Doc Script-Path References)** — see Phase1_Common.md. Pass-04-specific evidence: `brands/secondring/brand.yaml` lines 24–25 instruct operator to run `scripts/ghl_social_list_accounts.py` (consolidated into `ghl_social.py accounts`).

---

## Unknowns / Ambiguities

1. **`templates/` intent** (Phase 0 Unknown #1) — **NOT resolved**. No README mention, no doc reference, no code reference. File is a 0-byte placeholder. Carry to Pass 06.

2. **`campaigns/spring-launch-2026/` intent** — **NOT resolved**. No post at snapshot references this campaign slug; the 3 VP posts use `q2-2026-*` slugs instead. Could be (a) a stale placeholder superseded by `q2-2026-*`, (b) a forward-pointer for a not-yet-authored campaign, (c) a deliberate empty directory required by some script. UNKNOWN. Pass 06.

3. **`schemas/post.schema.yaml` `additionalProperties` policy** — not declared in this file. Whether unknown frontmatter keys are accepted/rejected is determined by `scripts/validate-post.py` (Pass 03 surface), not visible here.

4. **`author` enum vs SR post `davelawler-vp`** — schema enum `[dave, velocitypoint]` (line 59) does not include `davelawler-vp`, yet `2026-04-01-never-miss-a-call.md` line 12 sets `author: davelawler-vp`. That post has `ghl_mode: false` (line 13). Schema notes (line 62) say enum applies "In GHL mode (ghl_mode: true)" but the enum itself is declared unconditionally. Either (a) `validate-post.py` softens the enum check when `ghl_mode: false`, or (b) the SR post would fail validation today. UNKNOWN at this layer; Pass 03 (`validate-post.py`) resolves.

5. **`status: scheduled` on SR post with `ghl_mode: false`** — schema notes say `scheduled` means "createPost succeeded; GHL holds post until publish_at" but this post is `ghl_mode: false` (legacy direct-adapter path). Whether `scheduled` is meaningful in non-GHL mode, or this post was hand-edited to `scheduled` by an operator pre-Phase-1, is UNKNOWN. (Phase 0 noted SR post is the one originally targeting all 5 deprecated adapters.)

6. **velocitypoint `ghl_mode: true` posts with no `ghl:` block in brand.yaml** — all 3 VP posts at snapshot declare `ghl_mode: true`, but `brands/velocitypoint/brand.yaml` has no `ghl:` block at all (no `location_id`, no `accounts:` map). Per secondring brand.yaml comment (lines 32–33), missing `ghl:` is "valid" only for "non-GHL posts" — but VP's posts are explicitly GHL-mode. Either (a) VP posts will fail account resolution at publish time, (b) brand.yaml is incomplete and adding `ghl:` is a launch task, or (c) the publisher has a fallback for missing `ghl:` blocks. **Likely launch blocker for VP posts.** Pass 01 (publisher) resolves.

7. **`scripts/ghl_social_list_accounts.py` referenced in secondring brand.yaml comment but does not exist** — Phase 0 Review Note 2. Comment lines 24–25 instruct the operator to run a script that was consolidated into `scripts/ghl_social.py` (which has accounts-list as a subcommand). Stale comment. Should be flagged in Pass 06 hardening.

8. **`status: ghl-pending` (workflow doc) vs `status: scheduled` (schema)** — Phase 0 Unknown #10. Schema enum has no `ghl-pending` value; the value is `scheduled`. Workflow doc terminology is stale relative to schema. Pass 06.

9. **Schema vs models.py drift** — Phase 0 Component Map says `publisher/models.py` "mirrors schema structure (cited in models docstring)". This pass cannot verify drift between the schema's 14 top-level fields + 5 enums vs the pydantic model definitions. Carry to Pass 01.

10. **`account_ids` launch-blocker count canonicalization** — secondring has 6 unfilled `<account_id>` placeholders (4 dave + 2 velocitypoint). velocitypoint has 0 placeholders but only because the `ghl:` block is entirely absent — which itself blocks GHL publishing for VP. The "true" launch-blocker count is therefore **6 + (full `ghl:` block missing for VP)** — an inconsistent shape across brands.
