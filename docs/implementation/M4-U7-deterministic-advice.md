# M4-U7 deterministic advice — reviewed scope

## Authority and approved boundary

Read AGENTS, Coding Standards, Workflow, Product §§30–37, Architecture §§2.6,
5.8, 8.3–8.5, 11.6–11.8 and 15.10, Implementation Plan M4-U6/U7, and the
existing M4-U7/context correction. The new approval supersedes the context-only
restriction on combined model output/repair, not public contracts or validators.
No higher-authority conflict requires protected-specification edits. The Analyst
still selects relevant supported tradeoffs, verification actions and an optional
supplier, using its existing read-only tools and budgets. The separate tradeoff
endpoint retains its prompt, contract, parser and lifecycle behavior.

## Implementation sequence

1. Build a pure snapshot-bound fact catalogue and deterministic renderer; verify
   assembled outputs through both unchanged public validators before integration.
2. Add strict typed selections, semantic checks and one targeted repair. Model
   output contains no states, values, evidence IDs or display prose.
3. Opt the combined endpoint into this task inside the existing bounded runtime;
   preserve the default tradeoff path, provider policy, tools, budgets, tracing
   and freshness checks. Use comparison-selection-v1 / comparison-advice-v10.
4. Update source-detail requirement identity, deterministic test model, eval
   provenance/classification, retained-failure and regression coverage.
5. Measure actual serialized initial/follow-up/repair payloads, run provider-free
   checks, reconcile cumulative inventory, and stop for independent Review.

## Clarifications incorporated before implementation

### Repair and preservation

For a schema-valid draft, validate every slot and freeze valid slots. Invalid
optional list slots may explicitly be removed; invalid highlights may be removed
only if the final list retains its minimum of one. The suggestion is mandatory
and cannot be removed. Duplicate occurrences are all invalid slots. Replacements
and removals address original indexes, and merging occurs simultaneously so index
shifts cannot edit frozen entries. Repair must address each invalid slot exactly
once; unknown/duplicate/frozen slot edits fail. Cross-item constraints are checked
again after merging. A null VERIFY_BEFORE_CHOOSING suggestion without a valid
verification action is itself invalid, permitting a simultaneous suggestion/action
correction; a frozen valid suggestion cannot be invalidated by removing its last
verification action. If there is no valid replacement/removal consistent with
minimums and frozen entries, fail after the one repair. No second repair.
Malformed JSON/schema has no semantically validated slots and may receive the
single full-contract repair. Application-owned facts/disclosures never enter the
repair contract. Deterministic assembly failures never trigger model repair.

### Highlights

Highlights are ordered fact IDs, not an inclusion filter. Each fact renders once
per analysis section. Within its authoritative section, highlighted facts appear
first in model order, followed by other required/baseline facts in stable snapshot
order. Highlights of nonbaseline quote fields add those fields once. A highlighted
UNKNOWN/CONFLICT stays in its mandatory section. Selecting a monetary field also
binds its currency reference but does not duplicate a separate numeric fact.
Mandatory sections, supporting reasons and advisory choice remain independent;
highlights cannot suppress disclosures or make unresolved facts supporting reasons.

### Context mapping and measurements

Keep the current comparison_context projection with all decision-relevant facts,
evidence and provenance. Add a compact catalogue INDEX, not a second copy of those
facts: R IDs resolve supplier index and evaluation-result index; Q IDs resolve
supplier index and projected quote-field index. Requirement definitions remain in
brief.requirements and the enclosing supplier retains ownership/quote revision.
The application catalogue is built from the full original snapshot, not the
projection. Model index entries must resolve exactly to that original catalogue.
Comparison-tool replies use the same indexed projection for combined advice only;
other tool replies and tradeoff context stay unchanged. Repair keeps the original
context and exact rejected final, appending only bounded trusted slot feedback.
Measure serialized complete requests including instructions, schema, tools and
input_items for manual/missing/PDF fixtures in all three phases. Compare indexed
context with the former projection and a naive duplicated catalogue. Byte sizes
are not token, latency or live-quality claims.

## Internal contract and public assembly

All internal objects forbid extra fields. Every field is required, including
nullable suggestion properties. No model-authored narrative, state, value,
currency or evidence ID is accepted.

| Selection | Shape and semantic boundary |
| --- | --- |
| Envelope | version=comparison-selection-v1, bound snapshot_id, highlights, tradeoffs, verification_actions, suggestion |
| highlights | 1–12 unique catalogue IDs; ordering only, plus inclusion of selected nonbaseline quote fields |
| tradeoffs | 0–6 unique relation/fact_ids objects; SAME_REQUIREMENT has two suppliers' findings for one requirement; SAME_QUOTE_FIELD has two known compatible numeric/time fields; PRICE_AND_PRODUCTION has price/time A then price/time B |
| verification_actions | 0–6 unique action/fact_id objects; CONFIRM_MISSING→UNKNOWN, RESOLVE_CONFLICT→CONFLICT, VERIFY_QUOTE→known quote field, CONFIRM_DELIVERY→missing delivery_date/total_lead_time |
| suggestion | supplier_id or null; 0–6 reason_fact_ids; nullable no_suggestion_reason (NO_CLEAR_PREFERENCE or VERIFY_BEFORE_CHOOSING) |
| selected supplier | Participates in bound comparison; 1–6 unique owned MEETS requirement or KNOWN quote reasons; null explanation absent |
| null supplier | Empty supporting reasons; explicit explanation; VERIFY_BEFORE_CHOOSING requires a valid action and the public explanation cites its targets |
| repair | version=comparison-selection-repair-v1, same snapshot_id, 1–25 replacements; each invalid slot exactly once, typed replace or permitted remove/null |

Fact identity is R:supplier_id:requirement_id or Q:quote_id:field_key. The
application catalogue retains full original source/ownership/revision/evidence;
the model receives a location index into the existing projection. Requirement
evaluation and quote completeness are separate fact kinds. Same-quote currency
and quantity dependencies accompany monetary relationship citations. Monetary
relationships require equal known currencies and quoted quantities; price/time
also requires strictly separated production intervals. No FX conversion or
delivery inference is introduced.

Public ComparisonAdviceV1, AnalysisPoint, TradeoffAnalysis and
SuggestedSupplierResult are unchanged. Application code emits all evaluated
requirements, all UNKNOWN/CONFLICT requirements in their required sections, and
selected-supplier failures/uncertainties. Baseline commercial display covers
unit_price, quoted_quantity, moq, production_lead_time, shipping_cost,
tooling_cost, currency, total_lead_time and delivery_date. This is a presentation
policy, not a new public validator invariant requiring all missing quote fields.
Currency/quantity and delivery cautions are application-owned. Known monetary
facts preserve same-quote currency and correction provenance. Arbitrary saved
prose remains available in source details rather than entering state sentences.
Requirement identity and expected value/importance are displayed from the bound
snapshot; boolean false renders as No. The model chooses emphasis, supported
relationships, verification priorities and optional advisory supplier, with no
scoring or write authority. Both public validators run after assembly.


## Reviewed presentation corrections and acceptance

Verification actions name the owning supplier and exact target; repeated requirements retain expected values/importance. Only valid conflicting USER_CORRECTED unit price may additionally display current corrected amount without assigning unresolved currency or promoting numeric comparison/support. Current 4.50 is visible; extracted 4.22 remains separate provenance. Other fields/states/origins remain unchanged and both public validators apply.

Independent review and focused QA passed (three action scenarios and two correction scenarios). Original six-submission live batch remains FAIL (8/24 provider invocations). Separate supplemental PDF PASS used 1/1 submission, 1/4 invocation, no retry/repair/tools. It closes the specific omitted-amount defect only. Fifteen human reviews remain pending; general reliability, live-null usefulness and exact historical replay remain unverified.

See [final acceptance](M4-U7-final-done-check.md). Retention split approved and applied on 7 November 2026; commit remains paused. Full original record and all failed attempts remain in the local-only archive: `../../.local-investigation-artifacts/M4-U7/original-tree/docs/implementation/M4-U7-deterministic-advice.md`.
