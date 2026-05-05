# Phase 2 — Intent Inference

**Snapshot:** `67d061c` (2026-04-26)
**Method:** Inference from Phase 1 + Phase 1.5 evidence. Every inferred intent is labeled **High / Medium / Low confidence**. No fix proposals; no rewrite-as-spec; ambiguity highlighted, not resolved.
**Authors visible in artifacts:** Riley (post author), Dave (approver / repo owner), Bob (agent label on auth-check failures + Forge doc author), Tara (referenced for cross-repo wiring per Phase 0 / sr-google-ads / Daedalus).

---

## Group A — Two-Gate Publishing Workflow

**The headline feature.** Gate 1 = GitHub PR (copy approval). Gate 2 = GHL Social Planner (visual approval). Posts always land in GHL as drafts; never auto-fire.

### A.1 Intended purpose (High confidence)

The two-gate workflow exists to put **two independent human approvals** in the publish path: a textual review (PR diff in GitHub) followed by a visual review (rendered preview in GHL Social Planner). Evidence:

- README owns the framing (lines 11–26, "How It Works — Two Gates"); SOCIAL_CALENDAR_WORKFLOW formalizes it across 5 stages.
- `GHLAdapter.publish` hardcodes `"status": "draft"` in the API payload (`ghl.py:120`) with the inline comment "Gate 2: land as draft for Dave's manual approval in GHL UI." No flag, env var, or test path overrides this.
- `test_publishes_ready_post_immediate_as_draft` asserts that **even past-due `publish_at`** posts go to GHL as drafts. This is the strongest signal that "no auto-fire" is an explicit design invariant, not an emergent property.
- Status writeback is `ghl-pending` (success), never `published`. The state machine deliberately stops short of "fired."

### A.2 Domain interpretation (High confidence)

Two-gate is a **risk-control** pattern. Social media posts are public, irreversible, brand-affecting, and frequent. A single approval surface (PR alone, or GHL alone) would either:

- gate textual brand-voice but not the rendered image/cropping/preview behavior (PR-only); or
- gate the visual but lose the markdown-diff history and require an operator to copy/paste copy into a UI (GHL-only).

By splitting the gates, the workflow gives Dave two cheap "stop" buttons positioned at the two failure modes that matter for organic social: (1) wrong-words (textual), (2) wrong-look (visual/rendering/scheduling). Riley owns drafting; Dave owns both approvals. The README's framing — "Merge = Publish Approval" (DEVELOPER_GUIDE §1) — explicitly names merge as approval, not deployment.

### A.3 Why this repo gets two-gate when other VP repos don't (High confidence)

The cross-repo comparison is informative:

- **sr-google-ads**: paid-ads conversion-import. Outputs are server-to-server, **not user-visible**. No need for visual preview.
- **vp-cms**: copy lives in markdown, served via static site; review IS the PR. No second surface to approve against.
- **sr-ops-tools**: operator-actuated, not scheduled-publish. Operator IS the gate.

social-calendar is unique because the artifact (a social post) has both a textual surface AND a rendered/scheduled surface that lives in a third-party UI. **Intent: this repo gets two-gate because the artifact has two distinct approval surfaces** — the same post needs both copy review (markdown diff is the right tool) and visual review (GHL preview is the right tool). No single review tool covers both.

This also explains why the gate count is **two and not three**: there's no third surface (there's no "live published" reviewable surface — once it fires, it's irreversible).

### A.4 Assumptions

- **Dave is always available** to perform Gate 2. There's no escalation path, no second approver, no auto-approve-after-N-hours. (Medium confidence in this being intentional vs unconsidered — see Missing Intent.)
- **GHL preserves the draft indefinitely** until Dave acts. This is a GHL-platform assumption (out of scope for this repo).
- **`publish_at` is advisory at Gate 2.** The publisher writes `scheduledAt` to GHL even though the post is a draft. Gate 2 may schedule for the originally-intended time or override. The AC11 character-limit checking happens at Gate 1 only; nothing re-validates after Dave clicks Schedule (consistent — Gate 2 is visual-only).

### A.5 Missing intent

- **No documented Dave-unavailable path.** What happens if Dave is on vacation and a time-sensitive post is queued? The repo is silent.
- **No test of Gate 1 enforcement at the workflow level** (validate-pr.yml's required-check status). The gating works because branch protection is configured externally; intent is to rely on GitHub's required-check mechanism but this isn't owned by code in this repo.
- **No "abort Gate 2" path.** If Dave decides not to publish, he deletes the GHL draft. The publisher will see no `published_at` and never write back. There's no `cancelled` status in the schema — the post stays at `ghl-pending` forever. Whether this is intentional (it's just a manual-cleanup case) or an oversight is unclear.

### A.6 Inconsistencies (cross-ref CP-4)

- **WORKFLOW §10.1 says "Gate 2 not yet implemented" while `ghl.py:120` hardcodes draft mode AND tests assert it.** The doc was written before the code change and not updated. This is the cleanest case of "doc lags code" in this repo.
- **README's Telegram framing (Gate-bridge notification: "X posts pending approval") doesn't match retry.py's failure-only Telegram firing.** Gate-bridging in code only happens through the `[skip ci]` commit-back, which is silent for the operator unless Telegram is wired — and at this snapshot, Telegram only fires on failure. (Cross-ref CP-5, Group E.)

---

## Group B — AC-Driven Spec Discipline

This is the most spec-anchored repo we've reverse-spec'd: nearly every script, model, and workflow YAML carries `Ref: AC<N>` annotations. But CP-1 reveals that AC-numbering is unstable across the repo's documentation surface vs its code/comment surface.

### B.1 Intended purpose (High confidence on the convention; Medium on the namespace structure)

The AC-tagging convention is intentional: every code module advertises which acceptance criteria it claims to satisfy, both for review traceability and for a future spec-coverage audit. Evidence:

- Every publisher core module's docstring leads with `Ref: AC<list>`.
- Each adapter file carries module-level AC refs (CC-PA6).
- `validate-pr.yml`, `auth-check.yml`, `publish.yml` headers cite the ACs each workflow gates.
- `AC_VERIFICATION_SUMMARY.md` is a verification audit by AC# — explicit traceability artifact.

The intent is "every behavior has a spec anchor; you can grep for `AC7` and find every implementation site."

### B.2 The namespace divergence as an intent question (High confidence on the diagnosis; Low on the ownership intent)

CP-1 establishes that AC1–AC10 (canonical, per `AC_VERIFICATION_SUMMARY.md`, vintage 2026-03-27, issue-#2 / "Vulcan") and the broader namespace AC11–AC16 + AC-OQ2/3/4/6 (only in code/workflow YAML) **are not the same list with extensions** — they are two specs whose AC numbers happen to overlap (AC1, AC2, AC5, AC6, AC7, AC8 mean different things in each).

**Inference (Medium confidence):** This was almost certainly **not intentional collision**. Two separate work-streams ("Vulcan" — issue #2, GHL adapter integration; "Daedalus" — GHL Social Planner integration / draft-mode workflow) each authored their own AC list, each starting at AC1, neither aware that the other had an AC1. The Vulcan list got documented (in `AC_VERIFICATION_SUMMARY.md`); the Daedalus list lives only in code comments and the WORKFLOW doc's `<TBD>` issue placeholders.

**Why this matters for intent (High confidence):** the convention "every behavior has a spec anchor" is silently broken. Grepping for `AC7` returns:
- `AC_VERIFICATION_SUMMARY.md` AC7 = "GHL adapter routes through GHL API"
- `publish.yml` AC7 = "GHL adapter integration / failure issues"
- `OPERATIONAL_RUNBOOK.md` AC7 = "GitHub issue creation"

Three meanings, partially overlapping. The convention was meant to give traceability; the divergence undermines it.

**Alternative hypothesis (Low confidence):** the broader namespace was intentional — the team treated AC# as a per-issue counter, and "AC7 (Vulcan)" was meant to be read as "AC7-of-issue-#2" while "AC7 (Daedalus)" was meant as "AC7-of-issue-Daedalus." If this was the intent, it was never documented, and the disambiguation prefix never made it into any cite.

### B.3 The missing AC12 wiring (Medium confidence)

`validate-pr.yml`'s header cites AC12 as "ensures only valid docs reach main" — but AC12 appears in no script in the repo. `state.py:is_committed_on_main` exists (which would be the obvious AC12 implementation), but it isn't tagged with AC12 anywhere.

**Inference:** AC12 was a planned check ("verify the post being published was actually committed to main, not a stray feature branch") that **was implemented** as `is_committed_on_main` but not tagged with the AC# at code-write time. The workflow-header cite is correct in intent — the workflow does block invalid docs from reaching main via Job 1+2 — but the granular code↔AC mapping was never closed. Alternative: AC12 is a stale ref to a check that was descoped. Evidence weakly favors the first reading (the code IS there in `state.py`).

### B.4 What the divergence reveals about how specs are tracked (High confidence)

Several signals about the spec process in this repo:

1. **Specs live outside the repo.** The Vulcan and Daedalus AC lists live in GitHub issue threads (#2 + a `<TBD>` issue), not in this repo's `docs/`. `AC_VERIFICATION_SUMMARY.md` is a one-time audit artifact, not the source of truth.
2. **Spec freezes don't propagate back.** When the broader namespace was authored (post-Vulcan, "Daedalus"-era), no one regenerated `AC_VERIFICATION_SUMMARY.md` to extend the AC list.
3. **Multi-author handoff (Bob → Riley → Dave) is the source of the drift.** All three docs with stale script references (AC summary, DEVELOPER_GUIDE, ARCHITECTURE) were authored by `Bob — Forge Documentation Phase`. README and WORKFLOW (touched by other authors / later) are current. **CP-2 maps to "doc-author-cluster–specific staleness" — Bob's batch never got refreshed.**
4. **`<TBD>` issue numbers in WORKFLOW §10** are signed by Bob, dated 2026-04-02 (post-Vulcan). The team writes specs with `<TBD>` placeholders intending to fill them later; that filling step is unreliable.

### B.5 Assumptions

- **Specs that aren't in `docs/` exist somewhere.** The broader namespace must be enumerable from issue #2 + Daedalus issue threads. Phase 1.5 cannot reach those.
- **AC numbers are stable per-spec, even though they collide cross-spec.** Within a single spec, AC5 always means the same thing.

### B.6 Missing intent

- **No "AC source-of-truth" file.** No `docs/AC_INDEX.md` that enumerates every AC across both namespaces.
- **No automated AC-coverage check.** `AC_VERIFICATION_SUMMARY.md` is hand-curated; nothing keeps it in sync with code refs. Test coverage of ACs is uneven (Pass 05 found AC2/AC6/AC7 covered; AC12/AC13/AC14/AC16/AC-OQ4/AC-OQ6 not covered anywhere observable).

### B.7 Inconsistencies

CP-1 enumerates them. The most material:
- AC8 means "raw-token detection" in `validate-brand.py` and "required fields, status, author/account resolution" in `validate-post.py`. **Same script-author intent, different actual rules.**
- AC11 cited only in code comments + workflow YAML, never enumerated in any doc.
- AC18 implied for the Gate 2 "draft" enforcement (per Pass 02 prompt) but never written anywhere.

---

## Group C — Adapter Architecture (active GHL + deprecated platforms)

The repo has **6 platform adapters**: GHL (active) + 5 deprecated (facebook, instagram, linkedin, gbp, x_twitter). All 6 honor `BaseAdapter`'s interface. The 5 deprecated remain runtime-live for `auth_check` purposes.

### C.1 Intended purpose (High confidence — the active surface; Medium — the deprecated surface)

**GHL adapter:** primary publishing channel (per README + Phase 0). One CRUD interface to all 5 platforms via GHL Social Planner.

**Deprecated adapters:** preserved specifically for the **weekly auth-check sweep**. Evidence:
- `auth-check.yml` injects `FACEBOOK_PAGE_ID`, `LINKEDIN_AUTHOR_URN`, `GBP_LOCATION_NAME`, `INSTAGRAM_USER_ID` env vars.
- `run_auth_check` (publisher.py:469-496) iterates `brand.credentials.__dict__` and instantiates adapters from `ADAPTER_REGISTRY`.
- `ADAPTER_REGISTRY` excludes GHL but includes all 5 deprecated platforms.

**Inference (Medium confidence):** The deprecated adapters' `auth_check` methods are intentionally preserved as a **credential-health early-warning system**. Even though publishing routes through GHL, the underlying OAuth tokens (Facebook page token, LinkedIn author URN, etc.) are still maintained in Key Vault. If they expire or get revoked, GHL stops posting silently. The weekly auth-check probes them directly so the failure surfaces in our own GitHub-issues queue, not as a silently-missing post.

**Alternative hypothesis (Low confidence):** the deprecated adapters are "delete eventually" leftovers, and the auth-check sweep is a transitional scaffolding that will be removed when the team is confident GHL alone is sufficient. README line 153 ("GHL manages platform OAuth — no token rotation needed on our side") leans this direction; auth-check.yml's continued use of per-platform IDs leans the other.

**On balance:** the High-confidence reading is "intentional preservation for auth-check." The README claim is aspirational; the workflow implementation is conservative.

### C.2 Domain interpretation (High confidence)

Adapters represent a **defense-in-depth credential model**: even with GHL as the abstraction layer, the team owns the underlying platform credentials and probes them weekly. This is consistent with risk-management thinking elsewhere in the repo (two-gate workflow, fail-closed validation).

### C.3 Assumptions

- **GHL doesn't expose a per-platform credential-health API**, so per-platform probes are the only way to know the credentials are healthy. (External assumption; uncheckable here.)
- **The 5 deprecated adapters' `auth_check` implementations are still correct.** Pass 02 confirmed the interface conformance but no test exercises the deprecated adapters (CP-7).

### C.4 Missing intent

- **No explicit "auth_check is the only deprecated-adapter surface" docstring.** The deprecation markers in the 5 files are inconsistent (3× "Phase 1 skeleton"; 2× no marker; none say "deprecated"). A reader picking up the code would not know `publish()` is dead but `auth_check()` is live.
- **No "when do we delete the deprecated adapters" criteria.** The repo has no decommissioning plan for the 5.
- **AC15 is anchored to x_twitter and AC14 to instagram** — broader-namespace ACs whose canonical meaning isn't in the AC summary. These ACs effectively define the deprecated adapters' contract, but only by code-comment reference.

### C.5 Inconsistencies

- **README line 153 vs auth-check.yml**: "no token rotation needed on our side" vs per-platform env-var iteration.
- **Deprecation marker inconsistency** (CP-7).
- **Zero test coverage of the 5** (CP-7) — 942 LOC of tests cover ghl.py + publisher.py orchestration only.

---

## Group D — Authentication & Credential Health

KV secret-name pattern + weekly auth-check + GitHub-issue-on-failure.

### D.1 Intended purpose (High confidence)

The auth pattern's intent is **fail-fast credential health monitoring with on-call routing**:

- All credentials live in Azure Key Vault (per `kv-<brand>-<platform>-{token|credentials|config}` naming).
- A weekly cron (Mon 09:00 UTC) probes every credential.
- Failures auto-create a GitHub issue tagged `credential-failure` + `agent:bob` (the agent label is the routing mechanism — Bob owns credential ops).

Evidence: `auth-check.yml` (71 lines) is short and does one job; the GitHub-issue side is unconditional (`if: steps.auth_check.outcome == 'failure'`); the labels are stable.

### D.2 Domain interpretation (High confidence)

**Why weekly and not daily/hourly?** Token expiry windows are long (Facebook 60d auto-refresh, LinkedIn 60d per OPERATIONAL_RUNBOOK §6). Weekly catches failure modes well before they impact a posting cadence (per WORKFLOW §8: SR ~3-5 posts/week, VP cadence similar). Daily would be wasteful; monthly would risk missing a token within its grace window.

**Why GitHub issues and not Telegram?** Auth failures are not time-critical (token expiry has days of warning); they need a tracked-and-resolvable surface. Telegram is push-only; an issue can be assigned, commented, closed. **Cross-ref CP-5: the publish path uses Telegram + GitHub issue (paired), the auth-check path uses GitHub issue alone.** Different urgency profiles → different alert mechanisms.

### D.3 The Bob agent-label (High confidence)

The `agent:bob` label is the **routing primitive** for VP's bot-driven ops surface. Bob is the GHL/credentials specialist (per OPERATIONAL_RUNBOOK §9). When an issue lands with `agent:bob`, an external automation triages it. This pattern likely exists across the VP repo set; this repo is the producer.

### D.4 KV secret-name convention (High confidence)

The 3-segment pattern (`kv-<brand>-<platform>-<suffix>`) is a stable cross-spec contract (CP-11 + Phase 0 cross-spec markers). Suffixes encode credential shape:
- `-token`: simple OAuth bearer (LinkedIn, Facebook).
- `-credentials`: richer JSON blob (GBP, with refresh token + service-account fields).
- `-config`: tool-config blob (X — the `xurl` config JSON).

**Intent (Medium confidence):** the suffix conveys "what kind of secret resolution to do." The `_get_credential` resolver in `base.py` doesn't actually branch on the suffix — it just returns the secret value as a string and lets the adapter parse it. The convention is **author-side documentation discipline**, not enforcement.

### D.5 Assumptions

- **`AZURE_KEY_VAULT_NAME` is set in production CI**, not locally. Local dev uses env vars (CC-PA3: env-first, KV-fallback).
- **The `agent:bob` automation exists.** This repo only writes the label; the consumer is external.

### D.6 Missing intent

- **No KV secret-name positive validator.** `validate-brand.py` only rejects values that *look like* raw tokens; it doesn't enforce `kv-` prefix. (Pass 03 unknown #3.) This may be intentional (allow non-KV-named alternatives, e.g., `latest` or `${BRAND}-X`) or a gap.
- **No credentials freshness assertion for the GHL token itself.** `auth-check.yml` covers per-platform deprecated-adapter creds, but `GHL_API_KEY` is also exercised (the auth-check path goes through `run_auth_check` which calls `GHLAdapter.auth_check`). Ambiguous from artifacts whether GHL's token is on the same expiry watch as the others.

### D.7 Inconsistencies

- **`validate-brand.py` doesn't validate the `ghl:` block at all** (Pass 03), even though `ghl.location_id` and `ghl.accounts` are critical at publish time. The validator's scope was scoped to AC8's narrow read.
- **Conditional Azure Login in auth-check.yml** (`if: vars.AZURE_CLIENT_ID != ''`) — Phase 0 → Phase 2 staging, suggesting the KV path was added but the OIDC client hasn't been provisioned in all environments. Unfinished.

---

## Group E — Notification & Escalation Strategy

Telegram + GitHub Issues. Asymmetric across publish vs auth-check.

### E.1 Intended purpose (Medium confidence — current state ≠ stated intent)

**Stated intent (per docs):**
- README: Telegram fires on **publish-time success** ("X posts pending approval in GHL").
- WORKFLOW §10.2: Telegram is the **bridge between Gate 1 merge and Gate 2 click** — alerting Dave that drafts are ready.
- OPERATIONAL_RUNBOOK §3: Telegram for **failure alerting** (Phase 2 plan).

**Implemented behavior (per code):**
- `_send_telegram_notification` (retry.py:235–276) called from `_handle_final_failure` (retry.py:147) on `PermanentError` OR retry-exhaustion.
- Always paired with `_create_github_issue`.
- Auth-check path doesn't use retry.py — uses GitHub issue only.

**Inference (Medium confidence):** the *original* intent (README) was a Gate-bridging "posts ready for visual approval" notification. The *current* implementation is a failure alert paired with a tracked GitHub issue. **The shift happened mid-Phase-1**: somewhere in the Vulcan→Daedalus transition, the retry primitive was extended to call Telegram on failure (matching OPERATIONAL_RUNBOOK §3's "failure alerting" framing), but no one has yet implemented the success-path Telegram notification (matching README's framing). WORKFLOW §10.2 is the third state — "not implemented" — written to reflect "as of doc time, Telegram-on-success doesn't exist yet."

### E.2 Why Telegram for some things and GitHub Issues for others (High confidence)

The split is by **urgency × resolvability**:

| Surface | Urgency | Resolution kind | Mechanism |
|---|---|---|---|
| Publish-time failure (retry.py) | High (post about to miss schedule) | Tracked + needs-action | **Both** Telegram + GitHub issue |
| Auth-check weekly failure | Low-medium (days of warning) | Tracked + assignable | GitHub issue only |
| Publish-time success (README aspiration) | Medium (Gate 2 trigger) | Push notification | Telegram (not yet implemented) |

The intent is **layered alerting**: Telegram is for "act now"; GitHub issues are for "track to closure." Failure events get both because they're both urgent AND need tracking.

### E.3 Domain interpretation (Medium confidence)

This pattern — Telegram + agent-label-tagged GitHub issues — is consistent with VP's broader operational philosophy (per the user's CLAUDE.md: `agent:bob` cron-driven triage). Telegram is the human-facing alert; GitHub issues are the bot-facing queue.

### E.4 Assumptions

- **Telegram delivery is best-effort.** retry.py swallows Telegram failures — a Telegram outage shouldn't block the publish loop.
- **GitHub issue dedup works on title equality** (per CP-5 retry.py impl). Repeated identical failures don't spam; auth-check's dated title (`Weekly credential check $(date -u +%Y-%m-%d)`) ensures one issue per week.

### E.5 Missing intent

- **No Telegram-on-publish-success** at this snapshot. WORKFLOW §10.2 confirms it's REQUIRED but unimplemented. README was written assuming it would be in place.
- **No published-status sync** (WORKFLOW §10.3, NICE-TO-HAVE). The publisher writes `ghl-pending` but never `published` — no detection of GHL fire-time. This means the lifecycle never closes in this repo's view; the post stays at `ghl-pending` forever after Gate 2.

### E.6 Inconsistencies (cross-ref CP-5)

- README's "publish-success" Telegram framing vs retry.py's "failure-only" implementation.
- WORKFLOW §10.2 saying "not implemented" while publish.yml injects `TELEGRAM_BOT_TOKEN` — the secret-injection is a forward-pointer.

---

## Group F — Cross-cutting Concerns (per CP)

Inferred intent for each Phase 1.5 pattern.

### CP-1 — AC namespace divergence

**Intent (Medium confidence):** AC-tagging was always meant to be the traceability spine of the codebase. The divergence is accidental — two specs (Vulcan + Daedalus) happened to start at AC1 and the cross-spec collision was never reconciled. The pattern AMPLIFIES every other drift; addressing it would require a `docs/AC_INDEX.md` that disambiguates each AC by spec source. (See Group B.)

### CP-2 — Stale-doc script-path references

**Intent (High confidence):** the consolidation refactor (4 `ghl_social_*.py` → `ghl_social.py` subcommands) was correct; the doc updates were the dropped step. The **doc-author-cluster–specific drift** (Bob's batch is stale; README/WORKFLOW are current) reveals a process gap: Bob's docs were generated as a one-shot Forge phase artifact and never linked into the regular update flow. The intent of the consolidation was DRY/maintenance; the side-effect was orphaned docs.

### CP-3 — Status-lifecycle drift

**Intent (Medium confidence):** the canonical lifecycle is the **6-state machine** (`draft → ready → ghl-pending → scheduled → published`, plus `failed`) — the version in models.py + tests + README + WORKFLOW. The **schema enum + validate-post.py + ARCHITECTURE.md** trail behind, omitting `ghl-pending`. Inference: `ghl-pending` was added to the publisher when Daedalus draft-mode was wired (probably in a PR that touched models.py + tests + README), but the schema + script-validator + architecture doc weren't updated in the same PR. **The schema would actively REJECT the value the publisher writes** — this is a latent consistency bug, not a design intent.

(See Special-Attention answer in §Sp.B for the "which artifact is older" reading.)

### CP-4 — Two-gate workflow implementation

**Intent (High confidence):** the two-gate invariant is intentionally distributed across multiple layers (validate-pr.yml, status-enum, publisher state-machine, adapter payload literal). This is **defense-in-depth**: even if one layer fails, the others catch. No single test covers the end-to-end invariant — that's a coverage gap, not an intent gap.

### CP-5 — Notification layering

See Group E. Intent is **urgency × resolvability split**; the README/code drift is timing of impl vs doc.

### CP-6 — Stats-dict + best-effort side-effect convention

**Intent (High confidence):** **publisher availability > publisher correctness for side-effects.** The publisher must keep going even if Telegram is down, GitHub Issues API is down, or the frontmatter writeback fails. The stats-dict surface gives the workflow caller machine-readable outcomes; side-effects are observability. This is consistent with the "weekly auth-check is the credential-health monitor" intent — the publisher itself is meant to be resilient to operational degradation in any of its non-API integrations.

### CP-7 — Deprecated-adapter runtime liveness

See Group C. Intent is **defense-in-depth credential health** (Medium confidence — vs the alternative "leftover scaffolding").

### CP-8 — Schema field vs code validator coverage mismatch

**Intent (Low confidence):** unclear. The schema appears to be a documentation artifact (no automated reader); validate-post.py is the actual gate. **Inferred:** the schema was the originally-intended source of truth, and validate-post.py grew its own duplicate enum/regex literals as a "make CI work now" expedient. The `additionalProperties` policy gap (schema doesn't declare it; validate-post.py doesn't enforce it; pydantic models don't `extra=forbid`) means the schema's "strict validation" promise lives nowhere actionable. This may be deliberate (allow forward-compat fields) or a gap.

### CP-9 — Hardcoded constants & conventions

**Intent (Medium confidence):** most constants are localized DRY (each in its proper home — rate-limit defaults in models.py, base URL in ghl.py, char limits in schema). The exception — **char-limit triplication** (schema + validate-post.py + 3 deprecated adapters) — is unintentional. The deprecated adapters' constants would have been correct when they were the publishing path; the script + schema duplication grew during the GHL transition.

The **MAX_RETRIES = 4 vs comment "3 attempts"** reads as an off-by-one ambiguity (see Sp.F): the 4 includes the initial attempt + 3 backoff retries; the comment counts only the retries. Convention drift between author and author.

The **`ghl-publisher` concurrency group name** (vs Phase 0 review's claimed `publisher`) reads as VP-house convention: per-feature concurrency groups, not per-repo. This is consistent with sr-google-ads and other VP repos' conventions.

### CP-10 — Empty Phase-2 / forward-pointer placeholders

**Intent (Medium confidence):** the placeholders represent a deliberate Phase 1 / Phase 2 split — Phase 1 (GHL Social Planner integration) is what's live; Phase 2 (HeyGen avatar generation) is a future extension. The empty `templates/` and `campaigns/spring-launch-2026/` dirs are forward-pointers (probably for HeyGen-templated campaign content), but their lack of explicit labels makes them indistinguishable from oversight. (See Sp.G — `avatar_id: null` intent.)

### CP-11 — Cross-spec GHL convention

**Intent (High confidence):** the GHL HTTP convention (`Bearer` + `Version: 2021-07-28` + `services.leadconnectorhq.com`) is a stable cross-spec contract. RP, sr-ops-tools, and this repo all use it identically. **Inferred:** this is a VP-internal house standard for any GHL integration; the convention is owned by sr-ops-tools as the original implementation and copied here.

---

## Group G — Cross-repo Dependencies

### G.1 Core_Business#222 (High confidence)

The parent strategic issue. Anchor for "why this repo exists" — the social-media bookend to sr-google-ads's paid-ads bookend, both tracing back to Core_Business#222. **Intent: this issue defines the marketing-surface scope.** Out of scope here.

### G.2 Vulcan (`social-calendar#2`) and Daedalus (Medium confidence)

- **Vulcan = issue #2**, AC1–AC10, scope = GHL adapter + publisher integration. `AC_VERIFICATION_SUMMARY.md` is its verification artifact. Closed/largely-PASS by 2026-03-27.
- **Daedalus = unknown issue number**, AC11–AC16 + AC-OQ2/3/4/6, scope = the two-gate workflow + draft-mode + status polling + Telegram. The `<TBD>` placeholders in WORKFLOW §10 are the Daedalus deliverable list.

**Intent (Medium confidence):** Vulcan and Daedalus are two phases of the same Phase-1 work, named after the design specs that authored them. The naming is internal-team convention (Greek/mythic codenames) rather than user-facing. The repo is mid-Daedalus at this snapshot.

### G.3 sr-azure-infra (High confidence)

KV provisioning. The `kv-<brand>-<platform>-<suffix>` secrets are provisioned there, consumed here. **Intent: separation of concerns.** This repo is consumer-side; secret lifecycle is in the infra repo. Workflow `AZURE_KEY_VAULT_NAME` env var is the bridging primitive.

### G.4 sr-ops-tools (High confidence)

Sibling Python operational layer. Same GHL HTTP convention (CP-11). Same `cUgvqrKmBM4sAZvMH1JS` location-id. **Intent: shared GHL integration patterns.** sr-ops-tools likely has the original GHL helper code; this repo's `ghl.py` is a parallel implementation (not a shared library) — each repo carries its own copy. (Reading: VP doesn't have a shared Python library yet; copy-paste-and-keep-in-sync is the pattern.)

### G.5 sr-google-ads (Medium confidence)

The paid-ads bookend. **Intent: shared "single-source + manual sync" architectural pattern shape**, no shared code. Both repos are markdown-driven, both use Function App / GHA Python, both publish via OAuth-token KV indirection. They diverge on: this repo has 2 gates (visual surface needed); sr-google-ads has 1 gate (no visual surface).

### G.6 vp-cms / Product-SecondRing (Low confidence)

Product spec sibling. **Intent: design specs may live cross-repo.** No shared artifact in this snapshot.

---

## Group H — Out of Scope

Explicit per Phase 0:

- GoHighLevel API internals (black-box).
- Facebook / Instagram / LinkedIn / X / GBP API internals (black-box; deprecated anyway).
- Telegram Bot API internals (impl wiring is in scope; API surface is not).
- HeyGen (Phase 2 deferred).
- Azure KV internals.
- Vulcan + Daedalus design spec contents (cross-repo issue tracker).
- Riley's authoring tooling (this repo is the publisher).
- `Core_Business#222`.

**Phase 2 inference adds:**

- **`agent:bob` consumer automation** is out of scope here (this repo only writes the label; consumer triages). Same pattern as VP's `vp-fix-copilot` cron.
- **GitHub branch protection rules** — referenced by intent (validate-pr.yml gates merge to main), but the rules themselves are GitHub-side config not in repo.

---

## Special-Attention Items

### Sp.A — AC namespace divergence as intent question

**Best inference (Medium confidence):** the broader namespace was authored during Daedalus, parallel to the existing Vulcan AC1–AC10, with no awareness of the collision. The alternative (intentional per-issue counter) is unsupported by any in-repo disambiguation cite. **What it reveals:** specs at VP live in issue threads, not in repo; spec-freeze-then-back-propagate is unreliable; the AC convention was written to enable traceability but the convention's integrity decays once two work-streams overlap. (See Group B.)

### Sp.B — Schema-vs-publisher status-enum mismatch (`ghl-pending`)

**Inference (Medium confidence):** the publisher (models.py + retry.py + state.py) was extended FIRST when Daedalus draft-mode landed; the schema + validate-post.py + ARCHITECTURE.md weren't updated in the same PR. **Evidence:** tests (which were written alongside the publisher) treat `ghl-pending` as canonical; ARCHITECTURE.md is dated to a Forge phase pre-Daedalus. **The schema is the older artifact**, not the newer.

If the schema-validator chain were run against a `ghl-pending` post, it would REJECT it. In practice, `validate-post.py` runs only on PR open (Gate 1), at which point the post is `ready` not `ghl-pending` — so the schema-validator never sees the publisher's writeback. This is **why the bug is latent**: the validation surface and the writeback surface don't temporally overlap.

### Sp.C — Deprecated adapters runtime-live

**Inference (Medium confidence):** intentional preservation for auth-check coverage (Group C). The alternative (accidental leftover) is weaker because of the *active* env-var injection in auth-check.yml. If the team had simply forgotten to clean them up, no one would have intentionally added FACEBOOK_PAGE_ID etc. to the workflow.

### Sp.D — AC12 cited in workflow header but in NO script

**Inference (Medium confidence):** placeholder for FUTURE wiring of `state.py:is_committed_on_main` to an AC#. The workflow-header cite was written aspirationally ("when AC12 is wired, this workflow will reference it"), and `is_committed_on_main` was implemented but never tagged. Alternative: stale ref to a check that was descoped — but the check exists and runs (Pass 01), so this reading is weaker.

### Sp.E — Two-gate workflow distinctiveness

See Group A.3. **Inference (High confidence):** distinctive because the artifact (a social post) has two distinct approval surfaces (textual + visual) that no other VP repo's artifacts have. Other VP repos' artifacts have one surface (paid-ads conversion data, code, ops scripts) and need only one gate.

### Sp.F — MAX_RETRIES = 4 vs "3 attempts total"

**Inference (Medium confidence):** off-by-one in author convention, not a real behavior bug. `MAX_RETRIES = len(BACKOFF_DELAYS) + 1 = 4` reads as "1 initial + 3 backoff retries." The "3 attempts total" comment counts the retries only. Architecturally the publisher does 4 total HTTP calls per transient failure path (matching ARCHITECTURE.md "3 attempts" + 1 initial that the doc forgot to count, or matching the inverse — depends on how you read the doc). The comment-vs-code drift is real; the production behavior is "1 + 3 retries with 10/30/90 backoff" regardless of which counting convention you adopt.

### Sp.G — State-dir mismatch (`.state/rate_limits/` placeholder vs `state_dir/{platform}.json` actual)

**Inference (Medium confidence):** Phase 2 staging or oversight. The `.gitkeep` was placed at `brands/<brand>/.state/rate_limits/`, presumably anticipating per-platform sub-files. The actual code writes `.state/{platform}.json` (one level shallower). **Most likely:** an early design intent had a deeper directory layout; the implementation chose flatter. The placeholder wasn't moved/deleted. Not a runtime bug — `mkdir(parents=True, exist_ok=True)` builds whatever path the code writes.

### Sp.H — Multi-author signals

What the Riley/Dave/Bob/Tara split reveals (High confidence):

- **Riley** (post author): the human writer, target of `RILEY_HANDOFF_SPEC.md`. Doesn't author code.
- **Dave** (approver): owns Gate 1 (PR merge) AND Gate 2 (GHL Schedule click). Repo owner. Final auth.
- **Bob** (agent label + Forge doc author): a *bot persona* (`[Bob — claude-sonnet-4-6]`) responsible for credentials ops AND the Forge documentation pass. Two functions for one persona is unusual — suggests the codebase doesn't sharply distinguish "bot doing creds work" from "bot doing doc work"; both are surface-level Bob-tagged outputs with different `agent:` consumers. CP-2's "doc-author-cluster–specific drift" maps directly to "Bob's batch is stale, others' isn't."
- **Tara** (cross-repo wiring): present in spec lineage (sr-google-ads + Daedalus per cross-spec markers), not in this repo's authored artifacts. Intent: cross-repo coordinator persona.

**The split reveals four distinct roles in VP's content pipeline**: human authoring (Riley), human approving (Dave), bot ops (Bob), bot coordination (Tara). The repo is built around this division.

### Sp.I — `avatar_id: null` HeyGen placeholder — Phase 2 intent

**Inference (Medium confidence):** the field was added to the brand schema during Phase 1 with `null` as the explicit Phase-2 forward-pointer. The intent is that when Phase 2 lands, brand authors will populate `avatar_id` (a HeyGen avatar reference) and posts with `creative.type: heygen` will go through a HeyGen video-generation step. The intermediate state — `status: video-pending` — is in the schema enum, anticipating "publisher kicked off HeyGen, waiting for video render." **Phase 2 was not silently descoped** at this snapshot — the placeholders are deliberate.

### Sp.J — velocitypoint brand.yaml missing entire `ghl:` block

**Inference (Medium confidence):** intentional staging — VP's `ghl:` block was deferred until VP's GHL Sales sub-account had social accounts connected. Per AC9 (BLOCKED in `AC_VERIFICATION_SUMMARY.md`: "Sales sub-account has 0 social accounts connected"), the live E2E test is blocked on the same dependency that would populate VP's `ghl:` block. The 3 VP posts declaring `ghl_mode: true` are written assuming the block will exist by go-live.

**Latent consequence (Medium confidence):** if `publish.yml` runs against a VP post today, the publisher will hit `getattr(brand, "ghl", None)` → `None` → `_no_ghl_config_returns_early` path (per Pass 05 `test_no_ghl_config_returns_early`) → silently no-op. Stats dict reports 0 published, 0 failed, no error. **The post is silently never published, the failure is invisible.** This is a launch-blocker the repo currently treats as "soft-skip" rather than "loud-fail."

---

## Synthesis: What Phase 2 Reveals

1. **The two-gate workflow is the headline VP-divergence intent** (vs other VP repos). It exists because the artifact has two approval surfaces. No other VP repo's artifact does. (High confidence.)
2. **The AC convention is real but its integrity was broken by parallel work-streams.** The convention's intent was traceability; its current state is partial-traceability with cross-spec collision. (Medium confidence.)
3. **The deprecated-but-runtime-live pattern is intentional defense-in-depth**, not leftover code. The team owns the underlying credentials even when GHL handles routing. (Medium confidence.)
4. **The status-enum mismatch (`ghl-pending`) is latent** — the validation surface and writeback surface don't temporally overlap, so the schema-vs-code drift never bites. But it's a bug-in-waiting if validation is ever extended to post-publish. (Medium confidence.)
5. **The Phase 2 forward-pointers are deliberate**, not noise. HeyGen integration is on the roadmap; the schema, models, and brand.yaml were prepped for it. (Medium confidence.)
6. **The most critical immediate gap is the velocitypoint `ghl:` block absence.** Three VP posts will silently no-op at publish time. (Medium confidence.)
