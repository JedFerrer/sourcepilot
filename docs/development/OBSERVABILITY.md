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

### Comparison provider diagnostics

Future comparison failures append three ordered steps after each existing model failure and before any retry: `provider_category`, `provider_status`, and `provider_code`, each with outcome `DIAGNOSTIC`. Their `name` is a finite allowlisted label. Both comparison advice and tradeoff analysis use these steps; other provider adapters default to unknown diagnostics. Local records and optional external observations use the same labels. The existing model/retry/terminal events remain authoritative for execution and eval classification.

The comparison transport captures these labels before normalizing the exception. Only installed-SDK `APIStatusError` instances establish HTTP rejection; validated integer statuses map as follows:

| Status / failure evidence | Category |
| --- | --- |
| 400, 422 | `INVALID_REQUEST` |
| 401 | `AUTHENTICATION` |
| 403 | `PERMISSION` |
| 404 | `NOT_FOUND` |
| 408 or SDK/Python timeout | `TIMEOUT` |
| 429 | `RATE_LIMIT` |
| 500–599 | `SERVER_ERROR` |
| SDK connection exception | `CONNECTION` |
| TypeError / ValueError at the comparison client boundary | `LOCAL_CLIENT_ERROR` |
| Other or insufficient evidence, including HTTP 409 | `UNKNOWN` |

Status labels are `400`, `401`, `403`, `404`, `408`, `409`, `422`, `429`, individual `500`–`599`, `OTHER_HTTP` for other valid HTTP integers (100–599), or `NO_HTTP_STATUS`. Booleans, strings, out-of-range integers and malformed values are not HTTP evidence. A non-SDK exception with a status-like attribute remains diagnostically unknown. Retryability continues to use the existing independent policy; diagnostics do not decide retries or change budgets, validation or browser behavior.

The SDK's already parsed code may be retained only as `invalid_api_key`, `permission_denied`, `model_not_found`, `invalid_json_schema`, `unsupported_parameter`, `invalid_value`, `missing_required_parameter`, `rate_limit_exceeded`, `insufficient_quota`, `server_error`, or `internal_server_error`; everything else is `UNKNOWN`. Codes do not override the broad category. No exception text, body, header, request, URL, credentials, quote content or arbitrary type/name is copied into these steps. Missing diagnostics from older callers use `UNKNOWN` / `NO_HTTP_STATUS` / `UNKNOWN`.

Use the existing read-only queries above and ordered sequence/run ID to inspect attempts. HTTP 404 does not prove a bad model; HTTP 429 does not prove quota exhaustion. `NO_HTTP_STATUS` is absence of safe status evidence, not proof that no remote work happened. These diagnostics cannot reconstruct historical causes. The original provider cause, v4 validation rejection and historical quality findings remain unresolved. No historical records are backfilled and no live analysis is required to verify this instrumentation.

### Timeout origin and last observed transport operation

Comparison failures additionally record `timeout_origin`, `transport_phase`, and `transport_phase_state` as `DIAGNOSTIC` steps. These join an existing trace commit; callbacks do no persistence, logging, network I/O or body reads. The record is the **last observed operation/state**, not a timing measurement, a complete transport history or root-cause proof.

- Timeout origins: `SDK_CONNECT`, `SDK_READ`, `SDK_WRITE`, `SDK_POOL`, `SDK_UNKNOWN`, `APP_ATTEMPT`, `APP_WORK_BUDGET`, `APP_TOTAL_BUDGET`, `APP_CLEANUP_BUDGET`, `UNKNOWN`, `NOT_APPLICABLE`.
- Transport operations: `CONNECT_TCP`, `START_TLS`, `SEND_REQUEST_HEADERS`, `SEND_REQUEST_BODY`, `RECEIVE_RESPONSE_HEADERS`, `RECEIVE_RESPONSE_BODY`, `UNKNOWN`.
- Operation states: `STARTED`, `COMPLETE`, `FAILED`, `UNKNOWN`. A failed operation can reflect cancellation; it does not establish a network fault.

SDK timeout origin uses only the direct HTTPX exception type beneath an actual SDK `APITimeoutError`; no recursive cause traversal or exception attributes/content are captured. `SDK_UNKNOWN` means an SDK timeout without a recognized direct timeout subtype. A generic Python timeout without an expired application-owned timeout context is `UNKNOWN`. HTTP 408 retains its existing status/category and does not imply a client-side timer expired.

The comparison-owned HTTPX client attaches the supported async request trace extension. Exact HTTPCore event names map to the finite operation/state labels. Callback information dictionaries, request/response content, headers, credentials, URLs (including query parameters), raw messages, arbitrary event names and network stream objects are never inspected or persisted by the observer. Response-close events do not overwrite the last I/O operation; unsupported events yield unknown. Each HTTP exchange resets the observation; each application attempt creates fresh state. Failure evidence is frozen before provider cleanup. Observation failures are isolated; external cancellation still propagates.

There is no separate DNS or pool-acquisition phase hook in the inspected transport. Connect can include resolution; pool origin may be known while phase remains unknown. Connection reuse can omit connect/TLS events. Response-header waiting is not model processing time, and absence of HTTP 401 is not authentication acceptance. No authentication-success claim is added.

Application origins distinguish the work cutoff (which reserves cleanup time), the original total budget, the existing cleanup contexts, and the individual attempt timer. Cleanup failure alone is not cleanup-budget expiry. Expiry outside an active provider invocation uses unknown transport fields. If a frozen provider failure is followed by an independently observed application-budget expiry, the trace retains its first three-field snapshot and adds a second origin snapshot with unknown transport fields before the unchanged terminal outcome. This does not manufacture a second model attempt.

The approved deadline remains **cooperative**. No new timeout, rescheduling, retry, helper termination guarantee or remote-cancellation guarantee is introduced. Observation adds no dedicated database round trip or cleanup reserve. Exhausted budgets, database failure, process termination or interrupted finalization can still prevent persistence. Existing public error contracts, SDK retries zero, application retry/backoff, repair rules and configured budgets remain unchanged. Historical causes and validation/quality findings are unresolved; a live verification requires separate authorization.

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

## Quality and measurement limitations

The historical full 90-case baseline remains **ERROR / exit 2, 20 runtime
errors**. The separate 31-case follow-up remains **ERROR / exit 2, ten runtime
errors**. Human quality reviews remain pending; no successful complete
current-version live baseline or live-quality approval is established.

Historical structured-run usage retained the last reported attempt and can
undercount repaired/retried calls. Historical measurements are not current-version
performance or cost guarantees. Deterministic tests use artificial usage and local
timings; do not mix them with live measurements. Hosted tracing visibility remains
unverified. Reproduce deterministic checks above without invoking a live provider.
