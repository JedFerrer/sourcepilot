# UX-U1 self-critique and verification

**Design package prepared for human review. Final design approval pending.** This is the author's prototype critique, not an independent production Review or application Browser QA. No human usability test was conducted. No production migration is authorized.

## Impeccable visual refinement — 7 November 2026

Method: dual-agent (A: `/root/design_assessment` · B: `/root/mechanical_assessment`). Both assessments were isolated; A finished its design judgment before B's findings entered synthesis. Final refinement and verification were performed by the parent worker. This reopens visual approval only. All previous functional findings and regression requirements remain binding.

### Skill provenance and limits

Read the installed official [Impeccable SKILL.md](../../../.agents/skills/impeccable/SKILL.md), plus critique, typeset, quieter, operate, polish and craft-floor references. Project-only installation: Impeccable 4.8.0, source `https://github.com/pbakaus/impeccable`, revision `687bc381bc9091bf252c0a05303640561014a425`, path `.agents/skills/impeccable`. [Installation record](IMPECCABLE-INSTALL.json) lists all 63 added skill files with SHA-256 hashes. One unified skill was installed; command references and scripts are its official bundled contents, not separately enabled integrations. No hooks, automatic trust checks, runtime dependencies, remote fonts or external runtime assets were enabled/added. Skill discovery was confirmed on the next user turn; no reload is needed for this review.

Context launcher was declined because its fallback downloads an additional executable and defaults to a user-level cache. The main skill explicitly permits direct project-context reading on refusal. Assessment B attempted the detector with `IMPECCABLE_LAUNCHER_PROBE=1` to prohibit downloads: exit 127, empty stdout/stderr, no engine installed. Deterministic Impeccable scan is **unavailable**, not clean. No target slug or critique-storage snapshot was generated; this record is the repository critique archive. No ignore file exists. No overlay/live server was started; no browser visibility/overlay claim is made. Fresh isolated headless Chrome pages using the existing Playwright dependency supplied measurements and captures, and were closed. No generated evidence was deleted or historical archive rewritten.

### Design critique and response

The workflow is recognizably about sourcing: original/current quote values, requirement fit and explicit human preference are its strongest features. The old surface looked generic because green washes, small uppercase scaffolding, repeated badges and enclosed form groups outweighed those details. The emotional risk is a busy user overlooking provenance or mistaking green for permission to proceed. Five-stage navigation is justified; the problem was visual competition, not excess workflow choices.

| Priority | Finding | Applied refinement |
| --- | --- | --- |
| P1 | Inputs inherited 13px labels despite a 16px design intention; critical metadata shrank to 10–12px | Explicit 16px input text; 14px labels/warnings; compact metadata floor 13px; phone space recovered through tighter shell spacing |
| P2 | Green mixed action, selection and implied success | Blue action/selection tokens, charcoal text, neutral light canvas, white work surfaces; meaningful warning/error colors retained |
| P2 | Quote groups and evidence were repeatedly framed | One quote editing surface, thin group separators, restrained evidence paper; neutral badges become plain labels; duplicate comparison status badge removed |
| P2 | Uppercase tracked context competed with headings | Sentence-case context with normal tracking; stage context moved beneath H1; original source-document casing retained |
| P2 | Colored side rails overstated notice/advice emphasis | Side rails removed from notices, advice and source mark; warning wording and restrained full-border/surface treatment remain |

Independent A's baseline heuristic scores were: status 3, real-world language 4, control 3, consistency 2, prevention 3, recognition 3, efficiency 3, minimalist design 2, recovery 3, help 3: **29/40**. These are subjective prototype judgments, not a user-study result. No artificial post-change score is claimed. B independently confirmed the type inheritance issue, decorative rails, missing CSS theme declaration, weak secondary boundaries and absent hover styles. Rendered refinement keeps the field groups, navigation, supplier selector, disclosures, evidence distinctions and explicit saved-value approval interactions intact.

### Dark-background investigation

[Baseline browser measurements](../../../.local-investigation-artifacts/UX-U1/impeccable-assessment-b/baseline.json) cover all four widths with light and dark preferred schemes. Neither reproduced the dark background: html was light, body transparent, computed color scheme normal. Both prototype and atlas now declare the light theme on document/body, use explicit canvas/text backgrounds and `color-scheme: only light`, and supply matching metadata. The final checks verify light surfaces under both preferences. The reported preview's original cause remains unconfirmed. No browser extension, forced-colors preference or preview-host control is claimed.

### Final verification evidence

- [Functional regression report](../../../.local-investigation-artifacts/UX-U1/visual-refinement-final-02/report.json): **23/23 groups PASS**, unchanged existing test script. Includes all previous independent-review corrections, drafts, approvals, manual provenance, pending/failing saves, note/preference separation, modal keyboard trapping/return, 42 layout/state captures and six actual Chrome 400% zoom checks. **67 PNGs** total including targeted dialogs, first viewports and atlas. No browser JavaScript errors or HTTP requests.
- [Visual report](../../../.local-investigation-artifacts/UX-U1/visual-audit-final-02/visual-report.json): **48 combinations** (six screens × four widths × two color preferences). Explicit light surfaces, no page-level overflow, visible sampled text >=13px, controls 16px, no decorative side rails, visible keyboard focus and action hover checks. **16 PNGs**: four focus views and twelve warning/state screens. Atlas light-theme check passes.
- Color calculations: blue/white **6.47:1**; secondary/canvas **6.24:1**; control border/white **3.73:1**; amber label/background **6.14:1**; conflict label/background **6.38:1**; focus blue/light-blue surface **5.81:1**. Lowest sampled normal-state text ratio **5.62:1**. Sampling uses opaque ancestor backgrounds, excludes disabled and visually hidden text, and is not a complete accessibility audit.
- Rendered inspection covered desktop quote editing and supplier cards, 768px comparison, 390px Decision and failed PDF warning, 320px first quote viewport and three-supplier comparison, plus final warning/focus captures. Warning text wraps without clipping; local currency conflict remains alongside affected amounts, and failure/recovery actions stay readable.
- Initial refinement runs 01/02 failed the retained 320px first-field threshold (1012px, then 913px). Shell spacing was tightened without shrinking warning type; subsequent and final runs pass. The first visual-audit run exposed an overly strict outline-string assertion, not missing focus; the check now accepts browser serialization order. Failed evidence is retained honestly.

### Scope and handoff

Changed only prototype presentation/template markup and design documentation: `index.html`, `prototype.css`, `prototype.js`, `layouts.html`, `DESIGN.md`, `CRITIQUE.md`, `REQUIREMENTS.md`. Added `verify-visual.mjs`, `IMPECCABLE-INSTALL.json`, and the 63 project-local skill files. The existing `verify.mjs` regression script is unchanged. All generated evidence stays under ignored `.local-investigation-artifacts/UX-U1/` directories. Existing lifecycle edits and planning documents were left untouched by this pass. No production, backend, framework, protected-specification or participant-material changes; nothing staged or committed.

This is synthetic prototype verification, not production QA, full WCAG certification, cross-browser/screen-reader validation or human usability acceptance. Prior limitations below remain valid. **Stop for human visual review; visual approval remains pending.** Questions skipped: the user already supplied a concrete visual direction and requested delivery followed by visual review, not a menu of alternatives.

## Independent-review corrections — 7 November 2026

**Three requested prototype fixes implemented; awaiting independent review. Design approval and production implementation remain unauthorized.**

| Finding | Correction | Newly executed evidence |
| --- | --- | --- |
| Moss confirmation provenance | Review saved quote derives original currency/price from the selected supplier's immutable source fixture. Manual entries retain their no-PDF-evidence message. | At 1440/390/320, Moss extraction, source inspection and confirmation review all show USD 4.50; confirmation succeeds. Existing manual-entry regression rerun. [Desktop](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/moss-confirmation-1440.png), [phone](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/moss-confirmation-390.png) |
| Comparison-local currency conflicts | Harbor monetary cells/cards carry “Currency conflict: source says USD / EUR; unresolved.” Unit price and tooling retain their saved amounts; known shipping amounts use the same marker. Unknown shipping remains Unknown. Summary warning remains. | Price and tooling at 1440/390/320, evidence closed and summary scrolled above viewport; Harbor values unchanged and Cedar has no false marker. [Desktop tooling](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/comparison-tooling-local-1440.png), [320px tooling](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/comparison-tooling-local-320.png) |
| Complete saved Brief approval review | Reuses the complete saved-record summary: product, category, quantity, target, destination, delivery, context and every requirement/importance. Keeps original request accessible, explicitly states target-currency uncertainty and optional omissions, and exposes missing required-field warning. Existing dirty/pending/conflict and approval gates unchanged. | At 1440/390/320, a deliberately saved delivery edit appears in review alongside all fixture fields and original request. Dirty/pending review disabled; optional blank target displayed as Not provided without blocking approval; missing destination blocks approval. [Desktop](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/brief-complete-review-top-1440.png), [320px review/actions](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/brief-complete-review-bottom-320.png) |

### Newly executed verification

`node docs/design/UX-U1/verify.mjs .local-investigation-artifacts/UX-U1/independent-fixes-01` completed successfully: **23/23 groups PASS**, comprising all previous 20 groups plus three targeted groups. This reruns draft retention, saved-value review, manual-entry provenance, navigation, conflict handling, pending/failing saves, evidence keyboard focus and independent human preference/notes behavior. No browser JavaScript errors or HTTP requests were observed by the harness.

[Current report with source hashes](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/report.json). There are **67 PNGs**: previous 52 captures plus 15 targeted desktop/390px/320px captures. All 15 targeted captures were visually inspected: warnings remain readable beside values, source copy wraps, and complete Brief review remains readable with reachable actions through dialog scrolling. No layout changes were needed.

Actual Chrome 400% page zoom was rerun for the existing six-screen reflow group: [metrics](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/zoom-metrics.json) show outerWidth 1280, innerWidth/scrollWidth 316 and DPR 4. The new dialogs were tested at the stated widths, not separately at actual 400% zoom. Both JavaScript syntax checks and tracked diff whitespace check passed; authored-file trailing whitespace was also checked separately because design files remain untracked.

### Retained evidence and limits

The 20-group focused-review-03 report and earlier 18-group reports below are retained historical runs. Their source hashes do not identify this revision. Their previous blanket closure claim was superseded by the independent review's three findings; the current 23-group rerun supplies the correction evidence. No prior report or capture was rewritten.

These are worker-run synthetic prototype checks and visual inspection, not independent acceptance, production QA or human usability validation. Real persistence/concurrency/backend behavior, cross-browser and screen-reader testing, shorter phone viewports and participant acceptance remain unverified. Existing limitations below continue to apply.

Exactly four authored files changed in this correction pass: `prototype.js`, `verify.mjs`, `CRITIQUE.md`, and `REQUIREMENTS.md`. Generated evidence is confined to the new ignored `independent-fixes-01/` directory. No production code, backend behavior, protected specifications, dependencies, skills, participant materials or lifecycle records changed. Nothing staged or committed. Stop for independent review.

## Historical focused prototype review revision — 7 November 2026

The prior worker recorded the following four corrections; independent review subsequently found the three remaining gaps addressed above:

1. Harbor's intentional USD/EUR source conflict now appears in the quote attention summary and beside Original currency, even when evidence is closed. No contradiction is silently resolved by changing the editable currency.
2. Approved Brief opens as a saved summary with explicit Edit Brief. The unchanged editor's Save is disabled and secondary; editing enables and emphasizes Save. Existing saved-value approval and draft preservation remain intact.
3. Mobile shell spacing is reduced without shrinking stage/action targets below 44px. A labeled native supplier selector replaces stacked supplier buttons below 768px, retaining names, quote status and unsaved indicators. The complete first quote input is inside the initial 900px viewport at both 320px and 390px. These first-viewport captures were visually inspected, in addition to full-page reflow checks.
4. Immutable per-supplier source fixtures supply evidence excerpts and simulated PDF extraction. Cedar shows tooling USD 150 and shipping USD 650, with no false shipping/certification-unknown summary. Moss extraction uses its own USD 4.50 fixture. Intentional Harbor currency and Cedar branding conflicts remain explicitly labeled; later saved corrections do not rewrite source evidence.

Historical verification: **20 check groups PASS** in [focused-review-03/report.json](../../../.local-investigation-artifacts/UX-U1/focused-review-03/report.json). This includes the prior interaction/layout/400% zoom checks plus focused regressions for these findings. There are 52 PNGs: the previous capture coverage plus two first-viewport captures. No browser JavaScript errors or HTTP requests were observed. The initial focused run failed the first-viewport requirement at 320px (first input bottom 1058px); it remains retained, followed by corrected passing runs. This is worker verification, not an independent rerun or participant testing.

Review [390px first viewport](../../../.local-investigation-artifacts/UX-U1/focused-review-03/quotes-first-viewport-390.png), [320px first viewport](../../../.local-investigation-artifacts/UX-U1/focused-review-03/quotes-first-viewport-320.png), and [approved Brief](../../../.local-investigation-artifacts/UX-U1/focused-review-03/brief-390.png). Source hashes in the current report bind the verification to the revised prototype. The earlier package audit and 18-group report below describe the pre-revision package, not the current source hashes.

This revision changes seven authored files only: prototype.js, prototype.css, verify.mjs, layouts.html, DESIGN.md, REQUIREMENTS.md and CRITIQUE.md, all in docs/design/UX-U1. Participant materials, lifecycle records and the consolidated plan are unchanged by this revision. Production code, protected specifications, dependencies and installed skills remain unchanged. No live providers, staging or commit. Design approval, participant testing and screen-reader validation remain pending; all simulated-functionality limitations below still apply.

## Historical pre-revision verification

## Scope and evidence

The final synthetic-prototype run used the repository's already-installed Playwright package and installed Chrome, without downloading dependencies or browsers. It passed **18 check groups**, capturing **42 screen/state/width layouts** plus six actual-browser-zoom screens, one evidence-sheet viewport and one atlas capture: **50 PNGs** in the final run. No prototype JavaScript errors or HTTP service requests were observed.

Final local-only evidence: [report](../../../.local-investigation-artifacts/UX-U1/design-review-final-03/report.json), [zoom metrics](../../../.local-investigation-artifacts/UX-U1/design-review-final-03/zoom-metrics.json), [generated review directory](../../../.local-investigation-artifacts/UX-U1/design-review-final-03/). These generated files are ignored and are not supplied by a fresh clone. The authored atlas and prototype are self-contained source deliverables; no screenshot archive is required to open them.

The report includes SHA-256 identities for index.html, prototype.css, prototype.js, layouts.html and verify.mjs. Earlier failed/intermediate runs are retained separately, not rewritten as successes. Final package integrity and exact source/generated inventory are in the local [package audit](../../../.local-investigation-artifacts/UX-U1/package-audit.json).

## Critique findings and corrections

| Finding | Correction within the authorized prototype | Verification |
| --- | --- | --- |
| Disclosures closed during stage/approval rerenders | Preserve disclosure state by stage, supplier and record | Private-note disclosure and content survive Brief/shortlist review path |
| Populated textarea labels were ambiguous to the browser locator/accessibility surface | Explicit accessible names match visible field labels | Notes preservation and input interactions pass after rerender |
| Leave anyway re-entered the navigation guard | Carry the explicit departure authorization through the one navigation | Immediate departure, 10-second warning and saved-state return pass |
| Native dialog cycling could move focus outside the modal | Explicit Tab/Shift+Tab boundary wrapping; visible Close; Escape and return behavior | Twelve keyboard steps stay inside evidence dialog; Escape returns to evidence trigger |
| Rerenders could drop focused input/caret | Restore matching record/field or requirement control and selection without scrolling | Later input survives pending-save completion; keyboard interaction remains available |
| Input borders were too faint | Darken interactive boundaries from #B7C7BF to #7D9189 | Contrast against white rises from 1.76:1 to 3.34:1 |
| Price provenance was cramped | Separate source action and origin text; source action has 44px height | Desktop and phone visual inspection |
| A shared source template could show Harbor's amount for Cedar/manual entry | Supplier-specific sample amount; manual entry explicitly has no PDF/AI evidence | Manual quote requires save before review and contains no invented source |
| Conflict screens exposed raw JSON | Plain-language record summaries; amount/currency displayed together | Whole-record conflict interaction passes without automatic hybrid values |
| Requirement replacement could revive removed IDs | Structural conflict stops bulk replacement; use current saved record and normal Add explicitly | Requirement add/delete scenario reaches structural warning |
| Stale comparison could accidentally display newly saved values | Separate simulated comparison snapshot from quote saved state | Old 4.22 remains until explicit refresh; refreshed comparison shows 4.50 |
| Initial comparison only illustrated two suppliers | Add Three confirmed quotes fixture and equivalent mobile view | All four widths retain Moss's required material failure |
| Closing rename could hide a dirty name | Explicit keep-editing/discard warning, including Escape | Dirty-rename regression passes |

## Verification matrix actually exercised

| Area | Result and limits |
| --- | --- |
| Normal layouts | Dashboard and five stages at 1440, 768, 390 and 320 CSS pixels: one main heading, no page-level horizontal overflow |
| Representative states | Fourteen phone fixtures spanning empty, loading, failure, review, blocked and stale; plus three-supplier comparison at four widths |
| Navigation | Viewed-stage Back/Forward works; no mutation on stage navigation. Production history departure/focus/scroll reconciliation still needs app tests |
| Draft/evidence | Quote supplier switch and source sheet preserve 4.50 draft while original 4.22 remains; full-record currency conflict requires explicit review |
| Structural conflict | Concurrent saved requirement removal/addition cannot silently restore old IDs |
| Saving | Later edits survive pending save; failure retains draft; pending departure does not cancel simulated completion; returning reads saved simulation state |
| Approval | Brief then shortlist review works; unsaved private notes survive and are not saved by approval; manual quote must be saved before review |
| Decision | Cedar can be explicitly selected while AI suggests Harbor, before comparison; notes-only save retains saved preference and unsaved replacement |
| Keyboard | Evidence dialog traps Tab sequence; Escape returns focus; native labeled controls, stage links and visible focus remain operable |
| Desktop zoom | Actual Chrome page zoom, not CSS zoom or viewport-only resizing: outer width 1280, inner width 316, devicePixelRatio 4, scrollWidth 316. Six screens reflow without page-level horizontal overflow |
| Network boundary | No HTTP requests from the prototype; no app/backend/model calls |
| Static/scope | JS syntax checks, documentation local-link checks, whitespace and Git scope checks; no production/spec/dependency changes or staged files |

Chrome zoom verification sets the actual default page-zoom preference in an isolated disposable profile under the ignored output directory. Chromium's [zoom preference implementation](https://raw.githubusercontent.com/chromium/chromium/main/chrome/browser/ui/zoom/chrome_zoom_level_prefs.cc) establishes the partition-key dictionary mechanism. The measured layout/DPR values verify that zoom took effect. A previous scalar preference attempt did not apply zoom and remains recorded as NOT_VERIFIED in an earlier run; it is not counted as a pass.

Selected proposed color-pair calculations: primary action/white 6.88:1; secondary text/canvas 5.49:1; warning text/background 6.14:1; failure text/background 6.38:1; focus indicator/white 4.45:1; interactive border/white 3.34:1. These checks are not a complete accessibility audit of every state.

## Remaining limitations and honest gates

- All behavior is in-memory simulation. There is no genuine persistence, request cancellation, real parallel-client conflict, upload processing, provider result or session-expiry test. Reload clears prototype state.
- Future production must use the existing backend's workflow and concurrency rules. This prototype uses small illustrative state transitions, not a replacement workflow engine.
- Brief clarification generation/answer recovery, exact-date variants, complete membership/removal race handling, external removal restoration and full app-history scroll restoration are specified in UX-U1 but not exhaustively wired in the prototype. Their existing application contracts remain unchanged; production tests are required.
- Evidence excerpts are synthetic text, not a PDF viewer. Monetary corrections never rewrite their source. The three-supplier fixture is a design scenario, not live sourcing.
- Keyboard checks and Chrome zoom/reflow evidence do not establish screen-reader interoperability, cross-browser conformance or WCAG certification. No assistive-technology user session or newly installed accessibility scanner was used.
- Human owner recruitment, prototype participant sessions and final implemented-workflow usability acceptance are pending. The prepared tasks are not test results. If testing remains unavailable, checkpoint 4 overall acceptance and Done Check stay incomplete.
- Final design approval and production implementation authorization are separate and both pending. Existing M4-U7 quality/release limitations remain unchanged.

## Reproduce the prototype-only checks

From the repository root, run `node docs/design/UX-U1/verify.mjs`. This uses installed Chrome and the existing Playwright dependency, creates a unique ignored output directory and opens no production application. An optional output path must be under `.local-investigation-artifacts/`; a previous report is never overwritten. No installation is required. Generated Chrome profiles and captures stay under the ignored root.

## Exact repository file inventory

Modified only by adding current lifecycle notes above preserved history:

1. `docs/implementation/README.md`
2. `docs/implementation/M4-U7-final-done-check.md`
3. `docs/implementation/M4-U7-artifact-retention.md`

New authored planning/design source:

4. `docs/implementation/UX-U1.md`
5. `docs/design/UX-U1/index.html`
6. `docs/design/UX-U1/prototype.css`
7. `docs/design/UX-U1/prototype.js`
8. `docs/design/UX-U1/layouts.html`
9. `docs/design/UX-U1/DESIGN.md`
10. `docs/design/UX-U1/REQUIREMENTS.md`
11. `docs/design/UX-U1/PARTICIPANTS.md`
12. `docs/design/UX-U1/CRITIQUE.md`
13. `docs/design/UX-U1/verify.mjs`

Generated files are confined to ignored `.local-investigation-artifacts/UX-U1/`; the package audit lists them separately, including intermediate failed review runs. No historical M4-U7 artifact was edited. No files were staged or committed.
