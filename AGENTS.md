# SourcePilot Repository Context

## Purpose

SourcePilot is an AI-assisted, evidence-backed supplier sourcing workspace.

Its locked V1 flow is:

Brief → Suppliers → Quotes → Comparison → Decision

The user remains responsible for approving the brief, shortlist, quote data, and final preferred supplier.

## Authority and conflict handling

Follow this source-of-truth order:

1. `docs/specs/SourcePilot-Product-Specification-v0.2.md`
2. `docs/specs/SourcePilot-Technical-Architecture-v0.2.md`
3. `docs/specs/SourcePilot-Implementation-Plan-v0.2.md`
4. Approved current implementation-unit document in `.local-investigation-artifacts/private-development/docs/implementation/`
5. Existing code

If a lower-level source conflicts with a higher-level source:

1. do not silently choose;
2. do not redesign the system;
3. report the conflict clearly;
4. wait for human direction.

## Required context before substantial work

Before planning, implementation, or review work:

1. read this file;
2. read the relevant sections of the Product Specification, Technical Architecture, and Implementation Plan in the order above;
3. read the current implementation-unit document when one exists;
4. inspect the affected code and tests.

For a new implementation unit or a broad or ambiguous change, read the full relevant unit definition and enough of each authoritative document to establish all applicable constraints. Do not reread unrelated specification sections for a narrowly scoped follow-up or review.

## Protected source-of-truth documents

The following documents must not be modified incidentally during implementation:

- `docs/specs/SourcePilot-Product-Specification-v0.2.md`
- `docs/specs/SourcePilot-Technical-Architecture-v0.2.md`
- `docs/specs/SourcePilot-Implementation-Plan-v0.2.md`

Changes to these documents require an explicit documentation or design task and human approval. Implementation code must conform to them rather than silently modifying them to match implementation choices.

## V1 hard boundaries

V1 is a modular monolith using:

- Next.js / React / TypeScript frontend;
- FastAPI / Python backend;
- PostgreSQL;
- application-owned workflow;
- structured LLM calls for bounded tasks;
- one bounded, read-only Sourcing Analyst;
- deterministic business rules;
- human approval for important transitions;
- first-class evals and tracing.

Do not introduce or require the following unless the approved architecture is explicitly revised:

- LangGraph;
- CrewAI;
- LangChain dependency;
- LiteLLM;
- multi-agent architecture;
- a top-level AI orchestrator;
- Redis or Celery;
- vector databases or generalized RAG;
- OCR;
- live supplier research;
- microservices;
- speculative infrastructure.

Read the Technical Architecture for the authoritative details and rationale.

## Coding standards

Follow `docs/development/CODING_STANDARDS.md` for stable repository-wide coding principles.

Do not duplicate those standards here. Tool-specific commands and configuration belong in the repository only once those tools are approved and introduced.

## Change path

Follow the Full Flow by default for implementation units and material changes.

The Fast Path defined in `docs/development/WORKFLOW.md` may be used only for clearly small, isolated, low-risk changes.

When uncertain, use the Full Flow.

## Implementation-unit boundary

Work on one approved implementation unit at a time.

Do not begin, partially scaffold, or opportunistically implement the next unit. Stop after the current unit has passed its done check and been committed.

Follow `docs/development/WORKFLOW.md`.

## Private implementation records

Approved current-unit records live privately at
`.local-investigation-artifacts/private-development/docs/implementation/`.
A fresh clone can build and test without these records. Before continuing an
existing unit, obtain its approved record if it is absent; never infer approval
from code or commits. New unit work still requires an explicitly approved plan.
The private archive's navigation index maps original paths without changing
historical records. The Product Specification, Technical Architecture and
Implementation Plan remain the higher-authority tracked sources.
