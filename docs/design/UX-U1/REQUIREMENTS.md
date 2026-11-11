# UX-U1 design coverage checklist

Status meanings: **Designed** = recorded design contract; **Demonstrated** = synthetic prototype interaction/layout; **Pending production** = not implemented or verified in the app; **Pending human** = requires owner/participant evidence. Prototype verification details are in [CRITIQUE.md](CRITIQUE.md), never a production or usability pass.

| ID | Requirement | Design/package evidence | Boundary or later verification |
| --- | --- | --- | --- |
| B1 | Verify current baseline and previous commit | UX-U1 baseline and three lifecycle addenda; exact commit scope | Historical evidence unchanged; release limitations preserved |
| B2 | Consolidated proposal with both review rounds | UX-U1.md | PLANNING; no final design/implementation approval |
| D1 | Dashboard and five stages, desktop/mobile | layouts.html six annotated boards; 1440/390 selector | Demonstrated; full-stage screenshots generated locally |
| D2 | 320 and 768 adaptations | Atlas selector; DESIGN responsive matrix; CSS media rules | Demonstrated; app reflow pending production |
| D3 | Loading/empty/blocked/failed/stale | Review-control fixture selector; DESIGN inventory | Demonstrated representative screens; not backend responses |
| D4 | Visual system, type, spacing, action hierarchy | DESIGN token/copy tables; shared prototype CSS | Proposed, not approved; no installed component/font/icon package |
| D5 | Dashboard empty versus unavailable; source notice | Dashboard scenarios, compact dataset notice | Demonstrated; no fake analytics |
| D6 | Impeccable visual refinement: blue/charcoal/light, readable type, restrained framing | DESIGN tokens; atlas annotations; CRITIQUE dual-agent record; installation manifest | Visual review pending; 23 functional regression groups and 48 visual combinations pass; no production approval |
| N1 | Viewed stage versus workflow progress | Rail/grid current selection versus next-action strip | Demonstrated; backend remains production authority |
| N2 | One visible stage, draft-preserving switch | Prototype state survives stage/supplier switches | Production must retain mounted editor behavior; prototype rerenders local templates |
| N3 | URL query and legacy fragment rules | UX-U1 navigation contract; prototype location parser | Prototype has extra dashboard fixture route; full app history/focus/scroll suite pending |
| N4 | Persistent recovery guidance without auto-navigation | Next-action strip; approval/save retains viewed stage | Demonstrated; old-guidance refresh failures designed, app checks pending |
| S1 | Record saves, saved-value review, explicit approvals | Brief/shortlist/quote review dialogs, record save footers | Demonstrated; API tokens/atomicity unchanged |
| S2 | No project-wide save or ambiguous exit-save | Per-record actions; Stay/Discard or Leave anyway | Demonstrated |
| S3 | Dirty drafts across evidence, refresh and other records | Quote switch/evidence; external-change control; retained notes | Demonstrated selected cases; comprehensive production matrix in UX-U1 |
| S4 | Pending save edits, failure, uncertain departure | Next-save success/failure/uncertain controls | Demonstrated; simulation settles at 20s, warning threshold 10s |
| S5 | Related values never auto-merged | Whole-record currency conflict and structural Brief conflict | Demonstrated; stable server IDs/normalization fully verified later |
| S6 | Removal with drafts, external removal recovery | Removal warning; copy/discard unavailable quote design | Local warning demonstrated; complete external/removal-race matrix pending production |
| S7 | Private notes do not gate shortlist approval | Quiet note status, review excludes note drafts | Demonstrated; note pending and membership concurrency suite pending production |
| S8 | Brief clarification recovery | UX-U1 clarification and conflict contracts | Designed; generation/answer form not wired in static prototype; existing API unchanged |
| I1 | Material unknown/conflict/failure visible | Supplier findings, quote gap summary, comparison warnings | Demonstrated; mandatory M4-U7 disclosures retained in future app |
| I2 | Full field grouping and entry choices | Brief groups, all quote groups, empty Moss entry choices | Demonstrated period example; exact-date variant designed, existing app control retained |
| I3 | Original versus current corrected evidence | Harbor source 4.22, editable correction, evidence inspector/comparison | Demonstrated; synthetic excerpt, not a PDF parser |
| I4 | AI suggestion versus human preference | Comparison advisory section; Decision saved panel | Demonstrated; preference not gated by comparison/AI |
| I5 | No suggestion, stale/failed advice recovery | Generate resets suggestion; review-state fixtures | Demonstrated; model behavior/deadlines unchanged |
| A1 | Keyboard, labels, dialog focus/return/status | Native controls/dialogs, skip link, live status, visible focus | Prototype checks documented; screen-reader user testing pending |
| A2 | Evidence sheet and unobscured comparison | ≥1280 pane, smaller modal sheet, phone criterion cards | Demonstrated; no page-level horizontal overflow in selected checks |
| A3 | 320 CSS reflow and 400% desktop zoom distinct | Verification record describes method/result separately | Do not infer actual browser zoom from viewport resizing |
| U1 | Human owner recruits; worker prepares | PARTICIPANTS.md scripts/fixtures/observation/findings templates | Pending human; no outreach |
| U2 | Five observable tasks and thresholds | Participant pack and UX-U1 acceptance table | Not tested; no invented results |
| U3 | Design approval separate from usability | Checkpoint table and participant gate | Final implemented-workflow acceptance/Done Check incomplete until testing |
| R1 | Critique and correct within scope | CRITIQUE.md and reproducible prototype-only verifier | Self-critique, not independent application review |
| R2 | Source/generated artifact separation | Authored source in this folder; captures/results under ignored root | No archive rewrite; generated files not staged |
| R3 | Stop before production migration | UX-U1 bounded authorization and delivery status | No app/backend/spec/dependency/skill changes, no commit |

## Required design review decisions

The owner reviews the screens and interactions, then approves or requests changes to the design package. No routine color/layout choice is left undecided in the proposal. Recruitment scheduling belongs to the owner; missing participants do not become implied consent or a usability waiver. Any future requirement for atomic cross-tab approval would need separate backend scope approval, not a hidden frontend promise.

Focused review additions: persistent Harbor currency warnings outside evidence; approved Brief summary and deliberate editing; mobile first-viewport reachability; supplier-specific source and warning consistency. See the current focused-review result in CRITIQUE.md. Human testing and production gates remain pending.

## Independent-review correction coverage — 7 November 2026

| Coverage | Newly executed prototype checks | Remaining boundary |
| --- | --- | --- |
| I3 / S1 — Moss original source in confirmation | USD 4.50 through extraction, evidence and confirmation at 1440/390/320; existing manual-entry no-PDF regression rerun | Synthetic source only; no real extraction or persistence |
| I1 / A2 — Local comparison currency warnings | Harbor price/tooling retain unresolved USD/EUR text beside unchanged saved values after the summary scrolls away, evidence closed, desktop and mobile; Cedar receives no false marker | Existing summary retained; no FX resolution or conversion |
| S1 / I2 — Complete saved Brief review | All saved fixture fields, requirements/importance, original request and target uncertainty; edited delivery appears only after save; dirty/pending review blocked; optional omission and missing-destination approval gating checked | Conflict regression rerun; real cross-client approval races remain outside prototype guarantees |

Current [23-group report](../../../.local-investigation-artifacts/UX-U1/independent-fixes-01/report.json): all previous 20 groups rerun plus three targeted groups, all PASS. Fifteen additional desktop/mobile captures visually inspected; 67 captures total. Actual Chrome 400% six-screen reflow rerun. The older 20/18-group reports are retained historical evidence, not current-source results. See CRITIQUE.md for exact checks, visual evidence and limitations. Corrections await independent review; design approval, production authorization and human usability acceptance remain pending.
