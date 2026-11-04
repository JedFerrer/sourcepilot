# SourcePilot

SourcePilot is an AI-assisted, evidence-backed supplier sourcing workspace. It turns an informal product request into structured requirements, reviewed quotes and a supplier comparison, while keeping the final decision with the user.

**Brief → Suppliers → Quotes → Comparison → Decision**

| Stage | What happens |
| --- | --- |
| Brief | Interpret the request, clarify missing details, then explicitly approve the requirements. |
| Suppliers | Review candidates and evidence from the curated catalog; approve a shortlist of up to three. |
| Quotes | Upload PDFs or enter values manually; correct and explicitly confirm each quote. |
| Comparison | Compare facts, requirement fit and uncertainties; request AI tradeoff analysis and an optional suggestion. |
| Decision | The user selects **Mark as Preferred Supplier**. No procurement or supplier communication follows. |

## Synthetic demo data

Supplier names, capabilities, prices, and evidence fixtures are entirely
synthetic. The quote PDF fixtures are also synthetic. SourcePilot makes no
claims about real manufacturers. The curated supplier catalog exists to make
the demo and tests reproducible; it is not live supplier research.

## Architecture and responsibility boundaries

V1 is a modular monolith. **Application code owns the workflow. AI interprets and explains. Humans approve.**

```text
Next.js / React / TypeScript
    └── FastAPI / Python
          ├── Application services + deterministic domain rules
          │     ├── PostgreSQL: projects, revisions, evidence, AI runs
          │     └── Private PDF storage: local or S3-compatible adapter
          └── AI capabilities → model provider
                └── Optional sanitized metadata → Langfuse
```

| Responsibility | Owner |
| --- | --- |
| Readiness, candidate retrieval, requirement evaluation, source precedence, arithmetic, validation and workflow transitions | Deterministic application/domain code |
| Brief interpretation, clarification wording and quote-text interpretation | Bounded structured LLM calls |
| Evidence lookup, supplier explanations, comparison tradeoffs and optional suggestion | One bounded Sourcing Analyst |
| Brief approval, shortlist approval, quote verification and preferred supplier | Human |

The Sourcing Analyst is the only agent: it chooses read-only evidence tools within the current project. Defaults cap execution at **four model turns and six tool calls**; exhausted limits produce a recoverable failure. It cannot modify records, approve a step or contact suppliers. Extraction calls are separate structured tasks, not agents. Model-directed lookup is useful for explanation; the known five-stage workflow needs no AI orchestrator.

## Evidence and freshness

Supplier claims link to curated evidence. PDF fields reference validated page/block IDs. Source evidence, AI extraction, current values and their origins remain distinct: correcting a price changes the project value without making the PDF evidence support that correction. Only confirmed quotes enter the factual comparison; project-specific values take precedence over general catalog information. Different contexts are not automatically conflicts, and missing information remains **Unknown**, not a negative finding.

Internal Brief and quote revisions identify stale supplier evaluations and comparison inputs. Changed inputs require re-evaluation or regeneration; stale analysis is not presented as current advice. The UI provides guidance without a visible version-history system. See the [provenance design](docs/specs/SourcePilot-Technical-Architecture-v0.2.md#13-evidence-and-provenance-model) and [recovery/staleness design](docs/specs/SourcePilot-Technical-Architecture-v0.2.md#19-reliability-retries-and-idempotency).

## Evaluation and tracing

The [eval guide](apps/api/evals/README.md) covers Brief, clarification, supplier explanation, quote extraction, comparison and suggestion cases. Normal CI uses deterministic tests, model doubles and curated offline cases; live-model evaluation is explicit. Exact assertions, heuristic signals and human judgments remain separate. [Browser E2E](docs/local-development.md#deterministic-browser-workflow-m5-u3) exercises the integrated workflow with a test-only model.

PostgreSQL `AIRun` records retain prompt/model identity, validation, retries, timing, available usage and Analyst counts. [Optional Langfuse](docs/development/OBSERVABILITY.md) exports sanitized execution metadata on a best-effort basis; the application works without it. Raw prompts, PDF text, model outputs and credentials are not exported. **Hosted Langfuse visibility remains unverified.**

### Known quality and UX limitations

- The full 90-case Analyst-v2 baseline remains **ERROR / exit 2, 20 runtime errors**. The separate 31-case Analyst-v3 follow-up remains **ERROR / exit 2, ten runtime errors**. No successful complete current-version full baseline is established.
- Ten human reviews remain pending. Brief/quote correctness findings and Analyst quality failures remain unresolved; automated scoring does not establish narrative groundedness. See [M6-U1's preserved evidence and risks](docs/implementation/M6-U1.md#evidence-and-unresolved-product-quality-risks).
- Deterministic E2E success is not live-model quality approval. The real live-advice preservation browser assertion remains unexercised; [M5-U1](docs/implementation/M5-U1.md) records the prerequisite failures and fixture-backed coverage.
- **Save a manual quote draft before uploading another quote.** That upload can discard unsaved edits on another quote; [M6-U4](docs/implementation/M6-U4.md) records this existing UX limitation.

## Run and demonstrate locally

Start with [local setup](docs/local-development.md#configure-and-start), then follow the [manual demo walkthrough](docs/local-development.md#manual-demo-walkthrough). It uses the existing synthetic PDFs and actual approval actions, with manual recovery when extraction fails. Interactive AI actions require server-side model credentials; automated checks use doubles.

The workflow and storage adapters are implemented locally. **Production deployment (M6-U6) and final release approval remain pending**; this repository does not claim a verified hosted demo.

## Tradeoffs and deferred evolution

- **No LangGraph:** application transitions and PostgreSQL persistence handle pauses/resumption; V1 has no long-running model-controlled workflow.
- **No vector database:** 15 structured synthetic supplier records support deterministic retrieval without embeddings or generalized RAG.
- **No Redis/Celery:** lightweight in-process PDF work uses persisted status, stale-processing detection and explicit retries. This is not a durable worker queue.
- **Deliberate demo limits:** anonymous sessions default to a fixed 24-hour lifetime; PDF inputs must be text-extractable and within the default 10,000,000-byte/15-page limits. No OCR or spreadsheet upload. Original currencies and quantities remain visible; there is no automatic FX conversion or numeric supplier score.

Live supplier research, outreach, procurement execution, accounts/teams, OCR and heavier orchestration/worker infrastructure are outside V1. [Future architecture possibilities](docs/specs/SourcePilot-Technical-Architecture-v0.2.md#31-future-architecture-evolution) depend on new product or operational needs, not a committed migration path.

For the authoritative detail, read the [Product Specification](docs/specs/SourcePilot-Product-Specification-v0.2.md), [Technical Architecture](docs/specs/SourcePilot-Technical-Architecture-v0.2.md) and [Implementation Plan](docs/specs/SourcePilot-Implementation-Plan-v0.2.md). Contributor work follows [AGENTS.md](AGENTS.md), the [workflow](docs/development/WORKFLOW.md) and [coding standards](docs/development/CODING_STANDARDS.md).
