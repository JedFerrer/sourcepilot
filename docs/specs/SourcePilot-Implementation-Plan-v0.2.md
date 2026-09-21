# SourcePilot — Implementation Plan v0.2

**Status:** Final for Execution  
**Product source of truth:** SourcePilot Product Specification v0.2  
**Architecture source of truth:** SourcePilot Technical Architecture v0.2  
**Implementation style:** Vertical slices  
**Target:** SourcePilot V1 open-source portfolio release  
**Primary constraint:** One senior developer working with a coding agent

---

# 1. Implementation Strategy

SourcePilot should be implemented as a sequence of **vertical slices**.

Each milestone must leave the repository in a working, reviewable, and testable state.

The implementation order should avoid:

```text id="6jmwor"
complete backend
→ complete frontend
→ AI later
→ tests later
→ evals later
```

Instead, each bounded capability should include the layers it actually requires:

```text id="ml01tv"
domain/data
+
application
+
API
+
frontend
+
AI where required
+
tests
+
evals where required
+
tracing
```

The guiding principle is:

> **Build the smallest complete behavior, verify it end to end, then add the next behavior.**

Each implementation unit should normally represent:

- several focused development hours;
- up to approximately one focused development day;
- one coherent reviewable change;
- one logical commit or PR boundary.

Implementation units should not include unrelated cleanup unless necessary for that unit.

---

## 1.1 Coding-Agent Workflow

Every implementation unit should be executed approximately as follows:

```text id="zw8ynr"
choose implementation unit
        ↓
coding agent studies relevant repo context
        ↓
coding agent proposes detailed unit plan
        ↓
human reviews plan
        ↓
agent implements
        ↓
tests / evals run
        ↓
independent review
        ↓
fix findings
        ↓
human reviews final diff
        ↓
commit
```

This implementation plan defines:

- required outcome;
- boundaries;
- dependencies;
- acceptance criteria;
- required tests/evals.

It does not prescribe every file, class, or line of implementation.

---

## 1.2 Feature-Ordering Principle

Build broadly in product-flow order:

```text id="gexw6p"
Foundation
   ↓
Brief
   ↓
Suppliers
   ↓
Quotes
   ↓
Comparison + Analyst
   ↓
Decision / Full Flow
   ↓
Hardening / Release
```

Supporting infrastructure should only be introduced when a vertical slice requires it.

Examples:

- supplier fixtures appear when supplier discovery is built;
- object storage appears when PDF quotes are built;
- the Sourcing Analyst appears only after meaningful deterministic data/tools exist;
- quote fixtures appear alongside quote extraction;
- evals grow alongside their AI capability.

---

## 1.3 Correctness-Lives-With-Feature Principle

Stale-state correctness is part of the feature that creates derived data.

Therefore:

### Supplier evaluation

Once supplier evaluations exist in **M2**, changes to the approved brief must already:

- increment `brief_revision`;
- detect older supplier evaluations;
- mark them stale;
- show stale state to the user;
- allow supplier re-evaluation/re-discovery.

### Comparison

Once `ComparisonSnapshot` exists in **M4**, changes to comparison inputs must already:

- increment relevant revisions;
- make the previous comparison stale;
- prevent stale AI analysis from being presented as current;
- allow regeneration;
- ensure future analyst runs use the regenerated snapshot.

These behaviors are **not postponed to M5**.

---

# 2. Definition of Done for V1

SourcePilot V1 is complete when an anonymous visitor can successfully perform:

```text id="r67da5"
anonymous isolated session
        ↓
create sourcing project
        ↓
enter natural-language sourcing request
        ↓
receive structured brief
        ↓
answer clarification questions
        ↓
edit requirements
        ↓
approve brief
        ↓
discover ~5 synthetic supplier candidates
        ↓
review deterministic requirement evaluation
        ↓
review evidence-backed supplier explanation
        ↓
shortlist ≤3 suppliers
        ↓
approve shortlist
        ↓
upload PDF quote or enter quote manually
        ↓
review extracted fields
        ↓
inspect PDF evidence
        ↓
correct values while preserving provenance
        ↓
confirm quote
        ↓
compare ≥2 suppliers
        ↓
review deterministic comparison
        ↓
review Sourcing Analyst tradeoff analysis
        ↓
review optional Suggested Supplier
        ↓
mark preferred supplier
```

V1 is only done when the repository also contains:

- deterministic domain tests;
- API/integration tests;
- frontend tests;
- AI contract tests;
- version-controlled eval datasets;
- synthetic PDF quote fixtures;
- provenance tests;
- stale-state tests;
- analyst runtime-limit tests;
- browser E2E coverage;
- AI run tracing;
- synthetic-data documentation;
- local setup instructions;
- deployment documentation;
- architecture documentation;
- polished primary demo data.

---

# 3. Milestone Overview

| Milestone | Outcome |
|---|---|
| **M0 — Foundation** | Runnable monorepo, anonymous session isolation, database, AI boundary, tracing/test foundation |
| **M1 — Brief** | Natural-language request → structured editable brief → clarification → human approval |
| **M2 — Suppliers** | Approved brief → ~5 synthetic candidates → deterministic evaluation → evidence explanation → shortlist approval, including brief-revision staleness |
| **M3 — Quotes** | PDF/manual quote → extraction → provenance → correction → confirmation → retry/recovery |
| **M4 — Comparison + Sourcing Analyst** | Confirmed quotes → deterministic comparison → stale-input detection → bounded analysis → optional supplier suggestion |
| **M5 — Decision + Full Vertical Workflow** | Preferred-supplier decision, integrated five-stage UX, complete golden-path E2E |
| **M6 — Hardening + Portfolio Release** | E2E hardening, observability polish, eval baselines, docs, deployment, public demo |

---

# 4. Dependency Map

High-level:

```text id="2vuatn"
M0 Foundation
│
└── M1 Brief
      │
      └── M2 Suppliers
             │
             └── M3 Quotes
                    │
                    └── M4 Comparison + Analyst
                           │
                           └── M5 Decision / Full Flow
                                  │
                                  └── M6 Release
```

Detailed capability dependencies:

```text id="dytuda"
DemoSession
    ↓
Project
    ↓
Brief + Requirements
    ↓
Brief Approval + brief_revision
    ↓
Supplier Fixtures
    ↓
Candidate Retrieval
    ↓
Requirement Evaluations
    ↓
Supplier Evaluation Revision Tracking
    ↓
Supplier Evidence
    ↓
Shortlist Approval
    ↓
Quote + QuoteValue
    ↓
QuoteDocument / DocumentBlock
    ↓
QuoteExtractor
    ↓
Quote Confirmation + quote_revision
    ↓
ComparisonSnapshot + Input Revisions
    ↓
Comparison Staleness / Regeneration
    ↓
Analyst Tools
    ↓
Sourcing Analyst
    ↓
Preferred Supplier
```

Important dependency rules:

- supplier discovery requires an approved brief;
- supplier evaluations must record the brief revision they used;
- Sourcing Analyst supplier explanation requires deterministic evaluations and evidence;
- quote extraction requires PDF parsing and document blocks;
- final comparison requires confirmed quote values;
- ComparisonSnapshot must record its input revisions;
- tradeoff analysis must operate only on a current comparison;
- stale comparison must be regenerated before new analyst results are treated as current;
- suggested-supplier behavior depends on the deterministic comparison;
- E2E grows incrementally, while the full golden path arrives in M5.

---

# 5. Milestone 0 — Foundation

## Objective

Create the smallest production-style foundation required for the Brief vertical slice.

At the end of M0:

- frontend runs;
- backend runs;
- PostgreSQL runs;
- anonymous sessions isolate project data;
- project creation works;
- AI calls have a defined boundary;
- AI runs can be traced;
- local testing/CI exists.

Do not create speculative future domain entities.

---

## User-Visible Outcome

A visitor can:

1. open SourcePilot;
2. receive an anonymous demo session;
3. create a sourcing project;
4. see/open that project.

No sourcing AI exists yet.

---

## M0-U1 — Repository and Local Application Skeleton

### Objective

Create the monorepo/application structure and make web, API, and PostgreSQL runnable locally.

### Dependencies

None.

### Layers touched

- frontend;
- backend;
- infrastructure;
- tests.

### Scope

Establish:

- `apps/web`;
- `apps/api`;
- Python environment;
- TypeScript environment;
- PostgreSQL local service;
- basic configuration;
- frontend → backend connectivity;
- backend health endpoint;
- baseline lint/type/test commands.

Avoid speculative domain abstractions.

### Acceptance criteria

- frontend starts locally;
- backend starts locally;
- PostgreSQL is reachable;
- frontend can call backend health endpoint;
- environment configuration is documented;
- basic lint/type/test commands work.

### Tests required

- backend smoke test;
- frontend build/typecheck;
- initial CI smoke workflow.

### Demo checkpoint

Open SourcePilot shell and show successful frontend → FastAPI health request.

---

## M0-U2 — Persistence and Migration Foundation

### Objective

Add persistence needed immediately for anonymous sessions/projects.

### Dependencies

M0-U1.

### Layers touched

- database/domain;
- persistence;
- tests.

### Scope

Introduce:

- SQLAlchemy;
- Alembic;
- database-session management;
- migration workflow.

Create only:

- `DemoSession`;
- `Project`.

### Acceptance criteria

- migrations create required tables;
- fresh database upgrades cleanly;
- test database can be isolated/reset;
- Project belongs to DemoSession.

### Tests required

- migration smoke test;
- persistence integration tests.

### Demo checkpoint

Reset database, run migrations, inspect initial tables.

---

## M0-U3 — Anonymous Session Isolation

### Objective

Implement anonymous isolated demo sessions.

### Dependencies

M0-U2.

### Layers touched

- database/domain;
- application;
- API;
- frontend;
- security;
- tests.

### Scope

Implement:

- opaque server-generated session token;
- HttpOnly cookie;
- configurable 24-hour expiry;
- automatic session creation;
- session resolution;
- session-scoped project queries.

### Acceptance criteria

- first visitor receives a session;
- project belongs to current session;
- Visitor A cannot retrieve Visitor B's project;
- expired sessions cease to authorize old data;
- project ID alone cannot bypass isolation.

### Tests required

- expiry unit tests;
- API tests;
- session-isolation integration tests;
- frontend initialization test.

### Demo checkpoint

Two isolated browser contexts cannot see each other's projects.

---

## M0-U4 — Project Creation Vertical Slice

### Objective

Allow a visitor to create and reopen an empty sourcing project.

### Dependencies

M0-U3.

### Layers touched

- database/domain;
- application;
- API;
- frontend;
- tests.

### Scope

Implement:

- create project;
- list projects;
- read project;
- rename project;
- minimal dashboard;
- project workspace shell.

### Acceptance criteria

- visitor can create project;
- project appears in current session;
- project reopens successfully;
- rename persists;
- foreign session access fails.

### Tests required

- domain tests;
- API tests;
- frontend tests;
- browser smoke path.

### Demo checkpoint

Create and reopen “Recycled Cosmetic Travel Bag.”

---

## M0-U5 — AI Client, AIRun, and Prompt-Version Foundation

### Objective

Create the common boundary later AI capabilities use.

### Dependencies

M0-U2.

May proceed after persistence independently of M0-U4.

### Layers touched

- AI;
- persistence;
- tracing;
- tests.

### Scope

Introduce:

- official model-client wrapper;
- model configuration;
- prompt-version identifiers;
- structured-call helper;
- bounded retry helper;
- `AIRun`;
- latency/token/status capture;
- validation-outcome capture;
- optional Langfuse adapter boundary.

Do not create product prompts yet.

### Acceptance criteria

- development AI operation creates AIRun;
- success/failure persists;
- one repair retry can be tested;
- system runs without Langfuse;
- provider calls are mockable.

### Tests required

- helper unit tests;
- retry tests;
- AIRun integration test.

### Demo checkpoint

Run development AI smoke operation and inspect AIRun.

---

## M0-U6 — Shared API/Error/Testing Conventions

### Objective

Establish only the conventions needed by later slices.

### Dependencies

M0-U1 through M0-U5.

### Layers touched

- application;
- API;
- frontend;
- tests;
- CI.

### Scope

Add:

- common API error shape;
- frontend API client;
- test factories/helpers;
- CI lint/type/unit stages.

Avoid an internal framework.

### Acceptance criteria

- API errors are consistent;
- frontend displays recoverable error state;
- CI runs baseline checks;
- later slices can reuse testing infrastructure.

### Tests required

- API-error tests;
- frontend client tests;
- CI pass.

### Demo checkpoint

Request inaccessible project and show clean failure.

---

# 6. Milestone 1 — Brief

## Objective

Deliver:

**natural-language request → structured brief → clarification → editing → approval**

AI extraction, deterministic readiness, user editing, tracing, revisions, and evals appear together.

---

## User-Visible Outcome

The user enters an informal sourcing request and can:

- receive structured requirements;
- see missing information;
- answer clarification questions;
- edit requirements;
- reach Ready for Review;
- explicitly approve the brief.

---

## M1-U1 — Brief and Requirement Domain Model

### Objective

Introduce persistent data for the editable brief.

### Dependencies

M0 complete.

### Layers touched

- database/domain;
- persistence;
- tests.

### Scope

Add:

- `Brief`;
- `Requirement`;
- importance;
- explicit V1 requirement kinds;
- brief states;
- `brief_revision`.

Implement only requirement types needed for V1/demo.

### Acceptance criteria

- project owns current brief;
- key structured fields persist;
- Required / Preferred / Informational persist;
- revision can increment;
- no generic rules engine exists.

### Tests required

- domain tests;
- migration tests;
- persistence tests.

### Demo checkpoint

Persist a structured brief manually.

---

## M1-U2 — Brief Readiness Service

### Objective

Implement deterministic readiness before AI extraction.

### Dependencies

M1-U1.

### Layers touched

- domain;
- application;
- tests.

### Scope

Check:

- product/category;
- quantity;
- destination;
- delivery target;
- category-specific required information.

Target price remains optional.

Return:

- readiness status;
- missing fields;
- reason per missing field.

### Acceptance criteria

- incomplete brief cannot become Ready;
- missing target price alone does not block;
- category-specific required fields can block;
- result is deterministic.

### Tests required

- comprehensive readiness unit tests.

### Demo checkpoint

Run several sample briefs through readiness service.

---

## M1-U3 — Brief Interpreter Structured AI Capability

### Objective

Convert natural language to typed brief data.

### Dependencies

M0-U5, M1-U1.

### Layers touched

- AI;
- application;
- API;
- tracing;
- tests;
- evals.

### Scope

Implement:

1. typed contract;
2. prompt v1;
3. model call;
4. schema validation;
5. one repair retry;
6. AIRun;
7. deterministic post-validation;
8. initial eval dataset;
9. recoverable failure.

### Acceptance criteria

- valid request produces `ExtractedBrief`;
- missing information stays missing;
- schema failure gets one repair attempt;
- project remains usable after AI failure;
- AIRun records relevant metadata;
- initial evals run.

### Tests required

- contract tests;
- mocked model tests;
- API tests;
- ~10–15 initial eval cases.

### Demo checkpoint

Primary request → structured brief + AIRun.

---

## M1-U4 — Analyze Request API + Brief Editing UI

### Objective

Connect interpreter to project workspace.

### Dependencies

M1-U2, M1-U3.

### Layers touched

- application;
- API;
- frontend;
- AI;
- tests.

### Scope

Implement:

- analyze endpoint;
- extracted-field persistence;
- Brief screen;
- field editing;
- importance controls;
- readiness display;
- missing-field display.

### Acceptance criteria

- natural-language input populates editable brief;
- edits persist;
- meaningful edit increments revision where required;
- readiness recalculates;
- AI failure offers retry/manual editing.

### Tests required

- API tests;
- frontend tests;
- integration tests.

### Demo checkpoint

Request → extracted brief → edit.

---

## M1-U5 — Clarification Generator

### Objective

Convert deterministic missing fields into concise questions.

### Dependencies

M1-U2, AI foundation.

### Layers touched

- AI;
- application;
- API;
- frontend;
- tracing;
- evals/tests.

### Scope

Implement:

- `ClarificationSet`;
- prompt version;
- structured model call;
- one repair retry;
- field-key validation;
- AIRun;
- initial clarification evals.

### Acceptance criteria

- questions target only unresolved fields;
- known data is not redundantly requested;
- user answers update brief;
- readiness recalculates;
- manual edit remains fallback.

### Tests required

- contract tests;
- validation tests;
- clarification evals;
- frontend tests.

### Demo checkpoint

Incomplete request → clarification → complete brief.

---

## M1-U6 — Brief Approval and Revision Foundation

### Objective

Complete Brief stage and establish downstream revision semantics.

### Dependencies

M1-U1 through M1-U5.

### Layers touched

- domain;
- application;
- API;
- frontend;
- tests.

### Scope

Implement:

- Approve Brief;
- Ready for Review validation;
- approval timestamp;
- post-approval editing;
- `brief_revision` increments for meaningful changes.

Supplier staleness itself is implemented in M2 when supplier evaluations exist.

### Acceptance criteria

- incomplete brief cannot be approved;
- approved state is explicit;
- post-approval meaningful edit increments revision;
- user can continue editing.

### Tests required

- unit tests;
- API tests;
- frontend approval tests.

### Demo checkpoint

Request → clarification → edit → approve.

---

# 7. Milestone 2 — Suppliers

## Objective

Deliver:

**approved brief → ~5 synthetic candidates → deterministic evaluation → evidence-backed explanation → shortlist approval**

M2 also owns supplier-evaluation staleness caused by later brief edits.

---

## User-Visible Outcome

The user can:

- discover approximately five suppliers;
- see deterministic requirement states;
- inspect evidence;
- read grounded explanations;
- shortlist up to three;
- approve shortlist;
- see stale warnings if the approved brief later changes;
- re-evaluate suppliers against the new brief.

---

## M2-U1 — Synthetic Supplier Domain + Initial Fixtures

### Objective

Create supplier domain and enough data for candidate retrieval.

### Dependencies

M1 complete.

### Layers touched

- database/domain;
- persistence;
- fixtures;
- tests.

### Scope

Add:

- `Supplier`;
- `SupplierCapability`;
- `SupplierEvidence`.

Start with approximately 8 suppliers.

Include:

- strong match;
- near match;
- required failure;
- unknown;
- genuine evidence conflict.

### Acceptance criteria

- deterministic fixture loading;
- no real-manufacturer claims;
- capabilities/evidence queryable;
- repeatable seed process.

### Tests required

- fixture tests;
- repository tests.

### Demo checkpoint

Inspect synthetic suppliers/evidence.

---

## M2-U2 — Candidate Retrieval

### Objective

Return approximately five relevant candidates.

### Dependencies

M2-U1, approved brief.

### Layers touched

- domain;
- persistence;
- application;
- API;
- tests.

### Scope

Structured retrieval by:

- category;
- material;
- capabilities;
- certification context;
- MOQ compatibility/general facts.

Allow useful near matches.

### Acceptance criteria

- demo brief returns ~5 useful candidates;
- irrelevant categories excluded;
- near matches may remain;
- results deterministic.

### Tests required

- unit tests;
- repository tests;
- API tests.

### Demo checkpoint

Approved brief → Discover Suppliers.

---

## M2-U3 — Supplier Requirement Evaluators

### Objective

Evaluate supplier candidates deterministically.

### Dependencies

M2-U1, M2-U2.

### Layers touched

- domain;
- tests.

### Scope

Implement supplier-stage evaluators:

- material;
- certification;
- MOQ/general quantity compatibility;
- supported boolean/categorical capabilities.

Results:

```text id="4ooszs"
MEETS
DOES_NOT_MEET
UNKNOWN
CONFLICT
```

### Acceptance criteria

- missing evidence → Unknown;
- genuine incompatible same-context evidence → Conflict;
- no numeric scores;
- non-evaluable requirements remain informational.

### Tests required

- exact evaluator unit tests.

### Demo checkpoint

Inspect evaluation states for candidates.

---

## M2-U4 — ProjectSupplier, Supplier Review, and Staleness

### Objective

Persist supplier evaluations/review state and make them revision-aware.

### Dependencies

M2-U2, M2-U3, M1-U6.

### Layers touched

- database/domain;
- application;
- API;
- frontend;
- tests.

### Scope

Add:

- `ProjectSupplier`;
- `RequirementEvaluation`;
- candidate persistence;
- `evaluated_against_brief_revision`;
- shortlist toggle;
- dismiss/restore;
- personal notes;
- evidence viewer;
- requirement-state UI.

Add supplier-staleness behavior:

```text id="upe842"
current brief_revision
!=
evaluated_against_brief_revision
→ supplier evaluation is stale
```

When an approved brief changes meaningfully:

- stale evaluations are detected;
- supplier results display stale warning;
- old results are not silently shown as current;
- user can trigger re-discovery/re-evaluation;
- fresh evaluations record current `brief_revision`.

### Acceptance criteria

- supplier evaluation records revision;
- changing approved brief makes old evaluations stale;
- stale warning appears;
- re-evaluation clears stale state;
- old revision is never silently presented as current;
- shortlist/dismiss/note behavior still works.

### Tests required

- domain revision tests;
- persistence tests;
- API tests;
- frontend stale-state tests;
- integration test:
  - evaluate suppliers;
  - edit approved brief;
  - detect stale;
  - re-evaluate.

### Demo checkpoint

Discover suppliers, edit approved requirement, observe stale warning, re-evaluate.

---

## M2-U5 — Sourcing Analyst Read-Only Tool Foundation

### Objective

Create supplier tools used by the bounded analyst.

### Dependencies

M2-U3, M2-U4.

### Layers touched

- AI;
- application;
- tools;
- security;
- tests.

### Scope

Implement:

- analyst runtime context;
- `get_supplier_snapshot`;
- `get_supplier_evidence`;
- project/session scoping;
- typed contracts;
- read-only enforcement;
- tool-count foundation.

Tools must return current/non-stale data appropriately.

### Acceptance criteria

- current-project suppliers only;
- cross-project/session IDs rejected;
- no write tool exists;
- outputs typed;
- calls traceable.

### Tests required

- tool tests;
- security/scoping tests.

### Demo checkpoint

Developer-level evidence-tool invocation.

---

## M2-U6 — Supplier Explanation via Sourcing Analyst

### Objective

Use the bounded agent to explain supplier results.

### Dependencies

M2-U5.

### Layers touched

- AI;
- application;
- API;
- frontend;
- tracing;
- evals/tests.

### Scope

Implement:

- analyst prompt;
- bounded loop;
- max 4 model turns;
- max 6 tool calls;
- `SupplierExplanation`;
- evidence-ID validation;
- limit-exceeded behavior;
- AIRun steps;
- initial explanation evals.

Do not present supplier explanations as current when underlying evaluations are stale.

### Acceptance criteria

- explanations agree with deterministic states;
- Unknown/Conflict preserved;
- required failures visible;
- valid evidence only;
- runtime budget enforced;
- stale supplier evaluations require refresh before current explanation.

### Tests required

- loop tests;
- limit tests;
- contract tests;
- groundedness evals.

### Demo checkpoint

Open supplier → grounded explanation + trace.

---

## M2-U7 — Complete Supplier Fixtures + Shortlist Approval

### Objective

Finish supplier data and human approval.

### Dependencies

M2-U1 through M2-U6.

### Layers touched

- fixtures;
- domain;
- application;
- API;
- frontend;
- tests/evals.

### Scope

Expand to approximately 15 synthetic suppliers.

Ensure coverage of:

- matches;
- near matches;
- required failures;
- unknowns;
- conflicts;
- commercial tradeoffs.

Implement shortlist approval, maximum three.

Approval must rely on current supplier evaluation state.

### Acceptance criteria

- primary demo returns useful ~5 candidates;
- >3 shortlist cannot be approved;
- ≤3 can;
- stale supplier state must be resolved/re-evaluated before relying on refreshed evaluation output where required;
- fixture disclaimer documented.

### Tests required

- fixture regressions;
- API tests;
- browser supplier slice.

### Demo checkpoint

Brief → suppliers → optional stale/re-evaluate → shortlist three → approve.

---

# 8. Milestone 3 — Quotes

## Objective

Deliver:

**PDF/manual quote → extraction → evidence → correction → confirmation**

Preserve separately:

```text id="zmeaza"
PDF source value
AI extracted value
current normalized value
current origin
```

---

## User-Visible Outcome

For shortlisted suppliers, user can:

- upload PDF;
- see processing status;
- review fields/evidence;
- correct values;
- preserve provenance;
- confirm quote;
- use manual entry/fallback.

---

## M3-U1 — Quote Persistence and Provenance Domain

### Objective

Create quote/provenance structures.

### Dependencies

M2 shortlist approval.

### Layers touched

- database/domain;
- persistence;
- tests.

### Scope

Add:

- `Quote`;
- `QuoteValue`;
- status;
- `quote_revision`;
- entry type;
- origin enum:
  - `AI_EXTRACTED`;
  - `USER_CORRECTED`;
  - `USER_ENTERED`.

### Acceptance criteria

- quote belongs to shortlisted supplier/project;
- AI-extracted and current value are distinct;
- origin explicit;
- confirmed current value becomes authoritative.

### Tests required

- provenance unit tests;
- persistence tests.

### Demo checkpoint

Inspect manually created Quote/QuoteValue.

---

## M3-U2 — Manual Quote Entry Vertical Slice

### Objective

Complete simplest quote path before PDFs.

### Dependencies

M3-U1.

### Layers touched

- application;
- API;
- frontend;
- tests.

### Scope

Implement:

- manual entry form;
- USER_ENTERED origin;
- review;
- confirmation.

### Acceptance criteria

- manual quote works for shortlisted supplier;
- optional/missing fields allowed appropriately;
- user edits before confirmation;
- unshortlisted supplier rejected;
- confirmation establishes current revision.

### Tests required

- domain;
- API;
- frontend;
- browser path.

### Demo checkpoint

Add/confirm manual quote.

---

## M3-U3 — Document Storage and PDF Validation

### Objective

Introduce safe PDF storage.

### Dependencies

M3-U1.

### Layers touched

- documents;
- application;
- API;
- storage;
- security;
- tests.

### Scope

Implement:

- `DocumentStorage`;
- local filesystem implementation;
- S3-compatible production boundary;
- PDF magic bytes;
- 10 MB limit;
- 15-page limit;
- SHA-256;
- safe keys;
- `QuoteDocument`.

### Acceptance criteria

- valid PDF stores;
- invalid file rejected;
- oversize/page-limit rejected;
- duplicate hash detectable;
- ownership scoped.

### Tests required

- validation tests;
- storage tests;
- API tests.

### Demo checkpoint

Upload valid PDF and inspect metadata.

---

## M3-U4 — PDF Parsing and DocumentBlock Persistence

### Objective

Produce stable source evidence.

### Dependencies

M3-U3.

### Layers touched

- documents;
- database;
- persistence;
- tests.

### Scope

Implement:

- PyMuPDF extraction;
- page/block data;
- stable block IDs;
- `DocumentBlock`;
- clean failure for image-only PDFs.

No OCR.

### Acceptance criteria

- text PDFs generate page/block data;
- block references stable;
- unsupported scan fails;
- no external document URLs followed.

### Tests required

- parser fixtures;
- unsupported PDF test;
- persistence test.

### Demo checkpoint

Inspect PDF source blocks.

---

## M3-U5 — Initial Synthetic Quote PDF Fixtures

### Objective

Create reproducible extraction corpus.

### Dependencies

M3-U4.

### Layers touched

- fixtures;
- documents;
- evals/tests.

### Scope

Create three primary PDFs plus:

- missing shipping;
- conflicting lead time;
- unsupported scanned/image-only fixture.

### Acceptance criteria

- all explicitly synthetic;
- primary three use same currency;
- meaningful tradeoffs;
- at least one uncertainty/conflict;
- text extractable.

### Tests required

- parser fixture tests.

### Demo checkpoint

Show three primary quote PDFs.

---

## M3-U6 — Quote Extractor Structured AI Capability

### Objective

Extract typed values with source provenance.

### Dependencies

M0-U5, M3-U4, M3-U5.

### Layers touched

- AI;
- documents;
- application;
- tracing;
- tests;
- evals.

### Scope

Implement:

1. `QuoteExtraction`;
2. prompt v1;
3. model call;
4. source block IDs;
5. schema validation;
6. one repair retry;
7. source-ID validation;
8. AIRun;
9. initial extraction evals;
10. recovery behavior.

### Acceptance criteria

- primary PDFs produce expected fields;
- missing → unknown;
- source IDs valid;
- conflict may be surfaced;
- no tools available to extractor;
- failure preserves document.

### Tests required

- AI contracts;
- source-reference tests;
- evals;
- failure tests.

### Demo checkpoint

Supplier A PDF → extracted draft + evidence.

---

## M3-U7 — Lightweight Background Quote Processing

### Objective

Move PDF processing off upload response.

### Dependencies

M3-U6.

### Layers touched

- application;
- background execution;
- database;
- API;
- frontend;
- tests.

### Scope

Implement:

- PROCESSING;
- start/completion timestamps;
- attempts;
- background execution;
- frontend polling;
- FAILED state.

### Acceptance criteria

- upload returns quickly;
- UI shows Processing;
- success → Needs Review;
- failure → Failed;
- interrupted process can remain detectable without corrupting quote.

### Tests required

- integration;
- polling API;
- frontend state.

### Demo checkpoint

Processing → Needs Review.

---

## M3-U8 — Quote Correction, Provenance, and Evidence UI

### Objective

Expose source/extraction/current-value differences correctly.

### Dependencies

M3-U6, M3-U7.

### Layers touched

- domain;
- application;
- API;
- frontend;
- tests.

### Scope

Implement:

- `QuoteFieldEvidence`;
- source viewer;
- USER_CORRECTED;
- retained extracted value;
- current value;
- evidence association.

### Acceptance criteria

For source 4.22 → AI 4.22 → user 4.50:

- PDF source still 4.22;
- AI extraction still 4.22;
- current 4.50;
- origin USER_CORRECTED.

### Tests required

- provenance unit tests;
- API tests;
- frontend tests;
- browser correction path.

### Demo checkpoint

4.22 → 4.50 provenance example.

---

## M3-U9 — Quote Confirmation, Revision, Stale Processing, and Idempotent Retry

### Objective

Finish robust quote lifecycle and establish revision behavior needed by M4.

### Dependencies

M3-U7, M3-U8.

### Layers touched

- domain;
- application;
- API;
- frontend;
- reliability;
- tests.

### Scope

Implement:

- Confirm Quote;
- `quote_revision`;
- revision increment on later confirmed-value changes;
- 10-minute configurable stale-processing detection;
- Retry;
- idempotent processing;
- protection of confirmed quote from silent background overwrite;
- manual fallback.

### Acceptance criteria

- only user confirms;
- relevant confirmed-value edit increments quote revision;
- stale processing is retryable;
- retry does not duplicate Quote;
- confirmed value not silently overwritten;
- manual fallback available.

### Tests required

- revision tests;
- idempotency;
- stale-processing;
- API;
- browser retry/fallback.

### Demo checkpoint

Successful PDF, confirmed edit revision, stale retry, manual fallback.

---

# 9. Milestone 4 — Comparison and Sourcing Analyst

## Objective

Deliver:

**confirmed data → deterministic comparison → revision-aware snapshot → evidence-grounded bounded analysis → optional suggested supplier**

M4 owns comparison staleness.

---

## User-Visible Outcome

With at least two confirmed quotes, the user can:

- view deterministic comparison;
- see requirement states/warnings;
- inspect provenance;
- read AI tradeoffs;
- see optional Suggested Supplier;
- see a stale warning if comparison inputs later change;
- regenerate the comparison and receive fresh AI analysis.

---

## M4-U1 — Source Precedence Resolver

### Objective

Centralize source-precedence rules.

### Dependencies

M2 supplier facts, M3 confirmed quote values.

### Layers touched

- domain;
- provenance;
- tests.

### Scope

Implement:

```text id="orku8z"
confirmed project-specific value
>
general curated supplier value
>
unknown
```

Preserve context.

Unconfirmed AI drafts never enter final comparison.

### Acceptance criteria

- quote overrides general commercial context;
- general context remains inspectable;
- differing context does not equal Conflict;
- same-context incompatible values may Conflict.

### Tests required

- source-precedence tests.

### Demo checkpoint

General 30–40 days vs project quote 25 days resolves to 25 without Conflict.

---

## M4-U2 — Remaining Explicit Requirement Evaluators

### Objective

Complete deterministic comparison evaluators.

### Dependencies

M4-U1.

### Layers touched

- domain;
- tests.

### Scope

Implement:

- quantity;
- unit price;
- production lead time;
- delivery compatibility;
- remaining supported capability checks.

Reuse earlier:

- material;
- certification;
- MOQ;
- categorical capability.

### Acceptance criteria

- only approved four result states;
- different currency gives warning;
- quantity mismatch explicit;
- subjective unsupported requirement remains informational.

### Tests required

- comprehensive evaluator unit tests.

### Demo checkpoint

Run deterministic evaluation across primary quotes.

---

## M4-U3 — ComparisonSnapshot Generation and Staleness

### Objective

Create canonical deterministic comparison state and make it revision-aware from day one.

### Dependencies

M4-U1, M4-U2, quote revision semantics from M3-U9.

### Layers touched

- domain;
- application;
- persistence;
- API;
- tests.

### Scope

Add `Comparison`.

Generate snapshot containing:

- supplier facts;
- confirmed quote facts;
- origins;
- evaluator results;
- warnings;
- completeness;
- source references;
- `brief_revision`;
- quote revision map/snapshot.

Implement comparison staleness:

```text id="8x0uh4"
current brief revision or quote revision
!=
revision used by comparison
→ comparison.stale = true
```

When an input changes:

- existing comparison remains stored but is marked stale;
- stale snapshot must not be treated as current analysis input;
- regeneration creates a snapshot from current revisions.

### Acceptance criteria

- ≥2 confirmed quotes required;
- snapshot reproducible;
- no AI required;
- revisions recorded;
- current values used;
- quote/brief change marks snapshot stale;
- regeneration uses latest revisions and clears stale state.

### Tests required

- comparison unit tests;
- revision/staleness tests;
- integration tests;
- API tests.

### Demo checkpoint

Generate comparison, change confirmed quote, observe stale state, regenerate.

---

## M4-U4 — Comparison UI and Stale-State UX

### Objective

Expose deterministic comparison, warnings, provenance, and stale state before AI commentary.

### Dependencies

M4-U3.

### Layers touched

- frontend;
- API;
- tests.

### Scope

Build:

- comparison table;
- requirement states;
- warnings;
- provenance/source indicators;
- Unknown/Conflict;
- price comparison;
- stale warning;
- Regenerate Comparison action.

When stale:

- prior factual snapshot may be visibly marked outdated;
- AI commentary/suggestion must not appear as current.

### Acceptance criteria

- comparison understandable without AI;
- stale status obvious;
- regeneration available;
- stale AI output is hidden/labelled non-current;
- required failures visible.

### Tests required

- frontend tests;
- browser stale/regenerate comparison path.

### Demo checkpoint

Show current comparison, modify quote, show stale state, regenerate.

---

## M4-U5 — Complete Analyst Read-Only Tools

### Objective

Add comparison/quote evidence tools.

### Dependencies

M4-U3, existing M2 tools.

### Layers touched

- AI tools;
- application;
- security;
- tests.

### Scope

Add:

- `get_comparison_snapshot`;
- `get_quote_evidence`.

Tool must not return stale comparison as if current.

### Acceptance criteria

- current project only;
- quote evidence scoped;
- no writes;
- authoritative/current values distinguished from source values;
- stale comparison status exposed.

### Tests required

- tool tests;
- isolation tests;
- stale-snapshot tests.

### Demo checkpoint

Developer-level tool inspection.

---

## M4-U6 — Tradeoff Analysis Capability

### Objective

Explain only the current deterministic comparison.

### Dependencies

M4-U5.

### Layers touched

- AI;
- application;
- API;
- tracing;
- evals/tests.

### Scope

Implement:

- `TradeoffAnalysis`;
- comparison analyst task;
- prompt version;
- bounded loop;
- evidence lookup;
- AIRun;
- recoverable failure.

Before invoking the analyst:

- comparison must exist;
- comparison must not be stale.

If comparison becomes stale later:

- existing analyst result must not be presented as current;
- after regeneration, next analyst run receives the new snapshot.

### Acceptance criteria

- no analyst run on stale snapshot as current;
- regenerated snapshot drives next run;
- narrative agrees with snapshot;
- Unknown/Conflict preserved;
- no numeric score;
- runtime limits enforced.

### Tests required

- contract tests;
- runtime limits;
- stale-analysis tests;
- groundedness evals;
- mocked loop tests.

### Demo checkpoint

Current snapshot → AI analysis; change quote → analysis becomes stale; regenerate → new analysis.

---

## M4-U7 — Suggested Supplier Behavior

### Objective

Add optional validated suggestion.

### Dependencies

M4-U6.

### Layers touched

- AI;
- domain validation;
- frontend;
- evals/tests.

### Scope

Implement `SuggestedSupplierResult`.

Validate:

- supplier shortlisted;
- comparison current;
- cited evidence exists;
- suggestion invalidated when underlying comparison becomes stale.

### Acceptance criteria

Support:

- clear suggestion;
- tie;
- critical unknowns;
- required failure;
- stale comparison.

`null` remains valid.

### Tests required

- validation tests;
- AI evals;
- frontend no-suggestion/stale state tests.

### Demo checkpoint

Show valid suggestion, no-suggestion case, and stale invalidation.

---

# 10. Milestone 5 — Decision and Full Vertical Workflow

## Objective

Finish the final human decision and make the complete five-stage workflow coherent.

Supplier/comparison stale correctness is already implemented in M2/M4 and must not be reimplemented here.

---

## User-Visible Outcome

The user can complete:

**Brief → Suppliers → Quotes → Comparison → Decision**

without developer explanation.

---

## M5-U1 — Preferred Supplier Decision

### Objective

Implement the final human-controlled action.

### Dependencies

M4 current comparison.

### Layers touched

- domain;
- application;
- API;
- frontend;
- tests.

### Scope

Implement:

- preferred supplier;
- decision notes;
- change preferred supplier;
- clear preferred supplier.

### Acceptance criteria

- only shortlisted supplier can be selected;
- user may change selection later;
- no purchasing side effect;
- preferred supplier appears on project/dashboard.

### Tests required

- unit;
- API;
- frontend.

### Demo checkpoint

Select Supplier A, then change to Supplier C.

---

## M5-U2 — Full Workflow Integration and Next-Action UX

### Objective

Make all five stages feel like one coherent application.

### Dependencies

M1–M5-U1.

### Layers touched

- frontend;
- application;
- tests.

### Scope

Integrate:

- Brief;
- Suppliers;
- Quotes;
- Comparison;
- Decision.

Add/finish:

- current stage;
- next action;
- blocked-stage messaging;
- incomplete-state messaging;
- stale supplier warnings already supplied by M2;
- stale comparison warnings already supplied by M4;
- recoverable error/retry states;
- dashboard progress indicators.

Do not duplicate staleness logic.

### Acceptance criteria

- user always understands next valid action;
- stale data routes user toward existing M2/M4 refresh actions;
- inaccessible stages explain prerequisite;
- no unnecessarily large global-state UI;
- complete workflow works manually.

### Tests required

- frontend tests;
- workflow integration tests;
- browser navigation tests.

### Demo checkpoint

Walk through all five stages manually without developer intervention.

---

## M5-U3 — Full Golden-Path Browser E2E

### Objective

Encode the complete portfolio workflow as repeatable automation.

### Dependencies

M5-U1, M5-U2.

### Layers touched

- E2E;
- fixtures;
- CI.

### Scope

Automate:

```text id="qnan6s"
anonymous session
→ create project
→ request
→ structured brief
→ clarification
→ approval
→ discover suppliers
→ shortlist
→ approval
→ quotes
→ confirmation
→ comparison
→ analyst
→ suggested supplier where applicable
→ preferred supplier
```

Include targeted stale-state E2E checks already owned by M2/M4 where practical, without recreating their implementation.

Normal CI should use deterministic/mock model behavior.

Live-model E2E remains separate.

### Acceptance criteria

- golden path passes repeatedly;
- no production dependencies required for normal CI;
- failures identify stage clearly;
- core stale paths remain covered by their dedicated milestone tests.

### Tests required

This unit is primarily E2E.

### Demo checkpoint

One command executes the complete V1 golden path.

---

# 11. Milestone 6 — Hardening and Portfolio Release

## Objective

Turn the functioning MVP into a polished public portfolio release.

No new product functionality.

---

## User-Visible Outcome

A reviewer can:

- use public demo;
- complete core scenario;
- understand recovery behavior;
- inspect repository/docs;
- inspect evals and traces;
- see that all supplier/quote fixtures are synthetic.

---

## M6-U1 — Eval Dataset Completion and Baselines

### Objective

Expand feature-level evals into V1 release baseline.

### Dependencies

All AI capabilities.

### Layers touched

- evals;
- AI;
- documentation.

### Scope

Grow toward:

- 20–30 brief cases;
- focused clarification cases;
- supplier explanation cases;
- 10–20 quote cases/fixtures;
- comparison analysis cases;
- suggestion/no-suggestion cases.

Record baseline results.

### Acceptance criteria

- all eval categories runnable;
- metrics documented;
- failures inspectable;
- critical hallucination/correctness failures visible.

### Tests required

- eval runner validation.

### Demo checkpoint

Run full eval baseline.

---

## M6-U2 — Observability / Langfuse Polish

### Objective

Make AI execution easy to inspect.

### Dependencies

All AI capabilities.

### Layers touched

- tracing;
- AI;
- docs.

### Scope

Ensure traces include:

- run ID;
- operation;
- prompt version;
- model;
- latency;
- tokens/cost where available;
- validation;
- retry;
- tool calls;
- runtime limits;
- status.

Complete optional Langfuse integration.

### Acceptance criteria

- app works without Langfuse;
- traces readable when enabled;
- no secrets/session tokens leak.

### Tests required

- tracing adapter;
- disabled-provider test.

### Demo checkpoint

Show Brief, Quote, Analyst traces.

---

## M6-U3 — Security and Abuse Hardening

### Objective

Validate public-demo boundary.

### Dependencies

Full app.

### Layers touched

- API;
- security;
- sessions;
- documents;
- tests.

### Scope

Review:

- session isolation;
- expiry;
- PDF limits;
- magic bytes;
- storage safety;
- prompt-injection boundary;
- model context minimization;
- tool scope;
- secrets.

Add minimal hosting protection only if necessary.

### Acceptance criteria

- isolation passes;
- bad PDFs fail safely;
- agent cannot access foreign project;
- untrusted PDF cannot trigger tools.

### Tests required

- API security;
- isolation;
- PDF validation.

### Demo checkpoint

Two sessions + malformed PDF rejection.

---

## M6-U4 — Recovery and Failure-State Hardening

### Objective

Ensure failures look intentional and recoverable.

### Dependencies

Full app.

### Layers touched

- application;
- frontend;
- tests.

### Scope

Review:

- model timeout;
- structured-output failure;
- quote extraction failure;
- stale processing;
- no supplier candidates;
- insufficient comparison;
- analyst runtime limit;
- no suggestion.

Stale supplier/comparison correctness itself remains owned by M2/M4.

### Acceptance criteria

- no major failure becomes dead end;
- retry/fallback clear;
- user-facing wording understandable.

### Tests required

- failure API tests;
- frontend states;
- selected E2E recovery.

### Demo checkpoint

Failed PDF → manual entry → comparison.

---

## M6-U5 — README and Portfolio Documentation

### Objective

Make repository understandable to hiring reviewers.

### Dependencies

Architecture stable.

### Layers touched

- docs.

### Scope

README includes:

- purpose;
- five-stage flow;
- architecture;
- AI vs deterministic boundary;
- one-agent rationale;
- why no LangGraph/vector DB/Redis;
- provenance design;
- stale-state design;
- eval strategy;
- tracing;
- local setup;
- demo instructions;
- synthetic-data disclaimer;
- limitations;
- deferred evolution.

### Acceptance criteria

Reviewer understands architecture without reading entire codebase.

### Demo checkpoint

README walkthrough.

---

## M6-U6 — Production Deployment

### Objective

Deploy approved V1 architecture.

### Dependencies

Hardening sufficiently complete.

### Layers touched

- deployment;
- configuration;
- storage;
- database;
- frontend/backend.

### Scope

Deploy:

- frontend;
- FastAPI;
- PostgreSQL;
- S3-compatible PDF storage;
- model credentials;
- optional Langfuse.

### Acceptance criteria

- public demo loads;
- anonymous sessions work;
- golden path works;
- storage works;
- no secrets exposed;
- deployment documented.

### Tests required

- production smoke;
- deployment E2E subset.

### Demo checkpoint

Complete primary scenario publicly.

---

## M6-U7 — Final Portfolio QA and Release Tag

### Objective

Freeze polished V1.

### Dependencies

M6-U1 through M6-U6.

### Layers touched

- all;
- docs;
- tests.

### Scope

Final review:

- user journey;
- stale-state correctness;
- README;
- architecture consistency;
- eval baseline;
- tracing;
- tests;
- fixtures;
- deployment.

Remove obsolete experiments/debug artifacts.

### Acceptance criteria

- CI passes;
- golden E2E passes;
- eval baseline recorded;
- docs match implementation;
- synthetic disclaimer visible;
- release tag ready.

### Demo checkpoint

Final portfolio walkthrough.

---

# 12. Eval Growth Plan

Evals grow with each AI capability.

| Milestone | Eval growth |
|---|---|
| **M1** | Brief extraction + clarification |
| **M2** | Supplier explanation + grounded evidence |
| **M3** | Quote extraction, unknowns, conflicts, provenance |
| **M4** | Tradeoff analysis + suggested/no-suggestion + stale-analysis behavior |
| **M5** | Workflow-level AI regression through E2E |
| **M6** | Dataset expansion + release baseline |

---

## 12.1 M1

Initial brief set:

**10–15 cases**

Include:

- complete;
- missing destination;
- missing delivery;
- missing quantity;
- no target price;
- required certification;
- preferred certification;
- ambiguity;
- non-invention case.

Clarification tests:

- correct missing field;
- no redundant question;
- concise wording.

---

## 12.2 M2

Supplier explanation cases:

- clear match;
- required failure;
- Unknown;
- Conflict;
- near match.

Also verify that analysis is not treated as current when supplier evaluation is stale.

---

## 12.3 M3

Quote cases:

- three primary PDFs;
- missing shipping;
- conflict;
- unsupported scan.

Metrics:

- field accuracy;
- numeric accuracy;
- unknown detection;
- conflict detection;
- source-block accuracy;
- hallucination rate.

---

## 12.4 M4

Tradeoff/suggestion cases:

- clear suggestion;
- tie;
- required failure;
- critical unknown;
- incomplete evidence;
- stale comparison must not yield current analysis.

---

## 12.5 Eval Execution Policy

Normal CI:

- deterministic tests;
- mocked AI contracts.

Live-model evals:

- explicit workflow;
- prompt/model-change checks;
- pre-release validation.

---

# 13. Test Growth Plan

| Test type | M0 | M1 | M2 | M3 | M4 | M5 | M6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Domain unit | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | harden |
| Persistence integration | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | harden |
| API | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | harden |
| Frontend | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | harden |
| AI contract | foundation | ✓ | ✓ | ✓ | ✓ | | harden |
| AI evals | | ✓ | ✓ | ✓ | ✓ | regression | baseline |
| Tool/agent | | | ✓ | | ✓ | | harden |
| Stale-state | | revision foundation | supplier | quote revision | comparison | integration | harden |
| Browser E2E | smoke | brief | suppliers | quotes | comparison | full | production |

Principles:

- exact rules use exact tests;
- stale behavior is tested where derived data is created;
- AI isn't tested only by snapshots;
- provenance has dedicated tests;
- live models do not run on every commit.

---

# 14. Synthetic Data / Fixture Plan

## M2 — Suppliers

Start with approximately 8.

Expand to approximately 15.

Final fixture set should include:

- strong matches;
- near matches;
- required MOQ failure;
- missing certification;
- conflicting certification evidence;
- unsupported material;
- lead-time variation;
- price variation;
- differing capabilities.

All are fictional.

---

## M3 — Quotes

Three primary PDFs:

### Supplier A

- slightly higher price;
- meets requirements;
- strongest evidence;
- acceptable lead time.

### Supplier B

- lowest price;
- slower production;
- preferred certification missing.

### Supplier C

- fastest production;
- higher tooling;
- one unknown.

Additional test fixtures:

- missing shipping;
- conflicting lead times;
- image-only unsupported;
- malformed PDF;
- generated oversized/page-limit fixture where needed.

---

## M6 — Expansion

Only add fixture data needed by a real uncovered test/eval case.

Do not inflate volume for appearance.

---

# 15. Observability Plan by Milestone

## M0

Introduce:

- AIRun;
- prompt version;
- model;
- status;
- timing;
- attempts;
- tokens/cost fields.

## M1

Trace:

- Brief Interpreter;
- Clarification Generator;
- schema repair.

## M2

Trace:

- supplier analyst;
- tool calls;
- model turns;
- limits;
- brief revision used where relevant.

## M3

Trace:

- Quote Extractor;
- extraction failure;
- source-reference validation.

## M4

Trace:

- comparison analyst;
- comparison revision inputs;
- stale/current state;
- evidence tools;
- suggestions.

## M5

Ensure integrated workflow surfaces current trace/state correctly.

## M6

Polish:

- optional Langfuse;
- trace documentation;
- cost/latency baseline.

---

# 16. Implementation Dependencies

```text id="qaol2p"
M0-U1
└── M0-U2
    ├── M0-U3
    │   └── M0-U4
    └── M0-U5
        └── AI capabilities

M1-U1
├── M1-U2
└── M1-U3
     ├── M1-U4
     └── M1-U5
          └── M1-U6

M1-U6
└── M2-U1
    └── M2-U2
        └── M2-U3
            └── M2-U4
                └── M2-U5
                    └── M2-U6
                        └── M2-U7

M2-U7
└── M3-U1
    ├── M3-U2
    └── M3-U3
        └── M3-U4
            ├── M3-U5
            └── M3-U6
                └── M3-U7
                    ├── M3-U8
                    └── M3-U9

M3-U9
└── M4-U1
    └── M4-U2
        └── M4-U3
            ├── M4-U4
            └── M4-U5
                └── M4-U6
                    └── M4-U7

M4-U7
└── M5-U1
    └── M5-U2
        └── M5-U3

M5-U3
└── M6
```

Important ownership:

```text id="uc0l6p"
brief_revision creation
→ M1

supplier stale detection/re-evaluation
→ M2

quote_revision creation
→ M3

comparison stale detection/regeneration
→ M4

final workflow integration
→ M5
```

This avoids duplicate stale-state implementation.

---

# 17. Risks and Scope Guards

## Risk 1 — Brief becomes generic procurement schema

**Guard**

Implement only approved V1 fields/evaluators.

---

## Risk 2 — Supplier discovery becomes live research

**Guard**

Use only synthetic 15-record catalog.

No web search APIs, crawling, embeddings, or external supplier data.

---

## Risk 3 — Sourcing Analyst becomes orchestrator

**Guard**

- read-only;
- no workflow state mutation;
- max 4 turns;
- max 6 tools;
- deterministic application invokes it.

---

## Risk 4 — PDF processing expands into document platform

**Guard**

- PDF only;
- text-extractable only;
- 10 MB;
- 15 pages;
- no OCR;
- manual fallback.

---

## Risk 5 — Requirement evaluation becomes rules engine

**Guard**

Explicit Python evaluator types only.

---

## Risk 6 — Async work introduces queue stack

**Guard**

No Redis/Celery.

Background processing + stale detection + retry.

---

## Risk 7 — Evals postponed

**Guard**

AI unit is not complete without initial evals.

---

## Risk 8 — Stale correctness postponed again

**Guard**

Supplier staleness must be complete in M2.

Comparison/analysis staleness must be complete in M4.

M5 does not reimplement either.

---

## Risk 9 — UI deferred until end

**Guard**

Every milestone has a user-visible checkpoint.

---

## Risk 10 — Scope expansion

Before accepting work, ask:

> Is this required for Brief → Suppliers → Quotes → Comparison → Decision?

If not, defer it.

---

# 18. Suggested Commit / PR Boundaries

Each implementation unit should map roughly to one focused PR or coherent commit group.

Examples:

```text id="8sa1j2"
M1-U3
feat(ai): add structured brief interpreter

M2-U3
feat(suppliers): add deterministic requirement evaluators

M2-U4
feat(suppliers): add project supplier review and revision staleness

M3-U6
feat(quotes): extract structured quote fields with evidence

M4-U3
feat(comparison): add revision-aware comparison snapshots

M4-U6
feat(analyst): add bounded tradeoff analysis

M5-U1
feat(decision): add preferred supplier selection
```

Stale-state behavior should remain inside the PR boundary of the feature that owns it:

- supplier staleness → M2-U4;
- comparison staleness → M4-U3/M4-U4;
- stale analyst protection → M4-U6/M4-U7.

There should be no later “add stale correctness everywhere” PR.

Cross-layer vertical commits remain acceptable when they implement one coherent capability.

---

# 19. Final Implementation Sequence

Recommended execution order:

```text id="r84uqu"
M0-U1  Repository/local skeleton
M0-U2  Persistence/migrations
M0-U3  Anonymous session isolation
M0-U4  Project creation slice
M0-U5  AI client + AIRun foundation
M0-U6  Shared API/test conventions

M1-U1  Brief + Requirement model
M1-U2  Brief readiness
M1-U3  Brief Interpreter
M1-U4  Analyze + brief editing UI
M1-U5  Clarification Generator
M1-U6  Brief approval + revision foundation

M2-U1  Supplier model + initial fixtures
M2-U2  Candidate retrieval
M2-U3  Supplier requirement evaluators
M2-U4  Supplier review + supplier staleness/re-evaluation
M2-U5  Analyst supplier tools
M2-U6  Supplier explanation agent
M2-U7  Complete fixtures + shortlist approval

M3-U1  Quote/provenance domain
M3-U2  Manual quote path
M3-U3  Storage + PDF validation
M3-U4  PDF parsing + blocks
M3-U5  Synthetic PDF fixtures
M3-U6  Quote Extractor
M3-U7  Background quote processing
M3-U8  Correction/provenance UI
M3-U9  Confirmation + quote revision + stale-processing retry

M4-U1  Source precedence
M4-U2  Remaining evaluators
M4-U3  Revision-aware ComparisonSnapshot + stale detection/regeneration
M4-U4  Comparison UI + stale-state UX
M4-U5  Comparison/evidence analyst tools
M4-U6  Tradeoff analysis + stale-analysis protection
M4-U7  Suggested Supplier + stale invalidation

M5-U1  Preferred supplier
M5-U2  Full workflow integration + next-action UX
M5-U3  Golden-path E2E

M6-U1  Eval baseline completion
M6-U2  Observability polish
M6-U3  Security hardening
M6-U4  Failure/recovery hardening
M6-U5  README/docs
M6-U6  Production deployment
M6-U7  Final release QA
```

The plan remains deliberately composed of small, reviewable implementation units rather than large backend/frontend phases.

---

# 20. What Must Not Enter V1

Do not introduce implementation work for:

- live supplier research;
- external supplier APIs;
- browser research;
- multiple AI agents;
- AI orchestrator;
- LangGraph;
- CrewAI;
- LangChain dependency;
- LiteLLM;
- embeddings;
- vector databases;
- generalized RAG;
- Redis;
- Celery;
- RabbitMQ;
- durable worker infrastructure;
- OCR;
- scanned-document support;
- spreadsheet quote uploads;
- email;
- RFQ sending;
- supplier outreach;
- automated negotiation;
- purchase orders;
- payments;
- logistics;
- shipment tracking;
- production tracking;
- supplier portal;
- user accounts;
- OAuth;
- organizations;
- RBAC;
- advanced procurement analytics;
- configurable supplier weighting;
- numeric supplier scoring;
- generic rules engine;
- generic agent framework;
- generic document-processing platform;
- microservices;
- Kubernetes.

If implementation pressure suggests one of these is needed, first attempt to solve the V1 requirement within the approved architecture.

---

# Execution Readiness

**The plan is ready for execution.**

There are no unresolved implementation-planning decisions that block starting the repository.

The main sequencing dependencies are now explicit:

- M1 establishes `brief_revision`;
- M2 owns supplier-evaluation staleness and re-evaluation;
- M3 establishes `quote_revision`;
- M4 owns comparison/AI-analysis staleness and regeneration;
- M5 only integrates the completed stages and final human decision.

This removes the previous correctness gap where a vertical slice could display downstream results as current after its upstream inputs changed.

Implementation can proceed **one unit at a time** using the coding-agent workflow defined in this document.

---

# First Coding Unit

## M0-U1 — Repository and Local Application Skeleton

This remains the first unit to give to the coding agent.

Nothing in the sequencing cleanup changes that dependency.

M0-U1 comes first because every later slice needs a reproducible environment in which:

- Next.js runs;
- FastAPI runs;
- PostgreSQL is available;
- frontend can reach backend;
- configuration conventions exist;
- lint/type/test tooling works.

The coding agent should stop when M0-U1 acceptance criteria are met.

It should **not** opportunistically create:

- domain tables beyond what M0-U1 requires;
- AI prompts;
- supplier models;
- quote models;
- agent tools;
- future workflow abstractions.

After M0-U1 is reviewed and committed, execution proceeds to **M0-U2**.
