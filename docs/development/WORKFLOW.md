# Development Workflow

SourcePilot work follows:

PLANNING → IMPLEMENTATION → REVIEW → BROWSER QA when applicable → DONE CHECK → COMMIT

One approved implementation unit is active at a time.

## Standard Agent Commands

These commands refer to one named implementation unit. They do not authorize work outside that unit.

### Lifecycle status transitions

```text
Plan Mx-Uy
→ PLANNING

Human approves plan
→ PLAN_APPROVED

Implement Mx-Uy
→ IMPLEMENTING

Review Mx-Uy
→ IN_REVIEW

Browser QA Mx-Uy
→ QA

Done check Mx-Uy
→ READY_TO_COMMIT

Commit Mx-Uy
→ COMMITTED
```

An agent must never set `PLAN_APPROVED` on its own. It may record that status only after explicit human approval.

If Browser QA is not applicable, record `Browser QA: Not applicable` and a reason in the unit document without transitioning to `QA`. A failed Review, Browser QA, or Done Check must not advance the unit to the next lifecycle status. Set `COMMITTED` only after a successful commit.

### Plan Mx-Uy

- read `AGENTS.md`;
- identify the unit in the Implementation Plan;
- read relevant Product Specification and Technical Architecture sections;
- inspect affected existing code;
- create or update the active unit document;
- set its status to `PLANNING`;
- produce a detailed plan;
- stop before implementation.

### Implement Mx-Uy

- read `AGENTS.md`;
- read the approved active unit document;
- set status to `IMPLEMENTING`;
- implement only that plan;
- add required tests and evals;
- run relevant checks;
- update unit results;
- stop before review;
- do not commit.

### Review Mx-Uy

- inspect the active unit document;
- set status to `IN_REVIEW`;
- inspect the actual diff;
- inspect relevant tests;
- compare the change against relevant source-of-truth material;
- report findings by severity;
- do not modify files except for the status update unless explicitly asked.

### Fix Mx-Uy review findings

- address only approved review findings;
- rerun relevant checks;
- update review results;
- keep the unit in `IN_REVIEW` until review passes;
- stop before Browser QA or Done Check.

### Browser QA Mx-Uy

- determine whether Browser QA applies;
- when applicable, set status to `QA` and test the relevant browser-visible flow;
- record pass or fail evidence in the active unit document;
- when not applicable, record the reason without transitioning to `QA`;
- stop before Done Check.

### Done check Mx-Uy

- execute the Done Check in this document;
- confirm acceptance criteria, tests, review, QA, scope, documentation, diff, secrets, and artifacts;
- set status to `READY_TO_COMMIT` only when every Done Check item passes;
- update the active unit document;
- do not commit unless explicitly authorized.

### Commit Mx-Uy

- run only after the Done Check passes;
- stage only unit-related files;
- create one coherent unit-scoped commit;
- set status to `COMMITTED` only after the commit succeeds;
- show Git status and the commit;
- stop;
- do not begin the next unit.

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
