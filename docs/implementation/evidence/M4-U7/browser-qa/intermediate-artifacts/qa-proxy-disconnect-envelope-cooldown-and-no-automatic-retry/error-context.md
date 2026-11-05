# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: qa.spec.ts >> proxy disconnect envelope cooldown and no automatic retry
- Location: qa.spec.ts:97:5

# Error details

```
Error: expect(locator).toBeDisabled() failed

Locator: getByRole('region', { name: 'Comparison', exact: true }).getByRole('button', { name: 'Retry analysis', exact: true })
Expected: disabled
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeDisabled" getByRole('region', { name: 'Comparison', exact: true }).getByRole('button', { name: 'Retry analysis', exact: true }) with timeout 15000ms
  - waiting for getByRole('region', { name: 'Comparison', exact: true }).getByRole('button', { name: 'Retry analysis', exact: true })

```

```yaml
- alert
- main:
  - paragraph: Demo session ready
  - region "E2E proxy disconnect envelope cooldown and no automatic retry 0":
    - link "Back to projects":
      - /url: /
    - paragraph: "Current stage: Decision"
    - paragraph: Review the comparison and record your choice. AI analysis is optional.
    - 'link "Next: Review comparison and choose a preferred supplier"':
      - /url: "#decision-choice"
    - heading "E2E proxy disconnect envelope cooldown and no automatic retry 0" [level=1]
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
    - textbox "Rename project": E2E proxy disconnect envelope cooldown and no automatic retry 0
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
      - group "Requirement 2":
        - text: Requirement 2 Kind
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
          - option "Not set" [selected]
          - option "Required"
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
        - paragraph: 3 selected · maximum 3 for approval
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
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: UNKNOWN
          - listitem:
            - text: "MATERIAL (Informational): recycled polyester —"
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
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: MEETS
            - text: "· Evidence: Synthetic branding sheet"
          - listitem:
            - text: "MATERIAL (Informational): recycled polyester —"
            - strong: MEETS
            - text: "· Evidence: Synthetic material sheet"
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
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: UNKNOWN
          - listitem:
            - text: "MATERIAL (Informational): recycled polyester —"
            - strong: MEETS
            - text: "· Evidence: Synthetic material sheet"
          - listitem:
            - text: "CERTIFICATION (PREFERRED): grs —"
            - strong: UNKNOWN
        - paragraph: "General MOQ compatibility: UNKNOWN"
        - group: Available evidence
        - button "Explain this supplier"
        - button "Remove from shortlist"
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
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: UNKNOWN
          - listitem:
            - text: "MATERIAL (Informational): recycled polyester —"
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
            - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
            - strong: MEETS
            - text: "· Evidence: Synthetic branding sheet"
          - listitem:
            - text: "MATERIAL (Informational): recycled polyester —"
            - strong: MEETS
            - text: "· Evidence: Synthetic material sheet"
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
          - heading "Moss Thread Bags" [level=3]
          - paragraph: "Status: Not Added"
          - text: Upload PDF quote
          - button "Upload PDF quote"
          - paragraph: Leave a field blank if it is Unknown.
          - text: Quoted quantity
          - spinbutton "Quoted quantity"
          - text: Unit price
          - spinbutton "Unit price"
          - text: Original currency (three-letter code)
          - textbox "Original currency (three-letter code)"
          - text: Minimum order quantity
          - spinbutton "Minimum order quantity"
          - text: Sample cost
          - spinbutton "Sample cost"
          - text: Tooling or setup cost
          - spinbutton "Tooling or setup cost"
          - text: Packaging cost
          - spinbutton "Packaging cost"
          - text: Shipping cost
          - spinbutton "Shipping cost"
          - text: Sample lead time
          - textbox "Sample lead time"
          - text: Production lead time
          - textbox "Production lead time"
          - text: Shipping time
          - textbox "Shipping time"
          - text: Total stated lead time
          - textbox "Total stated lead time"
          - text: Payment terms
          - textbox "Payment terms"
          - text: Incoterm
          - textbox "Incoterm"
          - text: Quote validity
          - textbox "Quote validity"
          - text: Warranty
          - textbox "Warranty"
          - text: Certifications
          - textbox "Certifications"
          - text: Compliance notes
          - textbox "Compliance notes"
          - text: Exclusions
          - textbox "Exclusions"
          - text: Special conditions
          - textbox "Special conditions"
          - text: Supplier notes
          - textbox "Supplier notes"
          - text: Quote notes
          - textbox "Quote notes"
          - button "Create manual quote"
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
      - alert:
        - paragraph: Analysis took too long. Please retry.
        - button "Retry comparison"
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
        - option "Moss Thread Bags"
        - option "Willow Stitch Studio"
      - text: Decision notes
      - textbox "Decision notes"
      - button "Mark as Preferred Supplier" [disabled]
      - button "Save decision notes"
```

# Test source

```ts
  3   | import { createAndApprove, upload, confirm, comparison, readApi, quoteCard, approveShortlist } from '../../../../../apps/web/e2e/helpers';
  4   | const region = (p: Page) => p.getByRole('region',{name:'Comparison',exact:true});
  5   | const output = (p: Page) => p.getByRole('region',{name:'Comparison analysis',exact:true});
  6   | const button = (p: Page, name: string) => region(p).getByRole('button',{name,exact:true});
  7   | let requests: {method:string;path:string}[];
  8   | test.beforeEach(async ({page}) => {
  9   |   requests=[];
  10  |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});
  11  |   page.on('request',r=>{const u=new URL(r.url()); if(u.pathname.startsWith('/api/')) requests.push({method:r.method(),path:u.pathname.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/g,':id')});});
  12  |   await page.addInitScript(()=>{
  13  |     (window as any).__focus=[];
  14  |     for(const type of ['focus','blur']) window.addEventListener(type,e=>(window as any).__focus.push({type,trusted:e.isTrusted,focused:document.hasFocus()}));
  15  |   });
  16  | });
  17  | test.afterEach(async ({page},info)=>{
  18  |   const counts: Record<string,number>={}; for(const r of requests){const k=r.method+' '+r.path;counts[k]=(counts[k]??0)+1;}
  19  |   writeFileSync(info.outputPath('sanitized-network.json'),JSON.stringify({counts,sequence:requests},null,2));
  20  |   if(!page.isClosed()) {
  21  |     await page.bringToFront();
  22  |     writeFileSync(info.outputPath('focus.json'),JSON.stringify(await page.evaluate(()=>(window as any).__focus),null,2));
  23  |     await page.screenshot({path:info.outputPath('final.png'),fullPage:true});
  24  |     await region(page).scrollIntoViewIfNeeded();
  25  |     await page.screenshot({path:info.outputPath('comparison-viewport.png')});
  26  |     if(await output(page).isVisible()) await output(page).screenshot({path:info.outputPath('analysis.png')});
  27  |     writeFileSync(info.outputPath('visible-text.txt'),await page.locator('body').innerText());
  28  |   }
  29  | });
  30  | for(const outcome of ['success','failure'])test(`held ${outcome} survives failed pending verification and repeated reads`,async({page})=>{
  31  |   const id=await setup(page),g=gate(),readGate=gate();let posts=0,reads=0;
  32  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const result=outcome==='success'?await r.fetch():null;await g.promise;if(result)await r.fulfill({response:result});else await r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis could not be validated. Please retry.'}}});});
  33  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  34  |   await page.route(`**/api/projects/${id}/comparison`,async r=>{reads++;await readGate.promise;await r.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Freshness verification failed.'}}});});
  35  |   await nativeFocus(page);await nativeFocus(page);expect(reads).toBe(2);expect(posts).toBe(1);await expect(region(page)).toContainText('Analysis is pending while we verify');await expect(output(page)).toBeHidden();
  36  |   g.release();readGate.release();await expect(button(page,'Retry comparison')).toBeVisible();await expect(output(page)).toBeHidden();
  37  |   await page.screenshot({path:test.info().outputPath('unverified.png')});
  38  |   await page.unroute(`**/api/projects/${id}/comparison`);await button(page,'Retry comparison').click();
  39  |   if(outcome==='success')await expect(output(page)).toBeVisible();else {await expect(region(page)).toContainText('could not be validated');await expect(button(page,'Retry analysis')).toBeEnabled();}
  40  |   expect(posts).toBe(1);
  41  | });
  42  | test('regeneration while analysis pending rejects late success',async({page})=>{
  43  |   const id=await setup(page),g=gate();let posts=0;
  44  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await g.promise;try{await r.fulfill({response});}catch{}});
  45  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();await comparison(page,true);g.release();await nativeFocus(page);await expect(output(page)).toBeHidden();await expect(button(page,'Analyze Comparison')).toBeEnabled();expect(posts).toBe(1);
  46  |   await page.unroute(`**/api/projects/${id}/comparison/advice`);await analyze(page);
  47  | });
  48  | async function setup(p:Page){const project=await createAndApprove(p);for(const i of [0,1]){await quoteCard(p,i).getByLabel('Upload PDF quote').setInputFiles(require('node:path').resolve(__dirname, '../../../../../apps/api/tests/fixtures/quote_pdfs', ['harbor_primary.pdf','willow_primary.pdf'][i]));await expect(quoteCard(p,i)).toContainText('Status: NEEDS REVIEW');await confirm(p,i);}await comparison(p);return project.id;}
  49  | async function nativeFocus(p:Page){
  50  |   const cdp=await p.context().newCDPSession(p);await cdp.send('Emulation.setFocusEmulationEnabled',{enabled:false});
  51  |   const other=await p.context().newPage();await other.goto('about:blank');await other.bringToFront();
  52  |   await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(false);
  53  |   await p.bringToFront();await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(true);await other.close();
  54  |   const events=await p.evaluate(()=>(window as any).__focus);
  55  |   expect(events.some((e:any)=>e.type==='blur'&&e.trusted)).toBe(true);
  56  |   expect(events.some((e:any)=>e.type==='focus'&&e.trusted)).toBe(true);
  57  | }
  58  | async function analyze(p:Page){await button(p,'Analyze Comparison').click();await expect(output(p)).toBeVisible();}
  59  | async function invariant(p:Page,id:string,before:any){expect(await readApi(p,`/projects/${id}/comparison`)).toEqual(before);expect((await readApi<any>(p,`/projects/${id}`)).preferred_supplier_id).toBeNull();}
  60  | function gate(){let release!:()=>void;const promise=new Promise<void>(r=>release=r);return {promise,release};}
  61  | for(const outcome of ['success','failure']) test(`native focus pending ${outcome}, repeated focus and keyboard retry`,async({page})=>{
  62  |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`),g=gate();let posts=0;
  63  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=outcome==='success'?await r.fetch():null;await g.promise;if(response)await r.fulfill({response});else await r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis could not be validated. Please retry.'}}});});
  64  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  65  |   await nativeFocus(page);await nativeFocus(page);await expect(button(page,'Analyzing…')).toBeDisabled();expect(posts).toBe(1);g.release();
  66  |   if(outcome==='success')await expect(output(page)).toBeVisible();else {await expect(button(page,'Retry analysis')).toBeEnabled();await button(page,'Retry analysis').scrollIntoViewIfNeeded();await page.screenshot({path:test.info().outputPath('retry-error.png')});}
  67  |   await nativeFocus(page);await nativeFocus(page);
  68  |   if(outcome==='success')await expect(output(page)).toBeVisible();else {
  69  |     await expect(region(page)).toContainText('could not be validated');expect(posts).toBe(1);
  70  |     await page.unroute(`**/api/projects/${id}/comparison/advice`);
  71  |     // Real Tab navigation, not locator.focus(), reaches Retry and Enter activates it.
  72  |     let reached=false;for(let i=0;i<350;i++){await page.keyboard.press('Tab');if(await button(page,'Retry analysis').evaluate(el=>el===document.activeElement)){reached=true;break;}}
  73  |     expect(reached).toBe(true);await page.keyboard.press('Enter');await expect(output(page)).toBeVisible();
  74  |   }
  75  |   expect(posts).toBe(1);await invariant(page,id,before);
  76  | });
  77  | test('failed freshness hides advice and GET-only recovery retains success',async({page})=>{
  78  |   const id=await setup(page);await analyze(page);let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++;});
  79  |   await page.route(`**/api/projects/${id}/comparison`,r=>r.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Comparison verification unavailable. Retry.'}}}));
  80  |   await nativeFocus(page);await expect(button(page,'Retry comparison')).toBeVisible();await expect(output(page)).toBeHidden();
  81  |   await page.screenshot({path:test.info().outputPath('verification-failed.png'),fullPage:true});
  82  |   await page.unroute(`**/api/projects/${id}/comparison`);await button(page,'Retry comparison').click();await expect(output(page)).toBeVisible();expect(posts).toBe(0);
  83  | });
  84  | test('competing focus and post-result reads cannot restore stale advice',async({page})=>{
  85  |   const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`),old=gate(),analysis=gate();let reads=0,posts=0;
  86  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await analysis.promise;await r.fulfill({response});});
  87  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  88  |   await page.route(`**/api/projects/${id}/comparison`,async r=>{reads++;if(reads===1){await old.promise;await r.fulfill({json:before});}else await r.fulfill({json:{...before,stale:true}});});
  89  |   await nativeFocus(page);await expect.poll(()=>reads).toBe(1);analysis.release();await expect(region(page)).toContainText('Comparison outdated');old.release();
  90  |   await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');expect(posts).toBe(1);
  91  | });
  92  | for(const change of ['quote','brief','shortlist','regeneration']) test(`${change} invalidation and replacement`,async({page})=>{
  93  |   const id=await setup(page);await analyze(page);const old=await readApi<any>(page,`/projects/${id}/comparison`);
  94  |   if(change==='quote'){const c=quoteCard(page,0);await c.getByRole('button',{name:'Edit confirmed PDF quote',exact:true}).click();await c.getByLabel('Unit price',{exact:true}).fill('4.65');await c.getByRole('button',{name:'Save quote',exact:true}).click();}
  95  |   if(change==='brief'){const b=page.getByRole('region',{name:'Sourcing Brief',exact:true});await b.getByLabel('Destination',{exact:true}).fill('Melbourne');await b.getByRole('button',{name:'Save Brief',exact:true}).click();}
  96  |   if(change==='shortlist'){const s=page.getByRole('region',{name:'Suppliers',exact:true});await s.getByRole('article').filter({has:page.getByRole('heading',{name:'Moss Thread Bags',exact:true})}).getByRole('button',{name:'Remove from shortlist',exact:true}).click();}
  97  |   if(change!=='regeneration'){await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');}
  98  |   if(change==='brief'){await page.getByRole('button',{name:'Re-discover and re-evaluate',exact:true}).click();await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();}
  99  |   if(change==='shortlist'){await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();}
  100 |   await comparison(page,true);await expect(output(page)).toBeHidden();const current=await readApi<any>(page,`/projects/${id}/comparison`);expect(current.id).not.toBe(old.id);
  101 |   await analyze(page);if(change==='quote')await expect(region(page).getByRole('table')).toContainText('USD 4.65');
  102 |   expect((await readApi<any>(page,`/projects/${id}`)).preferred_supplier_id).toBeNull();
> 103 | });
      |                                                                                    ^ Error: expect(locator).toBeDisabled() failed
  104 | test('project switch A to B to A rejects late result',async({page})=>{
  105 |   const b=await setup(page);const a=await setup(page),g=gate();let posts=0;
  106 |   await page.route(`**/api/projects/${a}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await g.promise;try{await r.fulfill({response});}catch{/* Browser aborted the old navigation-owned request. */}});
  107 |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  108 |   await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${b}']`).first().click();await expect(output(page)).toBeHidden();
  109 |   await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${a}']`).first().click();g.release();
  110 |   await expect(button(page,'Analyze Comparison')).toBeEnabled();await nativeFocus(page);await expect(output(page)).toBeHidden();expect(posts).toBe(1);
  111 | });
  112 | test('backend deadline envelope permits explicit retry only',async({page})=>{
  113 |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  114 |   await page.route(`**/api/projects/${id}/comparison/advice`,r=>{posts++;return r.fulfill({status:504,json:{error:{code:'COMPARISON_ANALYSIS_TIMEOUT',message:'Analysis took too long. Please retry.'}}});});
  115 |   await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('Analysis took too long');await expect(button(page,'Retry analysis')).toBeEnabled();await nativeFocus(page);expect(posts).toBe(1);
  116 |   await page.unroute(`**/api/projects/${id}/comparison/advice`);await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();await invariant(page,id,before);
  117 | });
  118 | test('proxy disconnect envelope cooldown and no automatic retry',async({page})=>{
  119 |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  120 |   await page.clock.install();
  121 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  122 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'disconnect'});
  123 |   await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('may still be finishing');await expect(button(page,'Retry analysis')).toBeDisabled();await button(page,'Retry analysis').scrollIntoViewIfNeeded();await page.screenshot({path:test.info().outputPath('disconnect-cooldown.png')});await nativeFocus(page);expect(posts).toBe(1);
  124 |   await page.clock.fastForward(179000);await expect(button(page,'Retry analysis')).toBeDisabled();await page.clock.fastForward(1100);await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  125 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  126 | });
  127 | test('real backend deadline through actual proxy and explicit recovery',async({page})=>{
  128 |   test.setTimeout(240000);
  129 |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  130 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  131 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'deadline'});
  132 |   const response=page.waitForResponse(r=>r.url().endsWith('/comparison/advice'),{timeout:210000});
  133 |   const start=Date.now();await button(page,'Analyze Comparison').click();const result=await response;
  134 |   const body=await result.json();expect(result.status()).toBe(504);expect(body.error.code).toBe('COMPARISON_ANALYSIS_TIMEOUT');
  135 |   writeFileSync(test.info().outputPath('deadline.json'),JSON.stringify({elapsed_ms:Date.now()-start,status:result.status(),code:body.error.code,posts},null,2));
  136 |   await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  137 |   await page.screenshot({path:test.info().outputPath('deadline-error.png'),fullPage:true});
  138 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  139 | });
  140 | test('existing human preference survives advice and failures',async({page})=>{
  141 |   const id=await setup(page),d=page.getByRole('region',{name:'Decision',exact:true});
  142 |   await d.getByLabel('Preferred supplier',{exact:true}).selectOption({label:'Willow Stitch Studio'});await d.getByLabel('Decision notes').fill('QA human choice');await d.getByRole('button',{name:'Mark as Preferred Supplier',exact:true}).click();await expect(d).toContainText('Preferred supplier saved.');
  143 |   const before=await readApi<any>(page,`/projects/${id}`);await analyze(page);await nativeFocus(page);await expect(output(page)).toBeVisible();
  144 |   await page.route(`**/api/projects/${id}/comparison/advice`,r=>r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis unavailable. Please retry.'}}}));
  145 |   await button(page,'Analyze Comparison').click();await expect(button(page,'Retry analysis')).toBeEnabled();
  146 |   const after=await readApi<any>(page,`/projects/${id}`);expect(after.preferred_supplier_id).toBe(before.preferred_supplier_id);expect(after.decision_notes).toBe(before.decision_notes);await expect(d).toContainText('Willow Stitch Studio');
  147 | });
  148 | for(const suggestion of [false,true])test(`${suggestion?'suggestion':'null-success'} disclosures sources facts and preference`,async({page})=>{
  149 |   const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`);
  150 |   if(suggestion)await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{const response=await r.fetch(),body=await response.json();body.suggestion.supplier_id=before.comparison_payload.suppliers[0].supplier_id;body.suggestion.supporting_reasons=[body.analysis.supplier_summaries[0]];body.suggestion.tradeoffs=[body.analysis.key_tradeoffs[0]];await r.fulfill({json:body});});
  151 |   await analyze(page);await expect(output(page)).toContainText(suggestion?'Suggested Supplier to Investigate First':'No supplier suggested yet');await expect(output(page)).toContainText('You remain responsible for the supplier decision');await expect(output(page)).toContainText('Important unknowns');await expect(region(page).getByRole('table')).toBeVisible();
  152 |   await output(page).getByText('Source details',{exact:true}).first().click();await expect(output(page)).toContainText('Supporting PDF evidence: page 1, block 5');await invariant(page,id,before);
  153 | });
  154 | 
  155 | 
  156 | 
  157 | 
  158 | 
```