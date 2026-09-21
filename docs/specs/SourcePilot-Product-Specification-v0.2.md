# SourcePilot — Product Specification v0.2

**Status:** Final / Approved  
**Specification version:** 0.2  
**Product milestone:** SourcePilot MVP / first public portfolio release  
**Product type:** Open-source portfolio/demo application  
**Primary focus:** AI-assisted, evidence-backed supplier sourcing workflow  
**Scope principle:** Smaller, deeper, polished implementation suitable for one developer

---

# 1. Product Overview

SourcePilot is an AI-assisted sourcing workspace that helps a user turn an informal product sourcing request into a structured, evidence-backed supplier comparison.

The locked MVP journey is:

**Natural-language request → Brief → Suppliers → Quotes → Comparison → Decision**

More specifically:

1. User describes what they want to source.
2. SourcePilot converts the request into structured sourcing requirements.
3. SourcePilot identifies missing or unclear information.
4. User completes and approves the sourcing brief.
5. SourcePilot discovers potential suppliers from a curated synthetic-but-realistic supplier dataset.
6. User reviews supplier evidence and shortlists up to three suppliers.
7. User uploads or manually enters supplier quotes.
8. SourcePilot extracts and normalizes quote information.
9. User verifies extracted quote data.
10. SourcePilot compares suppliers against the approved sourcing requirements.
11. SourcePilot explains tradeoffs, uncertainties, evidence, and a suggested supplier.
12. The user makes the final decision by selecting **Mark as Preferred Supplier**.

SourcePilot ends there.

It does not execute procurement, communicate with suppliers, negotiate, place orders, manage logistics, or manage production.

The product should feel like one complete AI-assisted business workflow rather than a collection of unrelated AI features.

---

# 2. Problem Statement

Supplier sourcing often starts with incomplete information.

A user may initially know only:

> “I need 2,000 custom cosmetic bags made from recycled material for under $5 each.”

That request may still be missing information such as:

- dimensions;
- exact material;
- branding requirements;
- destination;
- required delivery timing;
- packaging requirements;
- certifications;
- acceptable MOQ.

Even after requirements are established, supplier information may differ in completeness and terminology.

Quotes may also be difficult to compare.

For example:

- one supplier includes tooling in unit cost;
- another lists tooling separately;
- one quote includes shipping;
- another does not;
- one supplier states a certification;
- another provides supporting evidence;
- one quote uses a different quantity;
- lead-time terminology may differ.

SourcePilot helps the user progressively turn this uncertainty into a structured sourcing decision.

It must clearly distinguish:

- known facts;
- missing information;
- conflicting information;
- user-entered information;
- AI-extracted information;
- supporting evidence;
- AI-assisted interpretation;
- final human decisions.

---

# 3. Product Goals

## 3.1 Turn an informal request into a usable sourcing brief

The user should not need to begin by completing a long procurement form.

SourcePilot should extract useful details from natural language and ask only the clarifying questions needed to make supplier evaluation meaningful.

## 3.2 Help the user identify plausible suppliers

SourcePilot should produce a small, manageable group of supplier candidates from a curated synthetic-but-realistic dataset.

The system should explain why each supplier appears relevant.

## 3.3 Preserve evidence and uncertainty

Important supplier claims and quote values should be supported by visible evidence where available.

Unknown or conflicting information must remain visible rather than being silently guessed.

## 3.4 Normalize quotes for meaningful comparison

Supplier quotations should be converted into a common structure while preserving their original values and context.

## 3.5 Explain tradeoffs

SourcePilot should help the user understand meaningful differences between suppliers rather than reducing the decision to an unexplained score.

## 3.6 Keep the human in control

SourcePilot assists with research, extraction, organization, comparison, and explanation.

The user approves the sourcing brief, selects the shortlist, verifies quote extraction, and makes the final supplier decision.

---

# 4. Non-Goals

The MVP is not intended to become:

- a procurement ERP;
- a supplier marketplace;
- a supplier portal;
- an RFQ communication system;
- an automated outreach platform;
- a negotiation system;
- a purchase-order system;
- a contract-management system;
- a payment platform;
- a logistics platform;
- a shipment tracker;
- an inventory system;
- a production-management system;
- a quality-control system;
- a customs or tariff platform;
- a multi-user enterprise application;
- a procurement analytics suite;
- a generalized AI assistant;
- an autonomous purchasing system.

If a feature primarily exists after the sourcing decision has been made, it is outside the MVP.

---

# 5. Target User

The primary user is an individual who needs to evaluate suppliers for a physical product.

Possible examples include:

- small-business owner;
- founder;
- product manager;
- sourcing specialist;
- operations manager.

The MVP assumes one user working independently.

The product does not need organizations, teams, roles, permissions, approval hierarchies, or collaboration features.

The target user:

- understands the product they want at a business level;
- may not initially know every sourcing specification;
- wants help structuring the request;
- wants supplier information to be explainable;
- wants quote data normalized;
- wants to understand uncertainty;
- remains responsible for deciding which supplier to pursue.

---

# 6. Core Use Case

A user wants to source:

> 2,000 custom cosmetic travel bags made from recycled material, with a target unit cost below $5 and delivery to Sydney before a target date.

SourcePilot helps the user:

1. structure the request;
2. identify missing requirements;
3. approve the completed brief;
4. discover approximately five relevant suppliers;
5. inspect supplier information and evidence;
6. shortlist up to three suppliers;
7. add supplier quotes;
8. extract and verify quote details;
9. compare suppliers against the approved brief;
10. understand tradeoffs and uncertainties;
11. review a suggested supplier;
12. record their own preferred supplier.

---

# 7. Main User-Facing Workflow

The primary workflow contains only five visible stages:

## Brief

Define and approve what is being sourced.

## Suppliers

Review candidates and approve a shortlist.

## Quotes

Add and verify quote information.

## Comparison

Review facts, requirements fit, evidence, uncertainties, and tradeoffs.

## Decision

Record the user's preferred supplier.

Local states such as **Processing**, **Needs Review**, **Approved**, or **Failed** may appear inside a stage.

SourcePilot should not expose a large global state machine to the user.

---

# 8. Primary Product Objects

The MVP contains six core product objects.

## Sourcing Project

The container for the complete sourcing workflow.

## Product Brief

The approved structured definition of what the user wants to source.

## Supplier Candidate

A supplier from the curated dataset that may satisfy the brief.

## Supplier Shortlist

Up to three suppliers selected by the user for quote comparison.

## Quote

Commercial information associated with one shortlisted supplier.

## Comparison

The combined evaluation of requirements, supplier data, quote data, evidence, and tradeoffs.

---

# 9. Stage 1 — Create Sourcing Project

The user starts by describing what they want to source.

Example:

> “I need 2,000 premium cosmetic bags using recycled material. They need our logo, should cost less than $5 each, and need to be delivered to Sydney before November.”

SourcePilot creates an initial structured brief.

The user should immediately see:

- project name;
- original request;
- extracted requirements;
- information that is unclear;
- important missing information;
- next required action.

The user can:

- rename the project;
- correct extracted information;
- remove incorrect information;
- add missing information;
- answer clarification questions.

The user remains in the **Brief** stage until the sourcing brief is approved.

---

# 10. Product Brief Information

The structured brief may contain:

## Product

- product name;
- product category;
- short description;
- requested quantity.

## Specifications

Depending on product category:

- material;
- dimensions;
- size or capacity;
- color;
- required features.

## Branding

- branding required;
- branding method if known;
- branding notes.

## Commercial Requirements

- target unit price;
- acceptable MOQ where relevant;
- destination;
- required delivery date or target delivery period.

## Compliance

- required certifications;
- preferred certifications;
- other product-specific compliance requirements.

## Packaging

- packaging requirements;
- labeling requirements.

SourcePilot should not force irrelevant fields onto every product category.

---

# 11. Requirement Importance

Every meaningful sourcing requirement may be classified as:

## Required

The supplier must satisfy the requirement.

Example:

**Material: recycled polyester**

## Preferred

Desirable but not mandatory.

Example:

**GRS certification preferred**

## Informational

Context that helps evaluate suppliers but should not qualify or disqualify them.

Example:

**Product intended for a premium skincare brand**

The user may change the importance of a requirement before approving the brief.

---

# 12. Clarification Experience

SourcePilot should identify missing or ambiguous information that materially affects supplier evaluation.

Questions should be:

- short;
- relevant;
- prioritized;
- limited in number.

Example:

**We need 3 more details before supplier discovery:**

1. What approximate dimensions should the bag have?
2. Which recycled material do you want?
3. When do you need the order delivered?

SourcePilot should not ask every theoretically possible sourcing question.

The goal is a brief that is **sufficiently complete for comparison**, not exhaustive procurement documentation.

---

# 13. Brief Readiness

The Brief stage may show these local states:

## In Progress

Important information is still missing.

## Ready for Review

SourcePilot believes the brief contains enough information for supplier discovery.

## Approved

The user has explicitly confirmed the brief.

The UI may show a simple completeness summary such as:

> 8 of 10 important sourcing details completed.

It should not imply unrealistic precision through arbitrary percentages.

---

# 14. Human Approval Point 1 — Approve Brief

Supplier discovery should only occur after the user approves the sourcing brief.

Before approval, the user should see:

- complete structured requirements;
- required requirements;
- preferred requirements;
- informational context;
- unresolved optional information;
- warnings;
- uncertainties;
- original request.

Available actions:

**Approve Brief**

**Continue Editing**

After approval, the project proceeds to **Suppliers**.

If the brief changes later, SourcePilot must determine whether downstream information may now be stale.

Visible brief-version history is not part of the MVP.

---

# 15. Stage 2 — Supplier Discovery

Supplier discovery uses a **curated synthetic-but-realistic supplier dataset**.

This is the official supplier source for the MVP.

Live supplier discovery from public websites or external supplier directories is deferred.

The dataset should contain realistic differences in:

- location;
- categories;
- manufacturing capabilities;
- materials;
- MOQ;
- typical lead times;
- certifications;
- indicative pricing where available;
- supporting evidence.

The product experience should still treat supplier claims as evidence-backed information so that live research could later replace or supplement the curated source without changing the core workflow.

---

# 16. Supplier Candidate Set

A standard demo sourcing project should produce approximately:

**5 supplier candidates**

This is intentionally small.

The user should be able to compare candidates meaningfully rather than scroll through a marketplace-sized result set.

The system should not optimize for quantity of supplier results.

---

# 17. Supplier Candidate Information

Each supplier candidate should show relevant information such as:

- supplier name;
- location;
- relevant product categories;
- capabilities;
- supported materials;
- MOQ if known;
- typical lead time if known;
- certifications;
- relevant pricing information if available;
- relevant markets or experience if included in the dataset;
- requirement fit;
- supporting evidence;
- potential concerns;
- unknown information.

Missing information must be shown as unknown rather than inferred.

---

# 18. Supplier Requirement Evaluation

SourcePilot must not display a numeric supplier score such as:

> 92% Match

Instead, individual requirements use explainable states:

## Meets

Available evidence indicates the supplier satisfies the requirement.

## Does Not Meet

Available information indicates the supplier does not satisfy the requirement.

## Unknown

There is not enough information to determine whether the requirement is satisfied.

## Conflict

Available information contains contradictory evidence.

These states should be visible in both candidate review and later comparison.

---

# 19. Supplier Explanation

Each candidate should provide a concise explanation.

Example:

**Meets**

- manufactures cosmetic travel bags;
- supports recycled polyester;
- MOQ is compatible with requested quantity.

**Preferred requirement**

- sustainability certification appears supported.

**Unknown**

- exact production lead time for this order has not been quoted.

**Concern**

- indicative pricing is near the user's target limit.

The explanation should rely on concrete requirements and evidence rather than a hidden overall ranking.

---

# 20. Supplier Evidence

Important supplier claims should expose their supporting evidence where available.

Example:

**Claim**

Supports recycled polyester products

**Evidence**

Product capability record / supplier catalog evidence

Example:

**Claim**

GRS certified

**Evidence**

Certification record

Evidence-related states may include:

- Supported;
- Partially Supported;
- Unknown;
- Conflict.

SourcePilot should never imply that unavailable evidence proves a claim is false.

---

# 21. Supplier Review Actions

For each supplier candidate, the user can:

- add to shortlist;
- remove from shortlist;
- dismiss from current consideration;
- restore a dismissed candidate;
- add private notes;
- inspect requirement fit;
- inspect available evidence.

Dismissing a supplier should not permanently delete supplier information.

---

# 22. Human Approval Point 2 — Supplier Shortlist

The maximum approved shortlist for the MVP is:

**3 suppliers**

The user decides which suppliers move forward.

SourcePilot may identify promising candidates but must not automatically approve the shortlist.

Before approval, show:

- selected suppliers;
- required requirement status;
- preferred requirement status;
- important unknowns;
- important conflicts;
- unresolved concerns.

Actions:

**Approve Shortlist**

**Continue Reviewing**

After approval, the project proceeds to **Quotes**.

---

# 23. Stage 3 — Quotes

The Quotes stage is used to add commercial information for shortlisted suppliers.

SourcePilot does not send RFQs or contact suppliers.

The user is responsible for obtaining the quotes outside SourcePilot.

For each shortlisted supplier, a quote may be added by:

1. uploading a PDF quotation; or
2. entering the quote manually.

Spreadsheet quote upload is not part of the MVP.

---

# 24. Quote Local States

A quote may have these local states:

## Not Added

No quote exists for the supplier.

## Processing

A PDF is currently being interpreted.

## Needs Review

Information has been extracted but requires user verification.

## Confirmed

The user has verified the normalized quote data.

## Failed

The PDF could not be reliably processed.

Manual entry remains available.

The overall project should remain usable even if one supplier has no usable quote.

---

# 25. Quote Information

A normalized quote may contain:

## Commercial

- quoted quantity;
- unit price;
- original currency;
- MOQ;
- sample cost;
- tooling or setup cost;
- packaging cost if stated;
- shipping cost if stated.

## Timeline

- sample lead time if stated;
- production lead time;
- shipping time if separately stated;
- total stated lead time if provided.

## Terms

- payment terms;
- incoterm if provided;
- quote validity if provided;
- warranty if relevant.

## Compliance

- certifications stated in the quote;
- compliance notes.

## Other

- exclusions;
- special conditions;
- supplier notes.

Missing fields remain explicitly unknown.

---

# 26. PDF Quote Extraction Review

Extracted quote data should never become confirmed automatically.

After processing, the user sees:

- extracted fields;
- uncertain fields;
- missing fields;
- source evidence where available;
- any conflicts found.

Example:

**Unit Price**

USD 4.22

**Source**

Quotation, page 2

The user can:

- accept extracted values;
- edit incorrect values;
- mark a value unknown;
- manually add missing values.

Once reviewed, the user selects:

**Confirm Quote**

Only confirmed quotes are treated as reliable inputs to the main comparison.

---

# 27. Manual Quote Entry

The user must be able to create a quote without uploading a document.

Manual entry supports:

- all important normalized quote fields;
- unknown values;
- optional notes.

This is also the fallback when:

- PDF extraction fails;
- a quote is incomplete;
- a supplier provided pricing through another channel;
- the user wants to correct the normalized record directly.

---

# 28. Quote Evidence and Corrections

Where possible, an extracted value should show its source.

If the user corrects a value, SourcePilot should clearly treat the user-confirmed value as the current comparison value.

The product does not need a complex visible edit-history interface.

The essential behavior is:

- AI extraction is reviewable;
- user corrections are allowed;
- confirmed user data takes precedence in comparison;
- original evidence remains inspectable where available.

---

# 29. Conflicting Quote Information

If a PDF contains conflicting values, SourcePilot should not silently choose one.

Example:

Page 1:

**Lead time: 20 days**

Page 3:

**Production: 30–35 days**

The quote should become:

**Needs Review**

The conflicting evidence should be shown to the user.

The user chooses the value or interpretation to use.

---

# 30. Currency Handling

SourcePilot preserves the original currency of every quote.

Automatic FX conversion is not part of the MVP.

If compared quotes use different currencies, SourcePilot should clearly warn:

> These quotes use different currencies and cannot be directly compared on price without external conversion.

The system should continue comparing non-price criteria where meaningful.

The primary portfolio demo scenario must use one currency across all quotes so the complete comparison remains straightforward.

---

# 31. Different Quoted Quantities

If suppliers quote different quantities, SourcePilot must clearly flag the difference.

Example:

**Requested quantity:** 2,000

Supplier A:

**Quoted quantity:** 2,000

Supplier B:

**Quoted quantity:** 5,000

SourcePilot should not present the prices as a clean equivalent comparison without highlighting the quantity mismatch.

---

# 32. Stage 4 — Comparison

The Comparison stage becomes available when at least two shortlisted suppliers have confirmed quote information.

The comparison combines:

- approved product requirements;
- curated supplier information;
- supplier evidence;
- confirmed quote data;
- deterministic factual comparisons;
- AI-assisted tradeoff explanation.

Raw facts should remain visible alongside analysis.

---

# 33. Comparison View

The comparison should include relevant fields such as:

| Criteria | Supplier A | Supplier B | Supplier C |
|---|---|---|---|
| Unit price | USD 4.22 | USD 3.95 | USD 4.50 |
| Quoted quantity | 2,000 | 2,000 | 2,000 |
| MOQ | 500 | 1,000 | 300 |
| Production lead time | 25 days | 38 days | 21 days |
| Tooling | USD 150 | Included | USD 220 |
| Shipping | USD 720 | USD 650 | Unknown |
| Required material | Meets | Meets | Meets |
| Required certification | Meets | Meets | Unknown |
| Preferred requirement | Meets | Does Not Meet | Meets |

The system should make incomplete information obvious.

There is no user-configurable weighted scoring in the MVP.

There is no hidden universal supplier score.

---

# 34. Comparison Requirement States

Every meaningful requirement should use the same explainable evaluation states:

**Meets**

**Does Not Meet**

**Unknown**

**Conflict**

Required requirements should be visually distinguishable from preferred and informational requirements.

A supplier that fails a required requirement should be clearly flagged but should not disappear automatically.

The user remains responsible for deciding whether to proceed.

---

# 35. Tradeoff Analysis

SourcePilot should explain meaningful differences between suppliers.

Example:

> Supplier B has the lowest unit price but the longest stated production lead time and does not currently satisfy the preferred sustainability certification.

> Supplier A costs more per unit but meets all currently verified required requirements and provides stronger supporting evidence.

> Supplier C has the shortest stated production lead time, but shipping cost and one required certification remain unknown.

The analysis must distinguish facts from interpretation.

It should not manufacture differences where the available information does not justify them.

---

# 36. Suggested Supplier

SourcePilot may identify a:

**Suggested Supplier**

or:

**Suggested Supplier to Investigate First**

The wording must remain advisory.

Example:

**Suggested Supplier to Investigate First**

Supplier A

**Supporting reasons**

- meets all currently confirmed required requirements;
- quote uses the requested quantity;
- production lead time fits the user's requirement;
- required certification is supported by evidence.

**Tradeoffs**

- unit price is higher than Supplier B;
- tooling is charged separately.

**Uncertainty**

- shipping estimate has not been independently verified.

SourcePilot should never claim that a supplier is objectively the “best supplier.”

---

# 37. Insufficient Information

SourcePilot must be allowed to provide no suggestion.

Example:

> There is not enough confirmed information to suggest one supplier yet. Two suppliers are missing shipping cost information and one required certification remains unverified.

This is preferable to forcing a recommendation.

---

# 38. Stage 5 — Decision

The final stage records the user's decision.

The primary action is:

**Mark as Preferred Supplier**

The user may also choose:

**No Decision Yet**

The user can return to:

- Brief;
- Suppliers;
- Quotes;
- Comparison

before recording a decision.

Selecting a preferred supplier means only:

> This is the supplier the user currently prefers based on the information inside SourcePilot.

It does not mean:

- an order has been placed;
- a contract exists;
- payment occurred;
- the supplier accepted the business;
- procurement is complete.

---

# 39. Human Approval and Review Points

The MVP has four meaningful human checkpoints.

## 1. Brief Approval

The user confirms:

> These are the requirements suppliers should be evaluated against.

## 2. Shortlist Approval

The user confirms:

> These are the suppliers I want to compare further.

## 3. Quote Verification

The user confirms:

> These normalized quote values are accurate enough to use in comparison.

This is a data-review checkpoint rather than a business decision.

## 4. Final Decision

The user chooses:

**Mark as Preferred Supplier**

The system never performs this final action automatically.

---

# 40. Stale Downstream Information

SourcePilot does not expose visible brief-version history in the MVP.

However, changing important requirements after supplier research or quote comparison may make downstream results stale.

Example:

Original:

**Recycled material — Preferred**

Changed to:

**Recycled material — Required**

SourcePilot should warn:

> Your sourcing requirements changed. Existing supplier evaluations may no longer reflect the current brief.

The relevant supplier evaluation should be marked as needing re-evaluation.

Similarly:

- changing a confirmed quote should mark comparison results as stale;
- correcting supplier information may affect comparison results.

The user should be able to refresh or re-evaluate the affected stage.

The product does not need to expose internal version numbers.

---

# 41. Error and Recovery Flows

## Incomplete Initial Request

If SourcePilot cannot create a usable brief:

- show what was understood;
- clearly identify what is missing;
- ask targeted questions.

Never invent missing product requirements.

---

## Product Category Is Unclear

Ask the user to clarify or confirm the product category before supplier discovery.

Do not guess if the category materially changes supplier selection.

---

## No Suitable Supplier Candidates

If the curated dataset contains no supplier satisfying all required requirements:

show:

**No supplier currently meets all required requirements.**

Explain which requirements cause the conflict.

Possible user actions:

- revise the brief;
- inspect suppliers that meet some but not all requirements.

Do not fabricate a supplier.

---

## Supplier Information Is Missing

Display:

**Unknown**

Do not infer missing MOQ, certifications, pricing, lead times, or capabilities.

---

## Supplier Evidence Conflicts

Display:

**Conflict**

Show the conflicting information.

Example:

- supplier profile says certification is active;
- certification evidence appears expired.

Do not silently choose one source.

---

## Quote PDF Cannot Be Processed

Show:

**We couldn't reliably extract this quotation.**

Offer:

- retry;
- upload a clearer PDF;
- enter the quote manually.

A failed upload must not block the project.

---

## Partial Quote Extraction

Extract only reliable information.

Mark other fields:

**Unknown**

or:

**Needs Review**

Allow manual completion.

---

## Unsupported File Type

Explain that SourcePilot MVP supports:

- PDF quote upload;
- manual quote entry.

Offer manual entry.

---

## Quote Uses Different Currency

Preserve the original currency.

Warn that price cannot be directly compared without external conversion.

Do not silently convert it.

---

## Quote Uses Different Quantity

Highlight the mismatch.

Do not present price comparison as directly equivalent without warning.

---

## User Changes Requirements After Supplier Discovery

Mark supplier evaluation as potentially stale.

Prompt the user to re-evaluate suppliers.

---

## User Changes Requirements After Quotes Exist

Keep existing quote records, but warn:

> These quotes were obtained against an earlier set of sourcing requirements and may no longer be directly applicable.

The user may still inspect them.

---

## User Corrects Confirmed Quote

Mark the existing comparison as stale until refreshed.

---

## Analysis Cannot Reach a Reliable Suggestion

Clearly communicate why.

Do not invent certainty.

---

# 42. Important Edge Cases

## Only One Supplier Has a Confirmed Quote

Allow quote review.

Disable meaningful multi-supplier comparison until another confirmed quote exists.

---

## User Shortlists One Supplier

Allow it.

Explain that side-by-side comparison requires at least two suppliers.

---

## User Shortlists More Than Three Suppliers

Prevent approval until the shortlist contains three or fewer suppliers.

---

## Supplier Has a Revised Quote

For MVP, the new quote replaces the active quote used in comparison.

Full negotiation history and quote version history are deferred.

---

## Supplier Fails a Required Requirement but Has the Lowest Price

Keep the supplier visible.

Clearly show:

**Does Not Meet Required Requirement**

The user makes the final decision.

---

## Certification Cannot Be Verified

Show:

**Unknown**

Do not interpret lack of evidence as proof the supplier lacks the certification.

---

## Suppliers Have Nearly Identical Results

Do not manufacture a meaningful ranking difference.

It is acceptable to say:

> These suppliers are currently difficult to distinguish based on available information.

---

## User Disagrees With Suggested Supplier

Allow any shortlisted supplier to be marked preferred.

The system should not block or discourage this.

---

## No Supplier Is Clearly Suggestible

Do not force a suggested supplier.

---

# 43. Dashboard

The dashboard should remain minimal.

Each project may show:

- project name;
- product;
- current main stage;
- shortlist count;
- confirmed quote count;
- whether comparison is ready;
- preferred supplier if recorded;
- last updated.

The dashboard should not contain:

- spend analytics;
- procurement KPIs;
- supplier-performance analytics;
- order metrics;
- shipping metrics;
- enterprise reporting.

---

# 44. Project Workspace

Each project contains the five primary sections:

**Brief**

**Suppliers**

**Quotes**

**Comparison**

**Decision**

An optional simple overview/header may summarize:

- current stage;
- next action;
- important warning;
- preferred supplier if selected.

No additional procurement modules are required.

---

# 45. User-Editable Information

## Project

The user can edit:

- project name;
- project notes.

## Brief

The user can edit:

- structured requirements;
- requirement importance;
- missing values;
- clarification answers.

## Suppliers

The user can edit:

- shortlist selection;
- dismissal state;
- personal notes.

Curated supplier evidence should not be editable as if the user authored the source.

## Quotes

The user can edit:

- extracted values;
- manually entered values;
- unknown fields;
- notes.

## Final Decision

The user can edit:

- preferred supplier;
- decision notes.

---

# 46. Evidence Principles

Evidence and uncertainty are first-class product principles.

## Principle 1 — Claims require support when support is available

Important supplier claims should point to their evidence.

## Principle 2 — Unknown is a valid state

Missing information must not be filled with invented assumptions.

## Principle 3 — Missing does not mean negative

**Certification unknown** is not the same as **not certified**.

## Principle 4 — Conflict must remain visible

Contradictory information should be surfaced rather than silently resolved.

## Principle 5 — Evidence and interpretation are different

Example:

**Evidence**

Production lead time is stated as 25 days.

**Interpretation**

That lead time appears compatible with the requested schedule.

## Principle 6 — User-confirmed corrections matter

A user must be able to correct AI-extracted information before it influences the final comparison.

---

# 47. Recommendation Principles

A suggested supplier should always explain:

- relevant required requirements;
- preferred requirements;
- important quote facts;
- supporting evidence;
- tradeoffs;
- missing information;
- conflicts;
- meaningful uncertainty.

The system must avoid:

- unexplained rankings;
- numeric match scores;
- claims of objective superiority;
- false precision;
- hiding required-requirement failures;
- forcing a recommendation.

---

# 48. Official MVP Boundary

The first public SourcePilot release contains exactly this primary workflow:

**Natural-language sourcing request**

↓

**Structured brief + clarification**

↓

**User approves brief**

↓

**Supplier discovery from curated synthetic-but-realistic dataset**

↓

**User shortlists up to 3 suppliers**

↓

**User uploads PDF quotes or enters quotes manually**

↓

**System extracts and normalizes quote data**

↓

**User verifies quote data**

↓

**System compares suppliers and explains tradeoffs**

↓

**System may identify a Suggested Supplier**

↓

**User selects Mark as Preferred Supplier**

This is the product boundary that technical architecture must protect.

---

# 49. Explicitly Deferred Features

## Live Supplier Research

- public web supplier discovery;
- supplier-directory integrations;
- live company research;
- live certification verification.

---

## Supplier Communication

- RFQ sending;
- supplier email;
- automated outreach;
- follow-ups;
- messaging;
- supplier responses inside SourcePilot.

---

## Negotiation

- AI negotiation;
- counteroffers;
- negotiation histories;
- automated commercial discussion.

---

## Procurement Execution

- purchase requests;
- purchase orders;
- contracts;
- approvals beyond the SourcePilot workflow;
- invoices;
- payments.

---

## Logistics

- freight booking;
- shipment tracking;
- customs;
- duties;
- import management;
- live landed-cost calculation.

---

## Production Management

- factory milestones;
- production tracking;
- sampling workflows;
- inspections;
- quality control;
- defect management.

---

## Supplier Platform Features

- supplier accounts;
- supplier portal;
- onboarding;
- bidding;
- supplier-managed profiles;
- marketplace functionality.

---

## Enterprise Features

- organizations;
- teams;
- RBAC;
- SSO;
- enterprise approval chains;
- compliance workflows.

---

## Advanced Procurement Analytics

- spend analytics;
- category analytics;
- historical supplier scorecards;
- savings analysis;
- enterprise dashboards.

---

## Advanced Decision Features

- user-configurable weighting;
- numeric supplier scoring;
- advanced optimization;
- automatic FX conversion;
- sophisticated landed-cost modeling.

---

## Advanced AI Features

- autonomous purchasing;
- autonomous supplier outreach;
- autonomous negotiation;
- continuous supplier monitoring;
- generalized AI chat;
- workflow builders;
- user-configurable agents.

---

## Additional Quote Formats

Spreadsheet uploads and other document formats are deferred.

The MVP officially supports:

- PDF;
- manual entry.

---

# 50. Primary Demo Scenario

The portfolio demonstration should use one intentionally designed scenario.

## Product

Custom cosmetic travel bag.

## Request

2,000 units.

## Requirements

Example requirements:

- recycled material;
- custom logo;
- target unit cost below USD 5;
- delivery to Sydney;
- target delivery timing;
- preferred sustainability certification.

## Candidate Suppliers

Approximately:

**5 suppliers**

Each should demonstrate meaningful differences in:

- requirement fit;
- capabilities;
- MOQ;
- lead time;
- evidence completeness;
- certification status;
- indicative commercial information.

## Shortlist

User selects:

**3 suppliers**

## Quotes

All three demo quotes use:

**USD**

to avoid FX complexity in the primary experience.

The quotes should create realistic tradeoffs.

Example:

### Supplier A

- slightly higher price;
- meets all required requirements;
- strongest evidence;
- acceptable lead time.

### Supplier B

- lowest price;
- longer production lead time;
- preferred certification not supported.

### Supplier C

- fastest production;
- higher tooling cost;
- one important field unknown.

The scenario should contain at least one uncertainty or conflict so evidence review is genuinely demonstrated.

---

# 51. Acceptance Criteria

The MVP is product-complete when a new user can complete the full sourcing journey without developer intervention.

## Project Creation

A user can create a sourcing project from a natural-language request.

## Structured Brief

SourcePilot converts the request into editable structured sourcing requirements.

## Clarification

The system identifies important missing or ambiguous information without inventing it.

## Requirement Importance

The user can classify requirements as:

- Required;
- Preferred;
- Informational.

## Brief Approval

The user explicitly approves the brief before supplier discovery.

## Curated Supplier Discovery

SourcePilot returns approximately five relevant candidates from the curated synthetic-but-realistic supplier dataset.

## Supplier Explainability

The user can see why each candidate may or may not fit the approved requirements.

## Evidence Visibility

Important supplier claims expose supporting evidence where available.

## Supplier Evaluation States

Requirements use:

- Meets;
- Does Not Meet;
- Unknown;
- Conflict.

No numeric supplier match score is required.

## Shortlisting

The user can shortlist and approve no more than three suppliers.

## PDF Quote Upload

The user can upload a supported PDF quote for a shortlisted supplier.

## Manual Quote Entry

The user can create or complete a quote manually.

## Quote Extraction

SourcePilot extracts the required commercial information from the supported demo PDFs.

## Quote Verification

Extracted quote information requires user review before becoming confirmed.

## Error Recovery

A failed or partial extraction can be completed manually without blocking the workflow.

## Original Currency

Quote values retain their original currency.

## Currency Warning

Different currencies trigger a clear comparison warning rather than automatic conversion.

## Comparison Readiness

At least two confirmed supplier quotes allow the comparison stage to proceed.

## Side-by-Side Comparison

The user can inspect supplier requirements and quote information together.

## Requirement Fit

The comparison visibly shows:

- Meets;
- Does Not Meet;
- Unknown;
- Conflict.

## Tradeoff Explanation

SourcePilot explains meaningful supplier differences without hiding missing or conflicting data.

## Suggested Supplier

SourcePilot may identify a **Suggested Supplier** or **Suggested Supplier to Investigate First** when evidence supports doing so.

## Insufficient Evidence

SourcePilot can explicitly decline to suggest one supplier when available information is insufficient.

## Human Decision

Only the user can select:

**Mark as Preferred Supplier**

## Final Boundary

Recording the preferred supplier ends the MVP workflow.

No purchasing, contracting, payment, communication, logistics, or production action occurs.

## Stale Results

Changing requirements or confirmed quote values causes affected downstream analysis to be identified as needing re-evaluation.

## Portfolio Quality

The full primary demo scenario can be completed cleanly from beginning to end with realistic data, useful empty/error states, visible uncertainty, and coherent terminology.

---

# 52. Portfolio Quality Constraint

SourcePilot must remain realistic for one developer to complete and polish.

When choosing between:

**more features**

and

**better depth, reliability, explainability, testing, error handling, and UX within the core flow**

the MVP should choose the second.

A complete five-stage workflow is more important than broad procurement coverage.

A feature should generally be rejected from MVP if it does not materially improve:

- brief creation;
- supplier evaluation;
- quote normalization;
- comparison;
- evidence visibility;
- uncertainty handling;
- final human decision.

---

# 53. Locked MVP Decisions

The following product decisions are now fixed for the first SourcePilot release.

1. The visible workflow is:

   **Brief → Suppliers → Quotes → Comparison → Decision**

2. Supplier discovery uses a **curated synthetic-but-realistic supplier dataset**.

3. Live public supplier research is deferred.

4. A typical demo returns approximately **5 supplier candidates**.

5. A user may approve a maximum of **3 shortlisted suppliers**.

6. Supplier evaluation does not use numeric match scores.

7. Requirement evaluation uses:

   **Meets / Does Not Meet / Unknown / Conflict**

8. Requirement importance uses:

   **Required / Preferred / Informational**

9. User-configurable scoring or weighting is deferred.

10. The MVP does not expose visible brief-version history.

11. Requirement changes can make downstream supplier analysis or comparison stale.

12. Quote input supports:

   **PDF upload + manual entry**

13. Spreadsheet quote upload is deferred.

14. AI-extracted quote information requires human verification.

15. Automatic FX conversion is not an MVP feature.

16. Quotes preserve their original currency.

17. The primary demo uses one currency.

18. Recommendation language uses:

   **Suggested Supplier**

   or:

   **Suggested Supplier to Investigate First**

19. The system may explicitly provide no supplier suggestion when evidence is insufficient.

20. The final action is:

   **Mark as Preferred Supplier**

21. Selecting a preferred supplier does not create a purchase, contract, order, or external action.

22. Supplier outreach, RFQ sending, negotiation, procurement execution, payments, logistics, production management, and supplier portals are outside scope.

23. Organizations, teams, RBAC, and enterprise SaaS functionality are outside scope.

24. General-purpose AI chat is outside scope.

25. The project is optimized for a polished one-developer open-source portfolio implementation.

---

# 54. Resolved Product Decisions

The remaining product questions have been resolved and are now locked for V1.

## 54.1 Brief Readiness

A brief is sufficiently complete for **Ready for Review** when it contains enough information to meaningfully evaluate suppliers.

The V1 minimum is:

- product/category;
- quantity;
- destination;
- delivery target;
- the important category-specific specifications needed to evaluate suppliers.

Category-specific specifications should be limited to information that materially affects supplier evaluation for the selected product category.

**Target price is optional** and does not block brief readiness when absent.

SourcePilot should not require every theoretically possible procurement field before the brief can be approved.

---

## 54.2 Supplier Evidence in the Curated Demo Dataset

Each synthetic curated supplier should contain only enough evidence to support the claims actually displayed in the product.

The practical V1 evidence package may include:

- capability or product/category evidence;
- MOQ information where available;
- lead-time information where available;
- certification evidence where relevant;
- other evidence only when needed to support a claim shown to the user.

Missing evidence remains **Unknown** where appropriate.

The MVP must not grow into a large evidence library, generalized evidence-management system, or supplier knowledge base.

---

## 54.3 Preferred Supplier Can Be Changed

**Mark as Preferred Supplier** is freely changeable in V1.

The user may:

- select a preferred supplier;
- change the preferred supplier later;
- clear the preferred supplier if needed.

Changing the preferred supplier does not require reopening the workflow.

V1 does not include:

- decision-history browsing;
- decision versioning;
- reopening workflows;
- approval history.

The current preferred supplier is the only decision state the MVP needs.

---

# 55. Architecture Handoff

The approved Technical Architecture v0.2 must preserve and support the product behavior defined in this specification without expanding its scope.

At minimum, the approved architecture must remain capable of supporting:

- natural-language project intake;
- structured and editable sourcing requirements;
- targeted clarification of missing information;
- explicit brief approval;
- a curated supplier source;
- supplier requirement evaluation using explainable states;
- evidence-backed supplier claims;
- shortlist selection with a maximum of three approved suppliers;
- PDF quote upload;
- manual quote entry;
- extraction of structured quote fields;
- user verification and correction of extracted values;
- visible unknown and conflicting information;
- preservation of original quote currencies;
- side-by-side supplier and quote comparison;
- factual comparison separated from AI-assisted interpretation;
- tradeoff explanations;
- optional suggested-supplier output;
- the ability to provide no suggestion when evidence is insufficient;
- stale-result detection when important upstream information changes;
- recoverable failures rather than dead-end workflows;
- explicit human control at brief approval, shortlist approval, quote verification, and final decision;
- recording a preferred supplier without triggering any external procurement action.

The approved architecture must also preserve the product's central principles:

**evidence over unsupported claims, uncertainty over invented certainty, explainability over opaque scoring, and human decisions over autonomous purchasing.**

No architectural change should require expanding SourcePilot beyond the five-stage MVP:

**Brief → Suppliers → Quotes → Comparison → Decision.**
