# SourcePilot design package

**Proposed for human design review.** This is a separate synthetic prototype, not an implemented SourcePilot redesign. No API, model, database, upload or durable save runs from these files. Reload resets the simulation. Production implementation and final design approval remain pending.

## Open and review

- Open [interactive prototype](index.html) in a browser. It works as local files without a server or installation.
- Open [annotated layout atlas](layouts.html). Choose 1440, 390, 320 or 768 CSS pixels, then scroll each frame or open its full-size screen. Annotations map to visible screen regions.
- Use **Review controls** in the prototype's separate gray banner to select normal, approval/review, empty, loading, blocked, failed, stale or three-confirmed-quote fixtures; change the next simulated save to success, failure or a 20-second uncertain result; trigger an external change; or reset.
- The dashboard is the prototype landing screen. The prototype-only `stage=dashboard` is not a proposed production workspace stage. Production retains the existing dashboard route plus five project stages.
- See [consolidated planning record](../../implementation/UX-U1.md), [requirement checklist](REQUIREMENTS.md), [participant pack](PARTICIPANTS.md) and [critique/verification](CRITIQUE.md).

## Design rationale and established constraints

The work area should answer three questions: What am I looking at? What needs attention? What did I actually save? The rail/phone grid answers the first; the next-action strip the second; explicit record status and review screens the third.

The established constraints are the five stages, existing fields and backend rules, human approval, preserved evidence, both quote-entry methods, synthetic supplier provenance and independent Decision access. The previous planning preferences are retained: calm professional presentation, wider workspace, one visible stage, progressive disclosure and eventual shadcn/ui adoption.

The values below are concrete design proposals for approval, not previously approved product specifications. The dependency-free HTML/CSS prototype approximates the proposed component system; it does not install shadcn, Tailwind, icons or fonts. Production later uses approved primitives and maintains the current Next/React versions.

## Proposed visual tokens — visual refinement, 7 November 2026

Impeccable 4.8.0's Operate guidance informs this refinement. The sourcing workflow, field groups, evidence, approvals and draft protection remain the design authority. This is a restrained visual revision for human review, not a new UX direction. [Installation and exact file hashes](IMPECCABLE-INSTALL.json) record the official pinned source; [critique](CRITIQUE.md) records independent assessments and verification.

| Token | Proposal | Purpose |
| --- | --- | --- |
| Canvas | `#F5F6F8` | Explicit light neutral background on html and body |
| Surface | `#FFFFFF` | Editing surfaces, supplier records, dialogs |
| Primary text | `#20242C` | Charcoal headings, body and important values |
| Secondary text | `#535C6B` | Supporting context and metadata |
| Primary action / focus | `#2457C5`; hover `#1945A2` | Blue actions and 3px focus ring with 3px offset |
| Selection / task surface | `#EDF3FF` / `#E8EFFF` | Current supplier/stage and next-action context; never implied approval |
| Border | `#DCE0E6`; controls `#7C8593` | Quiet section rules; distinct input and secondary-button boundaries |
| Warning | `#79531B` on white or `#FFF1D8`; notices `#684710` on `#FFF9ED` | Named uncertainty, unsaved, stale and prerequisite states |
| Failure/conflict | `#953330` on `#FCE8E6`; notices `#9B3035` on `#FFF4F2` | Explicit failure/conflict labels; never color alone |
| Informational | `#344D65` on `#F0F5F8` | Supplemental notices |
| Positive/neutral status | Plain text | Confirmed, Meets and current-state text do not need repeated filled badges |
| Radius | 7–8px controls; 12px working surfaces; 16px dialogs | Form groups use separators rather than nested rounded panels |
| Spacing | 4px base; 8/12/16/20/24/32px rhythm | Tight related controls, clear group separation |
| Type family | `"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif` | One locally available UI family; no font requests/assets |
| Type roles | 32px desktop / 26px phone H1; 21px section; 17–19px record heading; 16px body and inputs; 14px labels/warnings/table; 13px compact metadata | 400 body, 600 headings/labels, 700 selected navigation; no 10–12px metadata |
| Line height / tracking | 1.5 body; 1.2–1.35 headings; H1 −.025em; normal label tracking | Sentence-case context, balanced headings; original source fixture casing preserved |
| Numbers | Tabular figures for amounts and numeric inputs | Easier comparison without changing amounts |
| Content width | 1440px workspace; 224px rail; 1200px dashboard | Preserve evidence/comparison space and existing breakpoints |
| Targets | 44px primary/control action minimum | Preserve phone and keyboard interaction affordances |

No decorative colored side borders remain on notices, AI advice or source highlights. The source highlight is blue to identify inspected evidence, not a success/warning finding. Quote groups share one white editing surface with thin separators; supplier records retain distinct white surfaces. Nonsemantic badges become plain labels. Comparison Unknown/Conflict values use one label instead of duplicate text plus badge. Warnings remain beside affected amounts even when the summary is scrolled away.

Both documents declare `data-theme="light"` on html and body, a `color-scheme: only light` meta declaration, and explicit CSS `color-scheme`, text and canvas colors on html/body. Controlled Chrome did not reproduce the reported dark background before the change: root was light but body transparent and computed color scheme normal. The revised light intent is verified with both preferred color schemes. This does not identify or control browser extensions, forced-color settings, or the surrounding preview host.

Phone shell spacing is reduced to fund readable type while preserving the first complete quote input within the existing 900px-high viewport regression. No essential warning, navigation item, field, evidence control or approval action was removed. No font/icon/component package, remote asset, animation or runtime dependency was added.

## Action hierarchy and copy

Primary action follows the active task: create, save, review/approve or explicit preference. Secondary outlined controls support review/recovery; text controls navigate or inspect. Destructive actions are separate and named. AI analysis is optional and secondary to facts and human decision.

| Situation | Proposed copy |
| --- | --- |
| Source notice | Demo suppliers use a curated synthetic dataset. SourcePilot does not perform live supplier research. |
| Dirty record | Unsaved changes / Notes not saved |
| Save accepted with later edits | Submitted values saved. Newer edits remain unsaved. |
| Save failure | Save failed. Your draft is retained. |
| Conflict | This record changed elsewhere. Your draft is preserved. Review both complete records before saving. |
| Pending departure | Leaving does not cancel a request already submitted. On return, SourcePilot reloads saved data; unsaved drafts may be lost. |
| Bounded wait | Save outcome not yet confirmed. Check saved state or leave. |
| Stale comparison | These are previous results. Refresh comparison after saving any corrections. |
| Unknown | No supporting evidence was provided; this is not a failure finding. |
| Conflict finding | The available sources disagree. Inspect them before choosing a current value. |
| Human preference | Recording a preference does not place an order or contact a supplier. |

Keep technical revisions, trace IDs, raw requirement enums and infrastructure details out of the product UI. The separate prototype controls may explain simulation mechanics.

## Annotated screen inventory

The atlas contains each screen at all four requested widths; the same source responds rather than using unrelated mobile pictures.

| Screen | Reading order and key annotations | States to review |
| --- | --- | --- |
| Dashboard | Project entry → rows with current work/next action → saved preference/counts → dataset notice. No-project state points to existing creation form; errors never look like emptiness | Normal, empty, loading, failed, create dialog |
| Brief | Approved summary with explicit Edit Brief; editing: viewed stage/status → product/quantity → commercial/delivery → structured requirements/importance → optional context → save/review. Original request remains available in edit/review | Approved, review, blocked missing destination, analysis failed, external requirement change |
| Suppliers | Shortlist count/review → candidate identity/commercial summary → required/preferred findings → evidence → private notes. Failed required material and conflicts remain visible | Approved/review, empty discovery, stale, blocked, note draft, removal warning |
| Quotes | Supplier selector/status → current supplier/status/gaps → commercial/timeline → secondary groups → per-quote save/review. Evidence beside correction on desktop and in a sheet below 1280 | Confirmed correction, needs review, empty entry choice, PDF processing, failed extraction/manual fallback, external currency conflict |
| Comparison | Freshness/recovery → quantity/currency warnings → factual comparison → important unknown/conflict → optional AI suggestion. Omitted third quote is explicitly explained | Current, stale, not generated, AI failed, no suggestion after refresh, blocked |
| Decision | Saved human preference → optional AI suggestion clearly separate → unsaved replacement → notes → explicit actions | No preference, different human preference, retained outside shortlist, blocked upstream without Decision gate, stale comparison |

### Field grouping

Brief: Product (name, category, quantity); Commercial/delivery (target price, destination, date/period); Requirements (kind/value/importance); Additional context (informational attributes/notes). Existing field semantics and optional target-price behavior remain unchanged. The prototype illustrates the period variant; production must retain the existing exact-date and period controls.

Quote: Commercial (quantity, unit price, currency, MOQ, sample/tooling/packaging/shipping costs); Timeline (sample/production/shipping/total lead times); Terms (payment/incoterm/validity/warranty); Compliance (certifications/notes); Other (exclusions/conditions/supplier notes and separate user quote note). Commercial/Timeline start expanded. Optional missing data may collapse; material gaps remain named outside disclosures.

Upload PDF and Enter manually are explicit choices. The synthetic upload path has no file input and labels its sample operation; this must not be mistaken for working PDF processing. In production, unsupported file, upload-limit and duplicate-file behaviors remain those already provided by the backend.

## Responsive matrix

| Width | Navigation and forms | Evidence and comparison |
| --- | --- | --- |
| 1440 | 224px rail; one main stage; paired fields; two supplier cards per row | 310px evidence pane; semantic comparison table with bounded sticky labels |
| 1024 | Rail retained; working content shrinks, no fixed form minimum that forces page overflow | Evidence sheet; table scrolls only inside its region |
| 768 | Rail becomes five full-label navigation links; one main column; paired fields where readable | Modal evidence sheet; table may scroll horizontally inside labeled region |
| 390 | Two-column stage grid, labeled native supplier selector, stacked fields/cards, wrapping actions | Full-viewport evidence sheet; equivalent stacked criterion comparisons |
| 320 | Same functions and complete labels; tighter padding, no page horizontal scrolling | Same sheet/stacked comparison; no sticky content layer |

Short viewports disable sticky elements. Guidance remains in normal flow to avoid obscuring forms at zoom. The compact header and stage navigation remain present across stages; selecting a stage never implies workflow advancement.

## Interaction walkthroughs

1. **Approval:** select Brief and Review controls → Needs approval/review. Review saved Brief, inspect requirements/original request, approve. The view stays on Brief; next action changes to Suppliers.
2. **Private-note preservation:** type a supplier note, review/approve shortlist. The note remains unsaved with its own status. No exclusion confirmation.
3. **Evidence correction:** Quotes → Harbor → change Unit price to 4.50. Switch to Cedar and back. Inspect source: original USD 4.22 remains, current/draft are distinct. Save changes, review the saved quote and refresh the stale comparison. Confirmed quotes remain confirmed after correction.
4. **New quote:** Quotes → Moss → Upload PDF → Use sample PDF → Finish simulated extraction → Review saved quote → Confirm. Reset to try Enter manually; unknown fields are allowed.
5. **Related-value conflict:** change Harbor amount, then Review controls → Simulate external change. The draft keeps USD and the local amount; the separate saved record shows EUR 4.60. Review complete records before deliberately retaining a draft or using saved values. Neither action saves automatically.
6. **Structural conflict:** choose Edit Brief, change a Brief field then simulate external change. The saved fixture removes a material requirement and adds packaging. The conflict review prevents restoring deleted IDs by bulk overwrite; choose saved record then use normal Add deliberately.
7. **Save failure/new edits:** choose Failure for next save and verify retained inputs. Choose Success, save and immediately type another correction: acknowledged snapshot and later unsaved edits stay separate.
8. **Departure:** choose Uncertain for next save; submit a correction and choose All projects. Leave anyway is immediately available. After 10 seconds the notice offers Check saved state. A simulated response settles at 20 seconds; leaving does not cancel it. Returning shows saved simulation state, not a promise of draft restoration after actual page reload.
9. **Decision:** choose Cedar despite AI suggesting Harbor; explicitly save. Notes-only saving must not save a later draft replacement. Clearing preserves notes. The blocked fixture still permits this stage.

## Review and testing boundary

Approve the design package only after reviewing all screen families, responsive adaptations, important states, evidence distinction, saved/draft clarity and interaction annotations. Design approval is separate from participant-testing completion and from production implementation authorization.

Prototype self-checks are documented in CRITIQUE.md. They are not independent application Review, production Browser QA, real persistence validation, accessibility certification or human usability acceptance. The owner recruits participants; the worker prepares and analyzes materials. Final implemented-workflow participant testing is required before checkpoint 4/Done Check can pass.

## Reference standards

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [320 CSS-pixel reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).
- [Focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) and [modal-dialog interaction](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
- [GOV.UK check answers](https://design-system.service.gov.uk/patterns/check-answers/) and [error summaries](https://design-system.service.gov.uk/components/error-summary/).
- [Nielsen usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/).
- Optional future [official shadcn skill](https://ui.shadcn.com/docs/skills) and [Vercel review skill](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines); not installed and not acceptance gates.

Focused review revision: Harbor currency conflict remains in the quote attention summary and beside Original currency at every width, even with evidence closed. Source excerpts use immutable supplier fixtures; saved corrections never rewrite them. Cedar tooling/shipping are USD 150/650. Mobile shell spacing is compacted while stage targets remain at least 44px. Approved Brief opens as a saved summary; unchanged editor Save is disabled and secondary, becoming primary only with edits.
