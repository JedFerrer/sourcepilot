# Implementation Units

This directory holds the approved working context for active SourcePilot implementation units.

## Current implementation unit

**M3-U6 — Quote Extractor Structured AI Capability** is `READY_TO_COMMIT`. Its plan was approved by the human in this chat, and Review, Browser QA disposition, and Done Check passed on 2026-09-27. It remains uncommitted.

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
