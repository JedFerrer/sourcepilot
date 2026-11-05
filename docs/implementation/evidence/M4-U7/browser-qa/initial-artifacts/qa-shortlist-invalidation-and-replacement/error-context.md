# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: qa.spec.ts >> shortlist invalidation and replacement
- Location: qa.spec.ts:68:71

# Error details

```
Error: expect(locator).toBeEnabled() failed

Locator: getByRole('region', { name: 'Quotes', exact: true }).getByRole('article').filter({ has: getByRole('heading', { name: 'Harbor Pouch Works', exact: true }) }).getByLabel('Upload PDF quote')
Expected: enabled
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeEnabled" getByRole('region', { name: 'Quotes', exact: true }).getByRole('article').filter({ has: getByRole('heading', { name: 'Harbor Pouch Works', exact: true }) }).getByLabel('Upload PDF quote') with timeout 15000ms
  - waiting for getByRole('region', { name: 'Quotes', exact: true }).getByRole('article').filter({ has: getByRole('heading', { name: 'Harbor Pouch Works', exact: true }) }).getByLabel('Upload PDF quote')

```

```yaml
- alert
- main:
  - paragraph: Demo session ready
  - region "E2E shortlist invalidation and replacement 0":
    - link "Back to projects":
      - /url: /
    - paragraph: "Current stage: Decision"
    - paragraph: Review the comparison and record your choice. AI analysis is optional.
    - 'link "Next: Review comparison and choose a preferred supplier"':
      - /url: "#decision-choice"
    - heading "E2E shortlist invalidation and replacement 0" [level=1]
    - paragraph: "Preferred supplier: No Decision Yet"
    - navigation "Sourcing workflow stages":
      - list:
        - listitem:
          - link "Brief":
            - /url: "#brief"
            - strong: Brief
        - listitem:
          - link "Suppliers":
            - /url: "#suppliers"
            - strong: Suppliers
        - listitem:
          - link "Quotes":
            - /url: "#quotes"
            - strong: Quotes
        - listitem:
          - link "Comparison":
            - /url: "#comparison"
            - strong: Comparison
        - listitem:
          - link "Decision":
            - /url: "#decision"
            - strong: Decision
    - text: Rename project
    - textbox "Rename project": E2E shortlist invalidation and replacement 0
    - button "Save name"
    - region "Original sourcing request":
      - heading "Original sourcing request" [level=2]
      - paragraph: Source 2,000 custom cosmetic travel bags made from recycled polyester with a custom logo. Target unit cost below USD 5, delivery to Sydney, preferred GRS certification. Delivery timing is not decided yet.
    - region "Sourcing Brief":
      - heading "Sourcing Brief" [level=2]
      - paragraph: "Readiness: Approved"
      - paragraph: Approved on 11/4/2026
      - paragraph: No required information is missing.
      - heading "Product and delivery" [level=3]
      - text: Product name
      - textbox "Product name": custom cosmetic travel bags
      - text: Category
      - textbox "Category": cosmetic travel bags
      - text: Requested quantity
      - spinbutton "Requested quantity": "2000"
      - text: Destination
      - textbox "Destination": Sydney
      - text: Delivery target type
      - combobox "Delivery target type":
        - option "Not set"
        - option "Date" [selected]
        - option "Period"
      - text: Delivery date
      - textbox "Delivery date": 2026-12-15
      - text: Target unit price (optional)
      - spinbutton "Target unit price (optional)": "5.0000"
      - heading "Sourcing requirements" [level=3]
      - group "Requirement 1":
        - text: Requirement 1 Kind
        - combobox "Kind":
          - option "MATERIAL" [selected]
          - option "CERTIFICATION"
          - option "MOQ"
          - option "QUANTITY"
          - option "UNIT PRICE"
          - option "PRODUCTION LEAD TIME"
          - option "DELIVERY"
          - option "CAPABILITY"
          - option "INFORMATIONAL"
        - text: Value
        - textbox "Value": recycled polyester
        - text: Importance
        - combobox "Importance":
          - option "Not set"
          - option "Required" [selected]
          - option "Preferred"
          - option "Informational"
        - text: Notes (optional)
        - textbox "Notes (optional)"
        - button "Remove requirement"
      - group "Requirement 2":
        - text: Requirement 2 Kind
        - combobox "Kind":
          - option "MATERIAL"
          - option "CERTIFICATION"
          - option "MOQ"
          - option "QUANTITY"
          - option "UNIT PRICE"
          - option "PRODUCTION LEAD TIME"
          - option "DELIVERY"
          - option "CAPABILITY" [selected]
          - option "INFORMATIONAL"
        - text: Capability
        - combobox "Capability":
          - option "PRODUCT CATEGORY"
          - option "CUSTOM BRANDING" [selected]
          - option "BRANDING METHOD"
          - option "PRODUCT FEATURE"
          - option "MANUFACTURING CAPABILITY"
        - text: Custom branding
        - combobox "Custom branding":
          - option "Yes" [selected]
          - option "No"
        - text: Importance
        - combobox "Importance":
          - option "Not set"
          - option "Required" [selected]
          - option "Preferred"
          - option "Informational"
        - text: Notes (optional)
        - textbox "Notes (optional)"
        - button "Remove requirement"
      - group "Requirement 3":
        - text: Requirement 3 Kind
        - combobox "Kind":
          - option "MATERIAL"
          - option "CERTIFICATION" [selected]
          - option "MOQ"
          - option "QUANTITY"
          - option "UNIT PRICE"
          - option "PRODUCTION LEAD TIME"
          - option "DELIVERY"
          - option "CAPABILITY"
          - option "INFORMATIONAL"
        - text: Value
        - textbox "Value": grs
        - text: Importance
        - combobox "Importance":
          - option "Not set"
          - option "Required"
          - option "Preferred" [selected]
          - option "Informational"
        - text: Notes (optional)
        - textbox "Notes (optional)"
        - button "Remove requirement"
      - button "Add requirement"
      - heading "Informational attributes" [level=3]
      - button "Add attribute"
      - button "Save Brief"
    - region "Suppliers":
      - heading "Suppliers" [level=2]
      - button "Re-discover and re-evaluate"
      - region "Shortlist":
        - heading "Shortlist" [level=3]
        - paragraph: 2 selected · maximum 3 for approval
        - status: Shortlist approved. The project is ready for Quotes.
        - button "Review selected suppliers"
      - article:
        - heading "Cedar Pack Co" [level=3]
        - paragraph: Thailand · Fictional bag maker with a high general minimum order.
        - paragraph: "MOQ: 5000 · Typical lead time: 28 days"
        - paragraph: "Indicative price: 3.7000 USD"
        - paragraph: "Capabilities: CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
        - heading "Requirement fit" [level=4]
        - list:
          - listitem:
            - text: "MATERIAL (REQUIRED): recycled polyester —"
            - strong: UNKNOWN
          - listitem:
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: UNKNOWN
          - listitem:
            - text: "CERTIFICATION (PREFERRED): grs —"
            - strong: UNKNOWN
        - paragraph: "General MOQ compatibility: DOES NOT MEET"
        - group: Available evidence
        - button "Explain this supplier"
        - button "Add to shortlist"
        - button "Dismiss"
        - text: Private notes for Cedar Pack Co
        - textbox "Private notes for Cedar Pack Co"
        - button "Save notes" [disabled]
      - article:
        - heading "Harbor Pouch Works" [level=3]
        - paragraph: Vietnam · Fictional maker of custom cosmetic travel bags and small textile accessories.
        - paragraph: "MOQ: 1000 · Typical lead time: 32 days"
        - paragraph: "Indicative price: 4.6000 USD"
        - paragraph: "Capabilities: BRANDING_METHOD: screen print; CERTIFICATION: grs; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
        - heading "Requirement fit" [level=4]
        - list:
          - listitem:
            - text: "MATERIAL (REQUIRED): recycled polyester —"
            - strong: MEETS
            - text: "· Evidence: Synthetic material sheet"
          - listitem:
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: MEETS
            - text: "· Evidence: Synthetic branding sheet"
          - listitem:
            - text: "CERTIFICATION (PREFERRED): grs —"
            - strong: MEETS
            - text: "· Evidence: Synthetic current GRS record"
        - paragraph: "General MOQ compatibility: MEETS"
        - group: Available evidence
        - button "Explain this supplier"
        - button "Remove from shortlist"
        - button "Dismiss"
        - text: Private notes for Harbor Pouch Works
        - textbox "Private notes for Harbor Pouch Works"
        - button "Save notes" [disabled]
      - article:
        - heading "Moss Thread Bags" [level=3]
        - paragraph: Philippines · Fictional small-run pouch producer with unverified certification status.
        - paragraph: "MOQ: 800 · Typical lead time: 37 days"
        - paragraph: "Indicative price: Unknown"
        - paragraph: "Capabilities: CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
        - heading "Requirement fit" [level=4]
        - list:
          - listitem:
            - text: "MATERIAL (REQUIRED): recycled polyester —"
            - strong: MEETS
            - text: "· Evidence: Synthetic material sheet"
          - listitem:
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: UNKNOWN
          - listitem:
            - text: "CERTIFICATION (PREFERRED): grs —"
            - strong: UNKNOWN
        - paragraph: "General MOQ compatibility: UNKNOWN"
        - group: Available evidence
        - button "Explain this supplier"
        - button "Add to shortlist"
        - button "Dismiss"
        - text: Private notes for Moss Thread Bags
        - textbox "Private notes for Moss Thread Bags"
        - button "Save notes" [disabled]
      - article:
        - heading "Sunrise Textile Lab" [level=3]
        - paragraph: India · Fictional bag producer with conflicting current certification records.
        - paragraph: "MOQ: 1500 · Typical lead time: 45 days"
        - paragraph: "Indicative price: 4.1000 USD"
        - paragraph: "Capabilities: CERTIFICATION: grs; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
        - heading "Requirement fit" [level=4]
        - list:
          - listitem:
            - text: "MATERIAL (REQUIRED): recycled polyester —"
            - strong: UNKNOWN
          - listitem:
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: UNKNOWN
          - listitem:
            - text: "CERTIFICATION (PREFERRED): grs —"
            - strong: CONFLICT
            - text: "· Evidence: Synthetic certification register B, Synthetic certification register A"
        - paragraph: "General MOQ compatibility: UNKNOWN"
        - group: Available evidence
        - button "Explain this supplier"
        - button "Add to shortlist"
        - button "Dismiss"
        - text: Private notes for Sunrise Textile Lab
        - textbox "Private notes for Sunrise Textile Lab"
        - button "Save notes" [disabled]
      - article:
        - heading "Willow Stitch Studio" [level=3]
        - paragraph: Indonesia · Fictional textile studio with cosmetic pouch and branding capabilities.
        - paragraph: "MOQ: 1800 · Typical lead time: 40 days"
        - paragraph: "Indicative price: 4.2000 USD"
        - paragraph: "Capabilities: BRANDING_METHOD: embroidery; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
        - heading "Requirement fit" [level=4]
        - list:
          - listitem:
            - text: "MATERIAL (REQUIRED): recycled polyester —"
            - strong: MEETS
            - text: "· Evidence: Synthetic material sheet"
          - listitem:
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: MEETS
            - text: "· Evidence: Synthetic branding sheet"
          - listitem:
            - text: "CERTIFICATION (PREFERRED): grs —"
            - strong: UNKNOWN
        - paragraph: "General MOQ compatibility: UNKNOWN"
        - group: Available evidence
        - button "Explain this supplier"
        - button "Remove from shortlist"
        - button "Dismiss"
        - text: Private notes for Willow Stitch Studio
        - textbox "Private notes for Willow Stitch Studio"
        - button "Save notes" [disabled]
    - region "Quotes":
      - heading "Quotes" [level=2]
      - group:
        - article:
          - heading "Harbor Pouch Works" [level=3]
          - paragraph: "Status: CONFIRMED"
          - status: Confirmed PDF quote. Current values are ready for comparison.
          - paragraph: Review the PDF source, AI extraction, and current values.
          - term: Quoted quantity
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 2000"
            - paragraph: "Current confirmed value: 2000"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b4
                - blockquote: "Quoted quantity: 2,000 units"
                - paragraph: "Associated extracted value: 2000"
          - term: Unit price
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 4.60"
            - paragraph: "Current confirmed value: 4.60"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b5
                - blockquote: "Unit price: USD 4.60"
                - paragraph: "Associated extracted value: 4.60"
          - term: Original currency (three-letter code)
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: USD"
            - paragraph: "Current confirmed value: USD"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b5
                - blockquote: "Unit price: USD 4.60"
                - paragraph: "Associated extracted value: USD"
          - term: Minimum order quantity
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 1000"
            - paragraph: "Current confirmed value: 1000"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b6
                - blockquote: "Minimum order quantity: 1,000 units"
                - paragraph: "Associated extracted value: 1000"
          - term: Sample cost
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 40"
            - paragraph: "Current confirmed value: 40"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b8
                - blockquote: "Sample cost: USD 40"
                - paragraph: "Associated extracted value: 40"
          - term: Tooling or setup cost
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 150"
            - paragraph: "Current confirmed value: 150"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b7
                - blockquote: "Tooling/setup cost: USD 150"
                - paragraph: "Associated extracted value: 150"
          - term: Packaging cost
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Shipping cost
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 320"
            - paragraph: "Current confirmed value: 320"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b11
                - blockquote: "Shipping cost: USD 320 to Manila"
                - paragraph: "Associated extracted value: 320"
          - term: Sample lead time
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 7 days"
            - paragraph: "Current confirmed value: 7 days"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b9
                - blockquote: "Sample lead time: 7 days"
                - paragraph: "Associated extracted value: 7 days"
          - term: Production lead time
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 32 days after sample approval"
            - paragraph: "Current confirmed value: 32 days after sample approval"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b10
                - blockquote: "Production lead time: 32 days after sample approval"
                - paragraph: "Associated extracted value: 32 days after sample approval"
          - term: Shipping time
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 12 days after production"
            - paragraph: "Current confirmed value: 12 days after production"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b12
                - blockquote: "Shipping time: 12 days after production"
                - paragraph: "Associated extracted value: 12 days after production"
          - term: Total stated lead time
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Payment terms
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 30% deposit, 70% before dispatch"
            - paragraph: "Current confirmed value: 30% deposit, 70% before dispatch"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b13
                - blockquote: "Payment terms: 30% deposit, 70% before dispatch"
                - paragraph: "Associated extracted value: 30% deposit, 70% before dispatch"
          - term: Incoterm
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Quote validity
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 30 days"
            - paragraph: "Current confirmed value: 30 days"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b14
                - blockquote: "Quote validity: 30 days"
                - paragraph: "Associated extracted value: 30 days"
          - term: Warranty
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Certifications
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: Synthetic GRS record: current for this fictional supplier"
            - paragraph: "Current confirmed value: Synthetic GRS record: current for this fictional supplier"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 2, block p2-b4
                - blockquote: "Synthetic GRS record: current for this fictional supplier"
                - paragraph: "Associated extracted value: Synthetic GRS record: current for this fictional supplier"
          - term: Compliance notes
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Exclusions
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: import duties are not included"
            - paragraph: "Current confirmed value: import duties are not included"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 2, block p2-b7
                - blockquote: "Exclusion: import duties are not included"
                - paragraph: "Associated extracted value: import duties are not included"
          - term: Special conditions
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Supplier notes
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - paragraph: "Notes: None"
          - button "Edit confirmed PDF quote"
        - article:
          - heading "Willow Stitch Studio" [level=3]
          - paragraph: "Status: CONFIRMED"
          - status: Confirmed PDF quote. Current values are ready for comparison.
          - paragraph: Review the PDF source, AI extraction, and current values.
          - term: Quoted quantity
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 2000"
            - paragraph: "Current confirmed value: 2000"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b4
                - blockquote: "Quoted quantity: 2,000 units"
                - paragraph: "Associated extracted value: 2000"
          - term: Unit price
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 4.20"
            - paragraph: "Current confirmed value: 4.20"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b5
                - blockquote: "Unit price: USD 4.20"
                - paragraph: "Associated extracted value: 4.20"
          - term: Original currency (three-letter code)
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: USD"
            - paragraph: "Current confirmed value: USD"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b5
                - blockquote: "Unit price: USD 4.20"
                - paragraph: "Associated extracted value: USD"
          - term: Minimum order quantity
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 1800"
            - paragraph: "Current confirmed value: 1800"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b6
                - blockquote: "Minimum order quantity: 1,800 units"
                - paragraph: "Associated extracted value: 1800"
          - term: Sample cost
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 35"
            - paragraph: "Current confirmed value: 35"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b8
                - blockquote: "Sample cost: USD 35"
                - paragraph: "Associated extracted value: 35"
          - term: Tooling or setup cost
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 100"
            - paragraph: "Current confirmed value: 100"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b7
                - blockquote: "Tooling/setup cost: USD 100"
                - paragraph: "Associated extracted value: 100"
          - term: Packaging cost
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Shipping cost
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 280"
            - paragraph: "Current confirmed value: 280"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b11
                - blockquote: "Shipping cost: USD 280 to Manila"
                - paragraph: "Associated extracted value: 280"
          - term: Sample lead time
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 10 days"
            - paragraph: "Current confirmed value: 10 days"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b9
                - blockquote: "Sample lead time: 10 days"
                - paragraph: "Associated extracted value: 10 days"
          - term: Production lead time
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 40 days after sample approval"
            - paragraph: "Current confirmed value: 40 days after sample approval"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b10
                - blockquote: "Production lead time: 40 days after sample approval"
                - paragraph: "Associated extracted value: 40 days after sample approval"
          - term: Shipping time
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 14 days after production"
            - paragraph: "Current confirmed value: 14 days after production"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b12
                - blockquote: "Shipping time: 14 days after production"
                - paragraph: "Associated extracted value: 14 days after production"
          - term: Total stated lead time
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Payment terms
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 50% deposit, 50% before dispatch"
            - paragraph: "Current confirmed value: 50% deposit, 50% before dispatch"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b14
                - blockquote: "Payment terms: 50% deposit, 50% before dispatch"
                - paragraph: "Associated extracted value: 50% deposit, 50% before dispatch"
          - term: Incoterm
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Quote validity
          - definition:
            - paragraph: "Extraction: Known"
            - paragraph: "AI extracted value: 30 days"
            - paragraph: "Current confirmed value: 30 days"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b15
                - blockquote: "Quote validity: 30 days"
                - paragraph: "Associated extracted value: 30 days"
          - term: Warranty
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Certifications
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: "PDF source evidence:"
            - list:
              - listitem:
                - paragraph: Page 1, block p1-b13
                - blockquote: "Preferred GRS certification: not stated in this quote"
          - term: Compliance notes
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Exclusions
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Special conditions
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - term: Supplier notes
          - definition:
            - paragraph: "Extraction: Unknown"
            - paragraph: "AI extracted value: Unknown"
            - paragraph: "Current confirmed value: Unknown"
            - paragraph: "Current origin: AI EXTRACTED"
            - paragraph: No saved source citations available for this field.
          - paragraph: "Notes: None"
          - button "Edit confirmed PDF quote"
    - region "Comparison":
      - heading "Comparison" [level=2]
      - alert: The comparison changed. Review the current comparison before analyzing again.
      - status: Comparison is current.
      - table "Factual comparison of confirmed supplier quotes":
        - caption: Factual comparison of confirmed supplier quotes
        - rowgroup:
          - row "Criterion Willow Stitch Studio Harbor Pouch Works":
            - columnheader "Criterion"
            - columnheader "Willow Stitch Studio"
            - columnheader "Harbor Pouch Works"
        - rowgroup:
          - row "Unit price USD 4.20 Confirmed project quote price USD 4.60 Confirmed project quote price":
            - rowheader "Unit price"
            - cell "USD 4.20 Confirmed project quote price":
              - strong: USD 4.20
              - text: Confirmed project quote price
              - group: Source details
            - cell "USD 4.60 Confirmed project quote price":
              - strong: USD 4.60
              - text: Confirmed project quote price
              - group: Source details
          - row "Quoted quantity 2000 2000":
            - rowheader "Quoted quantity"
            - cell "2000":
              - strong: "2000"
              - group: Source details
            - cell "2000":
              - strong: "2000"
              - group: Source details
          - row "Minimum order quantity 1800 1000":
            - rowheader "Minimum order quantity"
            - cell "1800":
              - strong: "1800"
              - group: Source details
            - cell "1000":
              - strong: "1000"
              - group: Source details
          - row "Production lead time 40 days after sample approval 32 days after sample approval":
            - rowheader "Production lead time"
            - cell "40 days after sample approval":
              - strong: 40 days after sample approval
              - group: Source details
            - cell "32 days after sample approval":
              - strong: 32 days after sample approval
              - group: Source details
          - row "Delivery commitment Unknown Unknown":
            - rowheader "Delivery commitment"
            - cell "Unknown":
              - strong: Unknown
            - cell "Unknown":
              - strong: Unknown
          - row "Tooling or setup cost USD 100 USD 150":
            - rowheader "Tooling or setup cost"
            - cell "USD 100":
              - strong: USD 100
              - group: Source details
            - cell "USD 150":
              - strong: USD 150
              - group: Source details
          - row "Shipping cost USD 280 USD 320":
            - rowheader "Shipping cost"
            - cell "USD 280":
              - strong: USD 280
              - group: Source details
            - cell "USD 320":
              - strong: USD 320
              - group: Source details
          - 'row "Material Required Expected: recycled polyester Meets Meets"':
            - 'rowheader "Material Required Expected: recycled polyester"'
            - cell "Meets":
              - strong: Meets
              - group: Source details
            - cell "Meets":
              - strong: Meets
              - group: Source details
          - 'row "Capability Required Expected: Yes · CUSTOM_BRANDING Meets Meets"':
            - 'rowheader "Capability Required Expected: Yes · CUSTOM_BRANDING"'
            - cell "Meets":
              - strong: Meets
              - group: Source details
            - cell "Meets":
              - strong: Meets
              - group: Source details
          - 'row "Certification Preferred Expected: grs Unknown Meets"':
            - 'rowheader "Certification Preferred Expected: grs"'
            - cell "Unknown":
              - strong: Unknown
            - cell "Meets":
              - strong: Meets
              - group: Source details
      - status: Previous analysis is outdated. Analyze the current comparison again.
      - button "Retry analysis"
      - group: Missing or conflicting information
      - button "Regenerate Comparison"
    - region "Decision":
      - heading "Decision" [level=2]
      - paragraph:
        - text: "Current preference:"
        - strong: No Decision Yet
      - paragraph: This records your choice. It does not place an order or contact a supplier.
      - text: Preferred supplier
      - combobox "Preferred supplier":
        - option "Choose a shortlisted supplier" [selected]
        - option "Harbor Pouch Works"
        - option "Willow Stitch Studio"
      - text: Decision notes
      - textbox "Decision notes"
      - button "Mark as Preferred Supplier" [disabled]
      - button "Save decision notes"
```

# Test source

```ts
  1   | import { expect, test, type Locator, type Page } from "@playwright/test";
  2   | import { readFileSync } from "node:fs";
  3   | import path from "node:path";
  4   | import scenario from "../../api/tests/e2e_support/scenario.json";
  5   | 
  6   | export { scenario };
  7   | export const suppliers = ["Harbor Pouch Works", "Willow Stitch Studio", "Moss Thread Bags"];
  8   | export const pdfNames = ["harbor_primary.pdf", "willow_primary.pdf", "moss_primary.pdf"];
  9   | export const pdfDirectory = path.resolve("../api/tests/fixtures/quote_pdfs");
  10  | 
  11  | export type Quote = {
  12  |   id: string; supplier_id: string; status: string; entry_type: string;
  13  |   processing: { attempts: number; status: string } | null;
  14  |   values: Record<string, { current_value: string | number | null; current_origin: string;
  15  |     ai_extracted_value: string | number | null }>;
  16  | };
  17  | export type Project = {
  18  |   preferred_supplier_id: string | null; preferred_supplier_name: string | null;
  19  |   decision_notes: string | null;
  20  |   workflow: { suppliers_stale: boolean; comparison_stale: boolean; comparison_ready: boolean };
  21  | };
  22  | 
  23  | export async function readApi<T>(page: Page, route: string): Promise<T> {
  24  |   const response = await page.request.get(`/api${route}`);
  25  |   expect(response.ok(), `Read ${route}: ${response.status()}`).toBeTruthy();
  26  |   return response.json() as Promise<T>;
  27  | }
  28  | 
  29  | export function quoteCard(page: Page, index: number): Locator {
  30  |   return page.getByRole("region", { name: "Quotes", exact: true }).getByRole("article")
  31  |     .filter({ has: page.getByRole("heading", { name: suppliers[index], exact: true }) });
  32  | }
  33  | 
  34  | export async function createAndApprove(page: Page, inspectSupplier = false): Promise<{ id: string; name: string }> {
  35  |   const name = `E2E ${test.info().title} ${test.info().repeatEachIndex}`;
  36  |   await test.step("Anonymous session and project creation", async () => {
  37  |     await page.goto("/");
  38  |     await expect(page.getByRole("heading", { name: "Your sourcing projects" })).toBeVisible();
  39  |     await expect(page.getByText("Loading projects…", { exact: true })).toBeHidden();
  40  |     await page.getByLabel("Project name", { exact: true }).fill(name);
  41  |     await page.getByLabel("What do you want to source?").fill(scenario.request);
  42  |     await page.getByRole("button", { name: "Create project", exact: true }).click();
  43  |     await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  44  |     await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  45  |     await expect(page.getByRole("region", { name: "Decision", exact: true }))
  46  |       .toContainText("No Decision Yet");
  47  |   });
  48  |   const id = new URL(page.url()).pathname.split("/").at(-1)!;
  49  |   const brief = page.getByRole("region", { name: "Sourcing Brief", exact: true });
  50  |   await test.step("Analyze request and clarify missing delivery timing", async () => {
  51  |     await brief.getByRole("button", { name: "Analyze request", exact: true }).click();
  52  |     await expect(brief.getByLabel("Requested quantity", { exact: true })).toHaveValue("2000");
  53  |     await expect(brief.getByLabel("Destination", { exact: true })).toHaveValue("Sydney");
  54  |     await expect(brief).toContainText("Readiness: In progress");
  55  |     await expect(page.getByRole("link", { name: "Next: Complete the Brief", exact: true })).toBeVisible();
  56  |     await brief.getByRole("button", { name: "Get clarification questions", exact: true }).click();
  57  |     await expect(brief.getByRole("form", { name: "Clarification questions" })).toBeVisible();
  58  |     await brief.getByLabel("Delivery answer", { exact: true }).fill(scenario.delivery_answer);
  59  |     await brief.getByRole("button", { name: "Save answers", exact: true }).click();
  60  |     await expect(brief).toContainText("Readiness: Ready for review");
  61  |     await expect(page.getByRole("link", { name: "Next: Approve Brief", exact: true })).toBeVisible();
  62  |   });
  63  |   await test.step("Review importance and explicitly approve Brief", async () => {
  64  |     await brief.getByRole("group", { name: "Requirement 1", exact: true }).getByLabel("Importance").selectOption("REQUIRED");
  65  |     await brief.getByRole("button", { name: "Save Brief", exact: true }).click();
  66  |     await expect(brief.getByRole("button", { name: "Approve Brief", exact: true })).toBeEnabled();
  67  |     await brief.getByRole("button", { name: "Approve Brief", exact: true }).click();
  68  |     await expect(brief).toContainText("Readiness: Approved");
  69  |   });
  70  |   await test.step("Discover suppliers and approve shortlist of three", async () => {
  71  |     const section = page.getByRole("region", { name: "Suppliers", exact: true });
  72  |     await section.getByRole("button", { name: "Discover Suppliers", exact: true }).click();
  73  |     await expect(section.getByRole("article")).toHaveCount(5);
  74  |     if (inspectSupplier) {
  75  |       await test.step("Inspect supplier evidence and bounded analyst explanation", async () => {
  76  |         const card = section.getByRole("article")
  77  |           .filter({ has: page.getByRole("heading", { name: suppliers[0], exact: true }) });
  78  |         await card.getByText("Available evidence", { exact: true }).click();
  79  |         await expect(card).toContainText("Synthetic current GRS record");
  80  |         await card.getByRole("button", { name: "Explain this supplier", exact: true }).click();
  81  |         await expect(card.getByRole("heading", { name: "Supplier explanation", exact: true })).toBeVisible();
  82  |         await expect(card).toContainText("Material (recycled polyester): Meets.");
  83  |       });
  84  |     }
  85  |     for (const supplier of suppliers) {
  86  |       const card = section.getByRole("article").filter({ has: page.getByRole("heading", { name: supplier, exact: true }) });
  87  |       await expect(card).toBeVisible();
  88  |       await card.getByRole("button", { name: "Add to shortlist", exact: true }).click();
  89  |       await expect(card.getByRole("button", { name: "Remove from shortlist", exact: true })).toBeVisible();
  90  |     }
  91  |     await approveShortlist(page);
  92  |   });
  93  |   return { id, name };
  94  | }
  95  | 
  96  | export async function approveShortlist(page: Page): Promise<void> {
  97  |   const section = page.getByRole("region", { name: "Suppliers", exact: true });
  98  |   await section.getByRole("button", { name: "Review selected suppliers", exact: true }).click();
  99  |   await section.getByRole("button", { name: "Approve Shortlist", exact: true }).click();
  100 |   await expect(section).toContainText("Shortlist approved");
> 101 |   await expect(quoteCard(page, 0).getByLabel("Upload PDF quote")).toBeEnabled();
      |                                                                   ^ Error: expect(locator).toBeEnabled() failed
  102 | }
  103 | 
  104 | export async function upload(page: Page, index: number, filename = pdfNames[index], abandoned = false): Promise<void> {
  105 |   const card = quoteCard(page, index);
  106 |   await card.getByLabel("Upload PDF quote").setInputFiles(abandoned ? {
  107 |     name: "e2e-abandoned-harbor.pdf", mimeType: "application/pdf",
  108 |     buffer: readFileSync(path.join(pdfDirectory, filename)),
  109 |   } : path.join(pdfDirectory, filename));
  110 |   await expect(card).toContainText(abandoned ? "Status: PROCESSING" : filename === "image_only.pdf"
  111 |     ? "Status: FAILED" : "Status: NEEDS REVIEW", { timeout: 30_000 });
  112 | }
  113 | 
  114 | export async function confirm(page: Page, index: number): Promise<void> {
  115 |   const card = quoteCard(page, index);
  116 |   await card.getByRole("button", { name: "Review for confirmation", exact: true }).click();
  117 |   await card.getByRole("button", { name: "Confirm Quote", exact: true }).click();
  118 |   await expect(card).toContainText("Status: CONFIRMED");
  119 | }
  120 | 
  121 | export async function comparison(page: Page, regenerate = false): Promise<void> {
  122 |   const section = page.getByRole("region", { name: "Comparison", exact: true });
  123 |   await section.getByRole("button", { name: regenerate ? "Regenerate Comparison" : "Generate Comparison", exact: true }).click();
  124 |   await expect(section).toContainText("Comparison is current.");
  125 |   await expect(section.getByRole("table")).toBeVisible();
  126 | }
  127 | 
  128 | export async function advice(page: Page, id: string): Promise<void> {
  129 |   expect((await readApi<Project>(page, `/projects/${id}`)).preferred_supplier_id).toBeNull();
  130 |   const section = page.getByRole("region", { name: "Comparison", exact: true });
  131 |   const response = page.waitForResponse((item) => item.url().endsWith(`/api/projects/${id}/comparison/advice`)
  132 |     && item.request().method() === "POST");
  133 |   await section.getByRole("button", { name: "Analyze Comparison", exact: true }).click();
  134 |   const result = await response;
  135 |   expect(result.ok(), `Comparison analyst status ${result.status()}`).toBeTruthy();
  136 |   const body = await result.json();
  137 |   expect(body.suggestion.supplier_id).toBe(scenario.advisory.supplier_id);
  138 |   expect(body.suggestion.supporting_reasons).toEqual(scenario.advisory.supporting_reasons);
  139 |   expect(body.suggestion.tradeoffs).toEqual(scenario.advisory.tradeoffs);
  140 |   expect(body.suggestion.uncertainties[0].text).toBe(scenario.advisory.uncertainty);
  141 |   expect(body).not.toHaveProperty("preferred_supplier_id");
  142 |   const region = section.getByRole("region", { name: "Comparison analysis", exact: true });
  143 |   await expect(region.getByRole("heading", { name: "No supplier suggested yet", exact: true })).toBeVisible();
  144 |   await expect(region).toContainText(scenario.advisory.uncertainty);
  145 |   await expect(region).toContainText("Important unknowns");
  146 |   expect((await readApi<Project>(page, `/projects/${id}`)).preferred_supplier_id).toBeNull();
  147 |   await expect(page.getByRole("region", { name: "Decision", exact: true })).toContainText("No Decision Yet");
  148 | }
  149 | 
```