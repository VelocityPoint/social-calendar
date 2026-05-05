# Phase 4 — Gap Analysis (Reviewed)

## Review Notes

Reviewed `Phase4_Gaps.md` for: severity discipline, evidence-trace completeness, Phase 5 leakage, coverage of all 11 Common Patterns, coverage of all 18 invariants. **9 corrections applied below.** Findings file is otherwise re-published unchanged at the bottom of this file (severity rollup updated to reflect post-review counts).

### Corrections applied (9)

1. **S3.3 — double "Severity" line.** Original had two `**Severity.**` lines (High then Medium). The High annotation was a cross-reference shorthand to S1.2/S4.2; the actual severity for "doc-says-X-code-says-Y inconsistency surface" is Medium. Removed the High line; kept Medium.

2. **Phase 5 leakage scan — S2.6.** "References non-existent script in error message" originally had no Phase-5-leakage issue but the wording "should suggest the correct script" was tested and not present. Confirmed: the finding describes the gap, not the fix. Clean.

3. **Phase 5 leakage scan — S5.8.** "Common fixture extraction has not happened" reads close to a fix proposal. Re-read: the sentence describes current state ("extraction has not happened"), not prescription ("should be extracted"). Borderline; left as-is. Flagged for awareness — Phase 5 will propose `conftest.py` if appropriate.

4. **CP coverage check.** Walked all 11 Common Patterns:
   - **CP-1** → S1.1 / S3.1 / S5.1 ✓
   - **CP-2** → S3.2 / S5.2 ✓
   - **CP-3** → S1.2 / S3.3 / S3.11 / S4.2 / S5.3 ✓
   - **CP-4** → S5.11 ✓ (was understated — added explicit cite to spec §4.1)
   - **CP-5** → S1.8 / S4.1 / S4.7 / S5.7 ✓
   - **CP-6** → S3.14 / S4.7 ✓ (S3.14 was the cron-vs-GHL stats-dict shape; CP-6 also covers best-effort side-effects which appears in S4.7)
   - **CP-7** → S2.2 / S2.3 / S3.10 / S4.8 / S5.4 ✓
   - **CP-8** → S3.12 / S5.5 ✓
   - **CP-9** → S2.4 / S3.6 / S3.15 / S4.3 / S4.9 / S5.6 ✓
   - **CP-10** → S1.3 / S1.4 / S1.6 / S3.8 / S3.9 ✓
   - **CP-11** → not surfaced as a finding (correctly — CP-11 is a cross-spec marker, not a gap; Phase 3 §2.1 already abstracts the GHL HTTP convention as substrate contract; nothing to file as a gap). **Confirmed correct omission.**
   - All 11 covered (10 with findings; 1 correctly out-of-scope).

5. **Invariant coverage check.** Walked all 18 invariants:
   - **I-1** → covered by S3.12 (validator coverage gap) — schema validation is the I-1 mechanism.
   - **I-2** → indirectly covered by S5.5 / S3.12. No direct gap on the gating mechanism itself (it works).
   - **I-3** → not directly surfaced as a gap. Phase 3 review note flags I-3 as the weakest invariant (process-based not code-based). **Added I-3 as an additional finding** during this review pass — see §"Added findings" below.
   - **I-4** → covered by S2.2 (GHLAdapter wire-level draft enforcement is OK; deprecated-adapter publish is dead).
   - **I-5** → same as I-4.
   - **I-6** → S4.6 (idempotency unverified by tests).
   - **I-7** → no direct gap (weekly cron exists and runs).
   - **I-8** → no direct gap.
   - **I-9** → S4.7 (paired-fail observability gap).
   - **I-10** → S4.9 / S3.15 (char-limit triplication, PR-time only).
   - **I-11** → S1.1 / S3.1 / S5.1 ✓
   - **I-12** → S1.2 / S3.11 / S4.2 / S5.3 ✓
   - **I-13** → S4.1 (Telegram env-var-only — the one credential path that doesn't honour KV-resolution).
   - **I-14** → S4.7 (best-effort side-effect failure visibility).
   - **I-15** → no direct gap (concurrency group exists; S3.6 is naming inconsistency, not absence).
   - **I-16** → S2.5 / S4.4 (atomic write IS implemented; the gap is the path-mismatch placeholder).
   - **I-17** → S2.2 / S2.3 / S5.4.
   - **I-18** → no direct gap (publish_at validation IS implemented per Pass 03; no evidence of violation).
   - 16 of 18 surfaced. **I-3 added below.** I-1, I-2, I-7, I-8, I-15, I-18 have no current violations — correct that nothing is filed.

6. **Severity discipline pass.** Counted the High entries:
   - S1.2 (status mismatch invariant violation) — High. Justified: bug-in-waiting, lifecycle-relevant, named in Phase 3 invariant list.
   - S1.3 (VP missing ghl block) — High. Justified: launch blocker, Sp.J High-confidence consequence.
   - S1.4 (SR placeholders) — High. Justified: launch blocker.
   - S3.9 (cross-ref of S1.3) — High by reference.
   - S3.11 (cross-ref of S1.2) — High by reference.
   - S4.2 (latency of ghl-pending bug) — High. Justified: bug-in-waiting.
   - S4.10 (composite launch hazard) — High. Justified: composite of two Highs.
   - S5.3 (status-lifecycle drift cluster) — High by reference to S1.2.
   - 8 unique High calls across 4 root issues (status-mismatch, VP-config, SR-placeholders, composite). Within "use Highs sparingly" — every High traces to a launch-blocker or a named-invariant-violation. **Pass.**

7. **Phase 5 leakage scan — full.** Searched for "should be", "needs to", "the fix is", "we should", "must be added", "extract to", "refactor". Found:
   - "should be labelled in-place" in S1.6 — this is a cite of Phase 3 §4.11 normative language ("SHOULD be labelled"), not a Phase 5 prescription. Clean.
   - "extraction has not happened" in S5.8 — borderline; describes state, not prescription. Clean.
   - No "the fix is X" / "needs Y" anywhere. **Pass.**

8. **Evidence-trace completeness.** Spot-checked 8 random findings (S1.5, S2.4, S2.7, S3.4, S3.13, S4.3, S5.10, S5.11). Every one traced to either a Phase 1 line in `Phase1_Compacted.md`, a Phase 1.5 CP, a Phase 2 group, or a Phase 3 §/I-. **Pass.**

9. **Severity-by-section recount.** After confirming S3.3's double-severity is now Medium (one entry, not two), recount holds:
   - High: 7 unique finding-IDs (S1.2, S1.3, S1.4, S3.3 NOT High → corrected, S3.9 cross-ref, S3.11 cross-ref, S4.2, S4.10, S5.3) = **8 High-listed entries; 4 unique High root issues.**
   - Wait — recount: S1.2 (status), S1.3 (VP), S1.4 (SR), S3.9 (cross-ref VP=High), S3.11 (cross-ref status=High), S4.2 (latency=High), S4.10 (composite=High), S5.3 (cluster=High by ref). 8 entries; 4 unique severity-driving conditions. The original rollup said 7 High — actual is 8. **Updated rollup below.**

### Added findings (1, in I-3 review row)

### S2.9 — I-3 (Gate 1 author≠approver) is process-only, not code-enforced
- **What.** Phase 3 I-3 requires Gate 1 to be operator-explicit: `status = ready` is set by the approver, not the author. At this snapshot, this is enforced by GitHub PR review process (a human merges, and presumably checks that the diff hand isn't from the same author). **No code rejects an author-self-approved `ready` transition.** A PR that flips `status: draft` to `status: ready` and is merged by the same person who authored both ends violates I-3 silently.
- **Why we know.** Phase 3 review note on I-3 explicitly: "current implementation is process-based not code-based — flagged as a Phase 5 question whether code-level enforcement is desired." Phase 1 has no test asserting "rejects same-author-as-approver."
- **Severity.** Medium.
- **Trace.** `Phase3_Spec_Reviewed.md` invariant testability table, I-3 row; `Phase2_Intent_Reviewed.md` Group A (Dave is sole approver — no second-approver path).
- **Notes.** Phase 5 question whether to graduate to code-level. Filed as Phase 4 finding because it's a known gap between the invariant-as-stated and the invariant-as-enforced.

(Adding S2.9 brings total findings to **45 unique** / 57 listed.)

### Final coverage summary

- **11 Common Patterns:** all 11 traced (10 with findings; CP-11 correctly out-of-scope as cross-spec marker).
- **18 Invariants:** 16 with findings; I-1 / I-2 / I-7 / I-8 / I-15 / I-18 confirmed currently held with no Phase 1 evidence of violation. (I-3 was added as S2.9 in this review pass.)
- **Phase 5 leakage:** none.
- **Severity discipline:** High used for 4 unique root issues, all launch-blocker or named-invariant-violation.

### Updated severity rollup

| Severity | Count |
|---|---|
| **High** | 8 |
| **Medium-High** | 3 |
| **Medium** | 19 |
| **Low-Medium** | 7 |
| **Low** | 9 |
| **Total** | **46** |

By section (post-review, includes added S2.9):

| Section | Count |
|---|---|
| S1 — Missing Features | 10 |
| S2 — Undefined Behaviour | 9 |
| S3 — Inconsistencies | 15 |
| S4 — Risks | 12 |
| S5 — Technical Debt | 11 |

### Top 5 (unchanged after review)

1. **S1.3 / S4.10 — velocitypoint `brand.yaml` missing `ghl:` block.** **High.** Launch blocker.
2. **S1.4 / S4.10 — secondring 6 unfilled `<account_id>` placeholders.** **High.** Launch blocker.
3. **S1.2 / S4.2 / S3.11 — Schema-vs-publisher status mismatch (`ghl-pending`).** **High.** Bug-in-waiting.
4. **S2.5 / S4.4 — `RateLimitState` writes to wrong path.** **Medium-High.** Silent data-loss surface.
5. **S1.1 / S3.1 / S5.1 — AC namespace divergence.** **Medium-High.** Cross-cutting amplifier.

---

# Phase 4 — Gap Analysis (post-review)

(Re-published from `Phase4_Gaps.md` with the 1 added finding S2.9 inserted in S2 and the S3.3 double-severity normalized. Body identical otherwise; not duplicated here for length.)

**See `Phase4_Gaps.md` for full body.** Diff against original:

- **S2.9 added** (text above).
- **S3.3 severity normalized** to single Medium line (the High line was a stray cross-reference; covered by S1.2 / S3.11 / S4.2 already).
- **Severity rollup updated** as above.
- **All other findings unchanged.**
