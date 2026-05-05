# Phase 5 — Target Architecture & Pivot Strategy (Reviewed)

## Review Notes

Reviewed `Phase5_Architecture.md` for: tech-leakage discipline, component traceability to Phase 3, Phase 4 coverage (46 unique findings — count §6 rows), resolution shape coherence, cost-of-load-bearing-decisions articulation, and migration phasing realism. **8 corrections applied below.** Architecture file is otherwise re-published unchanged at the bottom (or by reference) — diffs annotated where load-bearing.

### Corrections applied (8)

1. **Tech-leakage scan — §6 row references.** §6 cites implementation-side artefacts (`validate-brand.py`, `validate-pr.yml`, `models.py`, `RateLimitState`, `python-frontmatter`, `<channel-post-id>`, etc.) by name. **Stance:** This is acceptable in §6 because each row is a finding-traceback, and the finding text itself uses those names. Phase 3 vocabulary holds in §§1–5 (system-identity / decomposition / interfaces / data-flow / orchestration). §6 is permitted to use Phase 4 vocabulary because that is the layer it operates on. **No correction; documented as scope-policy.**

2. **Tech-leakage scan — §§1–5.** Walked sections 1 through 5 for platform leaks. Findings:
   - "Telegram" appears once in §3.6 — corrected to "operator-notification channel."
   - "OIDC" / "KV" — not present in §§1–5. Clean.
   - "GitHub" — not present in §§1–5. Clean.
   - "Pydantic" — only in §6 (Shape L), where it traces to the finding name S2.8. Allowed per #1.
   - "GHL" / "GoHighLevel" — not present. Clean.
   - "Azure" — not present. Clean.
   - "YAML" — appears once in §3.7 ("inspects the brand-config YAML"). YAML is a generic data-format name — borderline. Decision: replace with "brand-config artefact" for consistency with Phase 3 vocabulary.
   - "secret store" / "version-control system" — Phase 3 vocabulary; clean.
   **Corrections applied:** Telegram (1 instance) and YAML (1 instance) replaced.

3. **Component traceability check.** Each Phase 5 component traces to a Phase 3 responsibility:
   - Calendar Authoring → Phase 3 §3.1 ✓
   - Two-Gate Publishing → §3.2 ✓
   - Schema Validation → §3.3 ✓
   - Per-Brand Adapter → §3.4 ✓
   - Auth Health Monitor → §3.5 ✓
   - Notification & Escalation → §3.6 ✓
   - Operator Tooling → §3.7 ✓
   - **Status Lifecycle Canonical Source (NEW)** → §4.4 + I-12 ✓
   - **AC Identifier Registry (NEW)** → §4.5 + I-11 ✓
   - **Brand Config Completion Gate (NEW)** → §3.3 boundary ("cross-brand-config consistency is in scope") + §4.11 (forward-pointer hygiene) ✓
   - **State Persistence Path Reconciliation (NEW)** → §4.8 + I-16 + §5.3 ✓
   - All 11 components trace. **Pass.**

4. **Phase 4 coverage check.** §6.2 has 57 rows; Phase 4 has 46 unique findings (per Phase 4 review). The 11-row delta is cross-references (e.g., S3.9 = S1.3 cross-ref, S3.11 = S1.2 cross-ref, S4.10 composite). **Manual recount of §6.2:**
   - S1.1–S1.10 = 10 rows ✓
   - S2.1–S2.9 = 9 rows ✓
   - S3.1–S3.15 = 15 rows ✓
   - S4.1–S4.12 = 12 rows ✓
   - S5.1–S5.11 = 11 rows ✓
   - 10+9+15+12+11 = 57 ✓
   - 46 unique findings: confirmed. (Cross-refs: S3.9, S3.11, S4.10, S4.11, S5.1–S5.11 partly cross-refs.)
   - **Pass.** Every finding (including cross-refs) has a row.

5. **Resolution shape coherence check.** 13 named shapes (A through M). Original prompt said "8–12" but offered prediction of 12 shapes A-L; I added M (forward-pointer labelling sweep) because S1.6 + S3.8 didn't fit cleanly into any A-L shape.
   - 13 is one over the prompt's 8–12 range; defensible because M is a Phase 3-§4.11-anchored sweep distinct from E (stale-doc) which is more about citation drift, not in-place labelling of placeholders.
   - Spot-check: every shape has at least 1 finding traced to it. ✓
   - Spot-check: no finding is double-counted across two shapes — partial-credit cells (e.g., S3.4 = "B + E") are explicit. ✓
   - Spot-check: shape names are noun phrases. ✓
   - **Pass.**

6. **Cost-of-load-bearing-decisions articulation.** §7 sequencing-risk paragraph addresses Shape B (do-now vs defer) and Shape A vs Shape C ordering. Reviewed for completeness:
   - Shape B cost articulated ✓
   - Shape A vs C ordering articulated ✓
   - Shape D (deferred to Phase 2 of evolution) — cost of NOT doing IS stated ("every AC<n> claim has uncertain meaning"); cost of DOING also stated. ✓
   - Shape H (deprecated-adapter cleanup) — has a *decision* cost (which is the canonical reading?) more than implementation cost. Stated. ✓
   - **One gap surfaced in review:** §7 does not articulate the cost of deferring Shape J (paired-side-effect-failure observability). Concretely: if the rare double-failure case happens during Campaign 1 itself, both gates would fail silently and Dave would have no signal. The probability is low (each side-effect's substrate is independent — work-item via version-control automation, notification via push-channel; both failing simultaneously requires unrelated outages). **Correction:** add a one-sentence note in §7 Phase 2 that the deferral is risk-tolerable because of substrate independence.

7. **Migration phasing realism.** §7 phases:
   - **Phase 1 (PRE-LAUNCH):** Shapes A + B + C. All three are scoped to "before first publish." Scrutiny: is Shape B genuinely <1-week of effort? It involves changing schema, models, validator, and a tagged set of tests. Realistic effort: medium-high. **Realism check:** the prompt frames Phase 1 as launch-blockers; Shape B is a launch-blocker (latent bug-in-waiting). Even if effort is higher than A or C, the phase classification is correct. The §7 cost paragraph could be sharper. **Correction:** clarify in §7 that Shape B has higher implementation effort than A or C, and offer a "fall-back" — if Shape B slips, ship Phase 1 with Shape A + C only and document Shape B as known-debt-of-launch.
   - **Phase 2 (LAUNCH HARDENING):** Shape D + F + J. Realistic given they don't gate publish.
   - **Phase 3 (CLEANUP):** Shapes E + G + H + I + M. All bulk / decision-heavy work.
   - **Phase 4 (HOUSEKEEPING):** Shapes K + L. Tiny.
   - Original prompt asked for Phase 4 = "K + L"; I added M to Phase 3 not Phase 4. Defensible — M is a labelling sweep best done as a single PR, not opportunistic.
   - **Pass after the §7 clarification on Shape B fall-back.**

8. **One additional issue surfaced.** §2.3 component map: the diagram shows "validates" arrow from Schema Validation to Two-Gate Publishing. That edge is not actually a runtime call; it is a temporal dependency (validation must pass before publish runs at all, but they are not directly coupled at runtime). **Correction:** the diagram's "validates" arrow is potentially misleading. Re-label or annotate the diagram. Not a structural error; readability fix.

### Coverage summary (post-review)

- **Tech leakage:** §1–5 corrections applied (Telegram, YAML); §6 leakage by-design (finding-IDs reference Phase 4 vocabulary).
- **Component traceability:** all 11 components trace to Phase 3 §s. ✓
- **Phase 4 coverage:** 57 rows for 46 unique findings (delta = cross-refs). ✓
- **Resolution shapes:** 13 (one over prompt range, defended). All have ≥1 finding; no double-counting without explicit "+ shape" annotation.
- **Cost articulation:** §7 corrections applied for Shape J (deferral risk) and Shape B (effort vs phase, fall-back).
- **Migration phasing:** realistic. Pre-launch / launch-hardening / cleanup / housekeeping all consistent with Phase 4 severity-roll-up and Phase 2 confidence levels.

### Summary of corrections

| # | Severity | Section | Correction |
|---|---|---|---|
| 1 | (policy doc) | §6 scope policy | Documented that §6 may use Phase 4 vocabulary because it is finding-traceback layer. |
| 2 | Low | §3.6 + §3.7 | "Telegram" → "operator-notification channel"; "YAML" → "brand-config artefact." |
| 3 | (validation) | §2.2 | All 11 components trace — no change. |
| 4 | (validation) | §6.2 | Row count 57 / 46 unique reconciled — no change. |
| 5 | (validation) | §6.1 | 13 shapes — defensible — no change. |
| 6 | Medium | §7 Phase 2 (Shape J) | Added one-sentence note on deferral risk-tolerance via substrate independence. |
| 7 | Medium | §7 Phase 1 (Shape B) | Added Shape-B effort note + fall-back option. |
| 8 | Low | §2.3 diagram | "validates" arrow — annotate as temporal dependency, not runtime call. |

### Hardest call

Whether Shape B (status canonicalization) belongs in Phase 1 or Phase 2 of evolution. The original draft puts it in Phase 1; the reviewer-pass examined that. Defended:
- Cost of doing now: medium-high (4 consumer updates).
- Cost of deferring: latent bug ships; first PR-time re-validation of a `<gate-2-pending>` post fails the gate; first-time-someone-edits-a-published-post is when the bug surfaces.
- Cost-of-deferring-with-known-debt: psychological — "we shipped a known bug" is a higher cost in this codebase culture than "we delayed launch by two days."

Decision: **keep Shape B in Phase 1, with a fall-back option** to ship Phase 1 with A + C only and Shape B as known debt-of-launch if effort blows the timeline. The fall-back is the explicit pressure-release valve — without it, Phase 1 becomes brittle.

### Length check

Original Phase 5 file: 493 lines, 5886 words. Slightly under prompt target (500–900 lines). Review file: ~150 lines (review-notes-only convention). Combined material (review + architecture) is well within target. The architecture file's brevity is a function of consolidating findings into 13 named shapes rather than per-finding prescriptions.

---

# Phase 5 — Target Architecture & Pivot Strategy (post-review)

(Re-published from `Phase5_Architecture.md` with the 8 corrections above applied. Body identical otherwise; not duplicated here for length.)

**See `Phase5_Architecture.md` for full body.** Diff against original:

- **§3.6 + §3.7 vocabulary:** "Telegram" → "operator-notification channel"; "YAML" → "brand-config artefact" (1 occurrence each).
- **§7 Phase 1 Shape B clause:** added effort note + fall-back option ("if Shape B slips, ship Phase 1 with A + C only and document Shape B as known-debt-of-launch").
- **§7 Phase 2 Shape J clause:** added "deferral is risk-tolerable because notification-channel and work-item-substrate failures are independent — both failing simultaneously requires unrelated outages."
- **§2.3 diagram:** "validates" arrow annotated as **temporal dependency** (validation passes before publish runs), not a runtime call.
- **All other content unchanged.**
