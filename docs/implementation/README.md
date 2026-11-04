# Implementation Units

This directory holds the approved working context for active SourcePilot implementation units.

## Current implementation unit

**[M6-U4 — Recovery and Failure-State Hardening](M6-U4.md)** is `READY_TO_COMMIT` after **DONE CHECK PASS** on 2026-11-04. Independent Review passed with no actionable findings and Browser QA passed, as explicitly confirmed by the user. Both approved frontend improvements are complete: empty discovery explains its result with a navigation-only Brief link, and failed quote-status reads recover through GET-only Retry. All eight recovery scenarios retain their approved dispositions; the six previously adequate paths are preserved. All seven Browser QA scenarios have sufficient retained evidence, including unchanged business rules/authorization, no status-retry mutation or extra processing attempt, failed PDF → manual entry → explicit confirmation → comparison, and session isolation/navigation. The original 12/12 browser run and final 1/1 supplemental selection remain preserved with their intermediate history. Backend evidence remains **1,264 passed, 1 failed**, with the test's incorrect approval assumption corrected and the affected supplier suite subsequently **10/10 passing**; no unperformed full-suite rerun or summed unique count is claimed. Frontend evidence remains 190 full-suite passes and 34 final quote-test passes with overlapping counts; lint, types and production build pass. Done Check verified the complete 17-file candidate diff, documentation, scope, secrets and artifacts using existing evidence, without rerunning tests/builds/evals or making provider calls. The unsaved-draft loss during another quote's explicit upload is **a nonblocking carry-forward UX limitation, not an M6-U4 regression or acceptance violation**: the responsible code is identical to pre-M6-U4 HEAD, isolated status Retry preserves drafts, and the sequential recovery workflow passes. Save the manual draft before another upload; no reconciliation fix was implemented. Only the unit document and index changed during Done Check. M6-U1–U3 records/risks and all review/QA evidence remain unchanged. Nothing staged or committed. Stop before commit; do not begin M6-U5.

## Previous implementation units

**[M6-U3 — Security and Abuse Hardening](M6-U3.md)** is `COMMITTED` after **DONE CHECK PASS** and explicitly authorized implementation commit `843ffcd4fcc12d1e93587a488e605ee5bacf4373` on 2026-11-04 (29 approved files). COMMITTED was recorded only after commit success in a separate two-file documentation-only lifecycle commit. The three approved security corrections and streaming proxy/Expect/413 recovery amendments satisfy their acceptance criteria. Independent review has no outstanding findings per human confirmation; Browser QA is PASS with saved sanitized 11/11 Playwright evidence. Required affected backend coverage is satisfied: the historical 1,542-pass/five-failure run is reconciled against the recorded 729-pass follow-up and later 31-pass API/PDF selection; no entirely passing wholesale rerun or summed unique count is claimed. Existing evidence also records 178 frontend tests, Ruff/Pyright, lint/typecheck/build and provider-free offline baseline 90/90 passing. Complete diff, documentation, scope, secrets and artifact checks pass. Only the unit record and index changed during Done Check; no tests were rerun, application behavior changed, paid provider calls made, staging or commit performed. The commit task reviewed the exact staged inventory, complete diff, whitespace, secrets and artifacts; four trailing-space lines in the new unit document were cleaned. No tests were rerun, provider calls made, application behavior changed or remote push performed during the commit task. `test_clarification.py` remains reported modified with no Git content diff and was left unstaged. Stopped after M6-U3; do not begin M6-U4. M6-U1/M6-U2 records, pending quality reviews and risks remain preserved. This is not release-quality approval; hosting configuration remains deferred to M6-U6.

**[M6-U2 — Observability / Langfuse Polish](M6-U2.md)** is `COMMITTED` after **DONE CHECK PASS** and explicitly authorized implementation commit `ce6c05bcf275fa1d73212f773a26ad81c2bd0b3c` on 2026-11-03 (21 approved files). COMMITTED is recorded only after implementation commit success in a separate two-file documentation-only lifecycle commit. The staged diff, file inventory, whitespace, secrets and artifact checks passed; the implementation commit left a clean working tree. Independent re-review passed with P2 resolved and no remaining actionable findings, per explicit human confirmation. Existing AIRun/run-step persistence covers all six operations without migrations; optional Langfuse 4.18.0 is disabled by default and exports sanitized manual observations only. Evidence includes 387 base-installation regressions, 12 optional-SDK adapter checks, 11 base adapter checks with one expected SDK-only skip, P2 regressions (10 focused and 419 broader), Ruff/Pyright PASS and offline baseline 90/90 COMPLETED/exit 0. The earlier broad run remains 3,509 passed/two failed, with both classifier failures corrected and verified by subsequent passing regressions; no fully passing wholesale rerun is claimed. Browser QA: Not applicable to internal observability. Hosted Langfuse visibility remains explicitly unverified as permitted by the approved plan. M6-U1 carry-forward risks and pending human quality reviews remain unchanged; this is not release-quality approval. Documentation, complete diff, scope, secrets and artifact checks pass. No application changes, provider calls, verification reruns, staging or commit during Done Check. No tests were rerun, provider calls made or application behavior changed during the commit task. No remote push performed. Stopped after M6-U2; no M6-U3 work.

**M6-U1 — Eval Dataset Completion and Baselines** is `COMMITTED` after a passing Done Check under the explicitly approved 2026-11-03 live-evidence criterion and implementation commit `317712ab073a12b1f20a8935b48ce163515d7e2c` (126 files, including 70 retained evidence files). Status was updated only after commit success in a separate documentation-only lifecycle commit. Independent reviews passed per human confirmation; offline baseline 90/90 and all 172 previously excluded distinct database checks passed. Dedicated eval configuration and database readiness were verified for the recorded runs; earlier missing-configuration/connectivity blockers are historical. The full 90-case Analyst v2 baseline remains ERROR/exit 2 (20 runtime errors); the separate 31-case v3 follow-up remains ERROR/exit 2 (ten runtime errors). No complete current-version full-run success is claimed. Ten human reviews remain PENDING/null. Browser QA: Not applicable to internal eval/prompt/contract changes. See [M6-U1](M6-U1.md) for the approved criterion, provenance, unresolved quality risks and final disposition. Staged scope, whitespace, secrets and artifact checks passed; root working artifacts remain excluded. No evaluation rerun, new production changes, remote push or M6-U2 work. Stopped after M6-U1.

**M5-U3 — Full Golden-Path Browser E2E** is `COMMITTED` after its passing Done Check and explicitly authorized implementation commit `c0d1f101773b0907344b4521ce8fa6f6992fe45f` on 2026-10-05. Acceptance criteria, resolved Review/Browser QA findings, final three consecutive golden passes, six independent targets with zero retries, 16 persistence checkpoints, recorded backend/offline eval and 160-test frontend results, lint/type checks, and production builds pass. Done Check reran all 67 model/reset/artifact tests and static checks, scanned all four retained sanitized bundles for credentials, and reviewed all 29 candidate files, scope, dependencies, documentation, cleanup, and secrets. The exact 29-file inventory was explicitly staged and reviewed, staged whitespace checks passed, and the implementation fingerprint matched the passing Done Check. Status was updated only after implementation commit success and recorded in a separate documentation-only lifecycle commit. Hosted GitHub CI and live-provider quality remain unexecuted; reviewed configuration and local evidence reveal no known CI configuration failure. Full evidence and limits are recorded in [M5-U3.md](M5-U3.md). No M2/M4 logic was reimplemented, no prior commit was amended, no remote push was performed, and no M6 work entered scope. Stopped after M5-U3.

The approved M5-U3 P1/P2 review fixes bind destructive reset to the positively validated connection, reject inherited libpq overrides, and gate CI uploads on session-credential sanitization. The authorized Browser QA stale-guidance correction invokes the existing project-refresh callback after Brief analysis and passed focused re-review. Both safety boundaries remain fail-closed. Details and local execution limits are recorded in M5-U3; status is now `COMMITTED`.

**M5-U2 — Full Workflow Integration and Next-Action UX** is `COMMITTED` after its full passing Done Check and explicitly authorized implementation commit `eadb9423f3274fed1aac4131210ce8845e667f41` on 2026-10-04. The approved amended plan, all resolved Review findings, and passing Browser QA (including genuine native focus refresh and quote draft preservation) are recorded in [M5-U2.md](M5-U2.md). Final verification: 802 PostgreSQL-backed backend tests including existing offline evals, 158 frontend tests across 14 files, Ruff/Pyright, frontend lint/type checking, production build, final diff/scope/documentation/artifact/secret checks all passed. No new AI evals were required. Session-scoped read-only batched summaries reuse M2/M4 predicates, omit comparison payloads, and permit Comparison with two eligible confirmed quotes; M5-U1 decision/comparison/advice preservation remains intact. The existing live-advice coverage limitation remains documented. The staged file list matched the exact approved 73-file inventory and `git diff --cached --check` passed before the implementation commit. Status was updated only after commit success and recorded in a separate documentation-only lifecycle metadata commit without amending the implementation commit. No remote push or next-unit work was performed; stopped after M5-U2.

**M5-U1 — Preferred Supplier Decision** is `COMMITTED` after its passing Done Check and explicitly authorized unit commit on 2026-10-03. Review passed; Browser QA PASSED WITH A DOCUMENTED COVERAGE LIMITATION accepted by human review. The real decision/persistence path, comparison preservation, and reviewed regressions passed; advice retention has labeled fixture and automated regression coverage. The real advice-preservation browser assertion remains unexercised due to prerequisite M4 validation and/or local response-delivery failures before decision writes. Full evidence and limits are recorded in `M5-U1.md`. Status was updated only after commit success and included by amending the same unit commit. No M4/provider/delivery fix, remote push, or next-unit work was performed. Stopped.

**M4-U7 — Suggested Supplier Behavior** is `COMMITTED` after a passing Done Check and its unit-scoped commit on 2026-10-03. All acceptance criteria and workflow checklist items pass: 771 PostgreSQL-backed backend tests, 238 explicit offline advice/tradeoff eval tests, 109 frontend tests, lint/type checks, and production build. Review findings are resolved; recorded Browser QA evidence is verified. Final diff, scope, documentation, dependency/infrastructure, artifact, and secret checks pass. Browser QA used deterministic HTTP responses; live-provider quality remains unverified and live evals remain opt-in. Full evidence and limits are recorded in `M4-U7.md`. Status was updated only after commit success and included by amending the same unit commit. Stopped; M5-U1 has not begun.

**M4-U6 — Tradeoff Analysis Capability** is `COMMITTED` as `5e8acc7` after re-review, a passing Done Check, and its unit-scoped commit on 2026-10-03. Browser QA is not applicable to this backend/API-only unit. Status was updated after the commit succeeded; M4-U7 had not been started at that checkpoint.

**M4-U5 — Complete Analyst Read-Only Tools** is `COMMITTED` after Review, Browser QA disposition, a passing Done Check, and its unit-scoped commit on 2026-09-30. The human approved the revised plan, including immutable permitted quote IDs.

**M4-U4 — Comparison UI and Stale-State UX** is `COMMITTED`. Review, browser UI QA, Done Check, and its unit-scoped commit passed on 2026-09-30.

**M4-U3 — ComparisonSnapshot Generation and Staleness** is `COMMITTED` after a passing Done Check and its unit-scoped commit on 2026-09-29.

**M4-U2 — Remaining Explicit Requirement Evaluators** is `COMMITTED` after a passing Done Check and its unit-scoped commit on 2026-09-29.

**M4-U1 — Source Precedence Resolver** is `COMMITTED` after a passing Done Check on 2026-09-29 and its unit-scoped commit. M3-U9 is `COMMITTED`.

**M3-U9 — Quote Confirmation, Revision, Stale Processing, and Idempotent Retry** is `COMMITTED`. Browser QA and Done Check passed on 2026-09-28, followed by its unit-scoped commit.

**M3-U8 — Quote Correction, Provenance, and Evidence UI** is `COMMITTED`. Its approved plan, implementation, review fixes, Browser QA, and Done Check passed by 2026-09-28; the unit-scoped commit succeeded. Implementation is limited to draft correction and evidence review.

**M3-U7 — Lightweight Background Quote Processing** is `COMMITTED`. Its approved plan, implementation, review recheck, Browser QA, and Done Check passed on 2026-09-27; the unit-scoped commit succeeded.

**M3-U6 — Quote Extractor Structured AI Capability** is `COMMITTED` as `11f8326`. Its plan was approved by the human in this chat, and Review, Browser QA disposition, and Done Check passed on 2026-09-27.

**M3-U5 — Initial Synthetic Quote PDF Fixtures** is `COMMITTED` as `b4b501c5f522d7f5eff8ca05a11e403b0d7f3502`. Its fixture-only plan was approved by the human, then passed review and Done Check.

**M3-U4 — PDF Parsing and DocumentBlock Persistence** is `COMMITTED` as `cadee28f117e5b980d2f892de5a28f2bbfbae67a`. Its amended plan was recorded as `PLANNING`, approved by the human, then transitioned through `PLAN_APPROVED`, implementation, review, and a passing Done Check.

**M3-U3 — Document Storage and PDF Validation** is `COMMITTED`.

**M3-U2 — Manual Quote Entry Vertical Slice** is `COMMITTED`.

**M3-U1 — Quote Persistence and Provenance Domain** is `COMMITTED`.

**M2-U7 — Complete Supplier Fixtures + Shortlist Approval** is `COMMITTED`.

M2-U6 — Supplier Explanation via Sourcing Analyst is `COMMITTED`.

M2-U5 — Sourcing Analyst Read-Only Tool Foundation is `COMMITTED`.

M2-U4 — ProjectSupplier, Supplier Review, and Staleness is `COMMITTED`.

M2-U3 — Supplier Requirement Evaluators is `COMMITTED`.

M2-U2 — Candidate Retrieval is `COMMITTED`.

M2-U1 — Synthetic Supplier Domain + Initial Fixtures is `COMMITTED`.

M1-U6 — Brief Approval and Revision Foundation is `COMMITTED`.

M1-U5 is `COMMITTED`.

M1-U4 is `COMMITTED`.

M1-U3 is `COMMITTED`.

M1-U2 is `COMMITTED`.

M1-U1 is `COMMITTED`.

M0-U1 through M0-U6 are `COMMITTED`.

## Unit lifecycle statuses

Each unit document contains one current status:

- `PLANNING`
- `PLAN_APPROVED`
- `IMPLEMENTING`
- `IN_REVIEW`
- `QA`
- `READY_TO_COMMIT`
- `COMMITTED`

Browser QA does not need its own status when it is not applicable. Record its result in the unit document instead.

## Unit documents

Create a unit document only when that unit becomes active.

Use this naming convention:

```text
M0-U1.md
M0-U2.md
M1-U1.md
```

Do not pre-create empty files for the roadmap.

A unit document normally contains:

```md
# Mx-Uy — Unit name

## Status

## Objective

## Source-of-truth references

## Dependencies

## Approved scope

## Explicitly out of scope

## Approved implementation plan

## Acceptance criteria

## Tests and evals

## Browser QA requirement

## Review findings

## Done-check result
```

The unit document is the approved working plan for that unit. It may refine implementation details, tests, and file-level impact, but it must not override the Product Specification, Technical Architecture, or Implementation Plan.

When a unit is committed, update its status and done-check result, then stop. The next unit requires its own activation, plan, and approval.
