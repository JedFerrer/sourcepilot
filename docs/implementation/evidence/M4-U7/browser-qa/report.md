# M4-U7 defect follow-up: formal Browser QA

**PASS — ready for Done Check, not a Done Check or commit approval.** Completed November 5, 2026 (Asia/Manila). The final matrix passed **18/18**, with zero skipped, unexpected or flaky tests and no automatic test retries. A subsequent positive-suggestion fixture wording correction passed its focused **1/1** check. No application defect was confirmed, no application source was changed, no paid AI call ran, and no commit was made.

## Tested source and environment

- Base commit: `0851b3ee80b5fa45a3582c6dc6b4ebc388d17518`, plus the reviewed uncommitted implementation.
- All **246 source/configuration hashes** matched `linux-corrections/final-source-manifest.json` before testing and remained unchanged afterward. See [source identity](source-identity.json) and [after-run confirmation](source-after.json).
- Windows, installed Chrome **157.0.8103.38**, headed, Playwright **1.63.0**, existing production Next build, real Next proxy, real FastAPI application and guarded disposable `sourcepilot_e2e` PostgreSQL database. Existing E2E safety checks establish separation from application/test databases before resetting E2E fixtures. No dependency was installed.
- Final matrix: [full results](full-matrix-results.json), [scenario summary](full-matrix-summary.json), [request counts](full-matrix-request-counts.json). Duration: 412.559 seconds. Focused corrected suggestion: [results](results.json), [summary](result-summary.json).
- Commands from repository root: `node docs/implementation/evidence/M4-U7/browser-qa/run.mjs`; focused correction: same command with `--grep 'suggestion disclosures'`. The harness expects an existing production web build with the default 180-second public budget. This QA built that source before the matrix. Operational details are in [environment.json](environment.json); runnable controls are retained beside this report.

## Scenario results

POST totals below count browser-page analysis requests only, including explicit subsequent analyses/retries. They exclude setup operations and programmatic GET assertions. Per-scenario network files retain normalized paths and method sequences, without cookies, headers, credentials or bodies. Full comparison-GET counts include setup reads; they are not just recovery reads.

| Scenario | Result | Observed evidence | Analysis POSTs |
| --- | --- | --- | ---: |
| Actual focus away/back before success, repeated focus before/after completion | PASS | Four trusted blur/focus pairs; pending progress and settled result retained | 1 |
| Actual focus away/back before failure, repeated focus, keyboard retry | PASS | Four trusted pairs; terminal error retained; real Tab navigation reaches Retry analysis and Enter succeeds | 1 + 1 explicit retry |
| Failed freshness verification after settled success, recovery | PASS | Advice hidden; Retry comparison restores held result; zero POSTs during focus/recovery | 1 total |
| Success arrives during failed pending verification; repeated reads | PASS | Two real focus cycles while reads held; progress retained; result withheld until GET-only recovery | 1 |
| Failure arrives during failed pending verification; repeated reads | PASS | Error retained internally, restored after GET-only recovery; retry available | 1 |
| Competing old focus read and newer post-result stale read | PASS | Older current response cannot restore advice after newer stale evidence | 1 |
| Confirmed quote correction | PASS | Actual UI edit to USD 4.65 invalidates advice; regenerated snapshot and explicit analysis use replacement facts | 2 |
| Brief change | PASS | Actual destination edit invalidates advice; rediscovery/shortlist approval/regeneration replace snapshot | 2 |
| Shortlist change | PASS | Actual removal and approval invalidate advice; new snapshot replaces prior snapshot | 2 |
| Explicit regeneration after settled advice | PASS | Advice cleared; different snapshot ID; replacement analysis requires explicit action | 2 |
| Regeneration while analysis pending | PASS | Old delivery rejected; no resurrection on real focus return; explicit replacement succeeds | 2 |
| Project A to B to A using project links | PASS | No A advice shown in B or resurrected in A after old delivery; new action remains available | 1 |
| Injected backend-timeout envelope | PASS | Understandable timeout, enabled retry, no focus-triggered rerun; explicit retry succeeds | 1 + 1 explicit retry |
| Real backend deadline through production proxy | PASS | Sleeping local model boundary returns HTTP 504 `COMPARISON_ANALYSIS_TIMEOUT` in **175,072 ms**; retry succeeds; comparison and preference unchanged | 1 + 1 explicit retry |
| Real proxy upstream socket disconnect | PASS | Production proxy emits connection-loss envelope; UI says prior analysis may still be finishing; disabled cooldown, then enabled retry; no automatic browser POST | 1 + 1 explicit retry |
| Null-success outcome | PASS | Successful no-suggestion state, uncertainties, advisory disclosure, PDF sources and factual table remain; no automatic preference | 1 |
| Positive-suggestion rendering | PASS | Injected suggestion displays advisory heading, reasons, tradeoffs, uncertainty and source details; factual comparison/preference unchanged; corrected fixture screenshot verified | 1 |
| Existing human preference across success/failure | PASS | UI-selected Willow preference and decision notes remain identical after successful advice, real focus and a subsequent failed explicit analysis | 2 |

## Retained visual evidence

Every final-matrix scenario has sanitized network counts, trusted-focus observations, visible fixture text and screenshots in [full-matrix-artifacts](full-matrix-artifacts/). Viewport/analysis images are preferable to very tall full-page captures, which can have browser rendering artifacts.

- [Current factual table after GET-only recovery](full-matrix-artifacts/qa-held-success-survives-f-657a2-fication-and-repeated-reads/comparison-viewport.png)
- [Keyboard-retry scenario](full-matrix-artifacts/qa-native-focus-pending-fa-4816c-ed-focus-and-keyboard-retry/retry-error.png)
- [Disconnect cooldown](full-matrix-artifacts/qa-proxy-disconnect-envelope-cooldown-and-no-automatic-retry/disconnect-cooldown.png)
- [Actual deadline result](full-matrix-artifacts/qa-real-backend-deadline-t-78a38-proxy-and-explicit-recovery/deadline.json)
- [Corrected positive suggestion and source details](artifacts/qa-suggestion-disclosures-sources-facts-and-preference/analysis.png)
- [Null-success analysis](full-matrix-artifacts/qa-null-success-disclosures-sources-facts-and-preference/analysis.png)

## Mocked boundaries and unverified behavior

The existing deterministic E2E model boundary blocks both live OpenAI constructors with no provider fallback. Brief interpretation, clarification, PDF extraction and analysis use fixture outputs. Upload, parsing, persisted quotes, approvals, factual comparison, UI mutations, freshness logic, project navigation and preference persistence use the actual application/database.

Pending-result scenarios hold HTTP delivery of a completed deterministic response; they establish browser lifecycle behavior, not the duration of live computation. Validation-error responses, failed/stale freshness reads and their ordering are injected at the browser HTTP boundary. The null-success outcome traverses the actual backend validator. The positive suggestion modifies that response only for UI rendering: it **does not establish acceptance by the backend suggestion validator or model quality**. Its first version inherited a contradictory null-fixture sentence; the corrected fixture replaces that sentence and its focused pass/screenshot supersede the earlier positive screenshot.

The real deadline uses the normal **180-second** budget with its five-second cleanup reserve and a cancellable local sleep at the model boundary. It verifies the actual timeout response path and explicit browser recovery, not remote SDK/provider behavior or non-cooperative OS-helper termination. The loopback fault proxy closes a real upstream connection before forwarding the selected analysis to FastAPI; the production Next proxy handles the disconnect. Thus this is not proof of cancellation of an already-running backend/provider operation. The cooldown uses Playwright's clock acceleration after the real focus verification finishes, rather than waiting another three wall-clock minutes. Proxy/browser 190/195-second timeout expiry was not independently exhausted. Browser POSTs were counted; upstream internal transport attempts and remote billing were not measured by this QA.

Real focus is not synthesized: Playwright's default focus emulation is explicitly disabled through CDP, tabs are switched in headed Chrome, and each required switch asserts `document.hasFocus()` false/true plus trusted blur/focus events. No `dispatchEvent` fallback is used. Native Windows activation was also attempted during diagnosis but unavailable; it is not claimed as evidence. Other browsers, mobile layouts, screen-reader behavior, hosted deployment, multi-worker load, crash recovery, cross-tab deduplication and persisted advice after full reload are not certified here.

## Harness corrections and preserved intermediate results

Initial setup encountered a Windows command-path issue, restricted local-database access (resolved with approved local execution), a missing Playwright browser (used installed Chrome), and a fixture helper assuming its usual working directory. Initial checks also exposed default focus emulation, a reapproval helper assuming empty quote cards, an overly exact select label, and a source-text expectation mismatched to the actual UI. Transport controls were corrected to use the real aliased schema name and to finish freshness verification before clock acceleration. A focused test selector initially matched no tests and was corrected. These are harness/setup corrections, not application fixes or passing application-defect findings. Earlier reports and artifacts are retained separately as `setup-*`, `initial-*` and `intermediate-*`; they are not the final matrix verdict.

## Remaining gates

Formal Browser QA passes within the disclosed deterministic boundaries. **Stop here: ready for Done Check; Done Check has not been performed and no commit is authorized.** The unknown original validation rejection (`e790ea26-b0cb-4b93-9b9a-4c8d0a2de0d5`), historical live-quality findings, and pending human quality reviews remain explicitly **UNRESOLVED**. This QA neither reconstructs the missing rejected final nor establishes live-model groundedness, quality or release readiness. The approved cooperative deadline limitations remain unchanged.
