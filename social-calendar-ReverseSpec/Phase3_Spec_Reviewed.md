# Phase 3 — Platform-Agnostic Specification (Reviewed)

## Review Notes

Reviewed `Phase3_Spec.md` for: platform-leakage scan (a curated denylist + a few additional terms surfaced during review), Phase-2 group coverage A–H + special-attention A–J, invariant testability, Phase 4/5 leakage (no fix proposals; finding-language permitted on I-11/I-12 with explicit "Phase 4 finding" labelling).

**Platform-leakage scan — pass 1 (corrected in `Phase3_Spec.md` before this review pass):**

| Term | Hits in original | Action |
|---|---|---|
| `GHL` / GoHighLevel / leadconnector | 0 | clean |
| `Telegram` | 0 | clean |
| `GitHub` | 0 | clean |
| `Azure` | 0 | clean |
| `Python` / `Pydantic` / `pytest` | 0 | clean |
| `Facebook` / `LinkedIn` / `Instagram` / Twitter / `xurl` / Google Business | 0 | clean |
| `HeyGen` | 0 | clean |
| `cron` (as the verb / runtime trigger) | 2 | replaced with "recurring-schedule triggering" / "Cron-triggered" → still in §3.5 step 1; flagged below |
| `OIDC` | 1 | replaced with "service-principal short-lived federated tokens" |
| `markdown` | 1 | replaced with "structured-document" |
| `main branch` / `main-branch` / `merge-to-main` | 4 | replaced with "integration line" / "integration-line" / "merges to the integration line" |

**Platform-leakage scan — pass 2 (corrections applied in this Reviewed file):**

5 additional residual leaks found during the second-pass read:

1. **§3.2 Inputs (line 168 of `Phase3_Spec.md`):** "post-documents in `status = ready` on main." → corrected to "on the integration line." Same idiom slipped in.
2. **§3.5 Workflow step 1 (line 308):** "Cron-triggered weekly" — `cron` is a specific scheduler family. Corrected to "Recurring-schedule-triggered weekly."
3. **§3.7 Boundaries (line 353):** "post-document on main reflects the prior state" — corrected to "post-document on the integration line."
4. **§4.1 layer-3 (line 383):** "Publisher state-machine processes only posts in `status = ready` AND committed on main." — corrected to "committed on the integration line."
5. **`Cron-triggered`** appears only once but is the most idiomatic of the leaks; flagged as a minor style point — "recurring-schedule" reads more clinically.

**Coverage check against Phase 2 groups:**

| Phase 2 group | Phase 3 coverage |
|---|---|
| **A — Two-gate workflow** | §3.2 + §4.1 + I-3, I-4, I-5, I-6 |
| **B — AC-driven spec discipline** | §4.5 + I-11 (called out as Phase 4 finding, not resolved) |
| **C — Adapter architecture (active + deprecated)** | §3.4 + I-17 |
| **D — Auth & credential health** | §3.5 + §4.3 + I-7, I-8, I-13 |
| **E — Notification & escalation** | §3.6 + §4.9 + I-9 |
| **F — Cross-cutting CPs** | distributed: CP-1→§4.5/I-11; CP-2→OOS; CP-3→§4.4/I-12; CP-4→§4.1; CP-5→§3.6/§4.9; CP-6→§3.2/I-14; CP-7→§3.4/I-17; CP-8→§3.3 (validator-as-binding-gate); CP-9→§4.7; CP-10→§4.11; CP-11→§2.1 (substrate contract abstracts the GHL-specific HTTP convention) |
| **G — Cross-repo dependencies** | §7 (out-of-spec) |
| **H — Out of scope** | §7 |
| **Sp.A — AC namespace divergence as intent question** | §4.5 + I-11 |
| **Sp.B — Schema-vs-publisher status-enum mismatch** | §4.4 + I-12 |
| **Sp.C — Deprecated adapters runtime-live** | §3.4 + I-17 |
| **Sp.D — AC12 cited in workflow header but in NO script** | NOT individually surfaced in spec; correctly punted to Phase 4 (a missing-AC-tag is a finding, not an invariant) |
| **Sp.E — Two-gate distinctiveness** | §1.1 (one-paragraph identity), implicit in §3.2 |
| **Sp.F — MAX_RETRIES counting convention** | NOT surfaced; correctly out-of-scope for Phase 3 (convention-mismatch is a Phase 5 cleanup item, not an invariant) |
| **Sp.G — State-dir mismatch** | NOT surfaced; correctly out-of-scope (forward-pointer hygiene is generically covered by §4.11) |
| **Sp.H — Multi-author signals** | NOT surfaced; correctly out-of-scope (a process observation, not a spec invariant) |
| **Sp.I — `avatar_id: null` Phase-2 placeholder** | §4.11 + §5.2 (note on `avatar_id`) + I-17-style label discipline |
| **Sp.J — VP brand-config missing publishing-channel block** | NOT individually surfaced as an invariant; covered by I-13 (credentials must resolve from secret store) and §4.11 (forward-pointer hygiene) — the silent-no-op is a Phase-4 / Phase-5 finding |

**Invariant testability check.** Each invariant should be expressible as "given X, observe Y."

| # | Testable as | Verdict |
|---|---|---|
| I-1 | "given an unsigned post-document, schema-validation rejects" | testable |
| I-2 | "given a malformed post in a change-request, the pre-merge gate blocks merge" | testable |
| I-3 | "given a post authored with `status = ready`, the system rejects on author=approver mismatch" | testable in principle; current implementation is process-based not code-based — flagged as a Phase 5 question whether code-level enforcement is desired |
| I-4 | "given a post created by this system in the third-party service, observe `status = draft`" | testable (this is the assertion the wire-payload test in Phase 1 already encodes) |
| I-5 | same as I-4 | testable |
| I-6 | "given a `<gate-2-pending>` post, re-run publish, observe no duplicate draft" | testable |
| I-7 | "given a 7-day window with no probe, fail observability check" | testable |
| I-8 | "given a probe failure, observe a tracked work-item with the credential-owner label" | testable |
| I-9 | "given a publish-path permanent failure, observe BOTH a notification AND a work-item" | testable |
| I-10 | "given a post with section over the per-network limit, validation rejects" | testable |
| I-11 | currently a **finding**, not a passing invariant — the spec correctly flags this as Phase 4 | testable as "grep for AC<n> across the repo; assert no <n> recurs across distinct sources" |
| I-12 | currently a finding | testable |
| I-13 | "grep source for token literals; assert none" | testable (negative test) |
| I-14 | "inject a notification-channel failure mid-run; observe publisher continues" | testable |
| I-15 | "launch two publish runs concurrently over the same brand; observe one acquires lock, other waits or fails fast" | testable |
| I-16 | "kill the publisher mid-write of rate-limit state; observe state file is either old-version-intact or new-version-intact, never partial" | testable |
| I-17 | "remove a legacy adapter from the registry; observe auth-check coverage drops" | testable |
| I-18 | "given a post with naive `publish_at`, validation rejects" | testable |

All 18 invariants are individually testable. I-3 is the weakest — it relies on process discipline (who clicks merge), not code-level enforcement. Flagged as a Phase-5 question: should I-3 graduate to code-level? (Possible mechanism: a pre-merge check that the diff's `status` change is in a commit not authored by the post-document author. That's a Phase-4-or-5 design question, not a Phase-3 invariant change.)

**Phase 4 / 5 leakage check.** Phase 3 should describe what MUST hold; not propose fixes for current violations.

- I-11 and I-12 explicitly cite "Phase 4 finding: currently violated." This is permitted: the invariant is stated normatively, the snapshot-state finding is bracketed. NOT a Phase-4 leakage.
- §4.4 and §4.5 do similarly. NOT leakage.
- §3.2 Boundaries notes "the system does NOT detect post-fire `published` events at this snapshot — that lifecycle closure is currently absent (deferred work)." This is a snapshot annotation. The invariant (lifecycle closure) is not declared because the spec doesn't currently mandate it. Borderline — a stricter Phase 3 would declare "MUST detect post-fire published" as an invariant. **Decision in this Reviewed pass:** leave as-is. Phase 2 explicitly flagged this as undetermined intent (E.5, "no published-status sync"); declaring it as a MUST in Phase 3 would resolve a Phase 2 ambiguity that was deliberately left open.
- No "the fix is" / "should be refactored to" / "needs a docs/AC_INDEX.md" prescriptive language found.

**Substrate-contract scope discipline check.** §2 lists capabilities required of substrates (third-party publishing service, version-control system, scheduled-automation runtime, secret store, operator-notification channel). Every capability listed is consumed by a service in §3. No orphan capabilities. The substrate contract is exactly the surface this system needs to integrate against — neither over-specified (no irrelevant capabilities) nor under-specified (each §3 service's needs are covered).

**Length check.** Final spec is 588 lines (target 500–800). Within target.

**Overall verdict.** The platform-stripping is clean after the second-pass corrections. The hardest call was whether `cron`, `OIDC`, and `markdown` were generic-enough technical terms to keep or substrate-specific enough to strip. Decision rule: a term that names a specific protocol/standard/format gets stripped (cron → recurring-schedule; OIDC → service-principal short-lived federated tokens; markdown → structured-document). A term that names a domain concept (post, brand, calendar, campaign, gate, platform-as-abstract-noun) gets kept. Applied consistently.

A second-hardest call was the boundary on §2.6 "Per-destination network." Should the spec say anything about destination networks at all, given they're reached only via the third-party publishing service? **Yes** — because per-network character limits are enforced *here* (at Gate 1), and that enforcement requires the system to know each network's limit. The destination-network capability surface is therefore part of the substrate contract even though network internals are out of scope.

---

# Phase 3 — Platform-Agnostic Specification

**Snapshot:** `67d061c` (2026-04-26)
**Method:** Platform-agnostic synthesis from Phase 1 (per-pass + Common) and Phase 2 (Intent_Reviewed). Implementation specifics — products, vendors, languages, frameworks, file paths — stripped. Behaviour, contracts, invariants, and workflow steps preserved.

This document is the canonical specification for the *added behaviour* of the social-calendar system. It defines the system's identity, the substrate it requires, the services it composes, the invariants those services must uphold, the data contracts they exchange, and what is deliberately out of scope.

---

## Section 1 — System Identity & Boundaries

### 1.1 What this system is

The social-calendar system is a **two-gated, calendar-driven publisher** for organic social-media posts. It accepts post artefacts authored as text-with-frontmatter, gates them through a textual review and then a visual review, and routes the result to a third-party social-publishing service that fans out to multiple destination networks. It is the organic-social bookend of a broader marketing-surface program; a sibling system handles the paid-ads bookend.

The system is **operator-mediated**, not autonomous: it never fires a post without an operator click in the third-party service. Its job is to assemble, validate, route, and observe — not to publish.

### 1.2 What is in the system

The system consists of:

- **A publisher engine** that reads post artefacts, dispatches them via per-brand adapters, captures outcomes, and writes back state.
- **A per-brand adapter layer** that abstracts destination-network-specific authentication and post-shape concerns. The active adapter delegates fan-out to the third-party social-publishing service; a set of legacy direct-network adapters remain runtime-resident for credential-health probing only.
- **Operator scripts** for ad-hoc tooling — destination-account discovery, post listing/inspection/deletion, and pre-merge validation gates.
- **A test surface** asserting the publisher orchestration, adapter wire payloads, gate-1 / gate-2 invariants, and stats-dict outputs.
- **A scheduled / triggered automation surface** consisting of three workflows: pre-merge schema validation, merge-triggered publishing, and weekly auth-health probing.
- **A schema artefact** declaring the canonical post-document shape, status enum, character-limit table, and required-field set.
- **Per-brand configuration artefacts** listing credentials map, destination-account map, cadence settings, and publisher-channel routing config.

### 1.3 Dependencies

The system requires:

1. A **third-party social-publishing service** capable of accepting drafts, listing accounts, retrieving posts, and exposing a draft → scheduled → published lifecycle.
2. A **version-control system** with pre-merge automation hooks, file-diff change-set semantics, and merge-triggered automation.
3. A **scheduled-automation runtime** capable of recurring-schedule triggering, service-principal credential resolution, and tracked work-item creation on failure.
4. A **secret store** for per-brand per-destination-network credentials.
5. An **operator-notification channel** for time-sensitive failure alerts.
6. **N destination networks** (the actual social platforms) — but only as black-box surface reached through the third-party publishing service.

### 1.4 Tier classification

| Capability | Tier | Rationale |
|---|---|---|
| **Two-Gate Publishing** | Tier 1 | Revenue-affecting marketing surface. Mis-fires are public, irreversible, brand-affecting. |
| **Auth-Health Monitoring** | Tier 1 | Gates publish reliability. Token expiry without warning becomes a silent publish failure. |
| **Schema Validation Gate** | Tier 1 | Sole pre-merge guard against malformed posts reaching the publisher. |
| **Calendar Authoring** | Tier 2 | Operator-facing draft lifecycle; mistakes are correctable before Gate 1. |
| **Operator Tooling** | Tier 2 | Out-of-band manual interventions; not on the publish path. |

---

## Section 2 — Substrate Contract

This section enumerates the capabilities the system requires from external substrates. These are the dependency surfaces; their internals are out of scope (see §7).

### 2.1 Third-party social-publishing service

Required capabilities:

- **post-create-as-draft**: accept a post payload and persist it in a `draft` state, NOT auto-fired. Must return a stable post-identifier for later reference.
- **post-list**: enumerate posts under a tenant scope, optionally filtered by status (e.g., `draft`, `scheduled`, `published`, `failed`).
- **post-get**: retrieve a single post by identifier.
- **post-delete**: remove a post by identifier (used by operator tooling).
- **account-list**: enumerate destination-network accounts attached to the tenant scope; doubles as an authentication probe.
- **lifecycle-states-known**: the service exposes (at minimum) the states `draft`, `scheduled`, `published`. The `draft → scheduled` transition is operator-mediated inside the third-party service (Gate 2). The `scheduled → published` transition is time-driven inside the third-party service.

### 2.2 Version-control system

Required capabilities:

- **change-request with file-diff**: an authored change-set wrapped in a reviewable container with file-level diff visibility.
- **pre-merge automation hook**: a gating check fired on change-request open / update; the change-set MUST NOT merge if the check fails.
- **merge-triggered automation**: a hook fired when a change-set lands on the integration line, capable of executing arbitrary publish-side logic.
- **textual-review affordance**: a human reviewer can read the file diff, comment, approve, and merge — this is Gate 1.
- **tracked-work-item creation**: programmatic creation of an assignable, labelable, closeable work-item bound to the repository.

### 2.3 Scheduled-automation runtime

Required capabilities:

- **recurring-schedule triggering**: invoke a workflow on a recurring schedule (used for auth-health weekly probe).
- **on-merge triggering**: invoke a workflow when a change-set merges (used for publish).
- **service-principal credential resolution**: the runtime authenticates to the secret store via short-lived federated tokens, not long-lived shared secrets.
- **secret injection**: per-workflow injection of env-vars sourced from the secret store.
- **work-item creation on failure**: a step that creates a tracked work-item, conditioned on the prior step's outcome.
- **concurrency-group locks**: a way to serialise overlapping workflow runs (used to prevent two publish runs from racing on per-brand state).

### 2.4 Secret store

Required capabilities:

- **per-brand per-destination-network secret resolution**: secret names follow a 3-segment pattern `<prefix>-<brand>-<destination-network>-<suffix>` where suffix encodes credential shape (simple bearer / structured-blob / tool-config-blob).
- **secret-by-name fetch**: given a secret name, return its current value.
- **rotation-aware**: the secret store is the source of truth for credential rotation; the system never persists tokens in source.

### 2.5 Operator-notification channel

Required capabilities:

- **per-brand per-batch summary**: a push-style notification with a free-form message body.
- **on-final-failure escalation**: paired with tracked-work-item creation; never sent alone.
- **best-effort delivery**: failures of the notification channel itself do not block the publish loop.

### 2.6 Per-destination network

Required capabilities (only via the third-party publishing service):

- **text post**: accepts a textual body within a per-network character limit.
- **image post**: accepts an image asset reference plus a textual body.
- **character-limit known**: each network has a fixed maximum character count enforceable at Gate 1.
- **response-shape known**: enough of the third-party service's response is well-defined to mark a post as draft and capture its identifier.

---

## Section 3 — Service Definitions

For each service: name, tier, responsibilities, boundaries, inputs, outputs, business rules, error handling, workflow.

### 3.1 Calendar Authoring Service (Tier 2)

**Responsibilities.**
- Provide a structured-document-with-frontmatter authoring surface for posts.
- Enforce the post-document schema at authoring time (informational) and at pre-merge gate (binding).
- Track post status through the early lifecycle: `draft` → `ready`.

**Boundaries.**
- The service does NOT publish, schedule, or fire posts. Its terminal state is `ready` (= textually approved).
- The service is unaware of the third-party publishing service, the destination networks, and the rate-limit state.

**Inputs.**
- A post-document authored by a content-author persona.
- A brand-config artefact describing the brand's destination accounts and cadence.

**Outputs.**
- A validated post-document committed on the integration line with `status = ready`.

**Business rules.**
- A post MUST be authored as a structured document with a frontmatter header and a body composed of per-destination-network sections.
- The author of a post MUST NOT set `status = ready`; only an approver may do so. This is the minimal expression of operator-explicit Gate 1.
- Per-destination-network character limits MUST be enforced at validation time (Gate 1), not at publish time.
- The `publish_at` timestamp MUST include an explicit timezone offset (no naive datetimes).

**Error handling.**
- Schema-violating posts are rejected at the pre-merge gate; the change-request cannot merge until repaired.
- Schema validation findings are surfaced as `ValidationFinding` records (see §5.8).

**Workflow.**
1. Author drafts a post-document with `status = draft`.
2. Author opens a change-request.
3. Pre-merge schema-validation gate runs (see §3.3).
4. Approver reviews diff, sets `status = ready`, merges.

### 3.2 Two-Gate Publishing Service (Tier 1)

**Responsibilities.**
- Detect newly-merged `ready` posts.
- Route each post through the per-brand adapter to the third-party publishing service.
- Capture the per-post outcome and write back status + identifiers to the post-document.
- Emit notifications and create tracked work-items on failure.

**Boundaries.**
- The service does NOT decide publish-time correctness of body content; that was Gate 1.
- The service does NOT fire posts. It posts to the third-party service as `draft`. The act of firing belongs to Gate 2 (operator inside the third-party service UI).
- The service does NOT detect post-fire `published` events at this snapshot — that lifecycle closure is currently absent (deferred work).

**Inputs.**
- A set of post-documents in `status = ready` on the integration line.
- The brand-config for each post's brand.
- The per-brand per-destination-network rate-limit state.
- Resolved per-brand credentials.

**Outputs.**
- For each post: a `PublishResult` (see §5.7).
- A stats-dict aggregating per-batch counts.
- Side-effect writes: post-document status update, post-identifier write-back, rate-limit state update.

**Business rules.**
- **Gate 1 (textual approval) is enforced** by the publisher refusing to process posts whose `status != ready`. This is the second of multiple layers enforcing Gate 1.
- **Gate 1 integration-line enforcement**: the publisher MUST verify the post-document is committed on the integration line of the version-control system before processing. A post present only on an unmerged change-request branch MUST be skipped.
- **Gate 2 (visual approval) is enforced** at the wire-level: every post created in the third-party service MUST be created with `status = draft`. No flag, parameter, or environment override may flip this.
- **Past-due is irrelevant to Gate 2**: even if `publish_at` is in the past, the post still lands as a draft. Time pressure does NOT collapse the gate.
- **State writeback on success** sets the post status to `<gate-2-pending>` (= post is in the third-party service awaiting operator visual approval) and records the third-party post-identifier on the document.
- **Replay protection**: re-running the publisher over a post already in `<gate-2-pending>` MUST be idempotent. The publisher MUST NOT create a duplicate draft.
- **Side-effects are best-effort**: notification, work-item creation, and frontmatter writeback failures are logged-and-swallowed, NOT propagated as publisher failures. Publisher availability ranks above publisher correctness for side-effects.

**Error handling.**
- Transient errors trigger a bounded retry sequence with explicit backoff delays (e.g., 10s / 30s / 90s).
- After retry exhaustion OR on a permanent error, the publisher invokes the Notification & Escalation service (§3.6) which emits both an operator-notification AND creates a tracked work-item.
- A retry-exhausted or permanent-error post writes `status = failed` to its post-document with an error-summary field.

**Workflow.**
1. Triggered when a change-set merges to the integration line.
2. Acquire concurrency-group lock to serialise overlapping runs.
3. Resolve credentials via the secret store.
4. Enumerate posts in `status = ready` per brand.
5. For each post: validate integration-line commit; check rate-limit; dispatch via per-brand adapter; capture `PublishResult`.
6. Write back status + identifiers per post.
7. Emit batch summary + per-failure escalations.
8. Return aggregate stats-dict to the caller.

### 3.3 Schema Validation Service (Tier 1)

**Responsibilities.**
- Validate all candidate post-documents against the canonical post-document schema before merge.
- Validate all brand-config artefacts against the brand-config schema before merge.
- Reject change-requests that introduce schema-violating artefacts.

**Boundaries.**
- This service is the SOLE binding pre-merge schema gate. The system MUST NOT rely on the publisher's own validation as the primary gate.
- Validation runs ONLY at change-request time. Post-publish writeback values (e.g., `<gate-2-pending>`) are NOT seen by this gate.
- Cross-brand-config consistency (e.g., does the post's `author` resolve to an account in the brand's destination-account map?) is in scope; cross-repo validation is OOS.

**Inputs.**
- A change-request with a file-diff.
- The current canonical post-document schema.
- The brand-config artefact for each post being validated.

**Outputs.**
- Pass / fail signal back to the version-control system's pre-merge gate.
- A list of `ValidationFinding` records on failure.

**Business rules.**
- Required fields MUST all be present. Required-field set: post identifier, publish-at timestamp, destination-network list, status, brand, author, plus per-section copy.
- Status MUST be one of the canonical enum values.
- Destination-network values MUST all be in the canonical destination-network enum.
- Per-destination-network character limits MUST be enforced.
- The author field MUST resolve to an account in the brand's destination-account map (when the brand-config has the relevant block populated).
- Post identifier MUST match the canonical identifier pattern.
- Publish-at MUST include an explicit timezone offset.

**Error handling.**
- Each finding becomes a separate `ValidationFinding` record.
- The gate fails if any finding is present.
- Findings are emitted to the change-request review surface for the author to repair.

**Workflow.**
1. Triggered on change-request open / update.
2. For each touched post-document: run validate-post.
3. For each touched brand-config: run validate-brand.
4. Aggregate findings.
5. Emit pass / fail to the version-control system's pre-merge gate.

### 3.4 Per-Brand Adapter Layer (Tier 1)

**Responsibilities.**
- Abstract the per-destination-network or per-publishing-channel auth + post-shape differences behind a common interface.
- Provide a uniform `auth_check` capability across all configured destination networks for the auth-health monitor.
- Provide a uniform `publish` capability for the active publishing channel.

**Boundaries.**
- The active publishing channel adapter is the only adapter whose `publish` capability is exercised at publish time.
- The legacy direct-network adapters remain runtime-resident SOLELY for their `auth_check` capability. Their `publish` capabilities are dead at runtime but MUST NOT be removed without removing their `auth_check` coverage.
- The adapter layer does NOT own credential resolution; it consumes credentials passed in by the publisher engine.

**Inputs.**
- A per-brand credentials map.
- A per-brand destination-account map.
- (For `publish`) a normalised post payload.

**Outputs.**
- (For `publish`) a `PublishResult`.
- (For `auth_check`) a per-destination-network pass/fail probe result.

**Business rules.**
- Every adapter MUST honour the abstract interface: `auth_check`, `publish`, plus rate-limit hooks.
- The active publishing channel adapter MUST hardcode `status = draft` in any wire payload sent to the third-party service. This is one of multiple defense-in-depth encodings of the Gate 2 invariant.
- All adapters MUST resolve credentials via env-first / secret-store-fallback. Source-embedded credentials are forbidden.
- Per-destination-network adapters MUST declare their character limit (informational; the binding limit is in the schema).

**Error handling.**
- Adapters distinguish transient errors (eligible for retry) from permanent errors (escalate immediately).
- Rate-limit-exhausted state propagates as a transient error with a delay hint.

**Workflow.**
- The publisher engine instantiates each configured adapter once per run.
- For publish: the active publishing channel adapter handles all destination-network fan-out internally (via the third-party service).
- For auth-check: each registered adapter is iterated and its `auth_check` invoked.

### 3.5 Auth Health Monitor (Tier 1)

**Responsibilities.**
- Probe credential health for every brand × destination-network combination on a recurring schedule.
- Surface failures as tracked work-items routed to the credential-owner persona.

**Boundaries.**
- The monitor does NOT publish, retry, or notify operationally. Its failure surface is the work-item queue alone.
- The monitor's cadence is intentionally LOWER than publish cadence — credential expiry windows are long; daily would be wasteful.

**Inputs.**
- The set of brands and their declared destination-network credentials map.

**Outputs.**
- An `AuthHealthReport` per run.
- One tracked work-item per run on any failure (with title scoped to the run-date for natural deduplication).

**Business rules.**
- Probe cadence: weekly (or, more loosely, at most-N-days for any token within its grace window).
- A probe failure for any brand × destination-network combination MUST create a tracked work-item.
- Probe failures DO NOT trigger operator-notification — the urgency profile (days of warning) is wrong for a push channel.
- The work-item MUST carry a label routing it to the credential-owner persona.

**Error handling.**
- A probe-execution error (vs probe-result-failure) is treated as a probe-result-failure for escalation purposes.
- Multiple failures in one run produce ONE work-item with a multi-line body, not N work-items.

**Workflow.**
1. Recurring-schedule-triggered weekly.
2. Resolve credentials via the secret store.
3. For each brand: instantiate every adapter the brand has credentials for; invoke `auth_check`.
4. Aggregate results into `AuthHealthReport`.
5. On any failure: create a tracked work-item with the run-date in the title.

### 3.6 Notification & Escalation Service (Tier 1)

**Responsibilities.**
- On publish-time permanent error or retry exhaustion: emit BOTH an operator-notification AND create a tracked work-item.
- The two MUST be paired — never notification-only, never work-item-only.

**Boundaries.**
- The service is the publish-path's escalation surface. The auth-health monitor uses a different escalation pattern (work-item only).
- This service does NOT handle success-path notifications at this snapshot. (Documented intent calls for a Gate-bridging "drafts ready" notification; current state is failure-only.)

**Inputs.**
- A failure context: post identifier, brand, destination-network, error class, error message.

**Outputs.**
- One operator-notification message.
- One tracked work-item with title and body capturing the failure context.

**Business rules.**
- Both side-effects MUST be best-effort: failure of the notification channel MUST NOT prevent the work-item creation, and vice versa. Failure of either MUST NOT propagate as a publisher failure.
- Work-item titles MUST be deterministic enough that repeated identical failures collide on the version-control system's natural-key dedupe.
- The work-item MUST carry a label routing it to the appropriate ops persona.

**Error handling.**
- The service swallows its own errors. Logging-only.

**Workflow.**
1. Invoked from the publisher engine's final-failure handler.
2. Construct the `NotificationPayload` and the `WorkItemPayload`.
3. Send notification (best-effort).
4. Create work-item (best-effort).

### 3.7 Operator Tooling (Tier 2)

**Responsibilities.**
- Provide ad-hoc manual operations against the third-party publishing service: account discovery, post listing, post inspection, post deletion.
- Provide pre-merge validation invocations that can also be run locally.

**Boundaries.**
- Operator tooling is OUT-OF-BAND of the publish path. It MUST NOT alter post-document state or rate-limit state in ways that affect the next scheduled run.
- Tooling does NOT bypass either gate. Operator may delete a draft inside the third-party service via tooling; the post-document on the integration line reflects the prior state and the next scheduled publish run will respect replay protection.

**Inputs.**
- Operator-supplied parameters.
- Resolved credentials (env-first / secret-store-fallback).

**Outputs.**
- Human-readable output.
- Side-effects on the third-party publishing service (e.g., delete).

**Business rules.**
- Tooling MUST resolve credentials from env or secret store; never source.
- Tooling actions are logged but not necessarily tracked.

**Error handling.**
- Tooling errors are surfaced to the operator via stderr / non-zero exit; no escalation primitives fire.

**Workflow.**
- Operator invokes a subcommand with parameters; the tool reads credentials, makes API calls, prints results.

---

## Section 4 — Cross-Cutting Specs

### 4.1 Two-gate invariant (defense-in-depth)

Every post MUST pass both gates before reaching `published`. The invariant is encoded REDUNDANTLY across at least four layers:

1. **Schema** declares `ready` as the gate-1-passed status.
2. **Schema validation** at pre-merge rejects malformed posts.
3. **Publisher state-machine** processes only posts in `status = ready` AND committed on the integration line.
4. **Adapter wire payload** hardcodes `status = draft` for the third-party publishing service, ensuring Gate 2 always exists.

No single test or check covers the end-to-end invariant; the redundancy IS the design.

### 4.2 Replay protection

The publisher MUST be idempotent over the same post: re-running publish MUST NOT create a duplicate draft in the third-party service. Mechanisms:
- The publisher refuses to act on posts in `status != ready`.
- After successful create, the post-document is updated to `<gate-2-pending>`, taking it out of the `ready` set.
- The third-party post-identifier is persisted on the post-document so any subsequent operation can reference the original.

### 4.3 Authorization model

- **Scheduled-automation runs** (publish, auth-check) authenticate via service-principal short-lived federated tokens. No long-lived shared secrets.
- **Operator scripts** authenticate via env-var-resolved tokens. The tokens MUST come from the secret store; placing tokens in source is forbidden.
- **Pre-merge validation** runs without privileged credentials — it inspects only the change-request file diff.
- **Schema validation** has no auth surface.

### 4.4 Status lifecycle

The canonical status enum has exactly 7 values:
`draft`, `ready`, `<gate-2-pending>`, `scheduled`, `published`, `failed`, `<phase-2-deferred>`.

(Plus optional `deferred` for rate-limit-deferred posts in legacy paths.)

The lifecycle MUST be canonical across schema, publisher state-machine, validation, and tests. **Phase 4 finding: at this snapshot, the lifecycle is NOT canonical** — see I-12.

### 4.5 Acceptance-criteria identifier uniqueness

Spec acceptance-criteria identifiers MUST be globally unique within the repository. Re-using `AC1`, `AC2`, ... across two spec sources without disambiguation breaks the traceability convention. **Phase 4 finding: at this snapshot, the identifier space is NOT globally unique** — see I-11.

### 4.6 Auth-health window

The weekly probe MUST trigger a tracked work-item if any token is within N days of expiry. (The window definition is intentionally loose; the binding rule is that no token should reach expiry without at least one prior probe-fail surfaced.)

### 4.7 Per-destination-network character-limit enforcement

Per-destination-network character limits MUST be enforced at Gate 1 (pre-merge). Enforcement at publish time is too late: the post would already have passed textual review.

The character-limit table MUST be consistent across the schema, the validator, and any adapters that declare it. (Multiple declaration sites are permitted defensively; they MUST agree.)

### 4.8 State persistence

Per-brand per-destination-network rate-limit state MUST persist between publisher runs. The state file format MUST be atomic-write-then-rename to prevent corruption from partial writes.

### 4.9 Notification semantics

For publish-path failures: notification fires on retry exhaustion AND on permanent error AND ALWAYS PAIRED with work-item creation. There is no notification-only path; there is no work-item-only path on the publish surface. (The auth-health surface is different — see §3.5.)

### 4.10 Concurrency

Publish runs MUST be serialised on a per-brand-publishing-channel basis. Two simultaneous publish runs over the same brand and channel would race on rate-limit state, post-document writeback, and (potentially) duplicate-create at the third-party service. The runtime MUST acquire a concurrency-group lock before processing.

### 4.11 Forward-pointer hygiene

Phase-2-deferred elements (placeholder fields, placeholder enum values, placeholder directories) MAY exist BUT each one SHOULD be labelled in-place as Phase-2 / future-work. Unlabelled placeholders are indistinguishable from oversight.

---

## Section 5 — Data Contracts

### 5.1 `PostDocument`

**Shape:** structured-document with frontmatter header + per-destination-network body sections.

**Frontmatter fields (15 total — 14 top-level + 1 nested object):**

| # | Field | Type | Required | Notes |
|---|---|---|---|---|
| 1 | `id` | string | yes | matches canonical identifier pattern |
| 2 | `publish_at` | string | yes | ISO 8601 with explicit timezone offset |
| 3 | `platforms` | list of enum | yes | non-empty; each in destination-network enum |
| 4 | `status` | enum | yes | one of 7 canonical values |
| 5 | `brand` | string | yes | matches an existing brand-config |
| 6 | `author` | enum | yes | resolves to brand's destination-account map |
| 7 | `account_id` | string | optional | per-destination-network override |
| 8 | `<channel-mode>` | bool | optional | routes via active publishing channel vs legacy direct |
| 9 | `campaign` | string | optional | campaign-grouping handle |
| 10 | `tags` | list of string | optional | free-form tags |
| 11 | `published_at` | string (UTC) | optional | written by publisher post-fire (currently unused) |
| 12 | `<channel-post-id>` | string | optional | written by publisher post-create |
| 13 | `post_ids` | object | optional | per-destination-network identifiers (legacy direct path) |
| 14 | `error` | string | optional | written on terminal failure |
| 15 | `creative` | object | optional | nested: `type` (enum incl. `<phase-2-deferred>`), `image_url`, `video_url` |

**Status enum (7 values):** `draft`, `ready`, `<gate-2-pending>`, `scheduled`, `published`, `failed`, `<phase-2-deferred>`.

**Body:** post-frontmatter sections, one per destination network, headed by canonical section markers. Each section's character count MUST satisfy the per-destination-network limit.

### 5.2 `BrandConfig`

**Shape:** structured config artefact, one per brand.

**Fields:**
- `brand_id` — stable identifier.
- `display_name`.
- `cadence` — timezone + per-platform posting cadence hints.
- `credentials` — map of destination-network → secret-name (resolves through the secret store).
- `accounts` — map of destination-network → destination-account-id.
- `<channel>` — active-publishing-channel routing block: location-id, per-author destination-account map.
- `avatar_id` — Phase-2 placeholder (currently nullable).

### 5.3 `RateLimitState`

**Shape:** per-brand per-destination-network counter blob.

**Fields:**
- `brand`.
- `platform` (destination network).
- `window_start_ts`.
- `count_in_window`.
- `limit`, `window_seconds` (defaults from canonical rate-limit table).

**Persistence:** one file per brand per destination network; atomic write-then-rename.

### 5.4 `AuthHealthReport`

**Shape:** per-run aggregate.

**Fields:**
- `run_ts`.
- `results`: list of `{brand, platform, ok: bool, error?: string}`.
- `summary`: counts by outcome.

### 5.5 `WorkItemPayload`

**Shape:** the body sent to the version-control system's tracked-work-item-create.

**Fields:**
- `title` — deterministic; for auth-health includes the run-date for natural dedupe.
- `body` — multi-line; includes brand, destination-network, error context, run identifier.
- `labels` — at minimum: a kind-label (e.g., `credential-failure` / `publish-failure`) AND an ops-persona-routing label.

### 5.6 `NotificationPayload`

**Shape:** the body sent to the operator-notification channel.

**Fields:**
- `subject`.
- `body` — short; includes brand, destination-network, error summary.
- `severity` — informational; permanent vs retry-exhausted.

### 5.7 `PublishResult`

**Shape:** per-post outcome record.

**Fields:**
- `post_id` (the local post identifier).
- `outcome` — one of `published_as_draft` (success), `transient_failure`, `permanent_failure`, `skipped`.
- `<channel-post-id>` — set on success.
- `error` — set on failure; class + message.
- `attempts` — integer.

### 5.8 `ValidationFinding`

**Shape:** per-violation record from a validate-* invocation.

**Fields:**
- `path` — relative path of the offending artefact within the change-request.
- `field` — name of the offending field (or `<root>` for whole-document issues).
- `rule` — the violated rule's identifier.
- `message` — human-readable description.

---

## Section 6 — Invariants

Numbered, named, individually testable. Each MUST hold true in any compliant implementation.

- **I-1** — Every post MUST be authored as a structured document with a frontmatter header validated against the canonical post-document schema.
- **I-2** — Schema validation MUST gate at version-control merge time. No malformed post may reach the publisher.
- **I-3** — Gate 1 (textual approval) MUST be operator-explicit: `status = ready` is set by the approver, never by the author.
- **I-4** — Gate 2 (visual approval) MUST occur in the third-party publishing service, not in this system. The system never fires posts.
- **I-5** — Posts created in the third-party service by this system MUST be created as drafts. No flag, parameter, environment override, or code path may produce a non-draft create.
- **I-6** — Re-running publish over a post already past Gate 1 MUST be idempotent. No duplicate drafts.
- **I-7** — Auth-health MUST be probed at least weekly per brand × destination-network combination.
- **I-8** — An auth-health probe failure MUST create a tracked work-item routed to the credential-owner persona.
- **I-9** — On publish-path final failure: an operator-notification AND a tracked work-item MUST both fire. There is no notification-only path; there is no work-item-only path on the publish surface.
- **I-10** — Per-destination-network character limits MUST be enforced at Gate 1.
- **I-11** — Spec acceptance-criteria identifiers MUST be globally unique within the repository. *(Phase 4 finding: currently violated — two parallel spec sources collide on AC1, AC2, AC5, AC6, AC7, AC8.)*
- **I-12** — The status enum MUST be canonical across schema, models, validator, and tests. *(Phase 4 finding: currently violated — `<gate-2-pending>` is in the publisher and tests but absent from the schema and validator.)*
- **I-13** — Credentials MUST resolve from the secret store, never from source. Both scheduled-automation and operator-tooling paths MUST honour env-first / secret-store-fallback resolution.
- **I-14** — Side-effects on the publish path (notification, work-item, frontmatter writeback) MUST be best-effort: their failure MUST NOT propagate as publisher failure. Publisher availability ranks above publisher correctness for side-effects.
- **I-15** — Per-brand publish runs MUST be serialised by a concurrency-group lock. Two simultaneous publish runs over the same brand × publishing channel are forbidden.
- **I-16** — Rate-limit state MUST persist between publisher runs and MUST be written atomically (write-then-rename).
- **I-17** — Legacy direct-network adapters MUST NOT be removed without removing their corresponding `auth_check` coverage. They are runtime-resident even though their `publish` capability is dead.
- **I-18** — `publish_at` timestamps MUST include an explicit timezone offset. Naive datetimes are rejected at validation.

---

## Section 7 — Out-of-Spec

The following surfaces are intentionally outside this specification. Implementations may treat them as black boxes or stubs; their internals are not constrained by this document.

- **Third-party social-publishing service internals.** The contract surface is enumerated in §2.1; behaviour beyond that surface is opaque.
- **Operator-notification channel internals.** Wire protocol, delivery guarantees, retention — opaque.
- **Per-destination network internals.** Reached only via the third-party publishing service in the active path; legacy direct adapters reach them only for auth-probing.
- **Avatar-rendering forward work** (the Phase-2 placeholder fields, enum values, and directory structures). The spec acknowledges their existence as forward-pointers but does not define their behaviour.
- **Cross-channel re-posting** (e.g., a content-management system's rendering of the same post). Out of scope; this system stops at the third-party publishing service.
- **Cross-repo design-spec contents.** The design specs that authored the AC lists live in cross-repo issue trackers; their contents are not normative for this document.
- **Parent strategic issue.** Marketing-surface scope discussions are out-of-scope.
- **Secret-store provisioning.** Secret lifecycle is owned by an infrastructure-side repo; this document only consumes the secret-store contract (§2.4).
- **Authoring tooling.** Content-author workflow tooling is out-of-scope; this system is the publisher, not the author.
- **`agent:*` consumer automation.** This system writes labels to tracked work-items; the consumer triage automation is out-of-scope.
- **Version-control branch-protection rules.** Referenced by intent (the pre-merge gate relies on it) but the rules themselves are version-control-side configuration not owned by this system.
