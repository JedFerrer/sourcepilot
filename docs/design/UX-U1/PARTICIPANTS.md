# SourcePilot usability task pack

**Prepared; recruitment pending; sessions pending; no participant evidence or pass result.** The human project owner recruits and schedules five people unfamiliar with implementation, preferably sourcing users. The worker prepares fixtures/tasks/observation sheets and records/analyzes authorized evidence. No participant has been contacted by this work.

Design-package approval is separate from testing completion. Prototype sessions may inform changes before or after design approval. Final testing on the implemented workflow is mandatory: if unavailable, human usability acceptance and checkpoint 4 overall acceptance/Done Check remain incomplete. Do not substitute developer self-review or automated tests.

## Preparation and consent

- Owner supplies participant availability and confirms permission to observe/take notes; recording requires separate participant agreement. Use anonymous IDs P01–P05, not names/contact details in repository records.
- Include desktop and phone sessions; recommended allocation three desktop and two phone. Record device, browser, viewport and any assistive technology. Do not collect purchasing secrets or real supplier documents.
- Prepare the synthetic travel-bag project and safe reset instructions. Prototype resets via Review controls → Reset simulation; reloading also clears the local simulation. The implemented-app round will require equivalent isolated synthetic fixtures and saved-state verification.
- Explain: “We are testing the design, not you. Think aloud if comfortable. This prototype simulates saving and approval; no real supplier is contacted. You may stop at any time.”
- Give goals without control names or step-by-step instructions. Do not reveal the walkthroughs in DESIGN.md before a task. Permit ordinary exploration; record requests for help and any procedural hints.

## Task fixtures and scripts

| Task | Facilitator setup, not read aloud | Participant prompt | Observe |
| --- | --- | --- | --- |
| 1 Find next action | Open Quotes; set Stale. This leaves the user viewing Quotes while supplier evaluations need attention | “You have returned to this project. Find what needs attention next and where you would act.” | Correct need/action/control within 30 seconds; distinguishes viewed stage from workflow progress |
| 2 Unknown versus conflict | Suppliers normal: Harbor certification Unknown; Cedar branding Conflict | “Compare the concerns for Harbor's certification and Cedar's branding. Explain what each means and how you would investigate.” | Missing evidence versus disagreeing evidence; does not interpret Unknown as failed; locates source |
| 3 Correct quote from evidence | Quotes Harbor normal; ask for a synthetic correction after showing original sample | “The reviewed commercial amount should be 4.50. Check the original evidence, correct the current value and save it. Explain what the document says and what the saved record says.” | Finds source USD 4.22; saves 4.50; does not claim original document proves correction; draft survives evidence/supplier switching |
| 4 Recover stale results | After task 3 leave comparison stale; retain an unsaved note for another supplier | “Your comparison may no longer reflect the latest quote. Bring it up to date and check that your other unfinished note is still available.” | Understands stale versus failure; refreshes saved facts; no draft loss; does not require optional AI to proceed |
| 5 Human preference | Decision normal, AI suggests Harbor, no saved preference | “You prefer Cedar after considering the tradeoffs. Record that decision and explain which part was your choice. Then show how you would change or clear it.” | Explicit human save, correct supplier, distinguishes advisory from saved state, notes/clear semantics |

Task 3 uses a controlled synthetic instruction, not a claim that the original document supports 4.50. Do not ask participants to invent financial corrections in a real sourcing task.

## Observation sheet template

Copy this blank section once per participant. Leave outcome fields blank until observed; no prefilled successes.

- Participant ID:
- Date / facilitator:
- Round: prototype / implemented workflow
- Prior familiarity with sourcing (not this implementation):
- Device / browser / viewport / input or assistive technology:
- Consent for notes / separate recording permission:
- Fixture reset and version:

| Task | Start/end or seconds | Completed unaided? | Wrong turns/errors | Help requested/provided | Participant explanation or quote | Severity/follow-up |
| --- | --- | --- | --- | --- | --- | --- |
| 1 Next action | | | | | | |
| 2 Unknown/conflict | | | | | | |
| 3 Evidence correction | | | | | | |
| 4 Stale recovery | | | | | | |
| 5 Human preference | | | | | | |

Critical-incident log:

| Time/task | Observed behavior | Data loss / accidental approval / provenance misunderstanding? | Did participant notice? | Recovery | Design finding |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Closing questions: “What was least clear?” “What did you believe was saved?” “Where did you expect to find the next action?” Record the participant's language rather than translating it into implementation terms.

## Findings and acceptance template

- Recruitment: **PENDING**
- Prototype sessions: **PENDING**
- Final implemented-workflow sessions: **PENDING**
- Evidence location / consent-safe notes:
- Tested source/version:

| Task | Unaided successes / 5 | Timing/errors | Finding | Proposed correction | Retest evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Not tested | | | | |
| 2 | Not tested | | | | |
| 3 | Not tested | | | | |
| 4 | Not tested | | | | |
| 5 | Not tested | | | | |

Acceptance requires at least 4/5 unaided successes for each task, next-action identification within 30 seconds, and zero unnoticed data-loss, accidental-approval or provenance-misinterpretation incidents. These are local thresholds, not statistical generalizations. Fix and retest affected tasks; report limitations if returning participants have learned the workflow. Prefer fresh participants for the final round.

Do not combine partial sessions into a fictional five-person pass. If unavailable, report **Human usability acceptance incomplete**. Design review may proceed; the later overall acceptance and Done Check cannot pass without the required evidence.
