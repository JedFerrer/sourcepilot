# UX-U1 — SourcePilot workflow usability design

## Status and bounded authorization

**READY_TO_COMMIT — Done Check PASS under the explicit 11 November 2026 acceptance amendment below, for the exact 67-path proposed inventory. Browser QA passes only the amended unit scope. Remaining actual 400% zoom, actual screen-reader interoperability and five-participant usability acceptance are DEFERRED AND UNVERIFIED, not passed. Historical FAIL/INCOMPLETE results are preserved. Unit completion does not establish accessibility conformance, validated usability or release readiness. No staging, commit, deployment or next unit is authorized.**

### Implementation authorization — 9 November 2026

The human explicitly approved the current blue/charcoal/light design and consolidated UX-U1 plan with its amendments, authorizing checkpoints 2–3 in the real application. Record transition: PLANNING → PLAN_APPROVED (human approval) → IMPLEMENTING. Stop after implementation verification and handoff; independent Review, Browser QA, participant acceptance and Done Check remain separate. No backend or protected-specification changes, deployment, staging, commit or next unit are authorized. Earlier bounded-authorization statements below describe the design preparation checkpoint and are retained as history.

Repository baseline rechecked at `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`. Pre-existing changes: M4-U7 retention/final-check addenda, implementation index, untracked UX-U1 record/design package and `.agents/` skill. Preserve all unrelated work and historical verification limitations.

Stable approved visual reference: the 7 November blue/charcoal/light prototype, including independent-review corrections, pinned by SHA-256 (files remain unchanged during implementation):

| File in `docs/design/UX-U1/` | SHA-256 |
| --- | --- |
| index.html | `EB01FF2F394BDE3D2FBCF9653AC6C54C092BA0DFE18107473E219BF4143846AE` |
| prototype.css | `8F4E2007D4514B15A255BAA2F83A00D622DF579A6CF0259E51D27808DBE5ABC6` |
| prototype.js | `1E135FBDD6FAAC465F32BC6DE05D72A4A258C2AA4EBE330F173B0719D4BADA42` |
| layouts.html | `64B119995A87A98B4D547FE090841BA4323D6F12E5E177E2F27D4EB680BF19D3` |

Impeccable 4.8.0 instructions and approved DESIGN.md read directly: the context launcher could not create its external engine cache. Engine/detector unavailable, not a clean scan. No design reopening or engine installation is required for this implementation.

On 7 November 2026 the human authorized baseline/lifecycle reconciliation and the UX-U1 design package only, using the revised proposal and latest five amendments. This authorizes a separate synthetic interactive prototype, annotated layouts, design requirements, participant materials and a self-critique with corrections. It does not approve the production plan or final design, install dependencies/skills, recruit participants, alter protected specifications or backend behavior, stage files or commit. Stop for human design review after delivering this package.

This is one proposed improvement unit linked to M5-U2's workflow-integration responsibilities, with internal checkpoints. It is not a deployment or release unit. This record consolidates and supersedes the earlier conversational proposals, incorporating both review rounds; its implementation provisions remain proposals.

## Baseline and authority

Baseline verified: clean worktree at `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`, `fix(comparison): ground analysis in deterministic facts and bounded selections`. Git records 377 deletions, 26 modifications and 39 additions: the previously recorded 442-path combined corrective/retention scope. Current lifecycle addenda reconcile that completed commit; historical paused/staged descriptions and evidence remain unchanged.

Carry forward: original six-submission batch FAIL (6/6 submissions, 8/24 provider invocations); separate supplemental PDF PASS (1/1, 1/4) closes only the corrected-amount defect; 15 human reviews pending; provider/authentication/timeout causes and broad disconnect trigger unproven; no full final-source database-suite or general reliability/release claim. M6 deployment/release work is not begun by UX-U1.

Authority, in order:

1. Product Specification v0.2, §§9–14, 21–40, 43–46, 48–54: five stages, human approvals, manual/PDF entry, evidence, unknown/conflict, minimal dashboard, freely changeable preference.
2. Technical Architecture v0.2, §§5.1, 11.4, 19.4–19.10, 20, 22: frontend presentation, original versus corrected values, concurrency/retry/staleness and existing API boundaries.
3. Implementation Plan v0.2, M5-U2 and M6-U4: coherent workflow, authoritative guidance and recoverable states.
4. M1-U5/U6, M2-U7, M5-U1/U2 and current M4-U7 corrective/retention records.
5. Existing frontend components/tests and supplier/quote/Brief contracts inspected during planning.

Follow AGENTS.md, CODING_STANDARDS.md and Full Flow. No higher-authority conflict is required by this design. The all-visible presentation of M5-U2 is deliberately superseded by this proposed follow-up, not its business rules.

## Objective and non-negotiable boundaries

Retain Brief → Suppliers → Quotes → Comparison → Decision, one visible stage, clearer hierarchy, wider layouts, progressive disclosure, evidence preservation and explicit human control. Retain the chosen calm professional direction and proposed shadcn/ui foundation.

Preserve Next.js/React/TypeScript and FastAPI/PostgreSQL modular monolith; application-owned workflow; bounded structured LLM calls and one read-only Analyst; deterministic rules, tracing and evals. No LangGraph, CrewAI, LangChain, LiteLLM, orchestration, Redis/Celery, vector/RAG, OCR, live supplier research, microservices or speculative infrastructure. No backend endpoint/schema/migration changes, framework upgrade, global store, form framework or query library.

No universal supplier score, currency conversion, automatic approval, automatic preference, external procurement action or added preference gate. Original evidence never becomes evidence for a corrected value.

## Delivery checkpoints

| Checkpoint | Deliverable | Exit condition |
| --- | --- | --- |
| 0 Baseline | Verified Git identity, current lifecycle addenda, proposed unit record | Factual reconciliation under bounded authorization; preserve historical limitations |
| 1 Design | Dashboard plus five-stage layouts at 1440/390, adaptations at 320/768, interactive prototype, tokens/copy, state inventory, requirement mapping, critique, participant task pack | Explicit human design-package approval; participant completion is recorded separately |
| 2 Interaction foundation | Future production primitives, navigation and local draft handling, focused regressions | Separately authorized implementation; preservation/history checks pass before broad migration |
| 3 Stage migration | Future dashboard and five-stage production UI | Implementation checks pass; stop before separately requested Review |
| 4 Full Flow | Independent Review, real-stack Browser QA, unfamiliar-user acceptance, Done Check | Each gate passes separately; only an explicitly authorized later commit |

Only checkpoints 0–1 preparation are authorized now. Design approval does not itself authorize production migration. Prototype verification is not application Browser QA. Final design and production plan must not be marked approved by the worker.

## Navigation and workflow presentation

- Keep editors mounted/project-scoped in future production; only one stage is visible/accessibly exposed. Switching stages or quote suppliers preserves drafts, record errors, disclosures and pending state. Visibility and workflow eligibility are separate inputs.
- Show viewed stage separately from backend current-stage/needs-attention guidance. Use selection styling and `aria-current="page"` for the viewed stage, not workflow progress. No ordinal completion inference or percentage progress.
- Keep saved preference separate from upstream needs-attention. Use one persistent next-action area from backend action/reason. Following it only navigates/focuses; it never mutates. No automatic stage jump after saves or refreshes.
- Let unavailable stages explain their prerequisite and recovery action. Decision remains accessible under M5-U1: any shortlisted supplier, before comparison, regardless of AI suggestion, quote availability or requirement findings. Retained choices allow notes/clear even with an empty shortlist.
- Future application URL: `/projects/{id}?stage=brief|suppliers|quotes|comparison|decision`. A single valid query wins. Otherwise recognized legacy stage/action fragments select their mapped stage; otherwise backend current stage, falling back to Brief with guidance unavailable. Invalid/duplicate parameters are replaced canonically, preserving unrelated parameters. Fragments focus only within the resolved stage; ignore incompatible/unknown fragments.
- Explicit navigation pushes history, focuses stage heading and starts at stage content. Next action focuses its control/group. Back/Forward restores viewed stage and recorded focus/scroll where available; missing targets fall back to heading. Background updates never steal focus/scroll.
- Refresh failures keep last-known guidance marked potentially outdated, with Retry. Hidden-stage failures surface a concise status/link without forcing navigation. Preserve request-sequence, obsolete-project and decision-response reconciliation protections.

## Information architecture and visual system

Full proposed tokens, annotated layout decisions and breakpoint matrix: [Design specification](../design/UX-U1/DESIGN.md). Reviewable screens: [layout atlas](../design/UX-U1/layouts.html). Interactive source: [prototype](../design/UX-U1/index.html).

One dominant action per task context; secondary and destructive actions visually differentiated. Navigation and AI advice must not compete with human approval. Semantic statuses use words plus color. A compact synthetic-data notice appears on dashboard and supplier-source context; it does not classify user uploads as synthetic. Session failures remain independently visible.

Dashboard prioritizes existing projects and New project. An empty state explains the first step and links to the existing name/request form. Loading or failed reads never masquerade as zero projects. Show factual progress/counts, saved preference and update time; no analytics or new modules.

Brief groups existing fields into Product; Commercial/delivery; Requirements with importance; Additional context. Required missing information and uncertainties remain exposed. Original request and clarification help remain accessible. Optional target price does not become mandatory. No irrelevant/new fields or frontend requiredness policy.

Quotes begin with Upload PDF or Enter manually, one chosen form. Switching choice preserves drafts; actual destructive replacement requires warning. Commercial and Timeline start expanded. Terms, Compliance and Other may collapse, but material issues must remain visible. All existing normalized fields and separate quote notes remain available. Failed PDF processing retains original evidence and manual fallback.

| Stage | Outside disclosures | Disclosures may contain |
| --- | --- | --- |
| Brief | Saved/draft/approval states, required missing fields, importance, uncertainty | Original request, help, optional context; original request available during review |
| Suppliers | Identity/location, MOQ, lead time, indicative price, selection/freshness, required/preferred findings, material unknown/conflict/failure | Full excerpts, optional explanation, secondary capabilities, private-note editor |
| Quotes | Supplier status/unsaved indicators, processing/failure, commercial summary, current provenance, save/review/confirmation state, material gaps | Secondary groups and lengthy evidence; group summaries name material issues |
| Comparison | Freshness, included suppliers, core commercial facts and requirement findings, quantity/currency warnings, important unknown/conflict, analysis state | Full source excerpts and optional supporting detail |
| Decision | Saved preference, explicitly unsaved replacement, notes/actions, retained-choice warning, relevant stale guidance | Supporting comparison detail through a link |

Unknown means insufficient reliable information; Conflict means evidence disagrees; Does not meet is a known failure; Optional—not provided is not a blocker; Blocked means an existing backend prerequisite. Deduplicate issue summaries by issue/supplier/field, with links and concise local markers. Do not collapse distinct concerns or hide mandatory M4-U7 disclosures behind AI-selected highlights.

## Editing and saved-value approval

Records use Saved, Unsaved changes, Saving, Save failed and Saved elsewhere—review changes. No project-wide save and no multi-record save. Each separate write reports its own outcome; never aggregate partial success into overall success.

| Record | Contract |
| --- | --- |
| Creation/name | Existing create request saves name/request. Rename explicitly saves name; dirty editor close warns. No approval |
| Brief | Existing full-snapshot PATCH with expected revision. Review saved values; dirty answers/edits, pending write or conflict prevent approval. Preserve backend ready post-approval edit retention and incomplete-edit revocation |
| Clarification answers | One revision-checked Brief PATCH; other edits saved/discarded first. Preserve answers on error. Externally resolved questions leave the active set, but retain prior answers separately for copying/deliberate editing of the latest Brief. Never replay them automatically |
| Membership | Explicit add/remove/dismiss/restore persists through existing mutation. Pending changes must settle and membership refresh before shortlist approval |
| Private notes | Per-supplier explicit save. Dirty or pending notes do not block approval or require exclusion. Quiet Notes not saved indicator. Approval submits no note drafts and preserves them |
| Quote | Upload/manual → processing or saved draft → saved-value review → explicit confirmation. Corrections save one quote. Confirmed edits preserve backend confirmation/revision behavior and disclose comparison invalidation |
| Decision | Mark/change preference saves selected supplier and submitted notes atomically. Notes-only save retains saved preference, never commits a draft replacement. Clear preserves saved notes and leaves unsaved notes/replacement drafts untouched. No extra approval state |

Before Brief/shortlist/quote approval, recheck the saved record used for review. Changed data refreshes review and requires renewed deliberate action. Brief has expected-revision protection; quote confirmation and shortlist approval have no reviewed-version token. Frontend rechecking cannot eliminate the cross-tab race between check and submission. Stronger atomic guarantees require a separately approved backend change and are not promised here.

## Draft preservation and safe reconciliation

Use a small editor-local helper with saved baseline, complete local draft, submitted snapshot, edit generation and latest remote value. Register dirty/pending metadata with the workspace only; no global business-state store or request orchestrator.

- Unchanged reads do not reset editors. Clean records may adopt latest editable content. Read-only workflow/processing/freshness updates separately.
- For a dirty Brief or quote, any changed saved editable content triggers record-level review, even for different fields. Keep complete draft and latest saved record separate; no automatic field merging.
- Atomic related units: amount/currency; quote currency and dependent monetary fields with quantity context; requirement kind/importance/expected value/notes; delivery type plus date/period; whole requirement collection when membership/identity changes.
- Match requirements by stable server ID; unsaved additions have local IDs, never array-index identity. Do not silently resurrect deleted requirements, discard external additions or equate ambiguous new items. Re-creation uses a deliberate normal Add action against the latest record.
- Conflict choices: Use saved record, or Review my edits against saved values. Explicitly reconcile complete related groups and review the resulting record before saving. Ambiguous structural changes remain in review, not a guessed merge. Further remote changes reopen review.
- Own save responses acknowledge the submitted snapshot only. Preserve later edits as complete related groups; ambiguous normalization/assigned IDs require review. Prevent overlapping writes to the same record.
- Stage/supplier/evidence interactions retain drafts and edit context. Another record's save never resets them. Failed saves preserve all values and field errors.
- Successful write plus failed refresh means Saved; guidance could not refresh. Retry the read. An uncertain write keeps drafts and requires read/recovery, not automatic write replay or duplicate create/upload.
- Local removal with dirty quote/notes offers Cancel removal or Discard edits and remove. Discard only after success; failure retains drafts. Pending writes prevent racing removal, but allow cancellation/departure.
- External removal retains a copyable/discardable, unavailable draft; no saving against ineligible supplier. Reconcile if restored.
- Draft persistence is current-visit memory only. No silent local storage or recovery promise after departure.

### Leaving with pending or uncertain changes

Unsaved-only exit: Stay (default) / Discard unsaved changes and leave, listing affected records. No Stay and save operation. Save records separately after staying.

Pending/uncertain exit: Stay / Leave anyway immediately. Explain that departure does not cancel an already submitted request and unsaved drafts may be lost. Observe the current request for up to 10 seconds after opening the warning, then show Save outcome not yet confirmed and Check saved state. Each check is a bounded read (10 seconds); leave remains available. These are UI thresholds, not new write, provider or processing deadlines. Do not automatically navigate on completion.

On return load current server records. Never replay departed drafts; old values do not prove a pending write failed. Show existing processing/retry states and allow refresh. Native reload/tab close uses the browser warning. Preserve duplicate-upload handling, idempotency, stale processing and Analyst/browser deadlines. No backend cancellation claim.

## Responsive accessibility

- Desktop ≥1024px: max 1440px workspace, roughly 224px rail, flexible wide working area; readable prose width separate from tables.
- 768–1023px: wrapping five-stage navigation, no rail, one content area. Tables scroll inside their region only.
- 320–767px: two-column full-label stage navigation, ≥44px action targets, stacked forms and wrapping labels. No clipped five-step strip.
- Evidence pane ≥1280px; below that a modal sheet; below 768px fills usable viewport. Field/source/AI extraction/saved correction/draft remain distinct; close returns to related control without saving.
- Comparison semantic table ≥768px, equivalent stacked field comparisons below. Sticky label ≤30% table region with matching scroll padding; never obscure focused content. Disable sticky layers on short viewports. Persistent next action means present across stages; sticky only where sufficient space exists, in normal flow when narrow/short.
- WCAG 2.2 AA target: visible focus, semantic headings/tables, labels/error links, keyboard disclosures/dialogs, focus trapping/return, reduced motion and non-color status. Polite meaningful status announcements, not polling chatter. Focus validation summary after explicit failed submit.
- Verify 320 CSS-pixel reflow and actual desktop browser 400% zoom separately. Automated checks alone do not establish conformance or usability.

## Future production inventory and verification

Affected existing production files when separately authorized: `project-workspace.tsx`, `workflow.ts`, dashboard/session components, `brief-editor.tsx`, `supplier-review.tsx`, `quote-review.tsx`, `comparison-review.tsx`, `decision-review.tsx`, globals/layout, approved component setup and matching tests/configuration. Proposed local helpers: WorkspaceShell, StageNavigation, NextAction, use-record-draft, record-save-status, draft-conflict, unsaved-changes-dialog, use-workspace-navigation, evidence-viewer. New types are frontend-only draft/navigation/display types. No public contracts change.

Foundation later: shadcn/ui primitives, semantic tokens, Tailwind and Lucide only as justified by this design, retaining current Next/React versions. No dependencies or installed skills change in the design package. Official shadcn skill and Vercel web-design-guidelines are individually justified optional aids, never acceptance gates. No broad skill bundle.

Replace quote-review.test.tsx's `reconciles changed server quotes, explicit cancellation, and successful saves` expectation of automatic unsaved-note overwrite with clean refresh, dirty conflict, explicit discard and save-normalization cases. Brief tests `drops an answer for a field resolved by another edit...` and `removes the retry...` keep no-stale-replay assertions and add recovery-copy assertions. Preserve existing late-response, failed-save, prerequisite, provenance and Decision freedom regressions.

| Verification family | Required scenarios |
| --- | --- |
| Reconciliation | Amount versus currency; external currency affecting all monetary fields; requirement kind/value/importance changes; add/add, edit/delete, delete/edit, reorder, assigned IDs; local Brief edit plus external requirement addition; typing during save; clean/unchanged reads; unrelated record save |
| Departure | Immediate leave; 10-second transition; failed check; delayed success/failure; completion after departure; reload saved state; no duplicate writes or promised draft restoration |
| Membership/notes | Unsaved notes approval without note write; note-save failure/pending independent; pending/uncertain membership blocks approval; removal failure keeps drafts |
| Navigation | Query/fragment precedence, invalid/duplicate values, Back/Forward, stage-specific focus/scroll, project exit guard, refresh without jumps |
| Approval | Saved-value summaries, dirty/pending/conflict gates, changed review reapproval, unchanged backend freedom |
| Evidence/AI | Original 4.22 versus corrected 4.50, unresolved USD/EUR, unequal quantity, required failures, unknown/conflict, null suggestion, stale/failed advice, decision-only advice preservation |
| Recovery | Failed processing/status reads, stale upstream inputs, guidance read failure, uncertain saves, expired session; empty not confused with failure |
| Accessibility | 320/390/768/1024/1440, desktop 400% zoom, keyboard and screen reader, focus/announcements/dialogs, automated accessibility scan plus manual coverage |
| App regression | Real frontend/FastAPI/isolated PostgreSQL golden path and targeted E2E, existing comparison QA; label deterministic AI fixtures honestly |
| Quality | Frontend tests/lint/types/build/diff and relevant existing backend contract/workflow tests when implementing; no live-provider calls required by UI work |

## Usability logistics and gates

The human owner recruits and schedules five people unfamiliar with implementation, preferably sourcing users; include desktop and phone sessions. The worker prepares scripts, synthetic fixtures, resets, observation sheets and findings, and analyzes authorized evidence. No recruitment/contact is authorized. [Participant pack](../design/UX-U1/PARTICIPANTS.md) is prepared; recruitment, sessions and results remain pending.

Tasks: find next action within 30 seconds; explain unknown versus conflict; correct a quote from evidence and explain source/current difference; recover stale results without draft loss; distinguish AI suggestion from saved preference and deliberately change/clear it. At least 4/5 complete each task without procedural assistance; zero unnoticed data-loss, accidental-approval or provenance-misinterpretation incidents. These are local acceptance thresholds, not statistical claims.

Design-package approval is separate from participant completion. Prototype testing informs revisions when available; final implemented-workflow testing remains required, preferably with fresh participants. If unavailable, report Human usability acceptance incomplete. Technical Browser QA may have its own result, but checkpoint 4 overall acceptance and Done Check remain incomplete. Never silently waive testing.

## Current package and limitations

See [requirement coverage](../design/UX-U1/REQUIREMENTS.md) and [self-critique and verification](../design/UX-U1/CRITIQUE.md). Authored source stays in `docs/design/UX-U1/`; generated captures/results go to unique directories under ignored `.local-investigation-artifacts/UX-U1/`. No historical archive is rewritten. The prototype uses in-memory synthetic records and simulated request outcomes; it is not app functionality, persistence, provider validation, production QA or human usability evidence.

Await human design review. No production migration, implementation approval, final design approval, participant completion, release approval or commit is inferred from this package.

### Bounded delivery record

The authorized baseline reconciliation and authored design package are prepared. Final prototype-only verification passed 18 check groups, including 42 screen/state/width layouts, six actual Chrome 400% zoom reflow checks, keyboard modal focus, record conflicts and pending departure. Fifty generated PNGs and the report are local-only under the ignored root. [Self-critique](../design/UX-U1/CRITIQUE.md) records corrections and limitations; [participant materials](../design/UX-U1/PARTICIPANTS.md) contain no invented results. This does not advance the unit beyond PLANNING or pass production Review/QA/Done Check. Stop for the human's design review.


## Production implementation record — 9 November 2026

Status remains **IMPLEMENTING**. This is implementation work and self-verification, not independent Review or Browser QA. The approved design source hashes above were rechecked unchanged. No protected specification or backend source was changed. Nothing was staged, committed or deployed; no other unit was started.

### Checkpoint 2 — component, navigation and draft foundation

Implemented approved light tokens, Tailwind/PostCSS, locally composed shadcn-style Button/Dialog primitives backed by Radix, and Lucide navigation/actions. Next.js 15.5.3 and React 19.1.1 are retained. Runtime additions are limited to Radix dialog/slot, the shadcn class utilities and Lucide. Tailwind/PostCSS are build dependencies; axe-core is a test-only accessibility dependency. No provider, orchestration, backend, schema or infrastructure dependency was introduced.

The workspace keeps five stage panels mounted and displays one. URL query/known legacy fragment precedence is canonicalized; navigation pushes browser history without workflow mutations. The selected view and backend next action remain distinct. Back/Forward restores recorded stage focus/scroll; background refreshes do not select a different stage. Last-known failed-refresh guidance is retained and marked outdated. Hidden-stage errors link back to the affected stage.

Whole-record draft reconciliation stores baseline, submitted snapshot, edit generation and latest saved values. Dirty concurrent records require explicit review; related amounts/currencies and requirement collections are not automatically merged. Ambiguous requirement identity changes expose both records for copying and deliberate re-entry. Save acknowledgement preserves later typing. Pending/uncertain writes do not replay automatically. Departure lists affected records, defaults to Stay, allows immediate deliberate departure, and offers a bounded saved-state check after ten seconds. Native reload/tab-close protection supplements application navigation guards.

### Checkpoint 3 — application stage migration

- Dashboard: real project summaries, explicit New project dialog, distinct loading/failure/empty states, retained creation drafts and uncertain-creation guidance.
- Brief: grouped editing, approved saved summary, saved-value approval review, stable local identities for new requirements, retained clarification recovery text, revision preflight and existing revision-conflict protection.
- Suppliers: responsive candidate cards, evidence/fit/uncertainty, separate private-note drafts and saves, shortlist approval review, deliberate removal with draft protection and independent membership state.
- Quotes: one selected supplier, explicit PDF/manual entry choice, persistent per-supplier drafts, grouped fields, saved-versus-unsaved distinction, source inspector beside the editor on wide screens and modal sheet on narrower screens, PDF/manual recovery, confirmation preflight, unavailable-supplier write guards and explicit replacement confirmation.
- Comparison: existing deterministic facts and optional bounded advice preserved; phone presentation repeats supplier names beside each value while retaining source, assumptions, unknown/conflict, required failures and stale-result warnings.
- Decision: saved preference stays separate from an unsaved replacement. Note-only save does not commit a draft replacement; clearing preference does not silently save unrelated note edits. Existing freedom to choose any shortlisted supplier remains.

The application uses existing API responses and business rules. No simulated prototype state machine or data was copied into production. Real data can yield different content length, next action and findings from the approved synthetic reference.

### Verification and interpretation

Frontend tests include record reconciliation, requirement collection conflicts, query/fragment precedence, draft departure and existing stale-response/provenance/Decision regressions. Existing tests were adapted to explicit stage/supplier selection and whole-record review instead of silent draft overwrite. A stale comparison fixture path was corrected to the existing API fixture. The browser advice expectation was corrected to the existing deterministic renderer's null-suggestion wording; backend behavior was not changed.

Selected API contract/workflow tests: **190 passed**, one existing Starlette/AnyIO deprecation warning. Command covered project workflow, Brief, supplier review, manual/PDF quotes, preference and projects. Initial duplicate local runners caused database interference; those task-owned runners were stopped and the successful run used one runner. This is not the full backend database suite and does not erase historical verification limits.

Local-only implementation evidence is under `.local-investigation-artifacts/UX-U1/`; it is ignored and is not release evidence. Browser tests use the real Next/FastAPI/PostgreSQL application with the existing deterministic test-only model boundary. They do not validate live-provider reliability. The first browser attempt required installation of the matching Playwright Chromium; later iterations found and corrected API serialization false conflicts, explicit-stage test selectors and a sticky-sidebar overlap. Earlier failed/intermediate logs are retained separately from final results.

### Independent Review handoff and remaining gates

Review the actual frontend diff, new shared draft/navigation primitives, dependencies/lockfile, modified tests and this unit record against the pinned prototype and the authoritative specifications. Pay particular attention to in-flight responses, dirty-versus-saved approval summaries, whole-record reconciliation, native history interception, supplier removal, and immutable PDF provenance. Reproduce the checks from the current source rather than treating this implementation record as independent Review.

After Review, perform the separately authorized Browser QA phase. Include manual keyboard and screen-reader coverage, focus/announcements, populated comparison at narrow widths and zoom, concurrent-tab changes, failure/uncertain-write recovery and expired sessions. Automated accessibility checks are supporting evidence, not WCAG certification or a substitute for assistive-technology testing.

Human usability acceptance is **incomplete**: the five participant sessions and the 4/5 task thresholds remain required; no participants were recruited or results invented. Screen-reader acceptance, independent Review, Browser QA and Done Check are not passed by this implementation. Historical provider batch failures, 15 pending human reviews, and bounded supplemental-PDF evidence remain unchanged. Frontend saved-state preflights do not add server-side optimistic concurrency to contracts that do not already provide it; a concurrent write after a read remains subject to those existing contracts. Drafts are in-memory and explicit departure can lose unsaved edits; submitted requests may complete after departure.

Run the actual application using [local development instructions](../local-development.md): start PostgreSQL; apply existing migrations and supplier seed; start the documented FastAPI command in one terminal and `pnpm --filter @sourcepilot/web dev` in another; open localhost:3000. Existing server-side model configuration is needed for live AI actions. The prototype remains a separate visual reference.

### Final implementation check ledger

| Check | Result / evidence |
| --- | --- |
| Frontend regression suite | 238 passed, 0 failed; `implementation-tests-final-04.json` |
| Selected backend contracts/workflows | 190 passed; `backend-regressions.txt` (one existing deprecation warning) |
| ESLint | Passed on final source |
| TypeScript | Passed on final source |
| Production build | Passed; run by the final browser configuration on the current source, Next 15.5.3 / React 19.1.1 retained |
| Browser implementation checks | **16/16 passed** on final application source; `browser-implementation-05.log` and `browser-results-final/` |
| Scope / whitespace | `git diff --check` passed; backend/protected-specification diff and staged diff empty |
| Approved visual source | All four pinned SHA-256 values unchanged |

The final code also retains private-note drafts for candidates removed by a later read, with copying available and saving disabled while unavailable. Rename initializes its baseline before exposing the editor. An uncertain creation keeps its request text when checking saved projects. Explicit quote discard is named as such and cannot clear an uncertain write without recovery. These cases have corresponding regression coverage or are exercised by the shared record/departure checks.

### Visual and interaction evidence

The final browser suite exercised all five stages with real application records (including two confirmed quotes and a populated comparison) at **320, 390, 768, 1024 and 1440 CSS pixels**, asserting one visible stage and no page overflow. Ten axe-core scans (five stages at 320/1440, WCAG A/AA tags) reported zero violations. These scans do not cover every state or establish accessibility acceptance. Actual Chrome default page zoom was set to **400%** at a 1280px outer window; dashboard and all five stages passed measured reflow checks (device pixel ratio at least 3.9, CSS viewport at most 330px, no horizontal page overflow). The zoom screenshot helper's clipped full-page captures were replaced with direct browser viewport captures; the layout assertions were unchanged. The affected UX test was rerun successfully (1/1) with a fresh production build; `browser-zoom-captures-final.log` and `browser-zoom-results-final/` retain the corrected evidence.

Thirty-three screenshots cover the five-width stages, dashboard, wide evidence inspector and six zoom screens. Visual inspection against the pinned approved package checked light canvas/surfaces, blue actions/selection, charcoal type, rail/phone navigation, grouped quote form and evidence placement. The implementation retains real source excerpts and actual values rather than fabricating the prototype's document facsimile. Desktop sidebar overlap and source-action spacing were corrected during this inspection. The unusually long automated-test project title deliberately exercises wrapping; content/state differences are not prototype pixel equality.

Browser interaction checks cover preserved quote and Decision drafts across stages/history, explicit Stay/discard departure, the mobile evidence dialog's Escape close, and the native beforeunload warning on cross-document Back. Earlier failure logs distinguish test adaptation/setup errors from application corrections; the successful final results above supersede them only for this implementation scope. Manual screen-reader evaluation, broader keyboard/state coverage and participant testing remain open for the later acceptance phases.

**Implementation handoff:** authorized implementation and implementation verification are complete. Remain at IMPLEMENTING until an independent Review is explicitly begun. No Review, Browser QA, Done Check, release or commit approval is inferred.


## Prototype fidelity correction — 9 November 2026

The human reported the crowded saved-Brief approval summary and explicitly requested a cross-screen prototype comparison, gap record and implementation corrections. Continue UX-U1 in IMPLEMENTING; this is a corrective implementation pass, not independent Review. Earlier verification remains historical and did not establish complete prototype fidelity. Existing uncommitted work, M4-U7 records and prototype sources remain preserved.

| Gap found against pinned prototype | Authorized correction |
| --- | --- |
| Brief approval summary permanently inserted above editing; raw object keys, duplicate status paragraphs and excessive whitespace | Explicit Review saved Brief dialog, readable label/value rows, compact status line, uncertainty visible outside and inside review, original request in disclosure |
| Brief form has one undifferentiated surface and expanded informational fields | Product, commercial/delivery, requirements and optional additional-context groups; approved summary with explicit Edit |
| Shortlist approval inserted into page above candidates | Focused saved-shortlist dialog with current findings, notes independence and existing recheck |
| Quote confirmation inline and saved field summary excessively verbose | Focused saved-value confirmation dialog, compact grouped saved fields, deliberate editing and immutable evidence retained |
| Supplier supporting capabilities compete with findings | Secondary supporting details progressively disclosed; required/preferred findings and material gaps remain visible |
| Dashboard rows and Decision lack prototype's hierarchy; Decision omits the proposed-choice review dialog; Comparison advice lacks a distinct surface | Structured project rows, saved-preference surface, review selected supplier and submitted notes before the existing atomic save, differentiated decision actions and factual/advisory surfaces |
| Tests only proved happy-path flow and overflow; missed saved/review visual states | Add explicit dialog/presentation regressions and desktop/mobile saved/review screenshots; compare to pinned captures |

No simulated prototype workflow, supplier claims or fabricated PDF content will be copied. Differences required by actual API fields, existing action names and richer evidence remain explicit rather than hidden. No backend/specification/dependency change, commit or deployment is included.


### Correction results and independent-review handoff

The gaps above are implemented. Brief, shortlist and quote approvals now open focused dialogs. Brief summaries show readable dates, values, requirement names and importance rather than serialized API objects. Saved and editable Brief states are separated; product, commercial/delivery, requirements and optional context have distinct groups. Original requests and uncertainties remain available. Quote save no longer automatically opens confirmation; review is deliberate. Decision shows the proposed supplier and submitted notes in the prototype's confirmation dialog before its existing atomic save; it introduces no backend approval state. Cancelling retains selection and notes. Notes-only and clear behavior is unchanged. Dashboard rows, saved preference and Comparison advice have the approved hierarchy. Supporting supplier capabilities and secondary quote fields are disclosures; material findings and evidence access remain visible.

Verification for this correction:

- Frontend regression suite: **242/242 passed**, including saved-review/no-implicit-write checks, readable value coverage, existing conflict/retry/draft/provenance/decision regressions (`fidelity-tests-final.json`).
- ESLint and standalone TypeScript checking passed (`fidelity-lint-final.log`, `fidelity-typecheck-final.log`).
- Full real-application browser suite: **16/16 passed** (`fidelity-browser-final.log`, `fidelity-browser-results-full/`). After the final Decision-dialog, display-label and field-alignment changes, the affected golden path and responsive suite were rebuilt and rerun: **2/2 passed** (`fidelity-browser-verified.log`, `fidelity-browser-results-verified/`). The final run includes a successful production build, type validation and lint. Intermediate failed runs remain retained: changed explicit-edit navigation/locator assumptions, plus a nullable display-label type error, were corrected. They are not unexplained or waived failures.
- Five stages checked at 320/390/768/1024/1440 CSS pixels. Brief editor and Brief/shortlist/two quote/Decision review dialogs captured at desktop and phone widths. **25 automated axe scans passed** across stage and review states. Actual Chrome 400% zoom reflow checks again passed for dashboard and all five stages. Screenshot inspection compared saved/edit/review hierarchy, typography, blue actions, light surfaces, grouping and responsive wrapping against the pinned prototype; corrected a two-column summary override and stretched requirement controls found during inspection.
- The four approved prototype hashes remain unchanged. Protected specs and backend have no diff; no dependencies were added in this correction. No staging, commit or deployment was performed. Prior M4-U7 work and historical verification limitations are preserved. The earlier selected backend test results remain historical; backend tests were not rerun for these frontend-only corrections.

Evidence is local and ignored under `.local-investigation-artifacts/UX-U1/`; it is not supplied by a clone. Production displays the real API's richer fields, uncertainty and source citations, so text/height are not pixel-identical to simulated prototype content. Dashboard uses available project summary fields; Decision does not invent the prototype's static AI suggestion. Approval rechecks retain the documented quote/shortlist check-submit race limitation. Automated accessibility results do not establish accessibility acceptance or participant approval.

**Independent Review remains next, not begun.** Review these corrective diffs together with the existing UX-U1 changes, especially modal recovery/focus, human approval boundaries, uncertainty and provenance visibility, draft retention, and Decision cancellation/notes-only/clear semantics. Independent Browser QA, manual assistive-technology/keyboard evaluation and participant testing remain required. UX-U1 stays IMPLEMENTING; this is implementation self-verification only.

Local spot check: open `http://localhost:3000`, reopen the existing project, and save the Brief. The former long approval block should be absent. Choose **Review saved Brief** for the readable saved summary; **Continue editing** returns without approval. Confirm the original request and uncertainties remain present. Approval shows an approved summary with **Edit Brief**. Also check shortlist/quote review and the proposed-preference confirmation at a phone width. Normal startup commands remain in `docs/local-development.md`.

Minor requested styling follow-up: removed the Brief requirement fieldset top border beside each legend; retained bottom separators. Verified the running app stylesheet in isolated browser markup at 1440px and 390px (top 0px, bottom 1px); inspected the phone capture. Evidence: requirement-border-1440.png and requirement-border-390.png under the existing local UX-U1 artifact directory. No behavior change or full-suite rerun; existing verification above remains historical.

Requested requirement-header follow-up: added a divider below the Requirements and importance section title and moved each remove action to the right of its requirement/attribute legend. Fieldsets retain their explicit accessible group names; removal still updates only the existing draft. Headers wrap safely at narrow widths. Targeted Brief tests passed 15/15 and TypeScript passed. Running stylesheet verified in isolated representative browser markup at 1440/390/320px; divider present and no overflow, with phone screenshot inspected. Evidence: requirement-header-tests.log and requirement-header-{width}.png in the local UX-U1 artifact directory. No full-suite rerun or change to the pending independent acceptance gates.


### Supplier-card hierarchy follow-up

Human approved the proposed card simplification. Implemented compact labeled minimum-order/lead-time/indicative-price facts, visible shortlist state, aligned requirement rows with text status badges, a prominent known MOQ failure message, and separate unknown/conflict explanations. Backend-derived findings remain authoritative; no scoring, automatic exclusion or inference from missing evidence was added. Add to shortlist is primary, View evidence opens/focuses the original evidence disclosure, and Dismiss/AI explanation are quieter. Supporting capabilities, source details and private notes remain available. Only explicitly informational Brief context collapses; required/preferred and unset-importance unevaluated requirements remain visible. This keeps unknown importance distinct from optional information. All existing membership, shortlist approval, stale-data handling, private-note drafts and explanation requests are unchanged.

Verification: full frontend suite **243/243 passed** with success=true (`supplier-card-tests-final.json`); added coverage for known MOQ failure versus unknown findings, required/unset-importance omissions, informational disclosure and opening evidence. Lint and TypeScript passed. The final isolated golden-path and responsive browser run **2/2 passed**, including a production build, five viewport widths, 25 existing automated accessibility scans and 400% zoom checks (`supplier-card-browser-final.log`, `supplier-card-browser-results/`). Desktop and phone supplier captures were visually inspected. Earlier runs exposed a test-environment scrolling API mismatch (removed redundant scrolling; focus already reveals evidence) and dev/production build-directory interference (paused dev during final verification). Final checks passed; earlier failures are retained, not waived.

No backend, protected specification, dependency, staging, commit or deployment change. UX-U1 remains IMPLEMENTING. Independent Review/Browser QA, participant testing and manual accessibility acceptance are still pending. Review the information-disclosure boundaries and evidence association along with existing UX-U1 diffs. Historical limitations remain unchanged.


### Shortlist review modal follow-up

Human requested clearer shortlist approval review. Replaced sentence/bullet dumps with separated supplier sections, compact labeled facts, readable indicative prices and aligned requirement/status rows using the supplier-card visual language. All evaluated findings are visible in the review (including unset importance), with required/preferred/unset unevaluated requirements explicitly retained. Unknown, Conflict and Does not meet remain distinct; derived MOQ findings use the existing backend status. Approval copy explains that the group proceeds to Quotes without choosing a preferred supplier; private-note drafts remain separate. Continue Reviewing precedes Approve Shortlist. The supplier-details region scrolls while actions stay visible at normal heights; small-height windows use whole-dialog scrolling. The region is named and keyboard-focusable, and approval errors stay outside it. Existing preflight, readiness, pending-write and revision checks are unchanged.

Verification: supplier-review regressions **18/18 passed** (`shortlist-modal-tests.log`), targeted ESLint and TypeScript passed. Browser checks exercised the real mounted application with isolated synthetic API responses (no user-project writes), at 1440/390/320px: three axe scans clean, approval buttons visible before/after scrolling, keyboard End scrolls details, Escape closes and restores trigger focus, opening/closing sends no approval write. Desktop and phone screenshots inspected (`shortlist-modal-{width}.png`, `shortlist-modal-bottom-{width}.png`). The first axe scan identified an unfocusable scroll region; fixed and rerun successfully. This targeted follow-up did not rerun the production build/full real-backend suite; preceding results remain historical. No backend, dependency, protected-spec, staging, commit or deployment change. Independent Review, Browser QA, participant and manual accessibility acceptance remain pending.

Quote spacing follow-up (10 November 2026): removed the negative top margin from quote-form helper text using a scoped override (12px clearance below entry controls); grouped saved PDF/manual edit/review buttons with the existing wrapping actions layout (8px gap, 12px separation from notes). No quote behavior changed. Browser-rendered representative markup with the running stylesheet verified at 1140/390/320px: helper clearance 12px, adjacent/wrapped button gap 8px, no horizontal overflow; phone capture inspected. TypeScript passed; quote regression results in quote-spacing-tests.log. Screenshots: quote-spacing-{width}.png in the local UX-U1 artifact directory. No full production/backend suite rerun; prior results and independent acceptance gates remain unchanged.


### Targeted removed-supplier quote selector fix — 10 November 2026

Human authorized only the diagnosed shortlist/quote-selection fix. Current eligible suppliers alone populate the main quote selector. Retained ineligible suppliers appear separately under No longer shortlisted on desktop and in a labeled optgroup on mobile, with explicit inactive labels. Existing saved quotes are matched to supplier records on load so the retained group does not disappear merely because the page was refreshed. Existing mounted cards/drafts are preserved; no quote, evidence or draft deletion was introduced. Restoring eligibility returns the supplier to the active choices without duplication. Existing mutation/confirmation eligibility checks and comparison selection remain unchanged; no backend or API contract changes.

Verification: quote regression suite **35/35 passed** (`retained-quote-tests.log`), including the Cedar-for-Harbor replacement, unsaved-note retention, disabled saving for removed suppliers, saved-quote access after remount, and reactivation without duplication. Targeted ESLint and TypeScript passed. A real mounted-app browser check with isolated API responses verified three active choices, separate Harbor, stable grouping after page reload, mobile optgroups at 390/320px, no overflow, existing save guard, and no mutation requests. Desktop/mobile screenshots inspected (`retained-quote-{width}.png` under local UX-U1 artifacts). No full production-build/backend-suite rerun for this bounded fix; previous results remain historical. No unrelated functionality, dependency, protected-spec changes, staging, commit or deployment. Independent acceptance gates remain pending.


Shortlisted-only refinement (10 November 2026): human explicitly chose to hide removed suppliers instead of showing a retained group. This supersedes the preceding selector presentation. Desktop and mobile now show only eligible shortlisted suppliers, and selection falls back to the first eligible supplier if the previous selection is removed. Removed cards remain mounted but hidden to preserve draft state; saved quotes/evidence remain untouched and become visible when the supplier is shortlisted again. Existing local dirty-removal confirmation and backend eligibility/comparison rules are unchanged. Removed the superseded retained-group UI/CSS only.

Targeted quote/supplier regressions passed **53/53**, including hidden draft retention/restoration, three active choices, remount behavior and saved-quote restoration; TypeScript and targeted ESLint passed. Browser verification used the running application with isolated responses at 1440/390/320px, including page reload, re-shortlisting and no mutation requests; desktop screenshot inspected. Evidence: shortlisted-only-tests.log and shortlisted-only-{width}.png under local UX-U1 artifacts. No backend, protected-spec, dependency, staging, commit or deployment changes; no full build/full-suite rerun for this narrow refinement. Independent acceptance gates remain pending.


### Local startup credential follow-up — 10 November 2026

Human requested that local API startup use the root .env instead of inherited application configuration. Investigation confirmed the old request worker inherited a different OPENAI_API_KEY; both comparison attempts recorded provider authentication 401. Added scripts/dev-api.py and updated the local startup command. The launcher clears inherited settings named by .env.example/.env and OPENAI_, SOURCEPILOT_, LANGFUSE_ prefixes, then loads the root .env with override enabled; OS essentials remain available. A missing .env stops startup. This is a bounded local tooling fix; backend business logic, production/test launch configuration, credentials on disk, and system/user environment settings are unchanged.

Verification: two isolated regression checks passed (inherited key replacement/omitted settings and missing-file refusal); Ruff passed. Restarted the local API with the launcher and securely compared the running request worker: key and model match root .env. Direct API and frontend-proxied health both returned 200. No live AI request was made, so provider acceptance of the current key remains unverified. No full application suite rerun. Targeted diff check passed; broader working-tree diff check still reports pre-existing whitespace in globals.css and quote-review.tsx, left untouched. Historical verification limitations and independent acceptance gates remain unchanged; no staging, commit, deployment or protected-spec changes.


### Tradeoff analysis readability follow-up — 10 November 2026

Human requested a clearer analysis presentation. Key tradeoffs, important unknowns and conflicts now precede supplier summaries. Summaries group by explicit single-supplier references; shared/unassigned findings appear once under Across suppliers. Supplier groups use responsive columns that stack on phones. Each finding has at most one Source details disclosure, with existing requirement and quote evidence renderers inside, preserving current versus original values and supporting versus provenance distinctions. Requirement status, importance and expected values remain visible. Suggestion/reasons/tradeoffs/uncertainties remain separate from summaries and do not perform any selection. Model text, backend calls, snapshot binding, staleness, retry and human decision behavior are unchanged.

Verification: comparison regression suite **54/54 passed**, including a new test for supplier grouping, shared/unassigned findings, visible failure/unknown information and a single evidence disclosure. ESLint and TypeScript passed after correcting an empty-array inference in the new test. Real component markup captured from an isolated test response was rendered with the running application's stylesheet at 1440/390/320px; no overflow, three automated axe scans passed, and keyboard Enter opens evidence. Desktop and phone captures visually inspected; an inherited block-style importance label was corrected and browser checks rerun. Evidence: tradeoff-render.html, tradeoff-{width}.png and check-tradeoff.cjs in the ignored local UX-U1 artifact directory. This is representative component verification, not independent Browser QA or a full live-provider workflow. No AI request, user-data mutation, backend change, dependency, protected-spec change, staging, commit or deployment. No full production build/full-suite rerun for this scoped presentation change. Existing independent Review, Browser QA, participant and manual accessibility requirements remain pending.


Decision mobile styling follow-up (10 November 2026): human requested removing the saved-preference accent border and full-width mobile action buttons, and asked for feedback on the next-action control and stage menu. Removed the decorative left border. At widths up to 767px, Decision form actions stack at full width and workflow guidance places its full-width action below the explanatory text, with a non-shrinking arrow. The stage menu is unchanged; recommended a compact stage selector for future human consideration. No decision, approval, draft or navigation behavior changed.

Verified on the running sample project in the integrated browser: at 390px, border is 0px and both buttons equal their 311px container; at 320px both equal their 241px container; no horizontal overflow. Visually inspected the 390px view and confirmed the guidance button below its message. A subsequent immediate desktop measurement still reported the prior viewport, so it is not claimed as desktop verification; viewport override reset. CSS-only follow-up; no new tests, full-suite/build rerun, AI request or user-data mutation. Independent acceptance gates and historical limitations remain unchanged.


Mobile stage selector follow-up (10 November 2026): human approved recommendation 4. Replaced the two-column navigation on widths up to 767px with a labeled native Stage selector. Options preserve the five-stage order and indicate the workflow stage needing attention. Selected value follows the viewed stage, including browser history. Desktop/tablet stage links remain unchanged. The selector calls the existing navigation hook; stage panels remain mounted and existing draft/departure protections are retained.

Verification: 13/13 targeted shell, workspace and draft regressions passed; ESLint and TypeScript passed. Added coverage for selector order, stage URL/content updates, retained drafts and history synchronization. Running sample project checked in the integrated browser at 390/320px (selector visible, old links hidden, no overflow) and 1440px (selector hidden, desktop links visible, no overflow). Visually inspected phone layout and used the selector to open Decision without a data mutation. Restored normal viewport. No backend, dependency, protected-spec changes, staging, commit, deployment or full build/full-suite rerun. Independent acceptance gates and prior limitations remain unchanged.


Palette refinement for human review (10 November 2026): human authorized implementing the researched ink-navy/warm-neutral/blue direction. Updated the running application's shared CSS tokens: warm canvas #F4F3EF, navy heading/brand #182B3A, neutral surface #EEEDE8, selected surface #EAF0FC, muted error red #A13935, and amber attention text #805B18 on #FFF5DF. Primary blue #2457C5 stays unchanged. Current preference is neutral; workflow attention uses amber rather than selection blue. White working surfaces, explicit status labels, focus indicators, and existing layouts/behavior remain. This is an authorized palette amendment for review; the original pinned prototype files and hashes are preserved as historical references.

Verification: calculated contrast for changed primary text/surface combinations: navy/canvas 13.08:1, amber/attention surface 5.65:1, blue/selected surface 5.66:1, white/primary blue 6.47:1, secondary text/neutral surface 5.76:1, error red/white 6.66:1. Visually inspected real sample Decision and supplier screens in the integrated browser, including 390px supplier layout with no horizontal overflow; computed canvas and heading values match tokens. Restored viewport. This is a CSS-only visual refinement; no full suite/build or complete accessibility audit rerun, and calculated pairs do not establish full accessibility acceptance. No backend, dependencies, protected-spec changes, user-data writes, deployment, staging or commit. Independent acceptance gates remain pending.


Panel definition follow-up (10 November 2026): human requested borders for colored attention/current-preference panels and white Rename project background. Added uniform 1px amber #DBC48E attention border and neutral #C9CCC7 preference border; no decorative side stripe. Rename disclosure now has a white rounded surface with padding, including its expanded form. Project title column can shrink to prevent overflow. Verified live sample at 390px: both borders compute to 1px, rename background white, no horizontal overflow; screenshot inspected with rename expanded. Viewport restored; no data edits or behavior changes. CSS-only targeted verification, no full-suite/build rerun; independent acceptance gates remain pending.


Active-menu follow-up (10 November 2026): added a subtle 1px inset blue outline to the active stage link without shifting its dimensions; retained a separate 3px offset keyboard focus outline. Verified the live sample at 1024px: computed 1px outline and no overflow; screenshot inspected and viewport restored. Suggested moving saved preference under the project title; no preference layout change yet because the user requested thoughts. CSS-only; no workflow changes or full-suite rerun. Existing acceptance limitations remain.


Project header alignment follow-up (10 November 2026): human approved placing saved preference directly below the project title. Moved it into the title column as an inline labeled value above the full-width Rename project disclosure; removed obsolete right-column constraints. Saved value and rename behavior unchanged. Eight targeted shell/workspace tests and ESLint passed; live 390px screenshot visually verified grouping and full-width rename. Viewport restored. No data writes, full build or full-suite rerun; independent acceptance requirements remain pending.


Transient save-status follow-up (10 November 2026): human approved hiding idle Saved indicators and showing success briefly. Shared save-status component now shows Saved for three seconds after an explicit successful draft-save event, never from pending completion alone or an initial/remounted clean record. useRecordDraft exposes a monotonically increasing save version from saved dispatches; Brief, quote, supplier-note, Decision and rename status consumers pass it through. Pending, dirty, failure and conflict notices retain precedence and remain visible while relevant. Workflow Approved/Confirmed/Needs review states are unchanged.

Verification: 108 targeted regression tests passed across affected editors, workspace, draft reducer and new timer tests. Timer tests cover initial/pending-only silence, repeat saves and persistent dirty/error/conflict notices. After preventing historical success replay on remount, three timer tests rerun successfully. ESLint and TypeScript checks passed. Live browser inspection confirmed existing unsaved Decision notes and Unsaved changes remain visible; did not save, discard or alter the user draft. No backend, dependencies, protected-spec changes, staging, commit or deployment; no full build/full-suite rerun. Independent acceptance gates remain pending.


Save-status heading alignment follow-up (10 November 2026): human approved placing record save feedback beside section titles. Brief, Decision and individual quote headings now share a wrapping row with their existing save-status component aligned right. At 420px and below status takes a line beneath the title. Brief readiness remains separate; detailed errors, recovery controls and footer feedback remain by their forms. Supplier private-note and rename feedback remain within their disclosures. No save timing or persistence behavior changed. Verified 67 targeted editor/status tests, ESLint and TypeScript passed. Live Decision screenshot inspected at wide and 390px widths; status aligned right on wide layout, wrapped below on phone, no phone overflow. Existing user draft preserved; no save/discard performed. Viewport restored. No full build/full-suite rerun; independent acceptance gates remain pending.


Saved manual quote layout follow-up (10 November 2026): human approved two-column grouped details. Manual saved/confirmed quote values now reuse existing Commercial, Timeline, Terms, Compliance and Other groups with visible headings and subtle separators. Label/value pairs use two columns above 767px and one column on phones; compliance notes, exclusions, special conditions and supplier notes span both columns. Quote notes remain full width and Unknown values remain visible. PDF evidence/review, dialogs, editing and confirmation behavior unchanged. Live sample verified at 1200px (two equal columns) and 390px (one column), no overflow; desktop screenshot inspected and viewport restored. Quote regression suite, ESLint and TypeScript run for this change. No data writes, backend/dependency/spec changes, staging, commit or deployment; no full build/full-suite rerun. Independent acceptance gates remain pending.


### Targeted review fixes — 10 November 2026

Human authorized only the three reported review findings. Status remains IN_REVIEW pending re-review; no advance to Browser QA or Done Check.

- Dashboard: explicit Leave anyway now clears the abandoned creation error/uncertainty and refreshes the project list, allowing a fresh request. Checking saved projects retains the original request and keeps replay blocked. Late failures of deliberately departed requests refresh the list without reintroducing the abandoned error.
- Retained creation drafts now keep native reload/tab-close protection even when the creation dialog is hidden. Explicit departure releases protection for the abandoned request; a new dirty request is protected.
- Browser test helper now selects the existing Stage control on phones and retains link navigation on wider layouts. No application navigation change.

Verification: five dashboard tests passed, including expanded regression assertions for hidden-dialog reload protection, deliberate abandonment, no automatic replay, fresh-form availability and protection of a new draft. ESLint and TypeScript passed. An isolated headless Chrome fixture using the actual navigation helper and application stylesheet passed all five stages at 1440, 768, 390 and 320px. The default bundled Playwright browser was unavailable; installed Chrome was used successfully. This fixture is not full application Browser QA. No full production build or end-to-end suite rerun; existing live server and user data were untouched. Full-diff whitespace check still reports two pre-existing quote-review.tsx whitespace lines outside this fix. Independent review, Browser QA, accessibility and participant acceptance remain pending. No backend, dependencies, protected specifications, staging, commit or deployment changes.


### Done Check � 10 November 2026

**Result: NOT READY TO COMMIT.** Requested by the human after targeted re-review. Remain IN_REVIEW; do not advance the lifecycle on an incomplete Done Check. The three reported findings were fixed and re-reviewed without new defects found. This same-context review does not replace the separately requested independent Review. No application code changed during this check.

| Workflow gate | Result and evidence |
| --- | --- |
| Current unit / scope | UX-U1 and explicitly authorized amendments only; earlier M4-U7 addenda preserved as unrelated work. No next unit begun. |
| Acceptance criteria | Incomplete: final implemented-workflow participant sessions/results absent. Five participants, at least four of five completing each task, and zero specified critical incidents remain required. |
| Required tests | Fresh frontend run: 249/249 tests, 21/21 files passed. Local environment launcher: 2/2 passed. Final integrated golden-path/targeted E2E, backend regression evidence and production build have not been refreshed after all amendments; prior results remain historical. |
| Evals | No model, prompt or backend contract change in this unit requires new live-provider calls. Historical provider failures, supplemental-only passes and pending human reviews remain unresolved as recorded above; no general reliability claim. |
| Type checking / lint | Both passed on current source. |
| Review findings | Three reported findings resolved; targeted re-review found no new defects. Dedicated regression for delayed completion after departure remains a coverage limitation, not a confirmed defect. Separately requested independent Review remains pending. |
| Browser QA | Required and incomplete. Earlier component/browser checks and the corrected navigation-helper fixture are supporting implementation evidence, not final independent application QA. |
| Accessibility | Manual keyboard/screen-reader and final responsive/zoom acceptance remain incomplete; earlier axe and contrast checks do not waive them. |
| No known regression | No new defect found in targeted re-review; cannot assert full-unit clearance while integrated QA is incomplete. |
| Dependencies / infrastructure | Approved frontend foundation retained; no new dependency in targeted fixes. Backend and protected specification diff remains empty. |
| Documentation | This result and review resolution recorded; historical limitations preserved. |
| Diff | Prior review plus targeted re-review completed. Whitespace check still flags quote-review.tsx lines 353 and 392; left unchanged in this checking-only task. |
| Artifacts | Generated local investigation artifacts remain ignored. Authored design package/verification scripts and installed skill files are distinct from generated evidence. Unrelated M4-U7 changes must not be swept into a future unit commit. |
| Secrets | No .env/.env.local files in changed/untracked candidates. Common OpenAI-key, AWS-key and private-key patterns found no matches across those candidates; this is a limited heuristic scan, not exhaustive secret certification. No credential values printed. |
| Approved reference | All four prototype SHA-256 hashes match the pinned approved reference. |
| Ready to commit | No: incomplete acceptance, independent Review/Browser QA, final integrated verification and diff hygiene remain. Nothing staged, committed or deployed. |

A production build/full E2E was not run during this evidence check: those commands share the active dev server's .next output, and the user's live workspace/drafts were left untouched. Run final verification in an isolated checkout/output environment or a coordinated server maintenance window. Complete the outstanding Review/QA and human acceptance before repeating Done Check. No participant recruitment or contact is authorized by this check.

## Independent production Review — 10 November 2026

**Disposition: Review FAIL. Status remains IN_REVIEW.** This review evaluates the production working tree against baseline `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`, the approved plan, pinned prototype and subsequent human-authorized amendments. It supersedes the earlier same-context re-review only as the current Review disposition; all historical results and limitations above remain intact. This is not Browser QA or a repeated Done Check.

### Findings, ordered by severity and user impact

All four findings are P2 (must be addressed before this unit passes Review).

1. **R1 — Later clarification typing is silently lost on save completion.** `apps/web/components/brief-editor.tsx:243–246, 419–423`. Clarification inputs remain editable during their PATCH, but success unconditionally clears the questions and entire answers map. Unlike the main record draft, answers have no submitted generation reconciliation. Reproduction: submit quantity 1000, type 2000 before the response, then resolve the PATCH with saved quantity 1000. The question disappears, the main form shows 1000, and neither an unsaved indicator nor a recoverable 2000 remains. Independently reproduced with a deferred response. This behavior existed in the earlier answer handler but remains an unmet approved UX-U1 draft-preservation requirement, not a claimed newly introduced backend regression. Preserve post-submission answers separately from the acknowledged snapshot and test delayed success and failure.

2. **R2 — Checking an uncertain quote save can leave the editor permanently locked.** `apps/web/components/quote-review.tsx:139–142, 318` and `apps/web/components/use-record-draft.ts:14`. A failed PATCH sets `uncertain`. Check saved quote reloads parent data, but identical editable server values retain the same `incoming.current` reference, so the receive effect never runs. The user retains the draft but cannot save, discard, or enter the explicit saved-versus-draft review. Independently reproduced: network-failed note edit followed by successful GETs returning the unchanged quote; Save and Discard remain disabled and neither reconciliation action exists. An unchanged read must not be interpreted as proof the write failed, but must allow deliberate review/recovery without abandoning the visit. Add component-level unchanged-read recovery coverage; reducer-only coverage does not catch this wiring defect.

3. **R3 — Opening a project bypasses departure protection for a retained creation request.** `apps/web/components/project-dashboard.tsx:125–128, 144`. Check saved projects deliberately hides the creation dialog while preserving its dirty/uncertain request. The now-accessible project links have no departure guard. Next Link performs same-document navigation, so the new native beforeunload protection does not cover this path; the dashboard unmounts and its retained request is lost without Stay/Leave anyway. The isolated component check confirms the click is not intercepted and no departure choice appears (Next Link is mocked; actual browser navigation was not executed). Guard this deliberate in-app exit, preserving the request on Stay and never replaying creation. The previous reload-warning/fresh-form fixes remain valid; this is an additional route they did not cover.

4. **R4 — Collapsed quote groups conceal the identity and kind of material issues.** `apps/web/components/quote-review.tsx:334, 404`. Saved PDF and editing views summarize any conflict/uncertainty only as “Issues to review.” Terms, Compliance and Other begin collapsed; their field names, Conflict label and uncertainty text are inside the closed disclosure. For example a certification conflict is indistinguishable from an optional terms uncertainty until opened. This falls short of the approved information-architecture requirement that material gaps remain visible and group summaries name material issues. Retain concise field-specific conflict/uncertainty summaries outside the collapsed content, with full evidence still disclosed. Source-inspection finding, not a new visual/assistive-technology test; add coverage for a conflict in a default-collapsed group.

### Completeness and scope assessment

- The dashboard and all five stage families are present, with mounted stage editors, viewed-stage versus backend guidance separation, explicit PDF/manual choices, grouped fields, saved-value dialogs, original evidence inspection, comparison facts/advice and independent human preference actions. The mobile selector, shortlisted-only quote choices, palette, header placement and transient save feedback are authorized amendments, not unexplained deviations from the original prototype. All four pinned prototype hashes still match.
- Missing approved behavior is the preservation/recovery/departure and named material-issue visibility described in R1–R4. No entire stage or quote-entry method is missing. Design completeness is therefore not passed. A source-level layout comparison does not establish final rendered visual fidelity.
- Production writes/reads use the existing shared API layer and endpoint contracts. Prototype fixture names, simulation switches and simulated persistence were not found in production components/lib; the few timers serve status, departure and existing analysis deadlines. No backend source, API-contract, migration or protected-specification diff was found. Next/React remain 15.5.3/19.1.1. Manifest/lock additions fit the approved Radix/shadcn utilities, Lucide, Tailwind/PostCSS and test-only axe foundation; no prohibited orchestration/store/infrastructure dependency was found. Local API launcher changes are the explicitly recorded tooling amendment. Unrelated M4-U7 addenda remain untouched.
- Approval code rechecks saved Brief/shortlist/quote data and requires explicit action. Decision can choose any shortlisted supplier independently of comparison/advice; notes-only and clear operations preserve an unsaved replacement/notes as specified. Decision-only responses retain unrelated comparison/advice and newer guidance protections. Existing quote/shortlist check-submit races remain the documented contract limitation, not a newly promised atomic guarantee.
- Original PDF excerpts/extracted values and user-corrected current values remain separate. Comparison continues to render backend conflicts, required failures, quantity/currency warnings, stale results, nullable suggestions and recovery. R4 concerns discovery of quote issues before opening secondary disclosures, not deletion or rewriting of source evidence.
- Navigation parsing/canonicalization, history handling, focus targets, modal focus return, narrow layouts and short-viewport styles were inspected. Existing tests cover query/fragment precedence, mounted draft retention, selector/history synchronization and departure timing. Full browser focus/scroll restoration, screen-reader semantics, touch/zoom and final responsive fidelity remain for Browser QA; no passing unit test is used as proof of them.

### Newly performed verification

| Check | Result and boundary |
| --- | --- |
| Current-source frontend regression suite | `pnpm --filter @sourcepilot/web test`: **249/249 passed, 21 files**. Includes previous dashboard abandonment/reload defects, mobile selector, quote retention/provenance, comparison and Decision regressions. These passing tests omit the new reproductions. |
| Focused independent defect probes | **3/3 reproduced the defective behavior** for R1–R3 in actual production components with isolated responses. These are diagnostic assertions of existing defects, not acceptance passes. Sources/config/report retained under ignored `.local-investigation-artifacts/UX-U1/independent-review-2026-11-10/`. Initial harness collection failed because of its Vitest import; corrected and rerun. Dashboard uses a Link mock and jsdom reports unsupported navigation; only absent interception/modal is claimed. |
| Type checking | `pnpm --filter @sourcepilot/web exec tsc --noEmit --incremental false`: passed. |
| Lint | `pnpm --filter @sourcepilot/web lint`: passed. |
| Scope/reference checks | Inspected production diff, new helpers/primitives, test changes, dependency manifest/lock, local launcher and authored design references. Backend/protected-specification diff and staged diff empty; four pinned SHA-256 values unchanged. No dependency install, application-code edit, whitespace cleanup, stage, commit or deployment. |

### Retained evidence and outstanding limitations

Inspected the existing implementation JSON (238/238), browser implementation log (16/16), selected backend log (190 passed, one deprecation warning), and supplier-card browser log (2/2), alongside later amendment records. These are **retained historical implementation results**, not reruns or evidence that every final amendment passed integrated checks. The prior dashboard fixes and corrected responsive test helper were inspected and their current frontend regressions rerun; their earlier Chrome fixture remains historical. Dedicated delayed creation completion-after-departure coverage is still incomplete.

No live provider call, user-data mutation, live-browser session, new visual comparison, manual accessibility session, participant session, final production build or integrated backend/E2E run was performed in this Review. The active development server/output and user drafts were left untouched. Manual accessibility, five unfamiliar participants (4/5 per task and zero specified critical incidents), final build, integrated regressions and whitespace cleanup remain outstanding. Historical provider failures, supplemental-only evidence and pending human reviews remain unchanged. No design detector was installed or run; no detector/accessibility certification is implied.

**Next gate: targeted fixes for R1–R4, with focused regression coverage, then independent re-review while retaining IN_REVIEW.** Separately authorized Browser QA follows only a Review PASS. Do not repeat Done Check now.

### Targeted fixes for independent Review R1–R4 — 10 November 2026

Human authorized these four fixes, their regression coverage and the two previously identified whitespace lines only. **Status remains IN_REVIEW; independent re-review is next.** The preceding Review FAIL and historical evidence are preserved. This implementation verification does not mark the independent Review passed.

| Finding | Implemented correction | New regression evidence |
| --- | --- | --- |
| R1: clarification edits during saving | Capture the submitted answer snapshot and compare it with the latest answers on successful completion. Acknowledge only submitted values; retain later answers, including deliberately cleared values and the delivery date/period type, in a separate visible Unsaved clarification answers recovery area even when questions disappear. These drafts participate in existing dirty/approval/departure guards. Copy into the latest Brief deliberately, then explicitly discard the retained copy; no stale answer is automatically reapplied. Failed saves retain editable answers. Main Brief saves also retain answer drafts they did not submit. | Deferred quantity save followed by 2000 or a blank edit; disappeared question, saved quantity unchanged, retained copy and unsaved status, approval disabled until deliberate disposal, no extra PATCH. Deferred delivery save failure retains current text/type; later success retains newer period text separately. |
| R2: unchanged-read uncertain quote recovery | The explicit recovery check now reads the current quote (or supplier quote list for an uncertain creation) and dispatches the read to record reconciliation even if editable values are identical. It preserves the complete draft and uncertainty until the user chooses saved values or reviews both records and keeps edits. Copy states that an unchanged read does not prove failure and the request may still complete. Failed reads leave recovery locked and retryable. A quote discovered after uncertain creation is adopted, so a subsequent deliberate save updates its existing ID. The workspace departure check uses the same read path. | Uncertain PATCH, failed recovery GET, then unchanged successful GET; both explicit keep/saved choices tested, no automatic second write. Uncertain creation with no saved quote retains the draft without replay. Creation that did persist is recovered and a later deliberate save PATCHes the recovered ID rather than creating again. |
| R3: dashboard navigation protection | Capture same-window internal link navigation while a creation draft/pending/uncertain request is retained, including project rows and the dashboard header outside the component. Reopen the existing warning with Stay focused. Stay cancels the destination and preserves the request; explicit departure clears the abandoned local draft and follows the chosen destination without replaying creation. Hash-only links and links opening another context retain their normal behavior; native reload/tab-close protection remains. | Project-row and header destinations after Check saved projects: navigation intercepted, Stay focused, original request retained and duplicate creation disabled; only Leave anyway navigates, with one original POST. Delayed success and failure after explicit abandonment neither redirect nor restore the abandoned error/request. Existing hidden-dialog reload protection and fresh-request tests remain passing. |
| R4: material issue summaries | Saved PDF and editing group summaries now name each affected field with Conflict and/or Uncertainty, including conflicting source interpretations. Optional unknown/omitted fields alone do not become material warnings. Full field details and original evidence remain inside the disclosures; no new confirmation gate. | Closed Terms and Compliance summaries expose Payment terms: Uncertainty and Certifications: Conflict in saved and editing views. Optional Warranty omission is absent from the issue summary. Confirmation remains available through the existing explicit review, and merely viewing issues sends no mutation. |

Production changes are limited to `brief-editor.tsx`, `quote-review.tsx` and `project-dashboard.tsx`, with regression additions in their three existing test files. This record is the only documentation changed by the fix task. No prototype, protected specification, backend contract/source, dependency or unrelated work was edited.

**Separately reported mechanical cleanup:** removed only the two whitespace-only lines previously reported at quote-review.tsx:353 and :392 (line positions shifted with these fixes). No broader whitespace cleanup was performed. `git diff --check` now passes.

#### New verification for this fix pass

- Affected suites: **67/67 passed** (Brief 18, Quotes 40, Dashboard 9). Report: `.local-investigation-artifacts/UX-U1/review-fixes-r1-r4-targeted.json`.
- Full frontend suite, after the affected suites: **261/261 passed, 21 files**. Report: `.local-investigation-artifacts/UX-U1/review-fixes-r1-r4-frontend.json`.
- ESLint and TypeScript (`tsc --noEmit --incremental false`): **passed**. The first lint run rejected a literal home anchor in the new test fixture; changed that fixture to the already-mocked Next Link, then reran Dashboard **9/9**, lint and type checking successfully. The 261-test result predates only this test-fixture lint correction; production source was unchanged afterward.
- Initial affected run: 65/66 passed; the collapsed-summary regression correctly caught that the first text replacement had not updated the rendered summary expressions. Updated both saved/editing expressions and reran successfully before the final 67-test and full-suite runs. Earlier failures are not counted as acceptance passes.
- Scope checks: backend/protected-specification diff and staged diff remain empty; all four pinned prototype SHA-256 hashes still match. Existing unrelated work remains present and untouched. No dependency installation, staging, commit or deployment.

These are component tests with isolated API responses and static checks. They exercise the production handlers but do not establish live-stack reliability, final visual fidelity, browser history/focus interoperability, accessibility conformance or participant usability. Dashboard navigation tests mock Next Link/router; real browser integration remains for the separate QA gate. Existing cross-tab check/submit races and in-memory-only draft lifetime are unchanged; unchanged reads never guarantee an uncertain write cannot later complete.

No formal Browser QA, Done Check, final production build, integrated backend/E2E regression run, manual accessibility session, participant acceptance or live-provider call was performed. The active application and user data/drafts were not operated on. Historical provider failures and pending reviews remain as previously recorded. Final production build, integrated regression verification, manual accessibility and five-participant acceptance remain outstanding.

**Handoff: stop for independent re-review of R1–R4. Keep IN_REVIEW; do not advance to Browser QA or Done Check from these implementation results.**

## Independent re-review of R1–R4 — 10 November 2026

**Overall independent Review: FAIL. Status remains IN_REVIEW.** The four original P2 failure cases are resolved, but the R2 correction introduces the actionable P2 regression R5 below. This disposition accounts for the preceding independent Review FAIL and its wider scope assessment; it does not erase that review, convert implementation evidence into independent QA, or repeat Done Check. No application code or approved prototype was changed during this re-review.

### Disposition of the original findings

| Finding | Independent disposition and evidence |
| --- | --- |
| R1 — clarification typing during saving | **Resolved for the reported failure.** Inspected the submitted-answer snapshot, latest-answer reference, retained-answer rendering and dirty/approval/departure registration. Replayed the original deferred quantity PATCH: submit 1000, type 2000, return saved 1000 with the question removed. The saved Brief stays 1000; 2000 remains in the visible unsaved-answer recovery area; approval stays disabled; only one PATCH occurs. Fresh existing regressions also cover a deliberately cleared answer, delivery DATE/PERIOD edits, failed save retention, explicit disposal, revision-conflict recovery and exclusion of externally resolved answers from subsequent PATCHes. Main Brief saves retain answers they did not submit by the same inspected branch; that particular branch was not separately exercised by a new independent probe. |
| R2 — unchanged reads after uncertain quote saves | **Original dead end resolved; related recovery regression R5 remains open.** Replayed the original network-failed notes PATCH followed by unchanged saved values, using the corrected single-quote GET contract. The draft survives, both saved-versus-draft recovery choices appear, and choosing to keep edits enables saving without another automatic PATCH. Fresh existing regressions cover failed GET then successful unchanged GET, both explicit choices, uncertain creation with no saved quote, and recovery of an existing quote ID so the next deliberate save PATCHes that ID. Inspected workspace registration: its check now uses the same explicit receive path. Passing these sequential cases does not cover overlapping recovery reads. |
| R3 — dashboard project navigation with retained creation | **Resolved for the reported link-navigation failure.** Replayed creation network failure → Check saved projects → project link. The click is prevented, Stay receives focus, and Stay preserves the original request without another POST. Fresh project/header link regressions verify that only explicit Leave anyway invokes the destination, abandoned drafts release native unload protection, and checking retained requests keeps duplicate creation disabled. Fresh delayed-success and delayed-failure tests cover completion after explicit abandonment without unwanted redirect or restored error. Next Link/router are mocked: this establishes handler behavior, not real-browser routing/focus acceptance. |
| R4 — collapsed quote issue summaries | **Resolved.** Inspected both saved PDF and editing disclosure summaries. Fresh tests keep Terms and Compliance closed while exposing Payment terms: Uncertainty and Certifications: Conflict, excluding an optional Warranty omission from material warnings, and retaining explicit confirmation availability. An additional independent probe covers collapsed Other with two conflicting source interpretations plus uncertainty: Special conditions: Conflict and Uncertainty appears in both views even without an explicit CONFLICT review-state value. Optional-only Terms stays unmarked; viewing/editing disclosure state sends no write. Full source details remain available through the existing evidence view. |

### New actionable regression

**R5 — P2: overlapping recovery reads can silently roll back the accepted saved quote. Unresolved.** Location: `apps/web/components/quote-review.tsx:179–186` and the enabled Check saved quote button at line 336.

The new `checkSavedQuote` path has no in-flight or response-order protection. Each completion unconditionally calls `onStatus(latest)` and dispatches `receive`. It bypasses the parent reload's existing request-sequence check. Because Check saved quote remains enabled during a read, ordinary repeated clicks can produce this sequence:

1. Edit quote notes and receive an uncertain PATCH failure.
2. Click Check saved quote twice, leaving both GETs outstanding.
3. Complete the second GET with revision 2 and notes `new saved server notes`; choose Use saved record. The editor correctly shows those notes.
4. Complete the first GET with its older revision 1 snapshot and notes `original`.
5. The editor now shows `original`, replacing the newer record the user deliberately accepted. The clean-record receive path adopts the stale response; the user has not chosen this rollback.

Independently reproduced against the actual current component using deferred API responses. The acceptance assertion that the editor still shows `new saved server notes` fails with actual value `original`. This is a frontend stale-response regression, not evidence that the backend persisted a rollback. It can mislead subsequent editing/review and defeats safe recovery. The existing processing-status out-of-order tests remain passing because they protect a different read path.

Required correction for a separately authorized fix: prevent obsolete recovery completions from updating either parent quote state or record reconciliation after a newer result/choice has superseded them; preserve draft retention and explicit choices, without replaying writes. Cover overlapping recovery reads, including late success/failure and interaction with recovery choices. No correction was made in this review.

### Fresh verification and retained evidence

- **91/91 focused tests passed** across six files: Brief, Quotes, Dashboard, workspace drafts, record-draft reducer and save-status timing. This includes the 67 affected-editor tests plus directly related draft/departure/status regressions. Report: `.local-investigation-artifacts/UX-U1/independent-rereview-targeted-2026-11-10.json`.
- **Independent probes: 4 passed, 1 failed.** Adapted the preceding review's R1–R3 diagnostic sequences into corrected-behavior assertions, with the new single-quote GET response shape for R2. Added combined-conflict/uncertainty coverage for R4 and the R5 ordering regression. Final source/config/report: `.local-investigation-artifacts/UX-U1/independent-rereview-2026-11-10/`, authoritative report `results-final-verified.json`. The one failing acceptance assertion is R5, not a passing defect test. Earlier scratch runs included an obsolete assertion, encoding and working-directory mistakes; those are harness/setup failures, not application findings or acceptance evidence. The original review's historical probes/results were not overwritten.
- **TypeScript passed:** `pnpm exec tsc --noEmit --incremental false`. **Focused ESLint passed** on the three changed components and their three regression files. No dependency installation was needed.
- **Whitespace/reference/scope:** fresh `git diff --check` passed. Inspected the two now-empty JSX separation lines identified by the preceding review: removing their whitespace is mechanical and introduces no logic or text change. The working tree combines the earlier UX-U1 implementation and amendments with these uncommitted fixes, so there is no separate pre-fix commit/snapshot for a byte-for-byte six-file fix-only comparison; exact historical attribution is bounded by the retained review locations and current source/diff. No unrelated feature or dependency was found in the inspected R1–R4 correction paths. Backend/protected-specification and staged diffs remain empty; all four pinned prototype hashes still match. Existing unrelated M4-U7 work remains untouched.
- The preceding implementation's **261/261 full frontend result**, earlier independent **249/249 result**, prior lint/type/build/backend/browser evidence and provider/human-review limitations remain **retained evidence**, not fresh full-suite or integrated results from this re-review.

### Verification limits and next gate

This was source/diff inspection, isolated component reproduction and focused static/regression checking. No Browser QA, live application operation, live provider call, production build, integrated backend/E2E rerun, manual accessibility session, participant session or repeated Done Check was performed. No staging, commit, deployment, protected-specification edit or application-code fix occurred. Only this unit record and ignored local review evidence were written.

**Next gate: separately authorize the targeted R5 fix and regression coverage, then independently re-review while keeping IN_REVIEW. Browser QA is blocked by Review FAIL.** After a subsequent Review PASS, separately authorized real-application Browser QA must exercise the retained-answer recovery, quote uncertainty/recovery ordering, dashboard departure and collapsed issue summaries in the actual Next.js/FastAPI/isolated PostgreSQL flow, alongside the existing golden path and directly affected navigation/provenance regressions. Preserve the active user's drafts and use isolated build/output or a coordinated maintenance window.

Final production build, integrated regressions, manual keyboard/screen-reader/responsive/zoom accessibility, and five unfamiliar participants remain outstanding. Participant acceptance still requires at least 4/5 completing each task and zero specified unnoticed-data-loss, accidental-approval or provenance-misinterpretation incidents. Existing in-memory draft lifetime, quote/shortlist check-submit race limits, uncertain writes that may complete after a read, historical provider failures, supplemental-only results and pending human reviews are unchanged. No Browser QA or Done Check completion is implied.

### Targeted R5 correction — 10 November 2026

Human authorized only the latest P2 R5 fix, deterministic regression coverage and verification. **Status remains IN_REVIEW. R5 is implemented and verified by the implementer, pending independent re-review.** The preceding independent Review FAIL and its reproduction are retained as historical evidence; no independent PASS is claimed here.

The correction is confined to `apps/web/components/quote-review.tsx` and its existing test file. The explicit saved-quote recovery path now uses an editor-local request sequence. Starting a later recovery check supersedes earlier reads; adopting saved values or deliberately keeping the draft also invalidates outstanding checks immediately. A saved quote update, project/supplier change or editor unmount invalidates reads from the preceding context. Both success and failure check the sequence before changing parent quote state, the draft reducer or local recovery feedback. Current failures still propagate to the workspace departure check; obsolete failures are ignored. Saved-record discard/cancel uses the same invalidation path.

The existing uncertain-write contract is unchanged: an unchanged successful read opens explicit saved-versus-draft reconciliation, does not establish that the write failed, and does not resubmit a write. The fix does not cancel submitted writes, change API contracts, add persistence or alter the approved prototype. Existing R1–R4 regression cases are preserved.

#### Deterministic verification

Controlled-response tests cover:

- The reported second-read-first completion followed by Use saved record, then the older response: newer saved notes remain accepted.
- The same ordering with Keep my edits: the draft remains intact, conflict stays resolved, and later explicit discard still uses the newer saved baseline.
- A new read started after a recovery review already exists, followed by either recovery choice: late success and late failure are tested separately for both choices. Later local typing survives; obsolete responses cannot reopen conflicts, restore uncertainty or replace feedback. These cases specifically verify choice invalidation beyond request ordering alone.
- A newer failed recovery followed by an older successful read: the newer error remains visible, the draft is retained and writing remains blocked pending recovery.
- Late success and failure after quote replacement, project change and unmount: obsolete completions do not notify the parent or replace the current quote/recovery feedback.
- Existing unchanged-read, failed-read retry, uncertain creation/recovered-ID, clarification preservation, dashboard departure and collapsed-material-issue cases remain passing. Recovery assertions check that no extra PATCH is sent automatically.

Fresh results, all using installed dependencies:

| Check | Result |
| --- | --- |
| Before correction | Initial seven new test cases failed against the uncorrected component while the existing 40 quote tests passed. Failures included the reported accepted-value rollback, conflict reopening, stale feedback and previous-context callbacks. This is defect reproduction, not acceptance evidence. |
| Initial corrected quote suite | 47/47 passed. The choice-invalidation tests were subsequently split into separate success/failure cases, yielding nine new cases in the final suite. |
| Affected suites | **97/97 passed**, five files: Quotes, Brief, Dashboard, workspace drafts and record-draft reducer. This run preceded only a local handler rename for lint. |
| Final frontend suite | **270/270 passed, 21 files**, including all nine new R5 cases and preserved R1–R4 regressions, after the handler rename. |
| Full frontend lint | **Passed** (`pnpm exec eslint .`). The initial run interpreted the handler name `useSavedRecord` as a React hook; renamed it to `acceptSavedRecord` and reran successfully. |
| TypeScript | **Passed** (`pnpm exec tsc --noEmit --incremental false`), including a final run after the rename. |
| Diff/scope | `git diff --check` passed. A pre-task content-hash inventory and fix-only diff confirm only the quote component, its tests and this unit record changed during the task, apart from ignored local evidence. Backend/protected-specification and staged diffs remain empty; prototype and dependency files are unchanged. |

Evidence is retained under ignored `.local-investigation-artifacts/UX-U1/r5-fix-2026-11-10/`: `before.json`, `quotes.json`, `affected.json`, `frontend.json`, `before-hashes.json`, pre-fix file copies and `r5-only.diff`. These fresh component/static results supersede no historical independent review or integrated evidence. The production correction adds response validity checks only; no unrelated refactor, dependency installation, backend change, prototype edit, staging, commit or deployment occurred.

**Handoff: independently re-review R5 against its recorded reproduction, response ordering, explicit-choice invalidation and quote/project/unmount cases, while retaining IN_REVIEW. Do not infer Review PASS from this fix pass.** No formal Browser QA or Done Check was begun or repeated. Final production build, integrated backend/E2E regressions, manual accessibility and five-participant usability acceptance remain outstanding, with all previously recorded provider, cross-tab and in-memory-draft limitations unchanged. Separately authorized real-application Browser QA follows only a subsequent independent Review PASS.

## Independent R5 re-review — 10 November 2026

**Overall independent Review: PASS. Status remains IN_REVIEW. R5 resolved; no new actionable finding or directly caused regression found.** This incorporates the preceding independent scope assessment and resolved R1–R4 dispositions, plus the fresh verification below. It supersedes the earlier overall FAIL only as the current Review disposition; historical failures, implementation results and limitations remain intact. Browser QA and Done Check were not begun.

### R5 disposition and evidence

Inspected the actual current quote component and tests, the retained pre-fix/fix-only diff, parent quote refresh/status handling, record-draft reducer/hook and workspace departure registration. The fix guards recovery completions before either the parent callback, reducer receive or feedback changes. A later check immediately supersedes earlier reads; both explicit recovery choices and saved-record discard invalidate outstanding reads. Effect cleanup/setup invalidates the previous saved quote/project/supplier context and unmounted editor. Current read failures still reject to the departure checker, while obsolete failures return without restoring errors. This is bounded response validity handling, not a backend concurrency guarantee or write cancellation.

- **Original failing sequence freshly reproduced, now passing:** uncertain notes PATCH → two outstanding GETs → second returns revision 2 / `new saved server notes` → Use saved record → first returns revision 1 / `original`. The final editor still contains `new saved server notes`. Reused the exact retained independent acceptance probe against current application source; did not rewrite its historical failed report.
- **Older successes and failures:** fresh supplied regression cases and two additional independent probes cover newer-result-first and older-result-first ordering. An older completion is ignored even while the newest request remains outstanding. With the newest recovery conflict still unresolved, late successes/failures neither replace its saved baseline nor change the local draft, parent callback count or feedback. Accepting afterward uses the newest baseline.
- **Explicit choices:** fresh deterministic cases start a read after a recovery review already exists, then choose Use saved record or Keep my edits before its success/failure. Later typing survives, conflicts/uncertainty do not reopen, and stale failure feedback does not return. Keeping edits then explicitly discarding uses the newer saved baseline. A newer failed read followed by an older success retains the newer error and blocks saving pending recovery.
- **Editor lifetime/context:** fresh cases resolve and reject outstanding reads after quote replacement, project change and unmount; no obsolete parent callback or feedback occurs. Supplier identity is also part of the inspected invalidation dependency; per-supplier mounted cards retain their own sequence and drafts. Supplier switching is not treated as destroying a draft.
- **Uncertain-write contract / R2:** unchanged reads still require explicit saved-versus-draft review and never prove write failure. No recovery branch sends a write. Fresh cases assert one original PATCH only, preserve failed-read retry, and recover an existing created quote ID for a subsequent deliberate PATCH rather than duplicate creation.
- **R1, R3 and R4 preserved:** fresh prior independent probes and focused suites retain clarification 1000 submitted / 2000 typed recovery with approval blocked; dashboard explicit departure and request retention without duplicate POST; and collapsed material conflict/uncertainty summaries with optional omissions quiet and original evidence retained. The R5 production diff changes only quote recovery validity, choice/discard wiring and guarded error reporting. No unrelated design decision was reopened.

### Fresh verification versus retained results

All checks used installed dependencies and isolated component responses; no application data was operated on. Deferred promises explicitly control response order rather than relying on network timing.

| Fresh check | Result / local evidence |
| --- | --- |
| Focused regression suites | **100/100 passed**, six files: quote-review (49), brief-editor (18), project-dashboard (9), workspace-drafts, record-draft and record-save-status. `.local-investigation-artifacts/UX-U1/independent-r5-targeted-2026-11-10.json` |
| Previous independent probes, unchanged source | **5/5 passed**, including the formerly failing R5 assertion and R1–R4 probes. New report: `.local-investigation-artifacts/UX-U1/independent-r5-original-probes-2026-11-10.json`; original probe source/config and earlier failed report remain in `independent-rereview-2026-11-10/`. |
| Additional independent ordering probes | **2/2 passed**, success/failure variants testing supersession before the newer result and preservation of an unresolved newer conflict. Source/config/report in `.local-investigation-artifacts/UX-U1/independent-r5-extra-2026-11-10/`. |
| Static checks | `pnpm exec tsc --noEmit --incremental false` and focused ESLint on quote-review.tsx / quote-review.test.tsx passed. |
| Scope/whitespace | `git diff --check` passed (line-ending advisory warnings only); backend/protected-specification and staged diffs empty. Only this unit document and ignored independent review evidence were written by this review. |

The implementer's **270/270 full frontend run**, full lint, pre-fix failing tests and hash inventory remain **retained evidence**, not fresh results from this review. The earlier broad independent review, full-suite results, production builds, selected backend checks and browser implementation checks likewise remain historical. No full review, full frontend suite, production build, backend/E2E suite, live-provider call or manual accessibility session was repeated here. Component mocks establish handler/reconciliation behavior, not browser integration or durable server ordering.

### Concrete handoff — real-application Browser QA remains next

Proceed only as a separately requested Browser QA task; keep IN_REVIEW until that task starts. Do not perform Done Check or commit from this Review PASS.

1. Use the documented real Next.js/FastAPI/isolated PostgreSQL setup in `docs/local-development.md`, synthetic projects and existing test-only model fixtures. Preserve the active user's projects/drafts. Coordinate a maintenance window or isolated checkout/output before production build: the default Playwright configuration builds into the application's normal output, which previously interfered with the development server. Use separate test databases/storage and one E2E worker, with no live-provider reliability claim.
2. Complete a **fresh final production build and integrated regression run**. `pnpm test:e2e` covers the golden path and targeted suite; explicitly run `pnpm --filter @sourcepilot/web exec playwright test ux-u1.spec.ts --workers=1 --retries=0` as well, because the root E2E wrapper does not include that file. Run the existing relevant backend project/workflow, Brief, supplier, manual/PDF quote and preference contract tests on the isolated test database. Record commands, source state, pass/fail counts, screenshots/traces and limitations; prior results do not satisfy these final-source checks.
3. In the actual application, replay R1 typing during a delayed save; R2 unchanged/failed recovery reads; **R5 two controlled outstanding recovery GETs with second-first completion, both choices, late success/failure, new typing, quote/project replacement and departure**; R3 uncertain creation followed by project/header navigation, Stay and explicit Leave anyway; and R4 closed Terms/Compliance/Other summaries. Use controlled interception/delays around real application requests where needed, label injected responses, inspect network writes and reread saved records. Verify no automatic PATCH/POST, implicit confirmation or assumption that an unchanged read proves failure. Include shared workspace Check saved state, not just the quote-local button.
4. Cover the affected navigation/draft/provenance flows: all five stages, supplier switches, Back/Forward and next-action focus, native reload/tab-close warnings, failed refresh retention, original PDF/extraction versus corrected current values, explicit saved-value approvals and unchanged Decision freedom. Keep record recovery and integrated persistence evidence distinct from simulated fault injection.
5. **Manual accessibility remains required:** keyboard-only disclosure/dialog operation, initial Stay focus, focus trap/Escape/return, recovery choice focus, validation/error focus and meaningful screen-reader status/error announcements without polling chatter. Inspect saved/edit/recovery/approval states at 320/390/768/1024/1440 CSS pixels, actual desktop 400% zoom, narrow/short viewports, evidence pane/sheet, visible focus, non-color statuses and reduced motion. Run automated accessibility scans as supporting evidence, not a substitute for manual coverage or a conformance claim.

**Five-participant usability acceptance is separate and pending:** five unfamiliar participants, at least 4/5 completing each specified task without procedural help, and zero specified unnoticed-data-loss, accidental-approval or provenance-misinterpretation incidents. No sessions or results are inferred from Review PASS or later technical QA. Checkpoint 4 acceptance and Done Check remain incomplete until their required gates are satisfied. Existing in-memory draft lifetime, cross-tab check/submit limitations, writes that may complete after a read/departure, historical provider failures, bounded supplemental results and pending human reviews remain unchanged. No dependency installation, application-code modification, staging, commit or deployment occurred.


## Browser QA — 10 November 2026 (Asia/Manila)

**Browser QA: FAIL. Lifecycle remains QA.** Independent Review PASS from the 10 November R5 re-review is confirmed and preserved, including its preceding FAIL reports and all limitations. This QA adds two P2 keyboard-focus findings. No application fix was made. Build and integrated regressions pass; accessibility acceptance fails and spoken screen-reader verification is incomplete. Five-participant usability acceptance remains a separate, incomplete human requirement. Done Check was not repeated.

### Source, isolation and evidence identity

- Git HEAD: `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`, with the existing uncommitted UX-U1 implementation/amendments. HEAD alone does not identify the tested source. `source-hashes.json` records SHA-256 for every copied tracked/nonignored file; `head.txt` and `status-before.txt` record the initial state.
- Evidence root: `.local-investigation-artifacts/UX-U1/browser-qa-2026-11-10/` (ignored). All new probes, reports, screenshots, profiles, traces, build output and test storage are inside this root. Existing evidence was not overwritten. Raw local traces may contain test-session cookies and are not publication artifacts.
- A byte-matched source copy in `source/` was built and tested, using junctions to already-installed dependencies. No dependency was installed. `source-verification.json` confirms no copied original file changed and only `docs/implementation/UX-U1.md` changed in the original tree during QA. Added QA-only test/config files exist solely in the ignored copy and are not proposed application changes.
- Personal servers on 3000/8000 were left running. QA used 13000/18000; final listener inspection confirmed both QA listeners stopped and personal listeners remained. The ordinary runner's `.next` output was confined to the source copy, avoiding the known development/build interference.
- Inspected `docs/local-development.md`, Playwright config/wrapper/helpers, deterministic server/model boundary, database guards and pytest fixtures before starting services. Existing local PostgreSQL databases `sourcepilot`, `sourcepilot_test`, `sourcepilot_e2e` were verified. Only guarded `sourcepilot_e2e` reset/seed operations and separate `sourcepilot_test` pytest resets occurred. No personal/demo project data was changed. Model fixtures, real FastAPI, PostgreSQL and existing PDF fixtures were used; no live-provider call or deployment occurred.
- Pinned prototype sources remain unchanged. Visual assessment used the blue/light/charcoal design plus the explicitly approved later palette, mobile native selector, supplier, header and status amendments in this unit record. The prototype did not substitute for application testing.

### Fresh results

| Check | Disposition and evidence |
| --- | --- |
| Final production build | **PASS.** `pnpm test:e2e` built the isolated final application source for golden and targeted runs; the explicit UX command built it again. `integrated.log`, `ux-browser.log` contain successful optimized compilation, lint/type validation, static generation and production startup. Next.js warned about nested workspace lockfiles; output still stayed in the isolated copy. No source or build configuration change was used to suppress it. |
| Five-stage golden path | **1/1 PASS**, real frontend/API/database/PDF pipeline, three explicitly confirmed quotes, factual comparison, deterministic no-suggestion advice, human preference persistence and dashboard reload. Trace verification helper also passed. `integrated.log`, `source/apps/web/e2e-logs/golden.log`. |
| Integrated targeted scenarios | **14/14 PASS.** Correction/original provenance, failed-PDF manual fallback, abandoned-processing retry, supplier and comparison/advice staleness, session isolation/expiry, pending analysis return, request rejection and real proxy/socket recovery. `integrated.log`, `source/apps/web/e2e-logs/targeted.log`. |
| Frontend regression suite | **270/270 PASS**, `frontend.json`, `frontend.log`. |
| Relevant backend contracts | **238/238 PASS**, 670.42 seconds, one third-party Starlette/httpx deprecation warning; `backend.xml`, `backend.log`. Projects/workflow, Brief persistence/workflow, supplier review/catalog, manual/PDF quotes and preference contracts. Not a claim of a fresh full backend suite. |
| Explicit UX-U1 browser suite | **1/1 PASS**, `ux-browser.log`, `ux-results/`, `ux-report/`. One visible stage, retained quote/Decision drafts, Back navigation, guarded departure, native history warning, evidence sheet, review dialogs and responsiveness. |
| R1–R5 additional browser probes | **8/8 PASS**, `recovery-results.json` is the verified 8-test report; `recovery-verified.log`, `recovery-verified/`. Probe source: `source/apps/web/e2e/qa-recovery.spec.ts`. Fault injection is identified below; it is not a claim about backend concurrency guarantees. |
| Decision freedom | **1/1 PASS**, `decision.log`, final `accessibility.json`. Browser selected Harbor, changed to Willow and cleared preference, rereading the real API after each operation, with zero quotes and no comparison/advice prerequisite. |
| Responsive and actual zoom | **PASS for exercised states.** Five stages at 320, 390, 768, 1024 and 1440 CSS pixels; no page overflow, one visible stage. Saved/editing/review/evidence captures retained. Actual installed Chrome default page zoom was 400%, not CSS scaling or only viewport emulation: separate profile, 1280px outer window, asserted DPR ≥3.9 and CSS viewport ≤330, six dashboard/stage captures without page overflow. Review dialogs additionally exercised at 1440/390/320; evidence at 390×500 in supporting check. Not physical-device testing or every state/width permutation. |
| Automated accessibility support | Ten stage/width axe scans reported zero violations, plus approval-review scans in the UX helper. **Not accessibility acceptance.** A separate keyboard evidence-sheet/short-viewport/reduced-motion check passed (`accessibility-validation.json`, `accessibility-verified.log`). |
| Manual keyboard/accessibility | **FAIL: QA-1 below.** Verified visible skip-link focus; creation trap/Escape/return; native required-field focus; stage heading focus and hidden-stage exclusion; Back/draft retention; departure initial Stay/trap/Escape/return; Brief review disclosure/Escape/return; shortlist named scroll region and keyboard exit; quote confirmation cancellation/return; evidence sheet initial focus/trap/Escape/return. Manual inspection used the real isolated application, not mocked page markup. |
| Recovery focus and native warnings | **FAIL: QA-2 below.** Native reload and tab-close warnings were observed and dismissed with the draft retained before the failing recovery-focus assertion. `recovery-focus.json`, `recovery-focus.log`, `recovery-focus-results/`. |
| Spoken screen-reader announcements | **INCOMPLETE.** Accessibility-tree and DOM `role=status`/`role=alert` inspection is supporting evidence only. No audio-capable screen-reader session was available through the used QA interface, so announcement wording/timing, duplicate announcements/polling chatter and complete screen-reader traversal were not certified. |
| Five unfamiliar participants | **INCOMPLETE, human-run.** No participants contacted and no results inferred. Existing threshold remains ≥4/5 completing each task and zero specified unnoticed-data-loss, accidental-approval or provenance-misinterpretation incidents. |

### Findings (application code unchanged)

**QA-1 — P2: Brief server validation does not move focus to the error or associate it with the field.**

Reproduction: create an isolated project → Brief → Add requirement → leave Material selected → put three spaces in Value → Save Brief. Native required validation accepts nonempty whitespace; the real API rejects it with `Requirement 1: value must not be blank`. The draft remains intact, but the disabled/re-enabled submit loses focus to BODY. The alert is above the form and offscreen (manual capture measured its top at approximately −637px). It has no focus target, and the Value field has neither `aria-invalid` nor `aria-describedby` linking the error. A keyboard user at the bottom sees only generic save failure and must search backwards for the actual problem. A genuinely empty Value does correctly trigger native validation and focus, so this finding concerns server-returned field errors.

Affected requirement: UX-U1 Responsive accessibility, “Focus validation summary after explicit failed submit,” labels/error links, and the Browser QA handoff's validation/error focus requirement. Relevant production code: `apps/web/components/brief-editor.tsx`, save catch/fieldErrors handling around lines 262–273 and alert rendering around 449–452. Severity is P2 because recovery is possible and no draft loss/implicit approval was observed; this still fails the approved QA criterion.

Evidence: manually reproduced in the in-app browser; independently reproduced by the real browser/API probe in `source/apps/web/e2e/qa-accessibility.spec.ts`. `accessibility-validation.json` contains the failing acceptance assertion (not a passing defect test), `validation-focus` attachment and `accessibility-verified/.../validation-error-offscreen.png`. Recommended bounded correction: focus a programmatically focusable error summary after rejected submission and associate affected fields with their errors while retaining drafts. Implementation requires a separate fix task.

**QA-2 — P2: Quote recovery choice removes keyboard focus.**

Reproduction: upload the existing Harbor PDF in an isolated approved-shortlist project → Edit PDF draft → change Quote notes → inject connection failure for that PATCH → Check saved quote against the unchanged real saved record → focus Use saved record and press Enter. The recovery section disappears and `document.activeElement` becomes BODY, with no usable editor target focused. The same run first verified native reload and tab-close warnings and retained the draft on dismissal. No replayed write or persisted-value corruption was observed.

Affected requirement: UX-U1 handoff “recovery choice focus” and visible keyboard focus/continuation. Relevant code: `apps/web/components/quote-review.tsx` around `acceptSavedRecord` (173–177) and shared `DraftConflict` in `record-save-status.tsx` (16–26). Evidence: `recovery-focus.json`, `recovery-focus.log`, `recovery-focus-results/`, retained failing acceptance assertion. This finding is specifically verified for Use saved record; do not infer a tested Keep my edits focus result. Recommended bounded correction: deliberately return focus to the retained editor or a meaningful recovery outcome target after removing the choice UI, and test both choices.

### R1–R5 and workflow coverage detail

- **R1:** delayed delivery-clarification PATCH used `route.fetch()` to perform a real write, withheld its response while a later answer was typed, then released it. The submitted date was reread from the database; later text stayed in Unsaved clarification answers across stage switches, approval stayed blocked, and only one PATCH occurred. Historical component quantity-1000/2000 cases remain retained evidence rather than a fresh browser quantity replay.
- **R2:** injected failed PATCH, failed recovery GET, then unchanged saved GET. Save stayed blocked until explicit reconciliation; unchanged values did not claim the write failed. The draft stayed complete and checks sent no writes. Shared workspace Check saved state was exercised after its 10-second threshold and returned the same explicit record recovery. Failed reads remained retryable.
- **R3:** uncertain create with injected connection failure, Check saved projects, project-row and header navigation, initial Stay focus, retained request, explicit Leave anyway and one original POST only. Real projects used for navigation were synthetic.
- **R4:** actual PDF quote responses augmented in-browser with labeled synthetic Terms/Compliance/Other uncertainty/conflict values. Closed saved and editing summaries exposed affected fields. Original evidence and actual PDF extraction/persistence were independently checked by golden/targeted and manual evidence inspection. Injected conflicts were not written to the database.
- **R5:** two held recovery GETs completed second-first; both saved/keep choices; a further GET begun after recovery review but before the choice; late success and late failure for both older and post-review reads; later typing and supplier switching; parent saved-quote object replacement; departure/unmount with late response and return to actual saved state. No automatic retry/write occurred. Failed recovery followed by unchanged recovery was fresh browser evidence. The additional newest-failure/older-success, identity-replacement and all prior-context permutations from independent component review remain retained; this browser set is not an exhaustive replay of every component permutation.
- Navigation/history, native reload/tab-close dismissal, next-stage heading focus, manual approval review/cancellation, provenance 4.60 original versus corrected current values, unknown/conflict meanings, stale guidance, optional advice, and freely changeable preference were exercised across the suites/manual checks above. No approval or human preference was inferred from stage navigation or advice.
- Visual inspection of fresh captures covered wide Brief, 1024 Suppliers, 768 Decision, 390 quote editing, 320 stacked comparison, desktop evidence and 400% reflow, plus manual phone dialogs. Light canvas/white surfaces, blue actions/selection, charcoal/ink text, amber attention, full labels and original/current/draft distinctions match the approved amended design. No additional visual defect was verified in these captures.

### Exact execution record

Paths below are relative to the evidence root. CWD for root commands was `source`; for web commands `source/apps/web`; for API commands `source/apps/api`. Log redirection stayed inside the evidence root. Installed tools were used without synchronization/installation.

E2E and persistent API environment (local Compose defaults, independently verified database names):

```powershell
$env:DATABASE_URL='postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/sourcepilot'
$env:TEST_DATABASE_URL='postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/sourcepilot_test'
$env:E2E_DATABASE_URL='postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/sourcepilot_e2e'
```

| CWD | Exact command (environment/storage details below) | Result |
| --- | --- | --- |
| source | `$env:UV_NO_SYNC='1'; pnpm test:e2e *> ../integrated.log` | exit 0; build + 1 golden + 14 targeted |
| source/apps/api | `uv run --no-sync pytest tests/test_projects.py tests/test_project_workflow.py tests/test_briefs.py tests/test_brief_workflow.py tests/test_supplier_review.py tests/test_suppliers.py tests/test_manual_quotes.py tests/test_pdf_quotes.py tests/test_preferred_supplier.py --junitxml=../../../backend.xml *> ../../../backend.log` | exit 0; 238 passed |
| source/apps/web | `pnpm exec vitest run --reporter=json --outputFile=../../../frontend.json *> ../../../frontend.log` | exit 0; 270 passed |
| source | `pnpm --filter @sourcepilot/web exec playwright test ux-u1.spec.ts --workers=1 --retries=0 --output=../../../ux-results *> ../ux-browser.log` | exit 0; 1 passed, fresh production build |
| source/apps/api | `uv run --no-sync python -m tests.e2e_support.server *> ../../../manual-api.log` | guarded reset/fixtures; stopped after QA |
| source/apps/web | `$env:API_ORIGIN='http://127.0.0.1:18000'; pnpm exec next start --hostname 127.0.0.1 --port 13000 *> ../../../manual-web.log` | served existing verified build; stopped after QA |
| source/apps/web | `pnpm exec playwright test --config=qa.config.ts --workers=1 --retries=0 *> ../../../recovery.log` | initial harness run: 2 passed, 6 locator failures |
| source/apps/web | `pnpm exec playwright test --config=qa.config.ts --grep 'saved with late success' --output=../../../recovery-diagnostic *> ../../../recovery-diagnostic.log` | diagnostic locator failure, retained |
| source/apps/web | `pnpm exec playwright test --config=qa.config.ts --output=../../../recovery-verified --workers=1 --retries=0 *> ../../../recovery-verified.log` | exit 0; 8 passed |
| source/apps/web | `pnpm exec playwright test --config=qa-accessibility.config.ts --workers=1 --retries=0 *> ../../../accessibility.log` | initial: alert-locator failure + 1 supporting pass |
| source/apps/web | `pnpm exec playwright test --config=qa-accessibility.config.ts --output=../../../accessibility-verified --workers=1 --retries=0 *> ../../../accessibility-verified.log` | 1 real acceptance failure QA-1 + 1 supporting pass |
| source/apps/web | `pnpm exec playwright test --config=qa-accessibility.config.ts --grep 'recovery choice keyboard' --output=../../../recovery-focus-results *> ../../../recovery-focus.log` | 1 real acceptance failure QA-2; earlier native-warning assertions passed |
| source/apps/web | `pnpm exec playwright test --config=qa-accessibility.config.ts --grep 'Decision remains' --output=../../../decision-results *> ../../../decision.log` | exit 0; 1 passed |

For the explicit UX run, `E2E_DOCUMENT_STORAGE_DIR="$PWD/../ux-storage"` and `PLAYWRIGHT_HTML_OUTPUT_DIR="$PWD/../ux-report"` were set in source-root CWD; storage directory created first. For the persistent API, `E2E_DOCUMENT_STORAGE_DIR="$PWD/../../../manual-storage"` was set in API CWD and created first. The root wrapper owns its temporary storage; its logs/reports are under the ignored source copy. The supplementary configs omit `webServer` and use the already-running isolated stack; they do not reset the database between probes. API/web processes received Ctrl+C after completion; neither test port remained listening.

Harness corrections only: initial recovery probes used exact `getByLabel` on controlled textareas (their label textContent included current text); changed to the textbox accessible role/name. R4 queries initially matched both mounted hidden/saved and visible editing summaries; scoped to `summary:visible`. Initial validation probe matched the framework route announcer as well as the Brief alert; scoped to `#brief`. Initial/diagnostic reports and logs are retained (`recovery-initial.*`, `recovery-diagnostic.*`, `accessibility-initial.*`). These setup failures are not application findings or acceptance passes. Final reports are explicitly named above.

Environment limitations: the design context engine could not initialize its external cache; existing context/design instructions were read directly, with no detector-install/clean-scan claim. Sandboxed native process inventory/browser launch was unavailable; authorized service runs used reviewed execution access, and manual UI checks used the in-app browser. Initial manual analysis used a nonexact synthetic request and failed the strict fixture; the later exact fixture worked. In-app date fill did not submit an answer; manual review continued with the supported Period entry, while actual date saving passed in Playwright/R1 and golden checks. Neither tool/fixture limitation is reported as an application defect. Prior lint/type/component/full-review/provider results remain historical unless freshly listed above.

### Remaining steps — stop at QA

1. Separately authorize bounded fixes for QA-1 and QA-2; preserve drafts, uncertainty semantics, approval boundaries and original evidence. Add meaningful keyboard-focus regressions for server field errors and both recovery choices, then independently review the fixes.
2. Rerun affected real-stack Browser QA on the corrected source, including the retained failing probes, recovery controls/field errors at narrow and zoomed sizes, and complete manual screen-reader status/error/recovery announcement and keyboard traversal checks. Do not convert this FAIL into PASS from component tests or clean axe scans alone. Retained component-only context permutations should be extended in-browser where needed for the changed paths.
3. Human owner runs the five-participant task pack and records actual acceptance. After the required technical and human gates pass, a separately authorized Done Check may follow; staging/commit remain later actions. No Done Check, staging, commit, deployment or next unit was performed in this task.


## P2 accessibility remediation — 10 November 2026

**IMPLEMENTING — corrections implemented; independent review pending.** This is the explicitly authorized implementation of Browser QA findings QA-1 and QA-2, not a new independent Review or Browser QA result. Per WORKFLOW.md's Implement action, remain IMPLEMENTING and stop before Review; the independent Review action sets IN_REVIEW. The historical **Browser QA FAIL** and preceding **independent Review PASS** above remain intact. Screen-reader validation and five-participant usability acceptance remain pending.

### Corrections and bounded scope

- **QA-1 / Brief server-validation errors (P2):** Explicit failed saves/answer submissions focus the visible error summary after pending state ends. Each specific server error is retained; known field paths link to the corresponding control and programmatically describe it with aria-invalid/aria-describedby. Links open enclosing details before focusing. Requirement errors resolve against submitted record identity; model-level errors describe related value controls. Drafts remain retained. Hidden stages and unrelated background refreshes do not trigger focus stealing.
- **QA-2 / Use saved record focus recovery (P2):** Explicit saved-record/keep-edits recovery focuses the affected supplier heading, falling back to the named editor when the heading is unavailable, and scrolls the target into view. A persistent status region announces the result. Existing R5 request-sequence invalidation and saved/draft semantics are unchanged.
- Files: `apps/web/components/brief-editor.tsx`, `quote-review.tsx`, their two component test files, new `apps/web/lib/editor-focus.ts`, and new `apps/web/e2e/ux-u1-accessibility.spec.ts`. No backend/contract, CSS redesign, prototype, dependency or protected specification edit. Other pre-existing working-tree changes are not part of this remediation.

### Implementation verification (fresh, not independent acceptance)

- Regression red evidence before application edits: **67 passed / 4 newly added cases failed**. Final focused component/shared draft checks: **96/96 passed**, including five new cases and existing R5 assertions. Tests cover server-message associations, collapsed field reveal, hidden stage/draft retention, keyboard recovery for both choices, unavailable heading fallback and later background updates.
- Final affected-file lint and full frontend TypeScript: **exit 0**. Production build in isolated source copy: **passed**. `git diff --check`: **exit 0**; no staged changes.
- Real frontend/FastAPI/PostgreSQL keyboard regressions: **6/6 passed** at **320, 390 and 1440 px**. Enter/Tab checks verify focus, viewport visibility, outline, linked field description, retained draft, recovery announcement markup and no extra write. Existing deterministic fixtures and guarded `sourcepilot_e2e` database only; no live providers or personal/demo data changes.
- Fresh re-execution of the retained R1–R5 browser probes: **8/8 passed**, including overlapping saved/keep recoveries with late success/failure. These pass counts are implementation regression checks, not a new Browser QA PASS.
- Evidence: `.local-investigation-artifacts/UX-U1/a11y-fix-2026-11-10/REPORT.md`, `before-tests.json`, `affected-final.json`, `browser.log`, `browser-verified.log`, `browser-verified-results/`, `remediation.diff`, `source-hashes.json`, `verification.json`. Report records commands, isolated source identity, limitations and failed harness attempts. HEAD remains `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`; hashes identify the uncommitted tested source.
- Two initial phone tests stopped during existing helper setup before reaching recovery; the new tests now set up the quote first and switch width before exercising recovery. All assertions retained; final six tests pass. A duplicate-server config attempt and initial output-path failures are retained in the report, not counted as passing runs.
- Fresh keyboard checks are browser automation plus inspection of captured focus states, **not spoken screen-reader validation**. No fresh 400% zoom or 768/1024 sweep, full golden/targeted, full backend/frontend suite, or participant acceptance is claimed. Previous evidence remains historical. QA-owned services stopped after execution.

### Focused independent-review handoff

Inspect only this delta against the original QA-1/QA-2 reproductions and evidence. Review submission-only focus timing, field/error identity mapping, collapsed disclosure reveal, unavailable/hidden targets, status-announcement semantics, responsive focus visibility, and unchanged R5 request-order protections. `remediation.diff` and `before/` isolate this work from the earlier uncommitted UX-U1 implementation. The original Review PASS covers the earlier source, not these changes.

**Remaining steps:** (1) independent Review sets IN_REVIEW and records its own result; (2) after review acceptance and authorization, focused Browser QA rechecks both findings and impacted accessibility behavior; (3) complete actual screen-reader validation and separately human-run five-participant acceptance. Historical Browser QA remains FAIL until a separately documented recheck supersedes it. No participants contacted. Stop here: no Done Check, staging, commit, deployment or next unit.

## Independent focused accessibility review — 10 November 2026

**Focused Review: PASS. Status remains IN_REVIEW. QA-1 and QA-2 are resolved for the reported failures; no new actionable defect was found in the remediation or directly affected regressions.** This is independent review of the two corrections, not a Browser QA result or Done Check. The historical independent R5 **Review PASS** and **Browser QA FAIL** above are preserved. Spoken screen-reader validation and five-participant usability acceptance remain incomplete.

### Findings and dispositions

| Finding | Independent disposition and evidence |
| --- | --- |
| **QA-1 — P2, Brief server-validation focus/association** | **Resolved.** Freshly repeated the original real-API reproduction: new synthetic project → Add requirement → Material Value containing three spaces → Save Brief. The specific `Requirement 1: value must not be blank` error receives focus in the visible, outlined summary. Tab reaches its link; Enter focuses the retained Value control, which has `aria-invalid=true` and the specific error as its accessible description. All three spaces remain. Both the original retained acceptance probe and stronger current regression pass. Fresh real-API supplemental coverage also rejects whitespace in an informational Context, opens its previously collapsed Additional context disclosure through the error link, and focuses/describes the retained field at 390×500. A held rejected PATCH completed while Decision was active leaves Decision heading focus intact; returning to Brief focuses Sourcing Brief, not the old error. |
| **QA-2 — P2, Use saved record loses focus** | **Resolved.** Freshly repeated the original PDF/notes/failed-PATCH/unchanged-GET sequence, including dismissal of native reload and tab-close warnings. Enter on Use saved record removes the recovery choices and focuses the retained supplier heading with a visible outline. The saved notes are restored, a persistent `role=status` region contains `Saved record loaded. Review the quote before making further changes.`, and Tab continues within the editor. No recovery write is sent. Both recovery choices, heading-unavailable named-editor fallback, and a later ordinary saved-record refresh pass the fresh component regressions. Announcement markup/content is verified; actual spoken output is not. |
| **R5 protection and affected regressions** | **Preserved.** The correction wraps, rather than replaces, `acceptSavedRecord`/`keepDraft`; both still invalidate outstanding reads before reconciliation. Request-order checks still precede parent callbacks, draft updates and failure feedback; context changes/unmount still invalidate older requests. Fresh component cases cover newer failure/older success, quote/project replacement, unmount, unchanged/failed reads and no replay. Fresh real-app probes cover two overlapping GETs, second-first completion, another GET started after review appears, saved/keep choices and late success/failure. Added review-only assertions confirm heading focus immediately after the choice, unchanged recovery status after obsolete responses, and continued focus in the subsequently edited notes. Drafts, resolved recovery state and write counts remain correct. Supplier switching and shared departure recovery also pass. |

Inspected the actual four-file before/current delta, the new focus helper and browser regression, original QA probes/reports, red/green implementation evidence, shared draft reducer/hook, recovery registration and focus styles. Brief focus is keyed to an explicit failed submission and consumed after pending state ends; background changes do not retrigger it. Requirement errors resolve submitted identity against current draft identity; model-level errors describe related value controls, and links reveal ancestor disclosures before focusing. Unknown/unavailable targets retain summary text/fallback rather than focusing another record. The shared helper rejects disconnected, hidden, inert and CSS-hidden targets. Quote focus depends on an explicit recovery result, not reads or polling. No backend rule, approval gate, evidence value, dependency or prototype change is part of this delta; no authority conflict found.

### Fresh verification and evidence identity

Local ignored evidence root: `.local-investigation-artifacts/UX-U1/a11y-review-2026-11-10/`. Reports are review evidence, not release artifacts; raw traces may contain synthetic test-session cookies.

| Fresh check | Result and boundary |
| --- | --- |
| Focused component/shared draft regressions | **96/96 passed**, five files: Brief, Quotes, record-save-status, workspace-drafts and record-draft. `components.json`, `components.log`. |
| Production build | **Passed**, including build lint/type validation and static generation. Rebuilt the isolated implementation source copy; SHA-256 comparison of all **295** current web/API/package files found zero differences before testing (`source-identity.json`). HEAD remains `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`; hashes, not HEAD alone, identify this uncommitted source. |
| Original Browser QA probes | **4/4 passed** freshly: both original defect reproductions, Decision freedom and evidence-sheet keyboard/short-viewport supporting check. Original probe source copied unchanged; prior failed reports remain untouched. |
| R1–R5 browser probes | **8/8 passed** freshly, with additional focus/status assertions in the review-only R5 copy. Real persistence is distinguished from injected PATCH failures and controlled GET responses. |
| Responsive focus regressions | **10/10 passed**: Brief summary/link/field and saved-quote recovery at **320, 390, 768, 1024 and 1440 CSS px**, height 900. Asserted focused target bounds, visible outline, retained data, descriptions and no extra PATCH. Inspected fresh summary/recovery captures across phone/tablet/desktop and the 390×500 Context capture. |
| Additional independent real-app probe | **1/1 passed** on rerun: collapsed Context reveal plus hidden-stage failed-response focus preservation. `supplemental.json`, `supplemental.log`, `supplemental-results/`. |
| Scope/reference | `git diff --check` passed; staged diff empty. All four pinned prototype hashes match. Only this unit record and ignored review evidence were authored; no application fix, installation, staging, commit or deployment. |

Execution: from repository root, `pnpm --filter @sourcepilot/web exec vitest run components/brief-editor.test.tsx components/quote-review.test.tsx components/record-save-status.test.tsx components/workspace-drafts.test.tsx lib/record-draft.test.ts --reporter=json --outputFile=<evidence-root>/components.json`. Browser command: `pnpm --dir .local-investigation-artifacts/UX-U1/a11y-fix-2026-11-10/source/apps/web exec playwright test -c <evidence-root>/review.config.ts --workers=1 --retries=0 --output=<evidence-root>/results`. Supplemental rerun uses `supplemental.config.ts independent.spec.ts` and `supplemental-results`. Configs/probes are retained in the evidence root. The supplemental config serves the identical fresh build without rebuilding.

Both runs used the existing guarded API test runner, real FastAPI/PostgreSQL and deterministic model/PDF fixtures; explicit local Compose URLs identify separate `sourcepilot`, `sourcepilot_test` and disposable `sourcepilot_e2e` databases. Only the guarded E2E database was reset; document storage is `<evidence-root>/storage`. Services use 13000/18000 and the isolated copy's build output, leaving personal application ports/drafts alone. No live provider was invoked.

Final verification found no changed application file among the 295 compared paths and no listener on either review port after runner exit (`final-verification.json`).

Non-acceptance attempts are retained: `browser.log` stopped before tests because the Python launcher could not persist its cache; reviewed execution access allowed the run. `browser-verified.log` / `browser.json` record **22 passes and one review-harness locator failure**, not a clean 23/23 run. The supplemental probe expected a heading named Brief instead of the actual Sourcing Brief after returning to the stage; its preceding error/hidden-focus assertions passed. Corrected only that review locator and reran successfully, preserving the first report/trace. Context/detector initialization was unavailable; existing design context was read directly, with no installation or clean-detector claim.

**Retained, not freshly repeated here:** implementation red 67-pass/4-fail and green 96/96 evidence; prior full frontend/backend/golden/targeted/axe results; prior actual 400% browser zoom; and earlier broader independent review. This review does not claim fresh full-suite, physical-device, zoom or assistive-technology acceptance. Keyboard automation and visual inspection do not complete screen-reader validation.

### Precise handoff — separately requested Browser QA recheck

1. Use the corrected, hash-identified real application with isolated build/storage and the guarded test database. Replay QA-1 and QA-2 exactly as above; retain both original acceptance assertions and the stronger `ux-u1-accessibility.spec.ts` checks. Record a separate Browser QA disposition; do not silently overwrite the historical FAIL.
2. Recheck multiple/specific Brief errors, keyboard summary links, collapsed fields, retained edits/answers, and hidden-stage delayed failure. Verify native empty-field validation still works and ordinary refreshes never move focus. For quotes, check saved/keep choices, fallback target, next Tab position, repeated recovery, supplier switching, and R5 older/post-review late success/failure while typing, with no extra write or resurrected conflict/error.
3. Recheck affected error/recovery states at 320/390/768/1024/1440, short viewports and **actual desktop 400% browser zoom**. The five-width checks above are fresh; prior zoom evidence is historical. Include visible unobscured focus, wrapping, scrolling, disclosure/evidence-sheet Escape/return and native departure warnings.
4. **Complete actual screen-reader checks**, recording browser/reader/version and observed speech: failed-submit summary and specific errors announced coherently; each link opens and names/describes the correct invalid field; both recovery outcomes are spoken once and keyboard continuation is meaningful. Check repeated recovery, delayed responses, ordinary refresh/polling and stage changes for missing, duplicate or stale announcements. Traverse relevant disclosures/dialogs and verify focus return. DOM roles, accessible descriptions, screenshots and keyboard assertions alone cannot pass these checks.
5. Five unfamiliar participants remain a **separate pending human acceptance gate**: at least 4/5 complete each defined task, with zero specified unnoticed-data-loss, accidental-approval or provenance-misinterpretation incidents. No participants were contacted and no results inferred. Do not perform Done Check from this review.

**Stopped after review.** Historical Browser QA remains FAIL pending its separately documented recheck; no lifecycle advancement beyond IN_REVIEW, Done Check, stage, commit, deployment or next unit.

## Authorized Browser QA recheck — 10 November 2026

**Browser QA: INCOMPLETE. Lifecycle: QA.** The human authorized this recheck after the latest focused **Review PASS**, which was confirmed before execution. Both original reported defects now pass their focused real-application checks. This is not an overall Browser QA PASS: actual screen-reader interoperability and fresh actual desktop 400% zoom remain unverified. The historical Browser QA FAIL, remediation results and independent review results above remain intact. No new application defect was established by the completed checks.

### Source identity and isolated execution

Evidence root: `.local-investigation-artifacts/UX-U1/browser-recheck-2026-11-10/`. HEAD remains `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`; HEAD alone does not identify the uncommitted implementation. `source-identity.json` compares SHA-256 for all **295** web/API/package paths from the focused review against both current source and the existing isolated copy: all match. `final-verification.json` confirms no change among those paths after execution, 23 expected passes, zero failures/skips/flaky tests, and no staged changes. No application code or test source in the application was edited during QA.

Reused the identical reviewed production build in `a11y-fix-2026-11-10/source`, existing dependency junctions, real FastAPI and guarded disposable `sourcepilot_e2e` PostgreSQL database. Explicit separate local Compose identities for `sourcepilot` and `sourcepilot_test` were supplied to the database guard; only the guarded E2E database was reset. Storage is this run's `storage/`. Existing deterministic model and PDF fixtures only; no live provider. Frontend/API run on loopback ports 13000/18000. The integrated browser initially had no session projects, so the authorized synthetic project **UX-U1 Browser QA recheck** was created with the exact existing scenario request: project `1c5e973b-386d-4def-9217-761f5848b1c2`. Its deliberately invalid Brief drafts remain in the open integrated-browser tab.

Services were started separately using `uv run --no-sync python -m tests.e2e_support.server` in copied `apps/api` and `pnpm exec next start --hostname 127.0.0.1 --port 13000` in copied `apps/web`, with `API_ORIGIN=http://127.0.0.1:18000`. Initial restricted API cache persistence failed and the restricted frontend was unreachable from the integrated browser; those processes were stopped and the same commands succeeded with reviewed execution access. These are environment limitations, not application failures. The isolated services are intentionally left running for the user's requested open project; no personal application service was changed.

Fresh browser command from repository root: `pnpm --dir .local-investigation-artifacts/UX-U1/a11y-fix-2026-11-10/source/apps/web exec playwright test -c <evidence-root>/qa.config.ts --workers=1 --retries=0 --output=<evidence-root>/results`. Config disables automatic server startup and uses the already-running isolated stack. Review probes were copied into this run's `e2e/`; original reports were not overwritten. Results: `browser.log`, `browser.json`, `results/`; **23/23 passed in 2.8 minutes**.

### Fresh checks and original-finding disposition

| Check | Result and evidence boundary |
| --- | --- |
| **QA-1: Brief server validation** | **Original finding resolved in browser recheck.** Original three-space Material Value reproduction passes, as do stronger visible-summary/link/field checks at 320, 390, 768, 1024 and 1440 CSS px. In the integrated browser, Enter on Save Brief focuses the outlined visible summary; Tab/Enter focuses the retained invalid field. Two invalid requirements produce separate specific messages and links to the correct respective controls; both retain all three spaces and have `aria-invalid=true` plus their matching `aria-describedby` text. Empty newly added Value produces native `Please fill out this field` with focus on that field. These are real server/native errors, not injected validation responses. |
| Collapsed fields, draft retention and unrelated focus | Fresh supplemental real-stack probe passes collapsed Context reveal at 390×500 and held real rejected PATCH completion while Decision is active: Decision focus remains, returning to Brief focuses its heading, and Context draft remains. R1 retains later clarification typing. Integrated-browser stage switching retains both invalid requirements, focuses the selected stage heading, and excludes hidden Brief controls from its accessibility snapshot. Snapshot exclusion is not reader traversal acceptance. |
| **QA-2: Use saved record** | **Original finding resolved in browser recheck.** Original PDF/edit-notes/failed-PATCH/unchanged-GET reproduction passes, including dismissed native reload/close warnings. Enter on recovery focuses the visible outlined supplier heading, restores saved notes, populates persistent `Quote recovery` status with `Saved record loaded. Review the quote before making further changes.`, and next Tab remains within the editor. No additional PATCH. Stronger checks pass at all five widths; the fresh 320px capture was visually inspected and shows unobscured heading focus and wrapping outcome text. The failed PATCH is deliberately injected; saved data and PDF processing use the real stack. Actual speech is unverified. |
| R5 protections | Fresh saved/keep × late success/failure probes all pass. They cover overlapping GETs, newer-read-first completion and another GET after recovery review appears. Choice invalidates obsolete responses; later typing retains focus/data, resolved status remains unchanged, and no conflict/error is resurrected or write replayed. All eight retained R1–R5/shared-recovery probes pass. |
| Keyboard/responsive supporting checks | Four original probes, eight recovery probes, ten five-width focus checks and one supplemental check total 23 passes. Evidence-sheet keyboard containment, Escape/trigger return and 390×500 layout pass. Integrated browser additionally checks two-error summary at 320×500: no horizontal overflow, outlined focused summary entirely within the viewport (top 165.98, bottom 334.67), wrapped links, keyboard field recovery and stage return. Temporary viewport override reset. No physical-device claim. |

### Screen-reader and zoom limitations

**Actual screen-reader validation: INCOMPLETE; no reader interoperability PASS and no observed speech transcript.** Browser interactions used the Codex integrated browser. Before the user's final browser-only instruction, installed Windows Narrator binary version **10.0.26100.8972** was identified; a launch attempt returned no targetable window, and subsequent desktop inspection was stopped with Escape. No successful reader session, browser/reader pairing, or spoken result was established. No NVDA/JAWS operation was established. No software was installed. The user then explicitly restricted interactions to the integrated browser; work resumed using only its tab APIs, with no further desktop/reader control. Available integrated-browser tools expose screenshots, keyboard input and DOM/accessibility inspection, not observed reader speech. This is a tooling/scope limitation, not evidence that the application is reader-compatible or that Narrator is absent.

All actual reader checks remain pending: labels and invalid-state descriptions; coherent summary/specific-error announcement; each summary link naming/describing its field; both recovery outcomes (including repetition) spoken appropriately without duplicates; delayed responses/polling/stage changes avoiding stale or unrelated announcements; dialog entry, containment, Escape and focus return; and hidden-stage exclusion during reader traversal. Existing keyboard, roles, status text and accessibility snapshots do not satisfy these checks.

**Actual desktop 400% browser zoom: INCOMPLETE for corrected source.** Integrated-browser Ctrl+0 followed by eight Ctrl+plus inputs did not change measured viewport/device-pixel ratio (1280×720, DPR 1 before and after); no 400% result is claimed. The available browser capabilities offered viewport resizing but no browser-zoom control. Narrow viewport tests are recorded separately and are not substituted for zoom. Previous actual 400% evidence predates the accessibility fixes and remains historical.

### Reused evidence and remaining acceptance steps

The focused review's production build and 96/96 component/shared-draft results remain applicable to the byte-identical 295-path source, including fallback focus and ordinary-refresh protections. They were not rerun merely to add counts. Earlier full frontend/backend/golden/targeted and automated-accessibility evidence remains historical for unchanged broader behavior. The remediation touched Brief/quote focus, error associations and recovery announcements, so those earlier runs alone cannot establish current accessibility acceptance; fresh targeted real-stack probes cover those changed paths. Backend contracts, fixtures and business rules are unchanged. No fresh full-suite, axe, provider or usability result is inferred. `git diff --check` passed (line-ending warnings only).

1. Complete actual screen-reader validation on this source with an operational browser/reader pairing and observed speech, recording exact versions, outcomes and limitations for every pending scenario above. This requires a human-run session or separately permitted tooling beyond the current integrated-browser-only capability; do not install software without authorization.
2. Complete actual desktop 400% browser zoom on corrected Brief-error and quote-recovery states, including keyboard links, visible focus, wrapping/scrolling and short-viewport dialog return. Record actual zoom evidence separately from viewport resizing.
3. Record the resulting Browser QA disposition after those checks; any new defect needs reproduction, separately authorized remediation and affected recheck. Preserve this INCOMPLETE result and the original FAIL.
4. Human owner separately runs the five-unfamiliar-participant task pack: at least 4/5 complete each defined task, with zero specified unnoticed-data-loss, accidental-approval or provenance-misinterpretation incidents. **Pending; no participants contacted.**
5. Only after required technical and human acceptance passes may a separately authorized Done Check occur. No Done Check, staging, commit, deployment or next unit was performed. Stop at QA.

## Outstanding-check tooling assessment — 11 November 2026

**Lifecycle remains QA. Actual 400% browser zoom: INCOMPLETE. Actual screen-reader validation: INCOMPLETE. Overall technical Browser QA: INCOMPLETE.** No completed check was rerun. The original FAIL, focused Review PASS, passing QA-1/QA-2 rechecks and **23/23** focused regression results are preserved unchanged.

The human initially authorized native Chrome/Edge and an available Windows reader for these two outstanding checks. Tool inventory exposed only the integrated browser and MCP Apps as controllable browser providers. A native Chrome window was listed, but selecting it returned `Computer Use was not approved to use Google Chrome` before any input was sent. This was a desktop-control tool rejection, not an application defect or a failed zoom test. The human then explicitly reinstated **integrated-browser-only** interaction; no further native control was attempted. The existing project tab was confirmed present at `http://127.0.0.1:13000/projects/1c5e973b-386d-4def-9217-761f5848b1c2?stage=brief` and retained for the user.

### Fresh evidence and exact limitations

- Source: HEAD `40f9c29a35c629f5080ca53a2f4e8229820ee0a8` plus uncommitted UX-U1 source. Fresh SHA-256 comparisons of **295** web/API/package paths match both the prior recheck manifest and existing isolated build source. Evidence: `.local-investigation-artifacts/UX-U1/outstanding-checks-2026-11-11/source-identity.json`; `unit-before.md` preserves the complete preceding record. No application code changed, and no build/regression suite was rerun. Prior build and targeted evidence retain their previously documented scope.
- Zoom: no native browser was operated, no 400% setting was established, and no fresh zoomed viewport measurement exists. Integrated-browser capabilities expose viewport resizing, not page-zoom control; the preceding attempted zoom shortcuts produced no measured zoom change. Resizing or CSS zoom would not satisfy this gate. Browser/version at successful actual zoom: **not established**.
- Screen reader: no operational browser/reader pairing or observed speech was available. Current tool inventory has no usable system-audio/screen-reader-output capture for this text chat; the available screen-context tool is explicitly restricted to active voice chats and was not invoked. Screenshots and accessibility snapshots cannot establish speech output, duplicate/missing announcements or reader traversal. Narrator's previously identified installed version remains historical inventory, not a fresh reader result. No reader was launched in this attempt and no software installed.
- Restoration: **no browser zoom, viewport, accessibility, network or reader setting was changed in this attempt**, so no restoration action was needed. The existing test services/project were left as found. No new application defect was established; neither outstanding check earns PASS or FAIL from these tooling limits.

### Short user-assisted test script (pending execution)

Use the same isolated application and an authorized browser/reader setup that can access this project's existing anonymous session. Do not reset the database or substitute a newly empty session. If the project is inaccessible in another browser, stop and arrange an authorized test-session handoff rather than interpreting the access error as a UX defect. Record browser/reader versions and original zoom/reader settings first.

1. **Set actual page zoom:** use the browser's own Zoom control until it explicitly displays **400%**; retain a screenshot including that indicator. Record CSS viewport `window.innerWidth × window.innerHeight` and `window.devicePixelRatio` using a read-only browser inspection, plus window size. Do not use CSS zoom, emulation or viewport resizing. If the integrated browser cannot expose actual page zoom, leave this check pending until a supported browser session is authorized/available.
2. **Brief at 400%:** on the existing QA project's retained invalid requirements, activate Save Brief by keyboard. Confirm the outlined summary is visible and scrollable; Tab/Enter through both specific error links reaches the correct retained Value fields. Navigate between stages and back, confirming stage controls and focus remain usable without clipping or obstruction.
3. **Quote recovery and evidence at 400%:** use a prepared deterministic quote in the isolated environment. With a retained note edit and a controlled failed save, restore connectivity if altered, choose Check saved quote, then Use saved record by keyboard. Confirm visible supplier-heading focus, readable recovery feedback and meaningful next Tab. Repeat with Keep edits. Open source evidence; verify all content/actions can be reached, keyboard focus stays in the modal, and Escape returns to the evidence trigger. If this project lacks a prepared quote/recovery state, arrange that bounded fixture setup before the session; do not count an unexercised path as passed.
4. **Reader output:** with an available reader running, listen and record actual words/output for field labels, invalid states, failed-submit summary, both specific errors and their links. Verify each link names/describes its correct field. For both recovery choices, record the outcome announcement and focused supplier, including a repeated recovery; check for missing, duplicate or stale speech after delayed responses/ordinary refreshes. Traverse the evidence dialog and its return target. Navigate stages and confirm hidden-stage controls are absent from reader traversal. Do not infer any of this from DOM markup.
5. **Restore and report:** restore original page zoom, reader state and any temporary connectivity setting. Record restoration, each scenario's PASS/FAIL/incomplete, observed speech, screenshots/measurements and exact reproduction steps for defects. Preserve results even when a later retry passes.

Remaining acceptance: complete the two assisted checks above and append their supported technical Browser QA disposition; **five-participant usability acceptance remains separately pending** under the existing task pack and thresholds. No participants contacted, Done Check, staging, commit, deployment or another unit. No application fixes performed. Stop at QA.

## Native desktop retry — 11 November 2026

**Technical Browser QA remains INCOMPLETE; lifecycle QA.** This retry was explicitly authorized after the assisted-testing discussion. The historical FAIL, focused Review PASS, resolved original findings and 23/23 regression results remain unchanged. No regression suite was rerun.

Direct observations through desktop control:

- Native Google Chrome control succeeded on this attempt. Opened a separate tab at the exact existing isolated project URL: `http://127.0.0.1:13000/projects/1c5e973b-386d-4def-9217-761f5848b1c2?stage=brief`. The real application returned **Project not found in this demo session**. Chrome has a different anonymous session from the integrated browser; no session credentials were copied, access checks bypassed, project ownership changed or replacement project created.
- The Chrome menu initially showed **100%**. Native Ctrl+plus inputs produced **400%**, visibly confirmed in both the zoom popup and Chrome menu. This establishes that actual page zoom can now be operated, superseding the earlier tooling-only limitation. It does **not** pass the required application zoom scenarios: only the session-access error page was available. No CSS zoom or viewport emulation was used.
- Restored **100%** with Ctrl+0, confirmed the restored percentage in the native browser UI, and dismissed the menu. No accessibility/reader/network settings were changed. The new Chrome tab remains on the access-error page; the original integrated-browser project and isolated services were left intact.
- Installed Chrome executable version: **157.0.8103.38**. Native screenshots in the conversation show a 1720×1392 captured window; this is a screenshot dimension, **not a measured CSS viewport**. CSS viewport and DPR were not captured; no measurement is inferred from the screenshot or zoom factor.
- Screen-reader output remains unobservable through the available tools. No Narrator speech or user observations were obtained; no Narrator launch or accessibility-setting change was made during this retry. Installed Narrator availability is already recorded above. Reading UI Automation text does not establish spoken-reader interoperability.

Fresh source check: all **295** paths in `browser-recheck-2026-11-10/source-identity.json` still match their recorded SHA-256 values; HEAD remains `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`. No application code, dependency, test fixture or protected specification changed.

### Unchecked items and how to finish

1. **Prerequisite — native test-session access:** the existing project must become accessible in the browser used for testing through an authorized test-session setup. The URL alone does not transfer the anonymous session. Do not assess the access-error page as the sourcing workspace. If preserving the exact project is not feasible, a separately approved equivalent deterministic fixture in native Chrome is an alternative, but was not substituted here.
2. **400% application behavior — INCOMPLETE:** once access is established, set Chrome menu Zoom to 400%; record browser version, `innerWidth`, `innerHeight` and DPR using read-only inspection. Keyboard-test stage navigation, validation summary and both field links, saved/keep recovery choices and next Tab, evidence access, dialog containment/Escape/return and visible unobscured focus. Record failures with exact steps. Restore the original zoom afterward.
3. **Actual screen reader — INCOMPLETE:** on the accessible prepared test project, the human tester can start Narrator with Ctrl+Windows+Enter, then listen while navigating the same flows. Record the actual announced labels/errors, field-link destination and descriptions, both recovery outcomes, repeated/delayed-response announcements, dialog entry/return, and whether hidden-stage controls are encountered. Silence, markup and keyboard focus alone are not passes. Restore Narrator to its initial on/off state after testing.

No user-observed evidence was reported during this attempt. Overall technical QA cannot pass until both application checks above have observed results. Five-participant usability acceptance remains separate and pending. No Done Check, staging, commit, deployment, participant contact or next-unit work.

## Supplied Computer Use handoff recorded — 11 November 2026

**Historical session observations imported from the supplied 11 November handoff; these are not fresh integrated-browser verification. Lifecycle QA; overall technical Browser QA INCOMPLETE.** Preserve the original Browser QA FAIL, focused Review PASS, resolved QA-1/QA-2 rechecks and 23/23 focused regression results.

The subsequently authorized native session created **UX-U1 Native Chrome QA**, project `45a33f8c-1120-4fff-aaf3-21915189d58c`, in the same isolated real application at `http://127.0.0.1:13000`. The test Brief and Harbor Pouch Works shortlist were approved and `harbor_primary.pdf` uploaded; the quote remained unconfirmed. Source identity reported in that session was HEAD `40f9c29a35c629f5080ca53a2f4e8229820ee0a8` plus reviewed uncommitted UX-U1 changes, with 295 application/package hashes unchanged. Chrome executable version previously recorded: 157.0.8103.38.

At actual Chrome page zoom visibly set to **400%**, Computer Use observed: the Brief server-error summary received visible focus and displayed “Requirement 4: value must not be blank”; Tab/Enter followed its link to the correct field; the Brief review dialog reflowed with visible keyboard focus and Escape returned focus to its trigger; supplier evidence remained accessible/readable; quote evidence opened in a responsive dialog with readable vertically scrollable content, visible close-button focus and Escape return to the evidence trigger. These are partial zoom observations, not a complete zoom gate PASS. No measured CSS viewport/DPR was captured.

Recovery preparation used temporary Chrome tab-level offline simulation to fail a real quote save. Connectivity was restored; Check saved quote produced the saved-versus-draft view (saved unit price 4.90 versus unsaved 4.60). The final 400% Use saved record interaction was not completed. Computer Use stopped because it could not confidently verify the current browser URL. Final zoom restoration was not confirmed; the user was asked to press Ctrl+0. The handoff did not establish a fresh R5 result or actual Narrator output. Existing R5 passes remain evidence within their original scope.

Actual screen-reader interoperability remains **INCOMPLETE**, with no observed speech or user-reported reader results. No code changes, completed-suite reruns, staging, commits, deployment, Done Check or participant contact occurred. Five-participant usability acceptance remains separately pending. This addendum records the observations omitted from the unit document when the native session was interrupted; subsequent agent-operated checks are restricted to the integrated browser.

## Fresh integrated-browser follow-up — 11 November 2026

**Lifecycle QA. Overall technical Browser QA: INCOMPLETE.** The preceding Computer Use observations are historical imported evidence; the following observations were directly performed in the integrated browser. No user-observed screen-reader results were supplied. Historical Browser QA FAIL, focused Review PASS, original QA-1/QA-2 passing rechecks and 23/23 focused regression results are preserved.

Source: HEAD `40f9c29a35c629f5080ca53a2f4e8229820ee0a8` plus the reviewed uncommitted UX-U1 changes. Fresh comparison of all 295 paths against `browser-recheck-2026-11-10/source-identity.json` found no application/package hash changes. Existing isolated production build and earlier integrated/focused regression evidence remain applicable within their original scope; no completed suites or build were rerun. Only this unit document was edited by this follow-up.

The stopped isolated services were restored using the existing build and deterministic API boundaries, retaining the existing database and document storage. The test server's database reset was suppressed for this process; its isolated-database validation remained enabled. No application code or fixtures were changed. The existing integrated project retained its invalid Brief drafts. Because it had no quote and native Chrome's project is in a separate anonymous session, a bounded integrated fixture was created through the real UI: **UX-U1 integrated recovery 11 November**, `http://127.0.0.1:13000/projects/fa1ed7f3-2e4b-4d7e-a5dc-69b2aedc1b9b?stage=quotes`. Brief and Harbor shortlist were approved solely for this test; a manual quote with quantity 2000, USD and saved unit price 4.90 was created and left unconfirmed.

### Observed results

| Check | Fresh direct evidence | Disposition |
| --- | --- | --- |
| Existing narrow-project stage navigation and retained draft | At the existing natural 319 × 1244 CSS viewport, DPR 1, changed Brief → Quotes → Brief using Stage selection. Quotes prerequisite appeared; destination headings received focus. Both invalid Brief values remained three spaces. No viewport or zoom setting was changed. | PASS for this bounded navigation/draft check; not zoom evidence |
| Use saved record recovery | At the integrated browser's natural 1280 × 720 CSS viewport, edited saved 4.90 to unsaved 4.60. Temporarily stopped only the isolated API, then clicked Save draft. Actual failed request produced retained draft, uncertain-save guidance and disabled further writes. Restarted the same API without resetting data. Check saved quote displayed saved 4.90 versus unsaved 4.60. Pressed Enter on Use saved record: 4.90 was restored, recovery controls disappeared, and focus moved to the Harbor Pouch Works H3. Screenshot and DOM observation showed the heading inside the viewport (x312, y346.09, width197.30, height27.30), with a visible solid 3px blue outline. Next Tab reached the Commercial disclosure with a visible outline. | PASS for visible focus, saved-value restoration and keyboard continuation |
| Recovery outcome feedback | Visible status read “Saved record loaded. Review the quote before making further changes.” No speech was captured or inferred. | PASS for visible feedback only; spoken announcement INCOMPLETE |
| Remaining stage navigation | Quotes → Comparison → Decision → Quotes focused each destination heading; Comparison displayed its unmet two-confirmed-quotes prerequisite and disabled generation. Return to Quotes retained 4.90 and the recovery feedback. No unintended approval or decision was made. | PASS for exercised navigation; not 400% or reader traversal evidence |

Recovery screenshot: `.local-investigation-artifacts/UX-U1/outstanding-checks-2026-11-11/integrated-recovery.jpg` (after returning to Quotes). The transient supplier-heading focus screenshot is in the conversation tool evidence. Existing R5 request-order tests remain 23/23 historical focused evidence; this bounded recovery does not claim a fresh delayed-response/R5 suite run. Keep-edits and other previously passing checks were not rerun without cause. No new application defect was observed in the exercised paths.

### Acceptance gaps and exact remaining steps

| Requirement | Evidence available | Exact missing observation | Completion needed |
| --- | --- | --- | --- |
| Actual 400% browser zoom | Historical native Chrome 157.0.8103.38 actual-400% observations above cover Brief errors/link, review-dialog return and supplier/quote evidence. Fresh integrated recovery and navigation pass at ordinary viewport only. | At actual 400%: stage navigation, both recovery choices, outcome/focus/next Tab; measured CSS viewport, DPR and window size; confirmation of restored original zoom. Preserve existing passing observations and revisit only where necessary to establish the remaining context. | User-assisted native-browser testing, or explicit acceptance amendment by the authorized owner. Integrated viewport resizing is not a substitute. |
| Actual screen-reader interoperability | Prior labels/associations/keyboard evidence and fresh visible recovery message; installed Narrator availability is historical inventory only. | Observed reader output for labels, invalid state and summary/errors, field-link destinations, both recovery outcomes including repeated/delayed-response cases, dialog entry/containment/return, and hidden-stage exclusion. Record browser/reader versions, exact output and limitations; restore initial reader state. | User-assisted reader session, or explicit acceptance amendment. DOM/AX inspection cannot close this gap. |
| Technical QA disposition | Original findings resolved in passing rechecks; focused Review PASS and 23/23 preserved; fresh bounded navigation/recovery pass. | Required actual-zoom and reader observations above. | Remains INCOMPLETE until evidence is reviewed; no waiver or overall PASS recorded. |
| Five-participant usability acceptance | Approved task pack; no participants contacted. | Five unfamiliar participants; at least 4/5 success per defined task and zero specified critical incidents. | Separate human-led acceptance remains pending; not replaced by technical QA. |

Use the existing assisted script above for remaining scenarios, recording human observations as user-observed evidence rather than agent verification. No native/browser-accessibility settings were changed in this integrated follow-up. The temporary isolated API outage was restored, both services were left running, and the fixture tab was retained. The earlier native session's unconfirmed zoom restoration remains a human check; it was not silently treated as restored. No code changes, Done Check, staging, commit, deployment, next unit or participant contact. Stop at QA.

## Human-authorized bounded acceptance amendment — 11 November 2026

The human explicitly authorized deferring the three remaining acceptance gates below so this implementation unit can complete, and authorized a repository Done Check against those amended criteria. This supersedes earlier unit-level instructions that these gates must complete before Done Check; all dated results and failures remain historical evidence. No unperformed check is passed or marked not applicable.

| Original acceptance gate | Amended unit disposition | Retained obligation / limitation |
| --- | --- | --- |
| Remaining actual desktop 400% browser-zoom checks | **DEFERRED AND UNVERIFIED**; not a UX-U1 completion blocker | Remaining recovery/navigation observations, measurements and original-zoom restoration confirmation are still absent. Earlier actual-zoom successes remain limited to their recorded states/source. |
| Actual screen-reader interoperability | **DEFERRED AND UNVERIFIED**; not a UX-U1 completion blocker | No observed reader output establishes labels/errors, recovery announcements, dialog traversal/return or hidden-stage exclusion. DOM, keyboard and axe evidence do not substitute. |
| Five-participant usability acceptance | **DEFERRED AND UNVERIFIED**; not a UX-U1 completion blocker | No participant sessions/results; the original task pack and thresholds remain available for later separately authorized acceptance. |

Authority assessment, in repository order: Product Specification v0.2 §51 retains full-journey, human approval, evidence, recovery and portfolio-quality requirements; Technical Architecture v0.2 §§5.1, 19.4–19.10 and 22 retain presentation/API, revision/retry and provenance boundaries; Implementation Plan v0.2 V1 Definition of Done, M5-U2 and M6-U4 retain workflow/navigation/recovery requirements. None mandates these three specific UX-U1 validation protocols as a unit-completion gate. No protected-specification conflict was identified for these bounded deferrals. This is not a deferral of the broader functional requirements or a claim that V1 is product-complete/release-ready. Protected specifications are unchanged.

The current **unit-scoped Browser QA gate is accepted under the amended criteria**, based on the resolved original findings and passing completed checks; the original full-scope technical QA remains historically INCOMPLETE. This distinction satisfies the workflow QA gate only for the human-amended unit scope. It does not convert deferred tests to PASS, claim full accessibility conformance or validated usability, or authorize release. The repository Done Check below determines readiness; no commit is authorized.

## Repository Done Check — 11 November 2026

**PASS under the expressly amended unit criteria. Lifecycle: READY_TO_COMMIT.** No remaining blocker to this exact unit-scoped inventory was identified. This is readiness for a separately authorized commit, not a commit, release decision, full accessibility acceptance or usability validation. All three deferred checks remain **DEFERRED AND UNVERIFIED**. The original QA FAIL, subsequent full-scope INCOMPLETE results and earlier failed Done Check remain preserved above.

### Done Check assessment

| Workflow item | Result and evidence |
| --- | --- |
| Current unit only / no scope creep | PASS for the exact 67-path inventory below. Frontend workflow/design, its regression coverage, approved dependency foundation and explicitly authorized local-startup amendment only. Unrelated records/tooling are excluded. No backend, public API, migration, protected-specification or next-unit change. |
| Acceptance criteria | PASS against the human-amended unit criteria only. Existing functional, evidence, human-approval, navigation, draft preservation and recovery criteria retain their recorded passing evidence. Three named validation gates are deferred, not performed or passed. |
| Required tests | Reused verified reports: earlier 270/270 frontend, 238/238 relevant backend, golden path 1/1, targeted E2E 14/14 and UX browser 1/1; latest affected component/shared-draft 96/96 and focused real-stack recheck 23/23. Local launcher 2/2 and Ruff remain applicable to unchanged launcher/test source. No suite rerun merely to increase counts. |
| Required evals | No changed model prompts, contracts, tools, analyst behavior, eval cases or backend business logic; fresh AI eval run not applicable to this frontend/unit amendment. Existing provider failures and pending human quality reviews are not erased or passed. |
| Type checking / lint / build | PASS reused from the final hash-matched focused-review production build: successful compilation, lint/type validation and static generation in a11y-review-2026-11-10/browser-verified.log. That combined browser run also contains a retained locator failure; the separate supplemental rerun and subsequent 23/23 QA run resolve the test-harness issue, not by reclassifying that first run as clean. |
| Review findings resolved | PASS: independent R5 Review PASS plus focused accessibility Review PASS. R1–R5 and original QA-1/QA-2 dispositions are preserved; no new unresolved code defect established by later checks. |
| Browser QA | **PASS for amended unit scope only**, based on completed real-stack checks and the 11 November integrated follow-up. Remaining actual-400% and spoken-reader checks are DEFERRED AND UNVERIFIED. This is neither N/A nor an unrestricted accessibility/technical-QA PASS. |
| No known regression | PASS within reviewed/tested scope; no new regression found. In-memory draft lifetime, existing check/submit race limitations, uncertain requests that may finish later and historical provider limitations remain documented. Deferred testing can still discover defects. |
| Dependencies / infrastructure | PASS: manifest and lock importer agree; approved direct additions listed below. No new backend/infrastructure/orchestration dependency; no install during Done Check. |
| Required documentation | PASS: authoritative current unit status, amendment, evidence boundaries, deferred obligations and exact inventory are here. Existing design/task pack and local-development instructions retained. The implementation index contains dated historical checkpoints and mixed unrelated reconciliation; it is not part of this proposed commit and does not override this unit record. Only UX-U1.md was edited in this task. |
| Git diff reviewed | PASS: current path/content inventory compared with independently reviewed evidence; all 295 current application/package paths match latest source manifest. Inspected dependency/lock, launcher/documentation and affected focus/error/recovery code/tests. All four pinned prototype hashes match. Fresh git diff --check passed. |
| No temporary/debug artifacts | PASS for proposed inventory: source-only design verification scripts retained; generated results/builds/traces/storage remain ignored. No debugger, console.log or exclusive-test markers found in proposed web code. Skill installation metadata is a historical design provenance record, not the installed skill or a runtime dependency. |
| No secrets added | No credential-pattern matches in the 67 proposed files; inspected configuration/launcher references use environment names and synthetic test values. No .env, credentials, cookie traces, databases or generated evidence proposed. This is a bounded inspection, not a comprehensive security certification. |
| Ready to commit | PASS / READY_TO_COMMIT for this inventory under amended criteria; staging and commit remain unauthorized. |

### Source identity and evidence reuse

HEAD remains `40f9c29a35c629f5080ca53a2f4e8229820ee0a8`; the source includes uncommitted UX-U1 work. Fresh SHA-256 verification found **295/295 matches** against `browser-recheck-2026-11-10/source-identity.json`, which ties the current application to the latest reviewed isolated build. The earlier full integrated QA source manifest differs in only the Brief/quote components and their two tests among previously inventoried application/tooling paths; the later focus helper and accessibility E2E file were added afterward. Those changes are covered by the focused Review, 96/96 component results and 23/23 browser recheck on the current manifest. Hence the earlier full-suite results support unchanged behavior, while the later focused results support the changed paths; no claim that the earlier full suite ran against every final file.

Directly inspected retained reports/logs: `browser-qa-2026-11-10/{frontend.json,backend.log,integrated.log,ux-browser.log,source-hashes.json}`, `a11y-review-2026-11-10/{components.json,browser-verified.log,supplemental.log}`, and `browser-recheck-2026-11-10/{browser.log,final-verification.json,source-identity.json}`, all under ignored `.local-investigation-artifacts/UX-U1/`. Earlier non-acceptance runs remain historical. Documentation-only acceptance changes do not invalidate runtime evidence. No fresh test/build/reader/zoom/participant execution is claimed by this Done Check.

### Dependency inventory

Retained Next.js **15.5.3**, React/React DOM **19.1.1**. Approved additions, pinned in manifest and lock:

- Runtime: `@radix-ui/react-dialog 1.3.1`, `@radix-ui/react-slot 1.5.0`, `class-variance-authority 0.7.1`, `clsx 2.1.1`, `lucide-react 1.70.0`, `tailwind-merge 3.7.0`.
- Build: `@tailwindcss/postcss 4.3.5`, `tailwindcss 4.3.5`, `postcss 8.5.32`.
- Test only: `axe-core 4.13.0`.
- Lockfile transitive updates belong to that previously reviewed dependency foundation; manifest/lock bytes match the tested source. The local Python launcher uses existing python-dotenv supplied by uvicorn[standard], adding no dependency.

### Exact proposed commit inventory — 67 paths

Only the following complete files are proposed; no staging has occurred.

```text
apps/web/app/globals.css
apps/web/app/layout.tsx
apps/web/app/page.tsx
apps/web/app/projects/[projectId]/page.tsx
apps/web/components.json
apps/web/components/brief-editor.test.tsx
apps/web/components/brief-editor.tsx
apps/web/components/comparison-review.test.tsx
apps/web/components/comparison-review.tsx
apps/web/components/decision-review.test.tsx
apps/web/components/decision-review.tsx
apps/web/components/project-dashboard.test.tsx
apps/web/components/project-dashboard.tsx
apps/web/components/project-workflow.test.tsx
apps/web/components/project-workspace-decision-refresh.test.tsx
apps/web/components/project-workspace-decision.test.tsx
apps/web/components/project-workspace-refresh.test.tsx
apps/web/components/project-workspace.test.tsx
apps/web/components/project-workspace.tsx
apps/web/components/quote-review.test.tsx
apps/web/components/quote-review.tsx
apps/web/components/record-save-status.test.tsx
apps/web/components/record-save-status.tsx
apps/web/components/supplier-review.test.tsx
apps/web/components/supplier-review.tsx
apps/web/components/ui/button.tsx
apps/web/components/ui/dialog.tsx
apps/web/components/use-record-draft.ts
apps/web/components/use-workspace-navigation.ts
apps/web/components/workspace-drafts.test.tsx
apps/web/components/workspace-drafts.tsx
apps/web/components/workspace-shell.test.tsx
apps/web/components/workspace-shell.tsx
apps/web/e2e/golden-path.spec.ts
apps/web/e2e/helpers.ts
apps/web/e2e/targeted.spec.ts
apps/web/e2e/ux-u1-accessibility.spec.ts
apps/web/e2e/ux-u1.spec.ts
apps/web/lib/editor-focus.ts
apps/web/lib/presentation.test.ts
apps/web/lib/presentation.ts
apps/web/lib/record-draft.test.ts
apps/web/lib/record-draft.ts
apps/web/lib/utils.ts
apps/web/lib/workspace-navigation.test.ts
apps/web/lib/workspace-navigation.ts
apps/web/package.json
apps/web/postcss.config.mjs
apps/web/test/setup.ts
apps/web/test/workspace-navigation.ts
apps/web/tsconfig.json
docs/design/UX-U1/CRITIQUE.md
docs/design/UX-U1/DESIGN.md
docs/design/UX-U1/IMPECCABLE-INSTALL.json
docs/design/UX-U1/index.html
docs/design/UX-U1/layouts.html
docs/design/UX-U1/PARTICIPANTS.md
docs/design/UX-U1/prototype.css
docs/design/UX-U1/prototype.js
docs/design/UX-U1/REQUIREMENTS.md
docs/design/UX-U1/verify-visual.mjs
docs/design/UX-U1/verify.mjs
docs/implementation/UX-U1.md
docs/local-development.md
pnpm-lock.yaml
scripts/dev-api.py
scripts/test_dev_api.py
```

Excluded and left untouched: `docs/implementation/M4-U7-artifact-retention.md`, `docs/implementation/M4-U7-final-done-check.md`, the entire mixed `docs/implementation/README.md` diff, all `.agents/` files, and all ignored local investigation/build/storage/evidence output. No protected specification is included. The index's UX-U1 dated entry is also excluded to avoid pulling its mixed baseline reconciliation into this unit commit.

Remaining follow-up is explicitly deferred, not a unit blocker: actual 400% completion and native zoom-restoration confirmation, operational screen-reader testing with observed output and restored settings, and five-participant usability sessions. Reauthorize and execute those before making the corresponding accessibility/usability claims; release readiness requires its own acceptance. No participants contacted, application code changed, services/browser settings operated, staging, commit, deployment or next unit begun during this task. Stop after Done Check.
