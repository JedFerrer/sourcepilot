# Implementation Units

This directory holds the approved working context for active SourcePilot implementation units.

## Current implementation unit

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
