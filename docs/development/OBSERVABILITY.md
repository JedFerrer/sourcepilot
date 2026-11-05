# AI observability

Comparison execution records allowlisted validation reason codes and phase labels for initial and repaired finals. Schema diagnostics include only known field/category labels; rejected output, quote content, exception messages, arbitrary schema keys and credentials are never diagnostic payloads. Unexpected validation errors remain `UNKNOWN_REJECTION`. These labels improve diagnosis without changing acceptance predicates or proving the historical rejection is fixed.

Comparison deadline expiry records `TIMED_OUT` / `ComparisonDeadlineError` when terminal persistence is available. Preparation can expire before an AIRun exists; database outage, exhausted cleanup or process death can prevent terminal persistence. The amended total is cooperative and includes independent cleanup attempts and attempted response handoff, not guaranteed helper termination or response delivery. Safe fixed warnings report incomplete provider/session/engine cleanup, transaction recovery, terminal persistence or shutdown; they contain no exception text or model output. Unconfirmed release retains comparison admission capacity. A trace COMMITTED/COMPLETED state cannot certify browser receipt, and a remotely accepted trace commit can finish after local cancellation. External cancellation propagates and records FAILED / INTERRUPTED only when bookkeeping can complete. No detached analysis job or crash-recovery mechanism is introduced. Historical live baseline failures and pending human quality reviews remain unresolved; offline passing results are not live-quality approval.

SourcePilot owns its AI run records in PostgreSQL. Langfuse is an optional view of sanitized execution metadata; it neither owns workflow state nor decides whether an operation succeeds. No tracing service is needed for the five-stage workflow or normal tests.

## Local records

The six operations are `brief_interpreter`, `clarification_generator`, `quote_extractor`, `supplier_explanation`, `tradeoff_analysis` and `comparison_advice`. Each created `AIRun` records its identity, operation, configured model, prompt version, input hash, attempts, validation status, terminal outcome, timing and available usage. Analyst runs also retain model-turn and successful-tool-call counts.

Ordered steps use the existing `supplier_explanation_run_steps` table and its `(air_run_id, sequence)` primary key. Its historical name does not restrict it to supplier explanations. No new table or migration is required. Steps distinguish model outcomes, retries, validation, tools, scope changes, limits, usage availability and final run status. They do not store prompts, responses, tool arguments/results or per-step timings.

Example read-only inspection from a trusted developer database session (not a public API):

```sql
SELECT id, operation, model, prompt_version, status, attempts, validation_status,
       error_type, started_at, completed_at, latency_ms, input_tokens, output_tokens,
       estimated_cost, model_turn_count, tool_call_count
FROM ai_runs ORDER BY started_at DESC LIMIT 20;

SELECT sequence, kind, outcome, name
FROM supplier_explanation_run_steps
WHERE air_run_id = '<run UUID>' ORDER BY sequence;
```

Use the run ID returned by the operation or the local record to correlate observations. Session tokens are never tracing identifiers. Local database access remains an administrative capability; no trace-reading endpoint has been added.

Usage totals sum only reported values across model invocations. `NULL` means no usage was reported; zero means reported zero. Each token dimension has a terminal `usage` step: `COMPLETE` if all attempts reported that dimension, `PARTIAL` if some did, and `UNAVAILABLE` if none did. Provider failures with no usage make later totals partial. No missing usage or cost is invented. `estimated_cost` remains nullable; there is no pricing lookup or pricing table.

`latency_ms` measures elapsed runtime with a monotonic clock, including retries and local processing/recording up to finalization. It is not provider-only latency. Ordered local events have no individual timestamps; optional live model/tool observations measure their own execution intervals. The supplier snapshot fetched before AIRun creation is recorded as a completed event, without inventing its duration.

Successful and exceptional execution paths finalize created runs. A superseded PDF worker still cannot write draft values or alter the new attempt. After its rejected transaction rolls back, narrowly scoped cleanup may mark only its own existing AIRun failed and append terminal metadata. Parsing/configuration failures before run creation remain quote-processing failures without a fabricated AI run. Process termination or database unavailability can prevent finalization; this unit adds no durable queue or crash-recovery mechanism.

## Optional Langfuse

From `apps/api`, install the approved extra:

```powershell
uv sync --dev --extra observability --locked
```

The optional extra is bounded to `langfuse>=4.18,<5`; the lockfile resolves SDK 4.18.0 and its dependencies. Its OpenTelemetry dependencies are SDK implementation details, not an additional collector, service or application telemetry platform. Use a Langfuse destination compatible with this SDK; SourcePilot does not provision one.

Set server-side environment values using the existing environment-loading workflow:

```text
SOURCEPILOT_LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=<project public key>
LANGFUSE_SECRET_KEY=<project secret key>
LANGFUSE_BASE_URL=https://<configured Langfuse endpoint>
```

Keep credentials outside version control and the frontend. An HTTPS endpoint is required; URLs containing user information, query strings or fragments are rejected. The default enable flag is false. Disabled execution imports no optional SDK and opens no tracing connection. Base installation remains `uv sync --dev --locked`.

The SDK is initialized lazily once per process. Missing configuration/package or initialization failure falls back to local records; restart after correcting configuration. No authentication probe or synchronous remote lookup runs in a sourcing request. Delivery uses the SDK's background batching (32 observations, five-second interval, two-second transport timeout), without per-request flush or application export retries. API shutdown and short-lived process exit close the SDK and its isolated provider; the caller waits at most three seconds for cleanup on a daemon thread, outside request handling. Delivery is best effort: outages or process termination may lose external observations, while persisted application records remain authoritative.

Only manual root/model/tool observations and explicit metadata are exported. Allowed metadata includes run ID, operation, configured model/prompt version, status, validation, normalized failure category, sequence, attempts, timing, usage and Analyst counts/limits. Unknown model-provided tool names/error labels become `OTHER`. Model usage is attached to generation observations once; root totals are metadata, not a second billable usage entry. Missing cost stays absent from usage/cost attributes. Langfuse may display its own inferred costs; these are not authoritative application costs.

No automatic prompt/output instrumentation is enabled. No raw request, original brief, PDF text, model output, tool arguments/results, exception message, project/session identifier, cookie, credential or input hash is exported. An isolated SDK tracer provider and an explicit span filter exclude unrelated instrumentation. SDK/exporter diagnostic messages are replaced with fixed text so remote errors cannot echo sensitive content. A tracing failure never changes a domain result or grants access to any workflow action.

## Deterministic verification and demonstration

Use existing pytest fixtures; no model provider or hosted Langfuse is required:

```powershell
uv run --no-sync pytest tests/test_ai_tracing.py
uv run --no-sync pytest tests/test_ai_foundation.py tests/test_supplier_explanation.py tests/test_tradeoff_analysis.py tests/test_comparison_advice.py tests/test_pdf_quotes.py tests/test_quote_extractor.py
uv run --no-sync python -m sourcepilot.ai.eval_baseline --mode offline --output .eval-results/m6-u2-offline
```

Database tests require the existing isolated `TEST_DATABASE_URL` safeguards. They reset the test database, never the application/eval database. Adapter tests use the SDK's in-memory exporter and reject network calls. Existing deterministic successful-operation fixtures demonstrate Brief, Quote and Analyst observations and their correlation with local records. Base installation tests exercise disabled/missing SDK behavior; the real-SDK smoke is skipped only when the optional extra is absent. Existing CI runs the base suite first, then the optional adapter tests in the same job.

To inspect actual Langfuse UI traces, use an explicitly configured test destination and a permitted synthetic demo execution. Locate the run using its ID; inspect model/tool children and terminal validation/status metadata. An unconfigured destination is an evidence limitation, not a successful UI smoke. Do not run a live model baseline simply to validate telemetry.

## Historical latency and usage baseline

Source: the retained [M6-U1 full live report](../implementation/evidence/M6-U1/final-full-live-2026-11-03-01/baseline/results.json), started 2026-11-03 at 07:34:54 UTC. All listed model runs used `gpt-6-luna`. The table counts actual AIRuns, not every evaluation case; parser rejections and deterministic cases without runs are excluded. All runs below have reported latency/input/output values; cost is unavailable for every run. Medians include failures.

| Operation / prompt version | Runs | Terminal status | Median latency (ms) | Reported input tokens, total | Reported output tokens, total |
| --- | ---: | --- | ---: | ---: | ---: |
| Brief / brief-interpreter-v2 | 24 | 24 COMPLETED | 7,124 | 35,926 | 8,507 |
| Clarification / clarification-v1 | 9 | 9 COMPLETED | 2,077 | 2,514 | 612 |
| Supplier explanation / supplier-explanation-v2 | 6 | 6 COMPLETED | 7,695 | 21,298 | 2,033 |
| Quote / quote-extractor-v2 | 10 | 10 COMPLETED | 14,858 | 48,278 | 12,521 |
| Tradeoff / tradeoff-analysis-v2 | 9 | 9 VALIDATION_FAILED | 72,703 | 74,780 | 66,814 |
| Advice / comparison-advice-v2 | 11 | 11 VALIDATION_FAILED | 74,000 | 105,297 | 89,841 |

These are historical measurements, not a current-version performance or cost guarantee. Historical structured-run usage retained the last reported attempt, so its totals may undercount repaired/retried calls; M6-U2 does not rewrite those records. Analyst v2 measurements are not relabeled as v3. Deterministic tests have artificial token values and local timings and must not be mixed with this live baseline. The full report remains ERROR/exit 2, the separate v3 follow-up remains ERROR/exit 2 with ten runtime errors, and human quality reviews remain pending. See [M6-U1](../implementation/M6-U1.md) for the complete carry-forward risks.
