# V1 eval baselines

All suppliers, requests, quotes and recorded responses are synthetic. Recorded
responses are curated contract/scorer regression fixtures, not proof of live model
quality. This unit adds no production behavior, schema, agent or tracing system.

From `apps/api`, with existing dependencies installed:

```text
uv run --no-sync python -m sourcepilot.ai.eval_baseline --mode offline --output .eval-results/offline
uv run --no-sync python -m sourcepilot.ai.eval_baseline --mode offline --categories brief clarification --output .eval-results/intake
uv run --no-sync python -m sourcepilot.ai.eval_baseline --mode live --output .eval-results/live
```

The first command is the full offline baseline and runs in normal CI. Live is
explicit only. Set the existing `OPENAI_API_KEY`, `SOURCEPILOT_AI_MODEL` and a dedicated
already-configured `EVAL_DATABASE_URL` in the command environment. Local `.env`
values must be loaded by the caller; the runner never searches for credentials or
falls back to `DATABASE_URL`/`TEST_DATABASE_URL`. Do not create, migrate, reset or
repurpose a database to make this run succeed.

Preflight validates selected fixture/scorer controls, provider configuration,
PostgreSQL URL/connectivity, connected database identity, repository Alembic heads
and required columns using a read-only transaction. Query/libpq routing overrides
are rejected. The eval engine is separate from the cached application engine.
Only after preflight does live evaluation insert fresh eval-owned synthetic
sessions/projects/suppliers/quotes/evidence/comparisons. Existing projects and shared
suppliers are untouched. Records are retained for inspection; no automatic cleanup
or schema mutation occurs. Existing application runtimes own validation, scope,
repair/provider retries and turn/tool limits. Tools read these real scoped records;
the runner does not patch their authorization or provide its own model loop.

## Cases and completeness

| Category | Required cases | Live input scenarios | Offline-only controls/no-model cases |
| --- | ---: | ---: | --- |
| Brief | 24 | 24 | None |
| Clarification | 12 | 9 | Three complete Briefs correctly skip the model |
| Supplier explanation | 11 | 6 | Five negative output controls |
| Quote extraction | 12 | 10 | Image-only and malformed parser rejection |
| Comparison | 13 | 9 | Three negative output controls; stale runtime rejection before provider construction |
| Suggestion | 18 | 11 | Seven negative output controls |

A run is complete relative to its selected categories when every required selected
case is accounted for exactly once. Omitted, duplicated or unexpected skipped cases
make it incomplete. Only runs selecting all six categories qualify as full baselines.
Negative controls test scorer sensitivity offline and are never prompts asking the
live model to produce deliberately bad answers. Live controls remain labelled as
offline-only checks, separate from provider-produced results.
The separate fifteen-example human-review set is not part of the 90 automated case
denominator. Automated case completion leaves its review status pending.

## Status and exits

| Outcome | Case/run status | Exit |
| --- | --- | ---: |
| Offline expectation mismatch or missed expected rejection | REGRESSION_FAILED | 1 |
| Configuration/database/preflight/provider transport/system/harness/adapter/scorer/report error | Specific error; ERROR or INCOMPLETE | 2 |
| Expected negative-output or unsupported-parser rejection | EXPECTED_REJECTION | 0 |
| Live exact assertion failure or triggered critical heuristic | QUALITY_FINDING; COMPLETED_WITH_FINDINGS | 0 |
| Correct runtime termination after model repair exhaustion, model turn/tool limit, or model-selected forbidden tool scope | QUALITY_FINDING; COMPLETED_WITH_FINDINGS | 0 |
| All applicable checks pass | PASS; COMPLETED | 0 |

Exit 2 takes precedence over exit 1. Runtime quality findings count as accounted-for
cases, but do not count as successful model outputs. Exit zero never certifies live
quality or release readiness. Critical findings need triage; production fixes require
separate scope approval. Independent cases continue after a failure. No outer retries
replace failing results. Source changes during a run invalidate its evidence.

## Metrics and limitations

`results.json` contains case outputs, named assertions, available AIRun metadata,
captured synthetic responses (including rejected model JSON/tool requests), counts
and critical findings. `summary.md` is the readable case/status index. No credentials,
session token, provider headers or database URL is included. CapturingClient only
delegates existing client methods; this is local eval evidence, not new tracing.

- `measurements` holds metric numerators/denominators and their `kind` (`exact` or
  `heuristic`), pooled across actual measured cases. Readable metric rows include
  the same kind. `metrics` holds **exact deterministic assertion pass counts** only.
  `heuristic_signals` holds triggered/inspected counts; a non-trigger is not a
  groundedness pass. `human_review` holds the difficult-case set with status
  `PENDING` and null review results until a person actually reviews it.
  `narrative_groundedness` is `NOT_ESTABLISHED_BY_AUTOMATED_SCORING` even when
  all 90 automated cases are complete.
- Brief: per-field accuracy (product/category, quantity, destination, delivery,
  optional price, requirements, attributes and ambiguity); hallucinated-field rate
  is invented nonempty values divided by fields expected absent. Structured lists
  compare without ordering. Decimal representations are equivalent. Only explicit
  category/ambiguity aliases in each case are accepted.
- Clarification: missing-field coverage, duplicate/redundant and irrelevant question
  rates remain exact. `clarity_rate` (fraction ending in a question mark with at
  least three words) and `conciseness_rate` (fraction with at most 120 characters)
  are **heuristics**, not human judgments. Their scorer metadata includes the
  original rate and definition; a rate below 1 triggers a noncritical signal.
  They appear in `heuristic_signals`, never in exact assertion pass counts. The
  existing `clarity_heuristic` and `conciseness_heuristic` measurements retain their
  original question-level numerators/denominators and are explicitly heuristic.
  Missing keys come from production readiness. The existing five-question cap is
  only a regression.
- Quotes: field accuracy, numeric/currency accuracy, unknown/conflict detection,
  source-block accuracy, and hallucination rate. Unknown is not zero. Source lists
  and conflict alternatives are order-insensitive; money decimals are equivalent.
  Free-text commercial clauses remain wording-sensitive except for the reviewed
  Harbor rules below; unfamiliar prose still needs human triage.
- Supplier explanations: exact checks cover production state/evidence validation,
  required sections and application-rendered requirement text. The separate
  `supplier_free_text_capability_signal` is a bounded lexical cue for recognizable
  unsupported supplier action or capability statements. It compares authored text
  with deterministic findings, normalized supplier facts and cited fetched evidence.
  The bounded actor vocabulary includes workshop(s) and manufacturer(s); these
  nouns add no capability support. The action and object must still match support.
  It may miss unsupported prose or flag a novel valid paraphrase; absence of a signal
  never certifies a supplier's free-text factual claims.
- Comparison/suggestion: exact checks cover production reference/state/disclosure
  validation and allowed suggestion IDs. Bounded narrative signals inspect recognized
  numeric/source discrepancies and topic disclosures. The named
  `incomparable_price_ranking_signal` flags recognizable relative price claims when
  currencies or quoted quantities are incomparable. Accurate supplier-bound figures
  and warnings are allowed without a fixed sentence grammar. Price checks recognize
  uppercase A/B/C aliases only for uniquely named Supplier A/B/C records in the
  scenario; aliases never bypass value, currency or reference checks. A nearby
  non-comparability warning does not suppress a recognized unsupported ranking.
  Bounded local cues such as "cannot conclude that B is cheaper" or "unclear
  whether B is cheaper" suppress only the immediately governed ranking. Each
  recognized ranking is inspected separately, so rejecting one does not hide
  another asserted ranking. "B is not cheaper" remains a comparative assertion.
  These rejection cues are non-exhaustive and do not interpret arbitrary prose.
  The
  `lead_time_context_signal` flags recognizable general/catalog versus project/quoted
  duration mismatches. Ambiguous phrasing is left for human review rather than being
  rejected by keyword proximity. These signals cover representative hazards, not all
  possible meanings. They are not exhaustive semantic validation.
- A zero denominator means not applicable; no artificial measured success is added.
  Reports identify how many cases actually supplied each metric. Failed runtime cases
  have no extracted-value measurements; their failure status remains prominent.

### Quote scorer correction (M6-U1, 2026-11-03)

Scoring requires the complete actual parsed blocks, bound to the selected PDF name,
SHA-256 and existing extraction-request hash (including ordered IDs and text).
`parser_result` attaches this transient context to the in-memory case for both the
offline and live scoring paths. It never writes it into a dataset. Missing,
incomplete or wrong-document context is `SCORER_ERROR`, exit 2, not a model quality
finding. Unsupported image-only/malformed cases still follow expected parser
rejection, without requiring extraction context. No expected-citation subset is
used as the document membership universe.

Membership and attribution are independent. Every returned field/alternative ID
must belong to the parsed document. Field evidence must additionally match its
expected set, including conflict value-to-source pairing, or an explicitly reviewed
case/field/content-specific alternative. A real but irrelevant ID fails attribution.
An ID shared by two PDFs does not establish the document's identity or its content.
Conflict field assertions, field accuracy and conflict detection all require the
correct state and alternative-to-evidence pairing.

Only `harbor-primary` / `harbor_primary.pdf` has these new equivalences:

- Exclusions: case-only equality with `import duties are not included`, backed by
  the exact `p2-b7` exclusion text. Negation, punctuation, conditions and wording
  are otherwise unchanged.
- Certifications: `GRS` is equivalent to the full synthetic-record value only
  with exactly `p2-b4`, its unchanged source text, and uncertainty exactly
  `The document describes this as a synthetic record, current for this fictional supplier.`
  Missing/altered qualifications or added verification claims fail. This is not
  real-world certification verification or general semantic matching.
- Currency: any nonempty subset of `p1-b5`, `p1-b7`, `p1-b8`, `p1-b11` supports
  USD when the extracted/expected currency is USD and every cited block matches
  its reviewed original text (unit price, tooling, sample and shipping costs).
  Empty, irrelevant, foreign-currency or additional unrelated citations fail.

Human approved retaining Harbor `supplier_notes=UNKNOWN`. The exact sourced
`Synthetic demo quote - not a real supplier offer` representation, with no added
uncertainty and a nonempty subset of the matching disclaimer blocks `p1-b1` and
`p2-b1`, is a **field-assignment error**, not unsupported invention. This exception
does not define other supplier notes. An exact expected fact assigned to another
field with that fact's exact evidence is likewise an assignment error; numeric
support can be recognized across integer/decimal field types without accepting
the incorrect destination field. Field accuracy, UNKNOWN detection and field-source
correctness still fail as applicable. Membership alone never establishes support.

Quote measurements use these explicit denominators:

| Metric | Numerator | Denominator |
| --- | --- | --- |
| `field_accuracy` | Correct expected field states/values under bounded rules | All 21 fields |
| `numeric_accuracy` | Correct expected KNOWN numeric fields | Expected KNOWN numeric fields |
| `currency_accuracy` | Correct expected KNOWN currency | 1 if expected KNOWN, otherwise 0 |
| `unknown_detection` | Correct UNKNOWN/null fields | Expected UNKNOWN fields |
| `conflict_detection` | Correct CONFLICT state and exact alternatives/evidence pairing | Expected conflict fields |
| `source_block_accuracy` | Correct field-specific evidence, separately from value correctness | All 21 fields |
| `hallucination_rate` | Unsupported KNOWN numeric/currency values in expected-UNKNOWN fields | Expected UNKNOWN fields |
| `expected_unknown_known_rate` | Every KNOWN output in an expected-UNKNOWN field (the former hallucination numerator) | Expected UNKNOWN fields |
| `unsupported_value_rate` | Unsupported KNOWN numeric/currency values, including expected-KNOWN replacements | All 21 fields |
| `unresolved_support_rate` | KNOWN free-text mismatches without recognized support/equivalence | All 21 fields |

These are bounded deterministic oracle checks, not exhaustive documentary entailment.
Unrecognized free text is **unresolved**, never automatically accepted or asserted
to be proven invention. It creates a named critical `field.<key>.unresolved_support`
finding even when `hallucination_rate` is zero. Unsupported numeric/currency values,
recognized assignment errors and misattributed evidence create respectively named
critical `unsupported_value`, `field_assignment` and `misattributed_evidence`
findings. Existing field/UNKNOWN assertions remain. Diagnostic rates are measurements,
not extra aggregate pass assertions. The original seven aggregate metric assertions
retain their names; named diagnostic findings are additional and counted separately
when comparing with historical assertion totals.

Assertion details retain rule identifiers, actual/expected values or evidence, and
qualification text. Historical baselines keep their original definitions and counts;
the retained Harbor result remains **34/43**, including its original **1/7**
hallucination measurement. Any corrected local rescore is new evidence with both
definitions/counts visible, not a replacement baseline or live acceptance result.

The small human-review set in `human_review/narrative_cases.json` includes mixed
currencies, unequal quantities, supplier actions with unrelated valid evidence, and
general versus quoted lead-time paraphrases. Its review criteria and automation
limits are recorded per example. Human review is **pending**; example criteria are
not review outcomes. Preserve actual outputs and signals during triage. No judge-model
dependency is used.

The currency-grounding follow-up adds five factual-review regressions: the exact
observed v7 shipping-currency contradiction, known quote currency with scalar
shipping/tooling amounts, missing currency, conflicting currency, and known
currency without PDF verification. Context and review criteria are retained per
case. The observed answer was structurally VALID but factually contradicted by
the saved USD currency; that historical finding remains open. The other examples
are curated contract-compatible responses, not live model outputs. Field-specific
evidence omitting sibling currency is distinct from currency missing in the full
snapshot. All five remain PENDING/null in offline reports under existing review
conventions; the 90 automated cases and scoring are unchanged. Provider-free
success proves neither live prompt adherence nor narrative factual correctness.

## Source provenance and retained evidence

Pre-run HEAD and dirty status accompany hashes of small explicit source/input lists
for the selected categories, selected datasets/outputs/PDFs, prompt definitions,
and dependency locks. Only live mode includes adapter and Alembic preflight inputs;
unrelated category data/source files are excluded. Model configuration and UTC timestamps
are recorded. The same
files are rehashed after execution. No self-referential final-commit SHA is required,
and this is not a generalized repository manifest framework.

Working `.eval-results/` reports are ignored. The recorded full offline evidence lives
under `docs/implementation/evidence/M6-U1/offline/`. A live baseline is **not started**
while EVAL_DATABASE_URL is absent; configuration blockage is recorded in the unit
document rather than represented as a successful live run. No live model-quality
claim can be made from offline or injected-client integration tests.

Adapter integration tests use the repository's existing test database under an outer
transaction rollback, with provider construction forbidden. These are normal tests,
not a live-baseline fallback. They do not create/migrate/reset the database and roll
back their new rows. They require an already migrated test database.
