# Development Workflow

SourcePilot work follows:

PLANNING → IMPLEMENTATION → REVIEW → BROWSER QA when applicable → DONE CHECK → COMMIT

One approved implementation unit is active at a time.

## 1. Planning

Before code changes:

- identify the current implementation unit;
- inspect relevant code;
- read relevant source-of-truth sections;
- identify dependencies;
- identify expected files to change;
- identify required tests and evals;
- identify risks and explicitly out-of-scope work;
- present an implementation plan;
- wait for approval.

Do not implement during Planning.

## 2. Implementation

After approval:

- implement only the approved plan;
- remain inside the current implementation unit;
- add required tests and evals;
- run relevant checks;
- do not commit;
- do not begin another unit.

If a conflict with a higher-authority source, missing decision, or scope expansion appears, stop and request human direction.

## 3. Review

Use a fresh or independent review context when practical.

Review the actual diff for:

- correctness;
- Product Specification compliance;
- Technical Architecture compliance;
- Implementation Plan compliance;
- scope creep;
- security;
- edge cases;
- error handling;
- test coverage;
- unnecessary complexity;
- accidental future-unit work.

Resolve review findings before proceeding.

## 4. Browser QA

Browser QA is required when the unit changes meaningful browser-visible behavior, including:

- UI;
- usability-relevant layout;
- forms;
- navigation;
- frontend/backend interaction;
- session behavior;
- uploads;
- loading or error states;
- user workflows.

Browser QA may be skipped for purely internal work, such as domain models, migrations, isolated deterministic services, internal AI contracts, or backend utilities, when browser testing would add no meaningful coverage.

When skipped, record in the active implementation-unit document:

```text
Browser QA: Not applicable
Reason: <why browser coverage adds no meaningful value>
```

## 5. Done Check

Before committing, verify:

- [ ] Current implementation unit only
- [ ] Acceptance criteria satisfied
- [ ] Required tests pass
- [ ] Required evals pass when applicable
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Review findings resolved
- [ ] Browser QA passed or explicitly marked N/A
- [ ] No known regression
- [ ] No unapproved infrastructure or dependency added
- [ ] No scope creep
- [ ] Required documentation updated
- [ ] Git diff reviewed
- [ ] No temporary or debug artifacts
- [ ] No secrets added
- [ ] Ready to commit

A failing item means the unit is not done.

## 6. Commit

Commit only after the Done Check passes.

A commit must correspond to the current implementation unit or one coherent part of it. After committing, stop. Do not automatically start the next implementation unit.
