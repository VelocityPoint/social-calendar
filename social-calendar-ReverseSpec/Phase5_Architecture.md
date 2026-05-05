# Phase 5 — Target Architecture & Pivot Strategy

**Snapshot:** `67d061c` (2026-04-26)
**Method:** Synthesises Phase 3 (services + invariants) and Phase 4 (46 findings, 8 High, 4 unique High root issues) into a target architecture. Technology-neutral. Every component traces to a Phase 3 responsibility; every Phase 4 finding either gets a resolution shape or an explicit out-of-scope acknowledgement.

**Posture.** social-calendar is post-MVP, pre-real-traffic. Campaign 1 has not yet run. The architecture below is a **pivot from current state**, not a redesign — the seven Phase 3 services stay; the pivot is to add four currently-absent components that resolve the 4 launch blockers and to consolidate the cross-cutting drift surfaces.

---

## Section 1 — Pivot Stance

**Stance.** *Pre-launch posture: resolve the 4 launch-blocking Highs before first publish; consolidate the AC namespace and the stale-doc cluster as immediate follow-ups; preserve the intentional two-gate defense-in-depth (4-layer redundant encoding) but make one layer canonical and document the redundancy; defer Phase 2 (avatar-rendering forward work) and the empty placeholder directories.*

**Defense.**

The four launch blockers (Phase 4 §"Top 5") are independent fault domains, each of which fails the first-publish smoke test on its own:

1. **velocitypoint missing publishing-channel block (S1.3 / S4.10).** First VP publish hits silent-no-op via the `_no_ghl_config_returns_early` test path (Phase 2 Sp.J High-confidence consequence). 0 published, 0 failed, no error surfaced.
2. **secondring 6 unfilled `<account_id>` placeholders (S1.4 / S4.10).** First SR publish on any of those 6 accounts fails or mis-routes at the third-party publishing service.
3. **Schema rejects `<gate-2-pending>` at PR-time but publisher writes it at runtime (S1.2 / S4.2).** Bug-in-waiting: the temporal non-overlap hides it today; the first PR-time re-validation of an already-published post triggers schema rejection.
4. **`RateLimitState` writes to wrong path (S2.5 / S4.4).** Silent-data-loss surface — the placeholder directory is never written; any future reader expecting the deeper layout misses state.

These four are individually low-effort to resolve, but their *combination* is what makes Campaign 1 a non-event. Resolving them before first publish prevents debt accumulation: each one becomes 10× harder to surface after a successful publish has happened, because "looks like it works" is a powerful sedative.

The fifth Top-5 finding — AC namespace divergence (S1.1 / S3.1 / S5.1) — is a Medium-High **amplifier**, not a launch blocker. It can ship as launch-hardening (Phase 2 of evolution).

**Preserve, don't dismantle.** Phase 2 explicitly identified the two-gate workflow as the system's headline VP-divergence intent (Sp.E: "the only VP repo where the second gate lives in a third-party UI"). Phase 3 §4.1 records the 4-layer redundant encoding as **intentional defense-in-depth** — schema enum, schema validation, publisher state-machine `status==ready` check, adapter wire-payload `status: draft` literal. This redundancy is a feature, not a bug. The pivot does NOT reduce it to one layer; the pivot is to **declare which layer is canonical** so that future schema/enum changes propagate predictably to the other three.

**Defer.** Phase 2 (avatar rendering) is correctly out of scope for this architecture. The Phase-2 forward-pointers (`avatar_id: null`, `<phase-2-deferred>` enum value, empty `templates/` and `campaigns/spring-launch-2026/` directories) stay where they are; they get **labelled in-place** per Phase 3 §4.11 forward-pointer hygiene, but their behaviour is not specified here.

---

## Section 2 — System Decomposition

The seven Phase 3 services remain. The architecture **adds four currently-absent components** that resolve cross-cutting drift surfaces and four launch blockers.

### 2.1 Existing components (Phase 3 services, recapped)

#### Calendar Authoring Service — Tier 2

- **Owns.** Phase 3 §3.1 — structured-document-with-frontmatter authoring; the `draft → ready` early lifecycle.
- **Boundary.** Stops at `ready`. Knows nothing of the third-party publishing service or rate-limit state.
- **Why this boundary.** Authoring concerns and publishing concerns are temporally separated by Gate 1 (the merge). Coupling them would make local authoring tooling depend on credentials.

#### Two-Gate Publishing Service — Tier 1

- **Owns.** Phase 3 §3.2 — detect newly-merged `ready` posts; route via per-brand adapter; capture outcome; write back state.
- **Boundary.** Posts as `draft` only. Never fires. Does NOT detect post-fire `published` events at this snapshot (deferred work).
- **Why this boundary.** The system is operator-mediated, not autonomous (Phase 3 §1.1). Publishing-as-fire is intentionally outside this surface.

#### Schema Validation Service — Tier 1

- **Owns.** Phase 3 §3.3 — validate post-document and brand-config against canonical schemas at change-request time.
- **Boundary.** Sole binding pre-merge schema gate. Runs only at change-request time; never sees post-publish writeback values.
- **Why this boundary.** Phase 3 §3.3 explicitly: "the system MUST NOT rely on the publisher's own validation as the primary gate." Centralising the binding gate at PR-time means the publisher can assume well-formedness.

#### Per-Brand Adapter Layer — Tier 1

- **Owns.** Phase 3 §3.4 — abstract per-destination-network or per-publishing-channel auth + post-shape concerns.
- **Boundary.** Active publishing-channel adapter is the only one whose `publish` is exercised. Legacy direct-network adapters remain runtime-resident SOLELY for `auth_check`.
- **Why this boundary.** Phase 3 I-17 — legacy adapters cannot be removed without removing their `auth_check` coverage. The boundary preserves auth-health surface area while making it explicit that publish-fan-out flows through one adapter.

#### Auth Health Monitor — Tier 1

- **Owns.** Phase 3 §3.5 — recurring-schedule probe of credential health per brand × destination-network.
- **Boundary.** Failure surface is the work-item queue alone. No operator-notification (urgency profile mismatch — see I-9 / §3.6 contrast).
- **Why this boundary.** Token expiry windows are days; push-notification urgency is wrong. Work-items decouple discovery from response.

#### Notification & Escalation Service — Tier 1

- **Owns.** Phase 3 §3.6 — paired notification + work-item on publish-path final failure.
- **Boundary.** Publish-path only. Auth-health uses a different escalation pattern.
- **Why this boundary.** Phase 3 I-9 — the pairing is invariant. Splitting the responsibility makes the pairing a checkable contract.

#### Operator Tooling — Tier 2

- **Owns.** Phase 3 §3.7 — ad-hoc account discovery, post listing, post inspection, post deletion.
- **Boundary.** Out-of-band of the publish path. Does NOT alter post-document state or rate-limit state.
- **Why this boundary.** Operator tooling is a hatch, not a control plane. Letting it write to the publish-state surface would break replay protection.

### 2.2 Currently absent — proposed components

These four components are **not present** at the current snapshot. Each resolves one or more Phase 4 findings.

#### Status Lifecycle Canonical Source (NEW)

- **Owns.** A single declaration of the canonical status enum, consumed by schema, models, validator, tests, and adapters as a build-time or load-time input. Resolves Phase 3 §4.4 + I-12 violation (currently 4 disagreeing sites for one enum).
- **Boundary.** Declares the enum and its allowed transitions. Does NOT declare validation rules per state — those stay in their respective consumers.
- **Why this boundary.** The enum-shape question and the per-state-validation question are different concerns. Canonicalising the enum stops drift; centralising every per-state rule would create a god-component.

#### AC Identifier Registry (NEW)

- **Owns.** A single in-repo enumeration of every acceptance-criterion identifier, its source spec, and its scope. Resolves Phase 3 §4.5 + I-11 violation (currently 2 colliding namespaces).
- **Boundary.** Registry is documentation; it does not own AC content. AC-tag attribution lives in source code at the implementation site.
- **Why this boundary.** The registry's purpose is uniqueness and traceability, not specification. Each AC's actual content remains in its source spec.

#### Brand Config Completion Gate (NEW)

- **Owns.** A pre-merge check that asserts every brand-config artefact intended for publish is *complete*: no `<account_id>` placeholders, no missing `ghl:` block when any of the brand's posts declare `ghl_mode: true`. Resolves S1.3 + S1.4 — 2 of the 4 launch Highs.
- **Boundary.** Gate fires at PR-time alongside post validation. Does NOT inspect runtime credential validity (that's Auth Health Monitor's job).
- **Why this boundary.** The launch blockers are **structural** (a key is missing from a YAML map), not **runtime** (the credential is rejected by the API). Catching them at PR-time is cheap; catching them at runtime is silent-no-op or mis-route.

#### State Persistence Path Reconciliation (NEW)

- **Owns.** A single agreed location for per-brand per-destination-network rate-limit state. Resolves S2.5 / S4.4 — code currently writes shallower than the placeholder anticipates.
- **Boundary.** This is a path-convention reconciliation, not a service. The reconciliation is a one-shot fix; the ongoing component is `RateLimitState` itself (Phase 3 §5.3) which writes to the agreed location.
- **Why this boundary.** Treating "the path mismatch" as a component-level concern overstates it. It is a convention-bug between two artefacts (gitkeep'd directory and code constant) that need to agree.

### 2.3 Component map

```
                              ┌─────────────────────────────────┐
                              │  Status Lifecycle Canonical     │ (NEW)
                              │  Source                         │
                              └────────────┬────────────────────┘
                                           │ consumed by
        ┌──────────────────────────────────┼──────────────────────────────────┐
        ▼                                  ▼                                  ▼
┌────────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│ Schema Validation  │             │  Two-Gate        │             │  Per-Brand       │
│ Service (Tier 1)   │  validates  │  Publishing      │   uses      │  Adapter Layer   │
│                    ├────────────►│  Service (T1)    ├────────────►│  (Tier 1)        │
│  + Brand Config    │             │                  │             │                  │
│    Completion Gate │             │                  │             │                  │
│    (NEW)           │             │                  │             │                  │
└────────┬───────────┘             └────────┬─────────┘             └────────┬─────────┘
         │ traceable to                     │ writes                         │ probes
         ▼                                  ▼                                ▼
┌────────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│ AC Identifier      │             │ State Persist    │             │  Auth Health     │
│ Registry (NEW)     │             │ (RateLimitState  │             │  Monitor (T1)    │
│                    │             │  + path reconc.  │             │                  │
└────────────────────┘             │  NEW)            │             └──────────────────┘
                                   └──────────────────┘
                                            │ on final failure
                                            ▼
                                   ┌──────────────────┐
                                   │  Notification &  │
                                   │  Escalation (T1) │
                                   └──────────────────┘

  ┌──────────────────┐                       ┌──────────────────┐
  │  Calendar        │  authors              │  Operator        │
  │  Authoring (T2)  │                       │  Tooling (T2)    │
  └──────────────────┘                       └──────────────────┘
```

NEW components are denoted; everything else is from Phase 3. The "validates" arrow from Schema Validation to Two-Gate Publishing is a **temporal dependency** (validation must pass before publish runs at all), not a runtime call — the two services are decoupled in execution.

---

## Section 3 — Interfaces & Contracts

For each cross-component edge: synchronicity, protocol shape, data contract, error semantics. Highlights the four edges that are currently the source of cross-cutting drift.

### 3.1 Schema Validation ↔ Status Lifecycle Canonical Source

- **Sync vs async.** Sync; build-time or change-request-trigger-time read.
- **Protocol shape.** Schema validator imports / reads the canonical enum; does not duplicate its values.
- **Data contract.** `Status enum` (Phase 3 §4.4) — exactly 7 values: `draft`, `ready`, `<gate-2-pending>`, `scheduled`, `published`, `failed`, `<phase-2-deferred>`. Plus optional `deferred` for legacy paths.
- **Error semantics.** If the canonical source is unreadable, validation fails closed (rather than fall-back to a hardcoded list).

### 3.2 Publisher state-machine ↔ Status Lifecycle Canonical Source

- **Sync vs async.** Sync; load-time read.
- **Protocol shape.** `models.py:VALID_STATUSES` becomes a derived value, not a hardcoded list.
- **Data contract.** Same `Status enum` as §3.1.
- **Error semantics.** Same: fail-closed if canonical source unavailable.
- **Currently the violation.** I-12 cite — schema (7 values) and models (8 values, includes `<gate-2-pending>`) disagree. Publisher writes a value the validator would reject.

### 3.3 Tests ↔ Status Lifecycle Canonical Source

- **Sync vs async.** Sync; test-collection-time read.
- **Protocol shape.** Tests assert publisher writes the canonical post-Gate-2 value; the literal comes from the canonical source, not from test fixtures.
- **Data contract.** Same `Status enum`.
- **Error semantics.** A test asserting a non-canonical literal fails to import.

### 3.4 Adapter wire-payload ↔ Status Lifecycle Canonical Source

- **Sync vs async.** Sync.
- **Protocol shape.** Adapter wire-payload `status: draft` literal references the canonical enum's `draft` value.
- **Data contract.** Same `Status enum`.
- **Error semantics.** Same.
- **Why all four edges read the same source.** Phase 3 §4.1 — the two-gate invariant is encoded redundantly across these four layers as defense-in-depth. The redundancy is the design; the goal is **consistency among the redundant copies**, not collapse to one.

### 3.5 AC tags in code ↔ AC Identifier Registry

- **Sync vs async.** Async. Registry is a documentation artefact; reconciliation is operator-driven (or by an automated coverage check — Shape G adjacent).
- **Protocol shape.** Each AC<n> tag in source code or workflow YAML carries a namespace prefix or a registry-pinned `id` field.
- **Data contract.** Registry entry: `{id, source_spec, scope, description}`. `id` is globally unique within the repo.
- **Error semantics.** Tag without registry entry → unresolvable; fail an automated coverage check at next run (out of scope for first launch).

### 3.6 Notification ↔ Work-Item creation

- **Sync vs async.** Best-effort, both. Phase 3 I-14 and §3.6 are explicit: each is logged-and-swallowed independently.
- **Protocol shape.** On final failure: emit `NotificationPayload` AND construct + post `WorkItemPayload`. The two are sibling effects, not one-after-another with dependency.
- **Data contract.** `NotificationPayload` (Phase 3 §5.6); `WorkItemPayload` (§5.5).
- **Error semantics.** Either side-effect's failure is logged; the publisher continues; the *other* side-effect still fires. **This is the gap S4.7 surfaces.** When BOTH fail, the failure is invisible; the spec does not require detection of paired-side-effect-failure (Phase 3 §3.6 + I-9 + I-14 are silent on this case). Risk-tolerable because the operator-notification channel and the work-item substrate are independent — both failing simultaneously requires unrelated outages.

### 3.7 Brand Config Completion Gate ↔ Schema Validation Service

- **Sync vs async.** Sync. The completion gate is a sibling check that runs at the same trigger as schema validation (PR open / update).
- **Protocol shape.** Completion gate inspects the brand-config artefact; if any post in the same change-request declares `<channel-mode>: true`, gate fails on missing publishing-channel block; gate fails on any `<account_id>` placeholder string under the brand's destination-account map.
- **Data contract.** Output is a `ValidationFinding` (Phase 3 §5.8) sibling to schema-validation findings; surfaces in the same review-surface.
- **Error semantics.** Findings → PR cannot merge. Same severity surface as a schema violation.

### 3.8 Publisher ↔ State Persistence (Rate Limit)

- **Sync vs async.** Sync; per-brand per-destination-network read at run-start, write at run-end.
- **Protocol shape.** Atomic write-then-rename to a single agreed path.
- **Data contract.** `RateLimitState` (Phase 3 §5.3).
- **Error semantics.** Phase 3 I-16 — atomic-write-then-rename. Either old-version-intact or new-version-intact, never partial.
- **Currently the violation.** S2.5 / S4.4 — code writes one level shallower than the placeholder directory anticipates. Within-code consistency holds (save and load agree); the cross-artefact drift is the bug.

---

## Section 4 — Data Flow

The end-to-end flow from authored post-document through both gates to a third-party-service draft.

### 4.1 Author → Calendar Authoring Service

1. Content author drafts a structured-document-with-frontmatter, sets `status: draft`.
2. Author opens a change-request.

### 4.2 Change-request → Schema Validation Service + Brand Config Completion Gate

3. Pre-merge automation hook fires. **Two sibling gates run in parallel:**
   - **Schema Validation Service** validates the post-document against the canonical schema and validates any touched brand-config artefacts (Phase 3 §3.3 workflow). Reads the canonical Status enum from the **Status Lifecycle Canonical Source**.
   - **Brand Config Completion Gate (NEW)** — inspects each touched brand-config: any `ghl_mode: true` post in the change-request requires the brand to have a populated `ghl:` block; any `<account_id>` string in the brand-config fails the gate.
4. Both gates emit `ValidationFinding` records on failure. Either gate's failure blocks merge.

### 4.3 Approver → Gate 1

5. Approver reviews diff.
6. Approver flips `status: draft → ready` in a separate commit (or as the merge-commit's content per repo convention).
7. Approver merges. Gate 1 is now passed.

### 4.4 Merge → Two-Gate Publishing Service

8. Merge-trigger automation fires the publish workflow.
9. Workflow acquires concurrency-group lock per brand × publishing-channel (Phase 3 I-15).
10. Workflow resolves credentials via secret store (Phase 3 §2.4).
11. Publisher engine enumerates posts where `status == ready` AND committed on the integration line.
12. For each post:
    - Verify integration-line commit (Phase 3 §3.2 business rule).
    - Check rate-limit (reads `RateLimitState` from the **reconciled state path**).
    - Dispatch via the active per-brand adapter.

### 4.5 Adapter → Third-party publishing service

13. Active publishing-channel adapter constructs the wire-payload with `status: draft` literal (Phase 3 §3.4 + I-5).
14. Adapter POSTs to the third-party publishing service.
15. Service returns either:
    - **Success** → PublishResult `published_as_draft`; record the third-party post-identifier.
    - **Transient failure** → bounded retry sequence (Phase 3 §3.2 error handling).
    - **Permanent failure** → escalate immediately.

### 4.6 Outcome → State writeback

16. **Success path.** Publisher writes back to the post-document: `status: <gate-2-pending>` (the canonical post-Gate-2 value), `<channel-post-id>` populated. **`<gate-2-pending>` is read from the Status Lifecycle Canonical Source** — same enum the validator uses.
17. **Failure path.** Publisher writes `status: failed`, `error` populated.
18. Rate-limit state writes to the **reconciled state path**.
19. Aggregate stats-dict returns to the caller.

### 4.7 Failure → Notification & Escalation Service

20. On retry-exhausted or permanent-error: invoke Notification & Escalation.
21. Service constructs `NotificationPayload` AND `WorkItemPayload`; sends both **in parallel** (best-effort, independent).
22. Failure of either side-effect is logged; publisher continues.

### 4.8 Operator → Gate 2

23. Operator opens the third-party publishing service UI.
24. Operator visually reviews each `<gate-2-pending>` draft.
25. Operator approves and fires the post inside the third-party UI. Gate 2 is now passed.

### 4.9 Lifecycle closure (out-of-spec at this snapshot)

26. The third-party service drives `draft → scheduled → published`. The system does NOT detect the post-fire `published` event at this snapshot (Phase 3 §3.2 boundary; S1.7).

---

## Section 5 — Workflow Orchestration

Cross-cutting concerns that span multiple components.

### 5.1 Idempotency for `<gate-2-pending> → published`

Phase 3 I-6 mandates replay protection: re-running publish over a post past Gate 1 MUST NOT create a duplicate draft. Mechanisms:

- Publisher refuses to act on `status != ready` (the canonical-source-driven check).
- Successful create flips status to `<gate-2-pending>`, removing the post from the `ready` set.
- Third-party post-identifier is persisted on the post-document.

**Currently untested.** S4.6 — no test asserts the idempotent behaviour; the mechanism is correct on inspection. Resolution: add a test that re-runs the publisher over a `<gate-2-pending>` post and asserts no duplicate create call (Shape F).

### 5.2 Auth-health failure propagation

Phase 3 §3.5 specifies: probe failures create work-items only, no operator-notification. Question raised in the prompt: *could it also re-attempt?*

**Stance.** No re-attempt within a single probe run. Token expiry windows are days, not minutes; a re-attempt within seconds adds nothing diagnostic. The Auth Health Monitor remains a single-pass probe with work-item-only escalation.

### 5.3 Brand-config validation timing

Phase 3 §3.3 boundary: cross-brand-config consistency is in scope for Schema Validation. The current `validate-brand.py` does NOT validate the `ghl:` block at all (Phase 1 Pass 03). Resolution:

**Brand Config Completion Gate (NEW)** runs at PR-time alongside post validation. Both must pass before merge. This puts brand-config validation on the same schedule as post validation, which is the right schedule: a PR that introduces an incomplete brand-config OR a post that depends on an incomplete brand-config either fails the gate.

### 5.4 Two-gate invariant — preserve, don't dismantle

Phase 3 §4.1 — the 4-layer redundant encoding IS the design. Phase 2 Sp.E confirms the two-gate workflow is the headline VP-divergence intent; reducing it would erode the system's identity.

**Resolution.** Preserve all four layers (schema enum, schema validation, publisher state-machine `status==ready` check, adapter wire-payload `status: draft` literal). **Make ONE canonical** — the Status Lifecycle Canonical Source — and have the four layers consume it rather than duplicate it. Document each layer's role and its relationship to the canonical source (Shape I).

The redundancy is preserved; the *drift surface* is collapsed.

### 5.5 Status-machine canonicalization

Single source consumed by all four layers (§5.4 above). Concrete shape: a single declaration (file, module, generated artefact — technology-neutral) that the validator, models, tests, and adapters all read from.

### 5.6 Concurrency

Phase 3 I-15 + §4.10 — per-brand per-publishing-channel concurrency-group lock. Currently held by the substrate (`publish.yml` concurrency group). No change needed at the architecture level; S3.6 (group-name doc drift) is a doc fix only.

### 5.7 Notification + Work-Item pairing

Phase 3 I-9 — paired escalation. S4.7 surfaces a coordination gap: when BOTH side-effects fail, the failure is silent. Resolution shape: pair the two more explicitly so a paired-failure observability surface exists (Shape J). This is Phase-2-of-evolution, not pre-launch.

---

## Section 6 — Gap Resolutions

Every Phase 4 finding (46 total) gets a resolution shape OR an explicit out-of-scope acknowledgement. Resolution shapes are named A through M; aim is consolidation — multiple findings often share one shape.

### 6.1 Resolution shapes (named)

- **Shape A: Brand-Config Completion Gate.** Pre-merge gate that fails if any brand-config has unfilled `<account_id>` placeholders or is missing the `ghl:` block when posts declare `ghl_mode: true`. Resolves the 2-of-4 launch Highs (S1.3, S1.4).
- **Shape B: Status Lifecycle Canonical Source.** Single-declaration enum consumed by schema, models, validator, tests, and adapters. Resolves S1.2 (I-12 violation), S3.3 (terminology drift), S3.11 (artefact-level drift), S5.3 (cluster). Indirectly aids S2.5 / S4.4 by establishing the precedent for single-source artefacts.
- **Shape C: State Persistence Path Reconciliation.** Reconcile the `RateLimitState.save` path with the placeholder gitkeep'd directory. One-shot fix. Resolves S2.5, S4.4 (silent-data-loss surface), S3.5 (placeholder-vs-code drift).
- **Shape D: AC Identifier Registry.** In-repo enumeration of every AC with global uniqueness; per-spec namespace (Vulcan vs Daedalus) reconciliation; broader namespace AC11–AC16 + AC-OQ2/3/4/6 surfaced. Resolves the CP-1 cluster: S1.1, S3.1, S3.7, S5.1, S3.13 (test linkage convention).
- **Shape E: Stale-Doc Sweep.** Bulk-update the 24 stale citations across 4 docs (`AC_VERIFICATION_SUMMARY.md`, `DEVELOPER_GUIDE.md`, `GHL_SOCIAL_PLANNER_ARCHITECTURE.md`, `OPERATIONAL_RUNBOOK.md`) plus brand.yaml comment + runtime error string. Mechanical fix; doc-author-cluster scoped. Resolves CP-2 cluster: S2.6, S3.2, S5.2.
- **Shape F: Test Coverage for Lifecycle Closure.** Add a test asserting the `<gate-2-pending> → ` (next state) transition is idempotent under re-run; even before the closure is implemented, the *replay protection* invariant (I-6) can be tested. Also add test for paired notification + work-item co-fire. Resolves S4.5, S4.6, S5.7 partial.
- **Shape G: AC12 Implementation OR Removal.** Decide whether the workflow-header citation of AC12 ("ensures only valid docs reach main") should be implemented (e.g., tagged at `state.py:is_committed_on_main`) OR removed from the workflow header. Either choice closes the gap. Resolves S1.5.
- **Shape H: Deprecated-Adapter Cleanup.** Decide the contested value question (S2.3): if `auth_check` for the 5 deprecated adapters is genuinely defense-in-depth, document that intent in-file and in README; if it is leftover scaffolding, remove the 5 adapters' `publish` methods (dead code per S2.2) and consider removing the adapters entirely. Resolves S2.2, S2.3, S3.10 (deprecation-marker inconsistency), S4.8 (weekly cost), S5.4.
- **Shape I: Two-Gate Invariant Documentation.** Preserve the 4-layer defense-in-depth but DOCUMENT each layer's role + which is canonical. Add a single-page reference (or invariant-section in the spec) declaring: "the Status Lifecycle Canonical Source is the canonical declaration; layers 1–4 each consume it; the redundancy is intentional." Resolves S5.11 (CP-4 documentation gap).
- **Shape J: Paired-Side-Effect-Failure Observability.** When BOTH notification and work-item creation fail, surface that fact somewhere (a fall-back log line, a deadletter queue, a metric). Resolves S4.7. The pairing invariant (I-9) is preserved; the observability of paired-failure is added.
- **Shape K: MAX_RETRIES Counting Convention Fix.** Pick one convention ("3 attempts total" OR "1 initial + 3 backoff retries") and align constant + docstring + comments. Small, isolated. Resolves S2.4, S4.3.
- **Shape L: RateLimitState Pydantic v2 Bug Fix.** Locate the bug, fix the model, remove the test patches. Resolves S2.8, S4.11, S5.9.
- **Shape M: Forward-Pointer Labelling Sweep.** Per Phase 3 §4.11, every Phase-2-deferred placeholder gets an in-place label declaring its purpose and target Phase. Resolves S1.6 (empty `templates/` and `campaigns/spring-launch-2026/`), S3.8 (3 `<TBD>` issue numbers), and the `avatar_id: null` plus `<phase-2-deferred>` enum value labelling.

### 6.2 Resolution table (all 46 findings)

| Finding | Severity | Resolution shape | Notes |
|---|---|---|---|
| S1.1 | Medium-High | **D** | AC namespace divergence — Phase 2 of evolution. |
| S1.2 | High | **B** | Status canonicalization — pre-launch. |
| S1.3 | High | **A** | VP missing `ghl:` block — pre-launch. |
| S1.4 | High | **A** | SR 6 unfilled placeholders — pre-launch. |
| S1.5 | Low-Medium | **G** | AC12 implementation-or-removal — cleanup. |
| S1.6 | Low | **M** | Empty placeholder directories — labelling sweep. |
| S1.7 | Low | OOS | Published-status sync absent — Phase 3 §3.2 explicit boundary; deferred work. |
| S1.8 | Low-Medium | OOS | Telegram-on-success not implemented — Phase 3 §3.6 explicit "documented intent calls for [it]; current state is failure-only." Deferred. |
| S1.9 | Low | OOS | No `cancelled` status / Gate-2-abort — Phase 3 §3.2 explicit boundary; deferred work. |
| S1.10 | Medium | **D** | No automated AC-coverage check — falls under registry. |
| S2.1 | Medium | **H** | Cron-mode unreachable — falls under deprecated-adapter / dead-path cleanup. |
| S2.2 | Low-Medium | **H** | Deprecated adapters' publish unreachable — same cleanup decision. |
| S2.3 | Low-Medium | **H** | Auth-check value-uncertain — same cleanup decision. |
| S2.4 | Low-Medium | **K** | MAX_RETRIES off-by-one — convention fix. |
| S2.5 | Medium-High | **C** | RateLimitState wrong path — pre-launch. |
| S2.6 | Low | **E** | validate-post.py error message → consolidated script — stale-doc sweep. |
| S2.7 | Medium | **F** + **D** | Test AC coverage 23.5% — partly registry-driven (D), partly test-coverage (F). |
| S2.8 | Medium | **L** | Pydantic v2 bug — debt fix. |
| S2.9 | Medium | OOS-ish — see notes | I-3 process-only. **Stance:** keep process-based for now (Dave is sole approver per Phase 2 Group A; same-author-as-approver is structurally rare). Re-evaluate if multi-author lands. |
| S3.1 | Medium-High | **D** | AC namespace divergence (inconsistency view). |
| S3.2 | Medium | **E** | 24 stale citations — bulk sweep. |
| S3.3 | Medium | **B** | Status terminology drift — canonical source. |
| S3.4 | Low | **B** + **E** | SR `author: davelawler-vp` violates schema enum — fix in-place during canonical-enum review (B) or in stale-doc sweep (E). |
| S3.5 | Medium | **C** | State-dir vs `.state/rate_limits/` mismatch — path reconciliation. |
| S3.6 | Low | **E** | Concurrency group name doc drift — Phase 0 review claim was wrong; doc fix. |
| S3.7 | Medium | **D** | README AC1–AC14 vs summary AC1–AC10 — registry sweep. |
| S3.8 | Low | **M** | 3 `<TBD>` issue numbers — labelling sweep. |
| S3.9 | High (cross-ref) | **A** | Same as S1.3. |
| S3.10 | Low | **H** | Adapter deprecation markers inconsistent — cleanup decides if "deprecated" is the right word. |
| S3.11 | High (cross-ref) | **B** | Same as S1.2. |
| S3.12 | Medium | **B** + OOS | Schema-vs-validator field-coverage — partial: status-enum coverage falls under B; the broader 9-field-uncovered question is OOS for first launch (validate-post.py validates the fields that matter for publish; the others are advisory). |
| S3.13 | Low | **D** | Test AC linkage convention inconsistency — registry sweep settles convention. |
| S3.14 | Low | OOS | Stats-dict shape divergence — cron-mode is the unreachable path; the divergence is a cosmetic issue on a dead-path. Leave as-is until cron-mode resurrected. |
| S3.15 | Medium | OOS-ish — see notes | Char-limit triplication — currently consistent; the triplication is acknowledged in Phase 3 §4.7 as defensively permitted. **Stance:** leave; revisit if a limit changes (then make canonical). |
| S4.1 | Medium | OOS | Telegram env-var-only — Phase 3 I-13 covers; the substrate-side decision (KV-bridge vs raw env) is owned by infrastructure, not this repo (Phase 3 §7 OOS). |
| S4.2 | High | **B** | Latency of `<gate-2-pending>` mismatch — canonical source. |
| S4.3 | Low-Medium | **K** | MAX_RETRIES operator-mental-model — convention fix. |
| S4.4 | Medium-High | **C** | RateLimitState silent-data-loss — path reconciliation. |
| S4.5 | Medium | **F** | Lifecycle half untested — test coverage shape. |
| S4.6 | Medium | **F** | Idempotency unverified — test coverage shape. |
| S4.7 | Medium | **J** | Paired-side-effect-failure observability — Phase 2 of evolution. |
| S4.8 | Low-Medium | **H** | Weekly OIDC + KV cost — cleanup decides. |
| S4.9 | Low-Medium | OOS-ish — see notes | Char-limit drift exposure — same as S3.15; leave with revisit-trigger. |
| S4.10 | High | **A** | Composite launch hazard — pre-launch. |
| S4.11 | Medium | **L** | Pydantic v2 bug as risk — debt fix. |
| S4.12 | Low | OOS | `agent:bob` external automation — Phase 3 §7 explicit OOS. |
| S5.1 | Medium-High | **D** | AC cluster (debt view). |
| S5.2 | Medium | **E** | Stale-doc cluster (debt view). |
| S5.3 | High | **B** | Status-lifecycle drift cluster (debt view). |
| S5.4 | Low-Medium | **H** | Deprecated-but-runtime-live adapters cluster. |
| S5.5 | Medium | OOS-ish | Schema-vs-validator coverage cluster — same as S3.12. Mostly leave. |
| S5.6 | Medium | **K** + **E** | Hardcoded constants cluster — convention fix (K) covers MAX_RETRIES; doc sweep (E) covers group-name claim drift. The location-id literal in brand.yaml is intentional (it's the third-party-service location identifier). |
| S5.7 | Medium | **J** | Notification layering cluster — partly J (paired-failure), partly E (stale doc framings). |
| S5.8 | Low | OOS-ish | No `conftest.py` — debt; nice-to-have. **Stance:** add when test surface grows; current 2-file duplication is tolerable. |
| S5.9 | Medium | **L** | Pydantic v2 bug debt view. |
| S5.10 | Low | OOS | `python-frontmatter` usage scope unverified — verify-or-remove is a one-line investigation; leave for next contributor. |
| S5.11 | Medium | **I** | Two-gate invariant documentation. |

**Total rows: 57** (matching the 46 unique findings post-cross-reference; multi-shape rows count once).

**Shape counts:**
- **A** (Brand-Config Completion Gate) — 4 findings (S1.3, S1.4, S3.9, S4.10).
- **B** (Status Lifecycle Canonical Source) — 8 findings (S1.2, S3.3, S3.4 partial, S3.11, S3.12 partial, S4.2, S5.3 + 2 cross-refs).
- **C** (State Persistence Path Reconciliation) — 3 findings (S2.5, S3.5, S4.4).
- **D** (AC Identifier Registry) — 7 findings (S1.1, S1.10, S2.7 partial, S3.1, S3.7, S3.13, S5.1).
- **E** (Stale-Doc Sweep) — 7 findings (S2.6, S3.2, S3.4 partial, S3.6, S5.2, S5.6 partial, S5.7 partial).
- **F** (Test Coverage for Lifecycle) — 3 findings (S2.7 partial, S4.5, S4.6).
- **G** (AC12 Implementation OR Removal) — 1 finding (S1.5).
- **H** (Deprecated-Adapter Cleanup) — 6 findings (S2.1, S2.2, S2.3, S3.10, S4.8, S5.4).
- **I** (Two-Gate Invariant Documentation) — 1 finding (S5.11).
- **J** (Paired-Side-Effect-Failure Observability) — 2 findings (S4.7, S5.7 partial).
- **K** (MAX_RETRIES Counting Convention Fix) — 3 findings (S2.4, S4.3, S5.6 partial).
- **L** (RateLimitState Pydantic v2 Bug Fix) — 3 findings (S2.8, S4.11, S5.9).
- **M** (Forward-Pointer Labelling Sweep) — 2 findings (S1.6, S3.8).

**OOS / OOS-ish:** 8 findings (S1.7, S1.8, S1.9, S2.9 hybrid, S3.14, S3.15, S4.1, S4.9, S4.12, S5.5, S5.8, S5.10) — all with explicit defence (Phase 3 OOS scope, low-priority debt, or revisit-trigger).

13 named shapes resolve 38 findings + cross-references; 8 are OOS-acknowledged. Coverage: 46/46.

---

## Section 7 — Evolution Strategy

Phasing the resolution shapes against the launch-readiness threshold.

### Phase 1 — PRE-LAUNCH BLOCKERS (gates first publish)

Resolve before first paid social spend. Each shape directly addresses one of the 4 unique High root issues OR a silent-data-loss surface. Total: ~3 of 4 unique Highs (the 4th, AC namespace, is amplifier-class and ships next phase).

- **Shape A — Brand-Config Completion Gate.** Resolves S1.3 + S1.4 (2 launch Highs). Implementation cost: low — extend `validate-brand.py` and wire into `validate-pr.yml`. Cost of NOT doing: Campaign 1 fails on attempt 1 silently (S1.3) or noisily (S1.4).
- **Shape B — Status Lifecycle Canonical Source.** Resolves S1.2 (1 launch High). Implementation cost: medium-high — single source artefact, four consumer updates (schema, models, validator, tests + adapter literal). Cost of NOT doing: bug-in-waiting on next PR-time re-validation of a `<gate-2-pending>` post. **Fall-back:** if Shape B effort blows the launch timeline, ship Phase 1 with Shape A + C only and document Shape B as known-debt-of-launch with explicit "do not edit a `<gate-2-pending>` post in a PR" operator guardrail until B lands.
- **Shape C — State Persistence Path Reconciliation.** Resolves S2.5 / S4.4 (silent-data-loss). Implementation cost: very low — agree on path; one constant in code OR move the gitkeep. Cost of NOT doing: any future reader of the deeper path misses state.

Phase 1 exit criterion: Campaign 1 can run end-to-end on both VP and SR without silent-no-op or mis-routing.

### Phase 2 — LAUNCH HARDENING (post-launch, near-term)

After first publish, before second campaign. Address amplifier-class drift and observability gaps.

- **Shape D — AC Identifier Registry.** Resolves CP-1 cluster (5+ findings). Cost of NOT doing: every "AC<n> covers this" claim has uncertain meaning; new contributors get lost. Cost of doing: one-shot reconciliation pass + per-PR registry-update discipline.
- **Shape F — Test Coverage for Lifecycle.** Resolves S4.5 / S4.6. Closes the "half-of-the-lifecycle untested" gap and verifies replay protection (I-6). Cost: low — 2 to 3 new tests.
- **Shape J — Paired-Side-Effect-Failure Observability.** Resolves S4.7. Adds a fall-back surface for the case where BOTH Telegram and work-item-create fail. Cost: low-medium.

### Phase 3 — CLEANUP (debt sweep, post-second-campaign)

Now that the system has run successfully twice, address structural debt that doesn't gate publish but accumulates if ignored.

- **Shape E — Stale-Doc Sweep.** Resolves CP-2 cluster (24 stale citations, 4 docs). Mechanical bulk fix. Cost: low.
- **Shape G — AC12 Implementation OR Removal.** Resolves S1.5. Decision-cost more than implementation-cost.
- **Shape H — Deprecated-Adapter Cleanup.** Resolves CP-7 cluster (S2.1, S2.2, S2.3, S3.10, S4.8, S5.4). Decision-cost: which is the canonical reading of the deprecated-adapter `auth_check` value? Implementation-cost varies by decision.
- **Shape I — Two-Gate Invariant Documentation.** Resolves S5.11. Single-page reference. Cost: very low.
- **Shape M — Forward-Pointer Labelling Sweep.** Resolves S1.6, S3.8. Cost: very low.

### Phase 4 — HOUSEKEEPING (parallel, opportunistic)

Tiny fixes that can be picked off whenever a contributor is in the area.

- **Shape K — MAX_RETRIES counting convention fix.** Resolves S2.4, S4.3, S5.6 partial. 5-line fix.
- **Shape L — RateLimitState Pydantic v2 bug fix.** Resolves S2.8, S4.11, S5.9. Fix the model, remove the test patches.

### What is NOT designed (deferred OOS)

- **Phase 2 (avatar rendering / HeyGen).** Phase 2 Sp.I is explicit that this is on the roadmap. The forward-pointers (`avatar_id: null`, `<phase-2-deferred>` enum value, empty `templates/` and `campaigns/spring-launch-2026/` directories) are preserved with in-place labels (Shape M). The architecture above does not specify Phase 2 behaviour; that is a Phase-5'-of-the-NEXT-spec exercise.
- **Lifecycle closure (`<gate-2-pending> → published`).** Phase 3 §3.2 explicit boundary. Deferred work — when implemented, it consumes the Status Lifecycle Canonical Source same as the existing layers.
- **`cancelled` status / Gate-2-abort path.** Phase 2 Sp.A.5 explicit. Same deferral.
- **Telegram-on-success notification.** Phase 3 §3.6 explicit. Same deferral.
- **External `agent:bob` automation.** Phase 3 §7 explicit OOS.
- **Secret-store provisioning lifecycle.** Phase 3 §7 explicit OOS — owned by sibling infrastructure repo.

### Sequencing risk

The riskiest sequencing decision is **Shape B (status canonicalization) before launch** vs **deferring it**. Deferring is tempting because the bug is latent (Phase 4 S4.2 — temporal non-overlap hides it). But: any docs-edit on a `<gate-2-pending>` post triggers PR-time validation failure, and that path *will* be exercised the first time someone fixes a typo on a published post. Treating Shape B as launch-hardening rather than launch-blocker is a defensible alternative; the call here is to do it before launch because the cost is small and the post-launch psychological cost of "we shipped a known bug" is higher than the pre-launch implementation cost.

The second-riskiest is **Shape A vs Shape C ordering**. Both are pre-launch. Shape A blocks Campaign 1 (no first publish at all without it); Shape C is silent-data-loss with no current reader of the deeper path. Order: **A first, then C.** Shape C is a 5-minute fix once decided; doing it second does not endanger anything. Shape A involves a new validation rule and brand-config schema additions; it is the harder of the two, and should land first so any iteration on it does not block the silent-data-loss fix.

---

**End of Phase 5 Architecture.**
