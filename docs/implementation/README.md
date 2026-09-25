# Implementation Units

This directory holds the approved working context for active SourcePilot implementation units.

## Current implementation unit

**M2-U2 — Candidate Retrieval** is `COMMITTED`.

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
