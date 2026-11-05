# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: qa.spec.ts >> project switch A to B to A rejects late result
- Location: qa.spec.ts:80:5

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: false
Received: true

Call Log:
- Timeout 15000ms exceeded while waiting on the predicate
```

```
Error: page.screenshot: Protocol error (Page.captureScreenshot): Unable to capture screenshot
Call log:
  - taking page screenshot
  - waiting for fonts to load...
  - fonts loaded

```

# Page snapshot

```yaml
- generic [active] [ref=f1e1]:
  - alert [ref=f1e2]
  - main [ref=f1e3]:
    - paragraph [ref=f1e4]: Demo session ready
    - region [ref=f1e5]:
      - link "Back to projects" [ref=f1e6] [cursor=pointer]:
        - /url: /
      - paragraph [ref=f1e7]: "Current stage: Decision"
      - generic "Next action" [ref=f1e8]:
        - paragraph [ref=f1e9]: Review the comparison and record your choice. AI analysis is optional.
        - 'link "Next: Review comparison and choose a preferred supplier" [ref=f1e10] [cursor=pointer]':
          - /url: "#decision-choice"
      - heading "E2E project switch A to B to A rejects late result 0" [level=1] [ref=f1e11]
      - paragraph [ref=f1e12]: "Preferred supplier: No Decision Yet"
      - navigation "Sourcing workflow stages" [ref=f1e13]:
        - list [ref=f1e14]:
          - listitem [ref=f1e15]:
            - link [ref=f1e16] [cursor=pointer]:
              - /url: "#brief"
              - strong [ref=f1e17]: Brief
          - listitem [ref=f1e18]:
            - link [ref=f1e19] [cursor=pointer]:
              - /url: "#suppliers"
              - strong [ref=f1e20]: Suppliers
          - listitem [ref=f1e21]:
            - link [ref=f1e22] [cursor=pointer]:
              - /url: "#quotes"
              - strong [ref=f1e23]: Quotes
          - listitem [ref=f1e24]:
            - link [ref=f1e25] [cursor=pointer]:
              - /url: "#comparison"
              - strong [ref=f1e26]: Comparison
          - listitem [ref=f1e27]:
            - link [ref=f1e28] [cursor=pointer]:
              - /url: "#decision"
              - strong [ref=f1e29]: Decision
      - generic [ref=f1e30]:
        - generic [ref=f1e31]:
          - text: Rename project
          - textbox "Rename project" [ref=f1e32]: E2E project switch A to B to A rejects late result 0
        - button "Save name" [ref=f1e33] [cursor=pointer]
      - region [ref=f1e34]:
        - heading "Original sourcing request" [level=2] [ref=f1e35]
        - paragraph [ref=f1e36]: Source 2,000 custom cosmetic travel bags made from recycled polyester with a custom logo. Target unit cost below USD 5, delivery to Sydney, preferred GRS certification. Delivery timing is not decided yet.
      - region [ref=f1e37]:
        - heading "Sourcing Brief" [level=2] [ref=f1e38]
        - paragraph [ref=f1e39]: "Readiness: Approved"
        - paragraph [ref=f1e40]: Approved on 11/4/2026
        - paragraph [ref=f1e41]: No required information is missing.
        - generic [ref=f1e42]:
          - heading "Product and delivery" [level=3] [ref=f1e43]
          - generic [ref=f1e44]:
            - text: Product name
            - textbox "Product name" [ref=f1e45]: custom cosmetic travel bags
          - generic [ref=f1e46]:
            - text: Category
            - textbox "Category" [ref=f1e47]: cosmetic travel bags
          - generic [ref=f1e48]:
            - text: Requested quantity
            - spinbutton "Requested quantity" [ref=f1e49]: "2000"
          - generic [ref=f1e50]:
            - text: Destination
            - textbox "Destination" [ref=f1e51]: Sydney
          - generic [ref=f1e52]:
            - text: Delivery target type
            - combobox "Delivery target type" [ref=f1e53]:
              - option "Not set"
              - option "Date" [selected]
              - option "Period"
          - generic [ref=f1e54]:
            - text: Delivery date
            - textbox "Delivery date" [ref=f1e55]: 2026-12-15
          - generic [ref=f1e56]:
            - text: Target unit price (optional)
            - spinbutton "Target unit price (optional)" [ref=f1e57]: "5.0000"
          - heading "Sourcing requirements" [level=3] [ref=f1e58]
          - group "Requirement 1" [ref=f1e59]:
            - generic [ref=f1e61]:
              - text: Kind
              - combobox "Kind" [ref=f1e62]:
                - option "MATERIAL"
                - option "CERTIFICATION" [selected]
                - option "MOQ"
                - option "QUANTITY"
                - option "UNIT PRICE"
                - option "PRODUCTION LEAD TIME"
                - option "DELIVERY"
                - option "CAPABILITY"
                - option "INFORMATIONAL"
            - generic [ref=f1e63]:
              - text: Value
              - textbox "Value" [ref=f1e64]: grs
            - generic [ref=f1e65]:
              - text: Importance
              - combobox "Importance" [ref=f1e66]:
                - option "Not set"
                - option "Required" [selected]
                - option "Preferred"
                - option "Informational"
            - generic [ref=f1e67]:
              - text: Notes (optional)
              - textbox "Notes (optional)" [ref=f1e68]
            - button "Remove requirement" [ref=f1e69] [cursor=pointer]
          - group "Requirement 2" [ref=f1e70]:
            - generic [ref=f1e72]:
              - text: Kind
              - combobox "Kind" [ref=f1e73]:
                - option "MATERIAL" [selected]
                - option "CERTIFICATION"
                - option "MOQ"
                - option "QUANTITY"
                - option "UNIT PRICE"
                - option "PRODUCTION LEAD TIME"
                - option "DELIVERY"
                - option "CAPABILITY"
                - option "INFORMATIONAL"
            - generic [ref=f1e74]:
              - text: Value
              - textbox "Value" [ref=f1e75]: recycled polyester
            - generic [ref=f1e76]:
              - text: Importance
              - combobox "Importance" [ref=f1e77]:
                - option "Not set" [selected]
                - option "Required"
                - option "Preferred"
                - option "Informational"
            - generic [ref=f1e78]:
              - text: Notes (optional)
              - textbox "Notes (optional)" [ref=f1e79]
            - button "Remove requirement" [ref=f1e80] [cursor=pointer]
          - group "Requirement 3" [ref=f1e81]:
            - generic [ref=f1e83]:
              - text: Kind
              - combobox "Kind" [ref=f1e84]:
                - option "MATERIAL"
                - option "CERTIFICATION"
                - option "MOQ"
                - option "QUANTITY"
                - option "UNIT PRICE"
                - option "PRODUCTION LEAD TIME"
                - option "DELIVERY"
                - option "CAPABILITY" [selected]
                - option "INFORMATIONAL"
            - generic [ref=f1e85]:
              - text: Capability
              - combobox "Capability" [ref=f1e86]:
                - option "PRODUCT CATEGORY"
                - option "CUSTOM BRANDING" [selected]
                - option "BRANDING METHOD"
                - option "PRODUCT FEATURE"
                - option "MANUFACTURING CAPABILITY"
            - generic [ref=f1e87]:
              - text: Custom branding
              - combobox "Custom branding" [ref=f1e88]:
                - option "Yes" [selected]
                - option "No"
            - generic [ref=f1e89]:
              - text: Importance
              - combobox "Importance" [ref=f1e90]:
                - option "Not set"
                - option "Required" [selected]
                - option "Preferred"
                - option "Informational"
            - generic [ref=f1e91]:
              - text: Notes (optional)
              - textbox "Notes (optional)" [ref=f1e92]
            - button "Remove requirement" [ref=f1e93] [cursor=pointer]
          - button "Add requirement" [ref=f1e94] [cursor=pointer]
          - heading "Informational attributes" [level=3] [ref=f1e95]
          - button "Add attribute" [ref=f1e96] [cursor=pointer]
          - button "Save Brief" [ref=f1e97] [cursor=pointer]
      - region [ref=f1e98]:
        - heading "Suppliers" [level=2] [ref=f1e99]
        - button "Re-discover and re-evaluate" [ref=f1e100] [cursor=pointer]
        - region [ref=f1e101]:
          - heading "Shortlist" [level=3] [ref=f1e102]
          - paragraph [ref=f1e103]: 3 selected · maximum 3 for approval
          - status [ref=f1e104]: Shortlist approved. The project is ready for Quotes.
          - button "Review selected suppliers" [ref=f1e105] [cursor=pointer]
        - article [ref=f1e106]:
          - heading "Cedar Pack Co" [level=3] [ref=f1e107]
          - paragraph [ref=f1e108]: Thailand · Fictional bag maker with a high general minimum order.
          - paragraph [ref=f1e109]: "MOQ: 5000 · Typical lead time: 28 days"
          - paragraph [ref=f1e110]: "Indicative price: 3.7000 USD"
          - paragraph [ref=f1e111]: "Capabilities: CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=f1e112]
          - list [ref=f1e113]:
            - listitem [ref=f1e114]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=f1e115]: UNKNOWN
            - listitem [ref=f1e116]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=f1e117]: UNKNOWN
            - listitem [ref=f1e118]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=f1e119]: UNKNOWN
          - paragraph [ref=f1e120]: "General MOQ compatibility: DOES NOT MEET"
          - group [ref=f1e121]:
            - generic "Available evidence" [ref=f1e122]
          - button "Explain this supplier" [ref=f1e124] [cursor=pointer]
          - generic [ref=f1e125]:
            - button "Add to shortlist" [ref=f1e126] [cursor=pointer]
            - button "Dismiss" [ref=f1e127] [cursor=pointer]
          - generic [ref=f1e128]:
            - generic [ref=f1e129]:
              - text: Private notes for Cedar Pack Co
              - textbox "Private notes for Cedar Pack Co" [ref=f1e130]
            - button "Save notes" [disabled] [ref=f1e131]
        - article [ref=f1e132]:
          - heading "Harbor Pouch Works" [level=3] [ref=f1e133]
          - paragraph [ref=f1e134]: Vietnam · Fictional maker of custom cosmetic travel bags and small textile accessories.
          - paragraph [ref=f1e135]: "MOQ: 1000 · Typical lead time: 32 days"
          - paragraph [ref=f1e136]: "Indicative price: 4.6000 USD"
          - paragraph [ref=f1e137]: "Capabilities: BRANDING_METHOD: screen print; CERTIFICATION: grs; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=f1e138]
          - list [ref=f1e139]:
            - listitem [ref=f1e140]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=f1e141]: MEETS
              - generic [ref=f1e142]: "· Evidence: Synthetic current GRS record"
            - listitem [ref=f1e143]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=f1e144]: MEETS
              - generic [ref=f1e145]: "· Evidence: Synthetic material sheet"
            - listitem [ref=f1e146]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=f1e147]: MEETS
              - generic [ref=f1e148]: "· Evidence: Synthetic branding sheet"
          - paragraph [ref=f1e149]: "General MOQ compatibility: MEETS"
          - group [ref=f1e150]:
            - generic "Available evidence" [ref=f1e151]
          - button "Explain this supplier" [ref=f1e153] [cursor=pointer]
          - generic [ref=f1e154]:
            - button "Remove from shortlist" [ref=f1e155] [cursor=pointer]
            - button "Dismiss" [ref=f1e156] [cursor=pointer]
          - generic [ref=f1e157]:
            - generic [ref=f1e158]:
              - text: Private notes for Harbor Pouch Works
              - textbox "Private notes for Harbor Pouch Works" [ref=f1e159]
            - button "Save notes" [disabled] [ref=f1e160]
        - article [ref=f1e161]:
          - heading "Moss Thread Bags" [level=3] [ref=f1e162]
          - paragraph [ref=f1e163]: Philippines · Fictional small-run pouch producer with unverified certification status.
          - paragraph [ref=f1e164]: "MOQ: 800 · Typical lead time: 37 days"
          - paragraph [ref=f1e165]: "Indicative price: Unknown"
          - paragraph [ref=f1e166]: "Capabilities: CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=f1e167]
          - list [ref=f1e168]:
            - listitem [ref=f1e169]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=f1e170]: UNKNOWN
            - listitem [ref=f1e171]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=f1e172]: MEETS
              - generic [ref=f1e173]: "· Evidence: Synthetic material sheet"
            - listitem [ref=f1e174]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=f1e175]: UNKNOWN
          - paragraph [ref=f1e176]: "General MOQ compatibility: UNKNOWN"
          - group [ref=f1e177]:
            - generic "Available evidence" [ref=f1e178]
          - button "Explain this supplier" [ref=f1e180] [cursor=pointer]
          - generic [ref=f1e181]:
            - button "Remove from shortlist" [ref=f1e182] [cursor=pointer]
            - button "Dismiss" [ref=f1e183] [cursor=pointer]
          - generic [ref=f1e184]:
            - generic [ref=f1e185]:
              - text: Private notes for Moss Thread Bags
              - textbox "Private notes for Moss Thread Bags" [ref=f1e186]
            - button "Save notes" [disabled] [ref=f1e187]
        - article [ref=f1e188]:
          - heading "Sunrise Textile Lab" [level=3] [ref=f1e189]
          - paragraph [ref=f1e190]: India · Fictional bag producer with conflicting current certification records.
          - paragraph [ref=f1e191]: "MOQ: 1500 · Typical lead time: 45 days"
          - paragraph [ref=f1e192]: "Indicative price: 4.1000 USD"
          - paragraph [ref=f1e193]: "Capabilities: CERTIFICATION: grs; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=f1e194]
          - list [ref=f1e195]:
            - listitem [ref=f1e196]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=f1e197]: CONFLICT
              - generic [ref=f1e198]: "· Evidence: Synthetic certification register B, Synthetic certification register A"
            - listitem [ref=f1e199]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=f1e200]: UNKNOWN
            - listitem [ref=f1e201]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=f1e202]: UNKNOWN
          - paragraph [ref=f1e203]: "General MOQ compatibility: UNKNOWN"
          - group [ref=f1e204]:
            - generic "Available evidence" [ref=f1e205]
          - button "Explain this supplier" [ref=f1e207] [cursor=pointer]
          - generic [ref=f1e208]:
            - button "Add to shortlist" [ref=f1e209] [cursor=pointer]
            - button "Dismiss" [ref=f1e210] [cursor=pointer]
          - generic [ref=f1e211]:
            - generic [ref=f1e212]:
              - text: Private notes for Sunrise Textile Lab
              - textbox "Private notes for Sunrise Textile Lab" [ref=f1e213]
            - button "Save notes" [disabled] [ref=f1e214]
        - article [ref=f1e215]:
          - heading "Willow Stitch Studio" [level=3] [ref=f1e216]
          - paragraph [ref=f1e217]: Indonesia · Fictional textile studio with cosmetic pouch and branding capabilities.
          - paragraph [ref=f1e218]: "MOQ: 1800 · Typical lead time: 40 days"
          - paragraph [ref=f1e219]: "Indicative price: 4.2000 USD"
          - paragraph [ref=f1e220]: "Capabilities: BRANDING_METHOD: embroidery; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=f1e221]
          - list [ref=f1e222]:
            - listitem [ref=f1e223]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=f1e224]: UNKNOWN
            - listitem [ref=f1e225]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=f1e226]: MEETS
              - generic [ref=f1e227]: "· Evidence: Synthetic material sheet"
            - listitem [ref=f1e228]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=f1e229]: MEETS
              - generic [ref=f1e230]: "· Evidence: Synthetic branding sheet"
          - paragraph [ref=f1e231]: "General MOQ compatibility: UNKNOWN"
          - group [ref=f1e232]:
            - generic "Available evidence" [ref=f1e233]
          - button "Explain this supplier" [ref=f1e235] [cursor=pointer]
          - generic [ref=f1e236]:
            - button "Remove from shortlist" [ref=f1e237] [cursor=pointer]
            - button "Dismiss" [ref=f1e238] [cursor=pointer]
          - generic [ref=f1e239]:
            - generic [ref=f1e240]:
              - text: Private notes for Willow Stitch Studio
              - textbox "Private notes for Willow Stitch Studio" [ref=f1e241]
            - button "Save notes" [disabled] [ref=f1e242]
      - region [ref=f1e243]:
        - heading "Quotes" [level=2] [ref=f1e244]
        - group [ref=f1e246]:
          - article [ref=f1e247]:
            - heading "Harbor Pouch Works" [level=3] [ref=f1e248]
            - paragraph [ref=f1e249]: "Status: CONFIRMED"
            - status [ref=f1e250]: Confirmed PDF quote. Current values are ready for comparison.
            - paragraph [ref=f1e251]: Review the PDF source, AI extraction, and current values.
            - generic [ref=f1e252]:
              - generic [ref=f1e253]:
                - term [ref=f1e254]: Quoted quantity
                - definition [ref=f1e255]:
                  - paragraph [ref=f1e256]: "Extraction: Known"
                  - paragraph [ref=f1e257]: "AI extracted value: 2000"
                  - paragraph [ref=f1e258]: "Current confirmed value: 2000"
                  - paragraph [ref=f1e259]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e260]:
                    - paragraph [ref=f1e261]: "PDF source evidence:"
                    - list [ref=f1e262]:
                      - listitem [ref=f1e263]:
                        - paragraph [ref=f1e264]: Page 1, block p1-b4
                        - blockquote [ref=f1e265]: "Quoted quantity: 2,000 units"
                        - paragraph [ref=f1e266]: "Associated extracted value: 2000"
              - generic [ref=f1e267]:
                - term [ref=f1e268]: Unit price
                - definition [ref=f1e269]:
                  - paragraph [ref=f1e270]: "Extraction: Known"
                  - paragraph [ref=f1e271]: "AI extracted value: 4.60"
                  - paragraph [ref=f1e272]: "Current confirmed value: 4.60"
                  - paragraph [ref=f1e273]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e274]:
                    - paragraph [ref=f1e275]: "PDF source evidence:"
                    - list [ref=f1e276]:
                      - listitem [ref=f1e277]:
                        - paragraph [ref=f1e278]: Page 1, block p1-b5
                        - blockquote [ref=f1e279]: "Unit price: USD 4.60"
                        - paragraph [ref=f1e280]: "Associated extracted value: 4.60"
              - generic [ref=f1e281]:
                - term [ref=f1e282]: Original currency (three-letter code)
                - definition [ref=f1e283]:
                  - paragraph [ref=f1e284]: "Extraction: Known"
                  - paragraph [ref=f1e285]: "AI extracted value: USD"
                  - paragraph [ref=f1e286]: "Current confirmed value: USD"
                  - paragraph [ref=f1e287]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e288]:
                    - paragraph [ref=f1e289]: "PDF source evidence:"
                    - list [ref=f1e290]:
                      - listitem [ref=f1e291]:
                        - paragraph [ref=f1e292]: Page 1, block p1-b5
                        - blockquote [ref=f1e293]: "Unit price: USD 4.60"
                        - paragraph [ref=f1e294]: "Associated extracted value: USD"
              - generic [ref=f1e295]:
                - term [ref=f1e296]: Minimum order quantity
                - definition [ref=f1e297]:
                  - paragraph [ref=f1e298]: "Extraction: Known"
                  - paragraph [ref=f1e299]: "AI extracted value: 1000"
                  - paragraph [ref=f1e300]: "Current confirmed value: 1000"
                  - paragraph [ref=f1e301]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e302]:
                    - paragraph [ref=f1e303]: "PDF source evidence:"
                    - list [ref=f1e304]:
                      - listitem [ref=f1e305]:
                        - paragraph [ref=f1e306]: Page 1, block p1-b6
                        - blockquote [ref=f1e307]: "Minimum order quantity: 1,000 units"
                        - paragraph [ref=f1e308]: "Associated extracted value: 1000"
              - generic [ref=f1e309]:
                - term [ref=f1e310]: Sample cost
                - definition [ref=f1e311]:
                  - paragraph [ref=f1e312]: "Extraction: Known"
                  - paragraph [ref=f1e313]: "AI extracted value: 40"
                  - paragraph [ref=f1e314]: "Current confirmed value: 40"
                  - paragraph [ref=f1e315]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e316]:
                    - paragraph [ref=f1e317]: "PDF source evidence:"
                    - list [ref=f1e318]:
                      - listitem [ref=f1e319]:
                        - paragraph [ref=f1e320]: Page 1, block p1-b8
                        - blockquote [ref=f1e321]: "Sample cost: USD 40"
                        - paragraph [ref=f1e322]: "Associated extracted value: 40"
              - generic [ref=f1e323]:
                - term [ref=f1e324]: Tooling or setup cost
                - definition [ref=f1e325]:
                  - paragraph [ref=f1e326]: "Extraction: Known"
                  - paragraph [ref=f1e327]: "AI extracted value: 150"
                  - paragraph [ref=f1e328]: "Current confirmed value: 150"
                  - paragraph [ref=f1e329]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e330]:
                    - paragraph [ref=f1e331]: "PDF source evidence:"
                    - list [ref=f1e332]:
                      - listitem [ref=f1e333]:
                        - paragraph [ref=f1e334]: Page 1, block p1-b7
                        - blockquote [ref=f1e335]: "Tooling/setup cost: USD 150"
                        - paragraph [ref=f1e336]: "Associated extracted value: 150"
              - generic [ref=f1e337]:
                - term [ref=f1e338]: Packaging cost
                - definition [ref=f1e339]:
                  - paragraph [ref=f1e340]: "Extraction: Unknown"
                  - paragraph [ref=f1e341]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e342]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e343]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e344]: No saved source citations available for this field.
              - generic [ref=f1e345]:
                - term [ref=f1e346]: Shipping cost
                - definition [ref=f1e347]:
                  - paragraph [ref=f1e348]: "Extraction: Known"
                  - paragraph [ref=f1e349]: "AI extracted value: 320"
                  - paragraph [ref=f1e350]: "Current confirmed value: 320"
                  - paragraph [ref=f1e351]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e352]:
                    - paragraph [ref=f1e353]: "PDF source evidence:"
                    - list [ref=f1e354]:
                      - listitem [ref=f1e355]:
                        - paragraph [ref=f1e356]: Page 1, block p1-b11
                        - blockquote [ref=f1e357]: "Shipping cost: USD 320 to Manila"
                        - paragraph [ref=f1e358]: "Associated extracted value: 320"
              - generic [ref=f1e359]:
                - term [ref=f1e360]: Sample lead time
                - definition [ref=f1e361]:
                  - paragraph [ref=f1e362]: "Extraction: Known"
                  - paragraph [ref=f1e363]: "AI extracted value: 7 days"
                  - paragraph [ref=f1e364]: "Current confirmed value: 7 days"
                  - paragraph [ref=f1e365]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e366]:
                    - paragraph [ref=f1e367]: "PDF source evidence:"
                    - list [ref=f1e368]:
                      - listitem [ref=f1e369]:
                        - paragraph [ref=f1e370]: Page 1, block p1-b9
                        - blockquote [ref=f1e371]: "Sample lead time: 7 days"
                        - paragraph [ref=f1e372]: "Associated extracted value: 7 days"
              - generic [ref=f1e373]:
                - term [ref=f1e374]: Production lead time
                - definition [ref=f1e375]:
                  - paragraph [ref=f1e376]: "Extraction: Known"
                  - paragraph [ref=f1e377]: "AI extracted value: 32 days after sample approval"
                  - paragraph [ref=f1e378]: "Current confirmed value: 32 days after sample approval"
                  - paragraph [ref=f1e379]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e380]:
                    - paragraph [ref=f1e381]: "PDF source evidence:"
                    - list [ref=f1e382]:
                      - listitem [ref=f1e383]:
                        - paragraph [ref=f1e384]: Page 1, block p1-b10
                        - blockquote [ref=f1e385]: "Production lead time: 32 days after sample approval"
                        - paragraph [ref=f1e386]: "Associated extracted value: 32 days after sample approval"
              - generic [ref=f1e387]:
                - term [ref=f1e388]: Shipping time
                - definition [ref=f1e389]:
                  - paragraph [ref=f1e390]: "Extraction: Known"
                  - paragraph [ref=f1e391]: "AI extracted value: 12 days after production"
                  - paragraph [ref=f1e392]: "Current confirmed value: 12 days after production"
                  - paragraph [ref=f1e393]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e394]:
                    - paragraph [ref=f1e395]: "PDF source evidence:"
                    - list [ref=f1e396]:
                      - listitem [ref=f1e397]:
                        - paragraph [ref=f1e398]: Page 1, block p1-b12
                        - blockquote [ref=f1e399]: "Shipping time: 12 days after production"
                        - paragraph [ref=f1e400]: "Associated extracted value: 12 days after production"
              - generic [ref=f1e401]:
                - term [ref=f1e402]: Total stated lead time
                - definition [ref=f1e403]:
                  - paragraph [ref=f1e404]: "Extraction: Unknown"
                  - paragraph [ref=f1e405]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e406]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e407]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e408]: No saved source citations available for this field.
              - generic [ref=f1e409]:
                - term [ref=f1e410]: Payment terms
                - definition [ref=f1e411]:
                  - paragraph [ref=f1e412]: "Extraction: Known"
                  - paragraph [ref=f1e413]: "AI extracted value: 30% deposit, 70% before dispatch"
                  - paragraph [ref=f1e414]: "Current confirmed value: 30% deposit, 70% before dispatch"
                  - paragraph [ref=f1e415]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e416]:
                    - paragraph [ref=f1e417]: "PDF source evidence:"
                    - list [ref=f1e418]:
                      - listitem [ref=f1e419]:
                        - paragraph [ref=f1e420]: Page 1, block p1-b13
                        - blockquote [ref=f1e421]: "Payment terms: 30% deposit, 70% before dispatch"
                        - paragraph [ref=f1e422]: "Associated extracted value: 30% deposit, 70% before dispatch"
              - generic [ref=f1e423]:
                - term [ref=f1e424]: Incoterm
                - definition [ref=f1e425]:
                  - paragraph [ref=f1e426]: "Extraction: Unknown"
                  - paragraph [ref=f1e427]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e428]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e429]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e430]: No saved source citations available for this field.
              - generic [ref=f1e431]:
                - term [ref=f1e432]: Quote validity
                - definition [ref=f1e433]:
                  - paragraph [ref=f1e434]: "Extraction: Known"
                  - paragraph [ref=f1e435]: "AI extracted value: 30 days"
                  - paragraph [ref=f1e436]: "Current confirmed value: 30 days"
                  - paragraph [ref=f1e437]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e438]:
                    - paragraph [ref=f1e439]: "PDF source evidence:"
                    - list [ref=f1e440]:
                      - listitem [ref=f1e441]:
                        - paragraph [ref=f1e442]: Page 1, block p1-b14
                        - blockquote [ref=f1e443]: "Quote validity: 30 days"
                        - paragraph [ref=f1e444]: "Associated extracted value: 30 days"
              - generic [ref=f1e445]:
                - term [ref=f1e446]: Warranty
                - definition [ref=f1e447]:
                  - paragraph [ref=f1e448]: "Extraction: Unknown"
                  - paragraph [ref=f1e449]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e450]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e451]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e452]: No saved source citations available for this field.
              - generic [ref=f1e453]:
                - term [ref=f1e454]: Certifications
                - definition [ref=f1e455]:
                  - paragraph [ref=f1e456]: "Extraction: Known"
                  - paragraph [ref=f1e457]: "AI extracted value: Synthetic GRS record: current for this fictional supplier"
                  - paragraph [ref=f1e458]: "Current confirmed value: Synthetic GRS record: current for this fictional supplier"
                  - paragraph [ref=f1e459]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e460]:
                    - paragraph [ref=f1e461]: "PDF source evidence:"
                    - list [ref=f1e462]:
                      - listitem [ref=f1e463]:
                        - paragraph [ref=f1e464]: Page 2, block p2-b4
                        - blockquote [ref=f1e465]: "Synthetic GRS record: current for this fictional supplier"
                        - paragraph [ref=f1e466]: "Associated extracted value: Synthetic GRS record: current for this fictional supplier"
              - generic [ref=f1e467]:
                - term [ref=f1e468]: Compliance notes
                - definition [ref=f1e469]:
                  - paragraph [ref=f1e470]: "Extraction: Unknown"
                  - paragraph [ref=f1e471]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e472]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e473]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e474]: No saved source citations available for this field.
              - generic [ref=f1e475]:
                - term [ref=f1e476]: Exclusions
                - definition [ref=f1e477]:
                  - paragraph [ref=f1e478]: "Extraction: Known"
                  - paragraph [ref=f1e479]: "AI extracted value: import duties are not included"
                  - paragraph [ref=f1e480]: "Current confirmed value: import duties are not included"
                  - paragraph [ref=f1e481]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e482]:
                    - paragraph [ref=f1e483]: "PDF source evidence:"
                    - list [ref=f1e484]:
                      - listitem [ref=f1e485]:
                        - paragraph [ref=f1e486]: Page 2, block p2-b7
                        - blockquote [ref=f1e487]: "Exclusion: import duties are not included"
                        - paragraph [ref=f1e488]: "Associated extracted value: import duties are not included"
              - generic [ref=f1e489]:
                - term [ref=f1e490]: Special conditions
                - definition [ref=f1e491]:
                  - paragraph [ref=f1e492]: "Extraction: Unknown"
                  - paragraph [ref=f1e493]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e494]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e495]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e496]: No saved source citations available for this field.
              - generic [ref=f1e497]:
                - term [ref=f1e498]: Supplier notes
                - definition [ref=f1e499]:
                  - paragraph [ref=f1e500]: "Extraction: Unknown"
                  - paragraph [ref=f1e501]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e502]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e503]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e504]: No saved source citations available for this field.
            - paragraph [ref=f1e505]: "Notes: None"
            - button "Edit confirmed PDF quote" [ref=f1e506] [cursor=pointer]
          - article [ref=f1e507]:
            - heading "Moss Thread Bags" [level=3] [ref=f1e508]
            - paragraph [ref=f1e509]: "Status: Not Added"
            - generic [ref=f1e510]:
              - text: Upload PDF quote
              - button "Upload PDF quote" [ref=f1e511]
            - generic [ref=f1e512]:
              - paragraph [ref=f1e513]: Leave a field blank if it is Unknown.
              - generic [ref=f1e514]:
                - text: Quoted quantity
                - spinbutton "Quoted quantity" [ref=f1e515]
              - generic [ref=f1e516]:
                - text: Unit price
                - spinbutton "Unit price" [ref=f1e517]
              - generic [ref=f1e518]:
                - text: Original currency (three-letter code)
                - textbox "Original currency (three-letter code)" [ref=f1e519]
              - generic [ref=f1e520]:
                - text: Minimum order quantity
                - spinbutton "Minimum order quantity" [ref=f1e521]
              - generic [ref=f1e522]:
                - text: Sample cost
                - spinbutton "Sample cost" [ref=f1e523]
              - generic [ref=f1e524]:
                - text: Tooling or setup cost
                - spinbutton "Tooling or setup cost" [ref=f1e525]
              - generic [ref=f1e526]:
                - text: Packaging cost
                - spinbutton "Packaging cost" [ref=f1e527]
              - generic [ref=f1e528]:
                - text: Shipping cost
                - spinbutton "Shipping cost" [ref=f1e529]
              - generic [ref=f1e530]:
                - text: Sample lead time
                - textbox "Sample lead time" [ref=f1e531]
              - generic [ref=f1e532]:
                - text: Production lead time
                - textbox "Production lead time" [ref=f1e533]
              - generic [ref=f1e534]:
                - text: Shipping time
                - textbox "Shipping time" [ref=f1e535]
              - generic [ref=f1e536]:
                - text: Total stated lead time
                - textbox "Total stated lead time" [ref=f1e537]
              - generic [ref=f1e538]:
                - text: Payment terms
                - textbox "Payment terms" [ref=f1e539]
              - generic [ref=f1e540]:
                - text: Incoterm
                - textbox "Incoterm" [ref=f1e541]
              - generic [ref=f1e542]:
                - text: Quote validity
                - textbox "Quote validity" [ref=f1e543]
              - generic [ref=f1e544]:
                - text: Warranty
                - textbox "Warranty" [ref=f1e545]
              - generic [ref=f1e546]:
                - text: Certifications
                - textbox "Certifications" [ref=f1e547]
              - generic [ref=f1e548]:
                - text: Compliance notes
                - textbox "Compliance notes" [ref=f1e549]
              - generic [ref=f1e550]:
                - text: Exclusions
                - textbox "Exclusions" [ref=f1e551]
              - generic [ref=f1e552]:
                - text: Special conditions
                - textbox "Special conditions" [ref=f1e553]
              - generic [ref=f1e554]:
                - text: Supplier notes
                - textbox "Supplier notes" [ref=f1e555]
              - generic [ref=f1e556]:
                - text: Quote notes
                - textbox "Quote notes" [ref=f1e557]
              - button "Create manual quote" [ref=f1e558] [cursor=pointer]
          - article [ref=f1e559]:
            - heading "Willow Stitch Studio" [level=3] [ref=f1e560]
            - paragraph [ref=f1e561]: "Status: CONFIRMED"
            - status [ref=f1e562]: Confirmed PDF quote. Current values are ready for comparison.
            - paragraph [ref=f1e563]: Review the PDF source, AI extraction, and current values.
            - generic [ref=f1e564]:
              - generic [ref=f1e565]:
                - term [ref=f1e566]: Quoted quantity
                - definition [ref=f1e567]:
                  - paragraph [ref=f1e568]: "Extraction: Known"
                  - paragraph [ref=f1e569]: "AI extracted value: 2000"
                  - paragraph [ref=f1e570]: "Current confirmed value: 2000"
                  - paragraph [ref=f1e571]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e572]:
                    - paragraph [ref=f1e573]: "PDF source evidence:"
                    - list [ref=f1e574]:
                      - listitem [ref=f1e575]:
                        - paragraph [ref=f1e576]: Page 1, block p1-b4
                        - blockquote [ref=f1e577]: "Quoted quantity: 2,000 units"
                        - paragraph [ref=f1e578]: "Associated extracted value: 2000"
              - generic [ref=f1e579]:
                - term [ref=f1e580]: Unit price
                - definition [ref=f1e581]:
                  - paragraph [ref=f1e582]: "Extraction: Known"
                  - paragraph [ref=f1e583]: "AI extracted value: 4.20"
                  - paragraph [ref=f1e584]: "Current confirmed value: 4.20"
                  - paragraph [ref=f1e585]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e586]:
                    - paragraph [ref=f1e587]: "PDF source evidence:"
                    - list [ref=f1e588]:
                      - listitem [ref=f1e589]:
                        - paragraph [ref=f1e590]: Page 1, block p1-b5
                        - blockquote [ref=f1e591]: "Unit price: USD 4.20"
                        - paragraph [ref=f1e592]: "Associated extracted value: 4.20"
              - generic [ref=f1e593]:
                - term [ref=f1e594]: Original currency (three-letter code)
                - definition [ref=f1e595]:
                  - paragraph [ref=f1e596]: "Extraction: Known"
                  - paragraph [ref=f1e597]: "AI extracted value: USD"
                  - paragraph [ref=f1e598]: "Current confirmed value: USD"
                  - paragraph [ref=f1e599]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e600]:
                    - paragraph [ref=f1e601]: "PDF source evidence:"
                    - list [ref=f1e602]:
                      - listitem [ref=f1e603]:
                        - paragraph [ref=f1e604]: Page 1, block p1-b5
                        - blockquote [ref=f1e605]: "Unit price: USD 4.20"
                        - paragraph [ref=f1e606]: "Associated extracted value: USD"
              - generic [ref=f1e607]:
                - term [ref=f1e608]: Minimum order quantity
                - definition [ref=f1e609]:
                  - paragraph [ref=f1e610]: "Extraction: Known"
                  - paragraph [ref=f1e611]: "AI extracted value: 1800"
                  - paragraph [ref=f1e612]: "Current confirmed value: 1800"
                  - paragraph [ref=f1e613]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e614]:
                    - paragraph [ref=f1e615]: "PDF source evidence:"
                    - list [ref=f1e616]:
                      - listitem [ref=f1e617]:
                        - paragraph [ref=f1e618]: Page 1, block p1-b6
                        - blockquote [ref=f1e619]: "Minimum order quantity: 1,800 units"
                        - paragraph [ref=f1e620]: "Associated extracted value: 1800"
              - generic [ref=f1e621]:
                - term [ref=f1e622]: Sample cost
                - definition [ref=f1e623]:
                  - paragraph [ref=f1e624]: "Extraction: Known"
                  - paragraph [ref=f1e625]: "AI extracted value: 35"
                  - paragraph [ref=f1e626]: "Current confirmed value: 35"
                  - paragraph [ref=f1e627]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e628]:
                    - paragraph [ref=f1e629]: "PDF source evidence:"
                    - list [ref=f1e630]:
                      - listitem [ref=f1e631]:
                        - paragraph [ref=f1e632]: Page 1, block p1-b8
                        - blockquote [ref=f1e633]: "Sample cost: USD 35"
                        - paragraph [ref=f1e634]: "Associated extracted value: 35"
              - generic [ref=f1e635]:
                - term [ref=f1e636]: Tooling or setup cost
                - definition [ref=f1e637]:
                  - paragraph [ref=f1e638]: "Extraction: Known"
                  - paragraph [ref=f1e639]: "AI extracted value: 100"
                  - paragraph [ref=f1e640]: "Current confirmed value: 100"
                  - paragraph [ref=f1e641]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e642]:
                    - paragraph [ref=f1e643]: "PDF source evidence:"
                    - list [ref=f1e644]:
                      - listitem [ref=f1e645]:
                        - paragraph [ref=f1e646]: Page 1, block p1-b7
                        - blockquote [ref=f1e647]: "Tooling/setup cost: USD 100"
                        - paragraph [ref=f1e648]: "Associated extracted value: 100"
              - generic [ref=f1e649]:
                - term [ref=f1e650]: Packaging cost
                - definition [ref=f1e651]:
                  - paragraph [ref=f1e652]: "Extraction: Unknown"
                  - paragraph [ref=f1e653]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e654]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e655]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e656]: No saved source citations available for this field.
              - generic [ref=f1e657]:
                - term [ref=f1e658]: Shipping cost
                - definition [ref=f1e659]:
                  - paragraph [ref=f1e660]: "Extraction: Known"
                  - paragraph [ref=f1e661]: "AI extracted value: 280"
                  - paragraph [ref=f1e662]: "Current confirmed value: 280"
                  - paragraph [ref=f1e663]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e664]:
                    - paragraph [ref=f1e665]: "PDF source evidence:"
                    - list [ref=f1e666]:
                      - listitem [ref=f1e667]:
                        - paragraph [ref=f1e668]: Page 1, block p1-b11
                        - blockquote [ref=f1e669]: "Shipping cost: USD 280 to Manila"
                        - paragraph [ref=f1e670]: "Associated extracted value: 280"
              - generic [ref=f1e671]:
                - term [ref=f1e672]: Sample lead time
                - definition [ref=f1e673]:
                  - paragraph [ref=f1e674]: "Extraction: Known"
                  - paragraph [ref=f1e675]: "AI extracted value: 10 days"
                  - paragraph [ref=f1e676]: "Current confirmed value: 10 days"
                  - paragraph [ref=f1e677]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e678]:
                    - paragraph [ref=f1e679]: "PDF source evidence:"
                    - list [ref=f1e680]:
                      - listitem [ref=f1e681]:
                        - paragraph [ref=f1e682]: Page 1, block p1-b9
                        - blockquote [ref=f1e683]: "Sample lead time: 10 days"
                        - paragraph [ref=f1e684]: "Associated extracted value: 10 days"
              - generic [ref=f1e685]:
                - term [ref=f1e686]: Production lead time
                - definition [ref=f1e687]:
                  - paragraph [ref=f1e688]: "Extraction: Known"
                  - paragraph [ref=f1e689]: "AI extracted value: 40 days after sample approval"
                  - paragraph [ref=f1e690]: "Current confirmed value: 40 days after sample approval"
                  - paragraph [ref=f1e691]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e692]:
                    - paragraph [ref=f1e693]: "PDF source evidence:"
                    - list [ref=f1e694]:
                      - listitem [ref=f1e695]:
                        - paragraph [ref=f1e696]: Page 1, block p1-b10
                        - blockquote [ref=f1e697]: "Production lead time: 40 days after sample approval"
                        - paragraph [ref=f1e698]: "Associated extracted value: 40 days after sample approval"
              - generic [ref=f1e699]:
                - term [ref=f1e700]: Shipping time
                - definition [ref=f1e701]:
                  - paragraph [ref=f1e702]: "Extraction: Known"
                  - paragraph [ref=f1e703]: "AI extracted value: 14 days after production"
                  - paragraph [ref=f1e704]: "Current confirmed value: 14 days after production"
                  - paragraph [ref=f1e705]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e706]:
                    - paragraph [ref=f1e707]: "PDF source evidence:"
                    - list [ref=f1e708]:
                      - listitem [ref=f1e709]:
                        - paragraph [ref=f1e710]: Page 1, block p1-b12
                        - blockquote [ref=f1e711]: "Shipping time: 14 days after production"
                        - paragraph [ref=f1e712]: "Associated extracted value: 14 days after production"
              - generic [ref=f1e713]:
                - term [ref=f1e714]: Total stated lead time
                - definition [ref=f1e715]:
                  - paragraph [ref=f1e716]: "Extraction: Unknown"
                  - paragraph [ref=f1e717]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e718]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e719]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e720]: No saved source citations available for this field.
              - generic [ref=f1e721]:
                - term [ref=f1e722]: Payment terms
                - definition [ref=f1e723]:
                  - paragraph [ref=f1e724]: "Extraction: Known"
                  - paragraph [ref=f1e725]: "AI extracted value: 50% deposit, 50% before dispatch"
                  - paragraph [ref=f1e726]: "Current confirmed value: 50% deposit, 50% before dispatch"
                  - paragraph [ref=f1e727]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e728]:
                    - paragraph [ref=f1e729]: "PDF source evidence:"
                    - list [ref=f1e730]:
                      - listitem [ref=f1e731]:
                        - paragraph [ref=f1e732]: Page 1, block p1-b14
                        - blockquote [ref=f1e733]: "Payment terms: 50% deposit, 50% before dispatch"
                        - paragraph [ref=f1e734]: "Associated extracted value: 50% deposit, 50% before dispatch"
              - generic [ref=f1e735]:
                - term [ref=f1e736]: Incoterm
                - definition [ref=f1e737]:
                  - paragraph [ref=f1e738]: "Extraction: Unknown"
                  - paragraph [ref=f1e739]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e740]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e741]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e742]: No saved source citations available for this field.
              - generic [ref=f1e743]:
                - term [ref=f1e744]: Quote validity
                - definition [ref=f1e745]:
                  - paragraph [ref=f1e746]: "Extraction: Known"
                  - paragraph [ref=f1e747]: "AI extracted value: 30 days"
                  - paragraph [ref=f1e748]: "Current confirmed value: 30 days"
                  - paragraph [ref=f1e749]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e750]:
                    - paragraph [ref=f1e751]: "PDF source evidence:"
                    - list [ref=f1e752]:
                      - listitem [ref=f1e753]:
                        - paragraph [ref=f1e754]: Page 1, block p1-b15
                        - blockquote [ref=f1e755]: "Quote validity: 30 days"
                        - paragraph [ref=f1e756]: "Associated extracted value: 30 days"
              - generic [ref=f1e757]:
                - term [ref=f1e758]: Warranty
                - definition [ref=f1e759]:
                  - paragraph [ref=f1e760]: "Extraction: Unknown"
                  - paragraph [ref=f1e761]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e762]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e763]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e764]: No saved source citations available for this field.
              - generic [ref=f1e765]:
                - term [ref=f1e766]: Certifications
                - definition [ref=f1e767]:
                  - paragraph [ref=f1e768]: "Extraction: Unknown"
                  - paragraph [ref=f1e769]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e770]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e771]: "Current origin: AI EXTRACTED"
                  - generic [ref=f1e772]:
                    - paragraph [ref=f1e773]: "PDF source evidence:"
                    - list [ref=f1e774]:
                      - listitem [ref=f1e775]:
                        - paragraph [ref=f1e776]: Page 1, block p1-b13
                        - blockquote [ref=f1e777]: "Preferred GRS certification: not stated in this quote"
              - generic [ref=f1e778]:
                - term [ref=f1e779]: Compliance notes
                - definition [ref=f1e780]:
                  - paragraph [ref=f1e781]: "Extraction: Unknown"
                  - paragraph [ref=f1e782]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e783]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e784]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e785]: No saved source citations available for this field.
              - generic [ref=f1e786]:
                - term [ref=f1e787]: Exclusions
                - definition [ref=f1e788]:
                  - paragraph [ref=f1e789]: "Extraction: Unknown"
                  - paragraph [ref=f1e790]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e791]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e792]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e793]: No saved source citations available for this field.
              - generic [ref=f1e794]:
                - term [ref=f1e795]: Special conditions
                - definition [ref=f1e796]:
                  - paragraph [ref=f1e797]: "Extraction: Unknown"
                  - paragraph [ref=f1e798]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e799]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e800]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e801]: No saved source citations available for this field.
              - generic [ref=f1e802]:
                - term [ref=f1e803]: Supplier notes
                - definition [ref=f1e804]:
                  - paragraph [ref=f1e805]: "Extraction: Unknown"
                  - paragraph [ref=f1e806]: "AI extracted value: Unknown"
                  - paragraph [ref=f1e807]: "Current confirmed value: Unknown"
                  - paragraph [ref=f1e808]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=f1e809]: No saved source citations available for this field.
            - paragraph [ref=f1e810]: "Notes: None"
            - button "Edit confirmed PDF quote" [ref=f1e811] [cursor=pointer]
      - region [ref=f1e812]:
        - heading "Comparison" [level=2] [ref=f1e813]
        - status [ref=f1e814]: Comparison is current.
        - table [ref=f1e816]:
          - caption [ref=f1e817]: Factual comparison of confirmed supplier quotes
          - rowgroup [ref=f1e818]:
            - row [ref=f1e819]:
              - columnheader "Criterion" [ref=f1e820]
              - columnheader "Willow Stitch Studio" [ref=f1e821]
              - columnheader "Harbor Pouch Works" [ref=f1e822]
          - rowgroup [ref=f1e823]:
            - row [ref=f1e824]:
              - rowheader "Unit price" [ref=f1e825]
              - cell "USD 4.20 Confirmed project quote price" [ref=f1e826]:
                - strong [ref=f1e827]: USD 4.20
                - generic [ref=f1e828]: Confirmed project quote price
                - group [ref=f1e829]:
                  - generic "Source details" [ref=f1e830]
              - cell "USD 4.60 Confirmed project quote price" [ref=f1e831]:
                - strong [ref=f1e832]: USD 4.60
                - generic [ref=f1e833]: Confirmed project quote price
                - group [ref=f1e834]:
                  - generic "Source details" [ref=f1e835]
            - row [ref=f1e836]:
              - rowheader "Quoted quantity" [ref=f1e837]
              - cell [ref=f1e838]:
                - strong [ref=f1e839]: "2000"
                - group [ref=f1e840]:
                  - generic "Source details" [ref=f1e841]
              - cell [ref=f1e842]:
                - strong [ref=f1e843]: "2000"
                - group [ref=f1e844]:
                  - generic "Source details" [ref=f1e845]
            - row [ref=f1e846]:
              - rowheader "Minimum order quantity" [ref=f1e847]
              - cell [ref=f1e848]:
                - strong [ref=f1e849]: "1800"
                - group [ref=f1e850]:
                  - generic "Source details" [ref=f1e851]
              - cell [ref=f1e852]:
                - strong [ref=f1e853]: "1000"
                - group [ref=f1e854]:
                  - generic "Source details" [ref=f1e855]
            - row [ref=f1e856]:
              - rowheader "Production lead time" [ref=f1e857]
              - cell [ref=f1e858]:
                - strong [ref=f1e859]: 40 days after sample approval
                - group [ref=f1e860]:
                  - generic "Source details" [ref=f1e861]
              - cell [ref=f1e862]:
                - strong [ref=f1e863]: 32 days after sample approval
                - group [ref=f1e864]:
                  - generic "Source details" [ref=f1e865]
            - row [ref=f1e866]:
              - rowheader "Delivery commitment" [ref=f1e867]
              - cell [ref=f1e868]:
                - strong [ref=f1e869]: Unknown
              - cell [ref=f1e870]:
                - strong [ref=f1e871]: Unknown
            - row [ref=f1e872]:
              - rowheader "Tooling or setup cost" [ref=f1e873]
              - cell [ref=f1e874]:
                - strong [ref=f1e875]: USD 100
                - group [ref=f1e876]:
                  - generic "Source details" [ref=f1e877]
              - cell [ref=f1e878]:
                - strong [ref=f1e879]: USD 150
                - group [ref=f1e880]:
                  - generic "Source details" [ref=f1e881]
            - row [ref=f1e882]:
              - rowheader "Shipping cost" [ref=f1e883]
              - cell [ref=f1e884]:
                - strong [ref=f1e885]: USD 280
                - group [ref=f1e886]:
                  - generic "Source details" [ref=f1e887]
              - cell [ref=f1e888]:
                - strong [ref=f1e889]: USD 320
                - group [ref=f1e890]:
                  - generic "Source details" [ref=f1e891]
            - row [ref=f1e892]:
              - 'rowheader "Certification Required Expected: grs" [ref=f1e893]':
                - text: Certification
                - generic [ref=f1e894]: Required
                - generic [ref=f1e895]: "Expected: grs"
              - cell [ref=f1e896]:
                - strong [ref=f1e897]: Unknown
              - cell [ref=f1e898]:
                - strong [ref=f1e899]: Meets
                - group [ref=f1e900]:
                  - generic "Source details" [ref=f1e901]
            - row [ref=f1e902]:
              - 'rowheader "Material Informational Expected: recycled polyester" [ref=f1e903]':
                - text: Material
                - generic [ref=f1e904]: Informational
                - generic [ref=f1e905]: "Expected: recycled polyester"
              - cell [ref=f1e906]:
                - strong [ref=f1e907]: Meets
                - group [ref=f1e908]:
                  - generic "Source details" [ref=f1e909]
              - cell [ref=f1e910]:
                - strong [ref=f1e911]: Meets
                - group [ref=f1e912]:
                  - generic "Source details" [ref=f1e913]
            - row [ref=f1e914]:
              - 'rowheader "Capability Required Expected: Yes · CUSTOM_BRANDING" [ref=f1e915]':
                - text: Capability
                - generic [ref=f1e916]: Required
                - generic [ref=f1e917]: "Expected: Yes · CUSTOM_BRANDING"
              - cell [ref=f1e918]:
                - strong [ref=f1e919]: Meets
                - group [ref=f1e920]:
                  - generic "Source details" [ref=f1e921]
              - cell [ref=f1e922]:
                - strong [ref=f1e923]: Meets
                - group [ref=f1e924]:
                  - generic "Source details" [ref=f1e925]
        - button "Analyze Comparison" [ref=f1e926] [cursor=pointer]
        - group [ref=f1e927]:
          - generic "Missing or conflicting information" [ref=f1e928]
        - button "Regenerate Comparison" [ref=f1e929] [cursor=pointer]
      - region [ref=f1e930]:
        - heading "Decision" [level=2] [ref=f1e931]
        - paragraph [ref=f1e932]:
          - text: "Current preference:"
          - strong [ref=f1e933]: No Decision Yet
        - paragraph [ref=f1e934]: This records your choice. It does not place an order or contact a supplier.
        - generic [ref=f1e935]:
          - generic [ref=f1e936]:
            - text: Preferred supplier
            - combobox "Preferred supplier" [ref=f1e937]:
              - option "Choose a shortlisted supplier" [selected]
              - option "Harbor Pouch Works"
              - option "Moss Thread Bags"
              - option "Willow Stitch Studio"
          - generic [ref=f1e938]:
            - text: Decision notes
            - textbox "Decision notes" [ref=f1e939]
          - button "Mark as Preferred Supplier" [disabled] [ref=f1e940]
          - button "Save decision notes" [ref=f1e941] [cursor=pointer]
```

# Test source

```ts
  1   | import { test, expect, type Page } from '../../../../../apps/web/node_modules/@playwright/test';
  2   | import { writeFileSync } from 'node:fs';
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
> 21  |     await page.bringToFront();
      |                ^ Error: page.screenshot: Protocol error (Page.captureScreenshot): Unable to capture screenshot
  22  |     writeFileSync(info.outputPath('focus.json'),JSON.stringify(await page.evaluate(()=>(window as any).__focus),null,2));
  23  |     await page.screenshot({path:info.outputPath('final.png'),fullPage:true});
  24  |     writeFileSync(info.outputPath('visible-text.txt'),await page.locator('body').innerText());
  25  |   }
  26  | });
  27  | async function setup(p:Page){const project=await createAndApprove(p);for(const i of [0,1]){await quoteCard(p,i).getByLabel('Upload PDF quote').setInputFiles(require('node:path').resolve(__dirname, '../../../../../apps/api/tests/fixtures/quote_pdfs', ['harbor_primary.pdf','willow_primary.pdf'][i]));await expect(quoteCard(p,i)).toContainText('Status: NEEDS REVIEW');await confirm(p,i);}await comparison(p);return project.id;}
  28  | async function nativeFocus(p:Page){
  29  |   const cdp=await p.context().newCDPSession(p);await cdp.send('Emulation.setFocusEmulationEnabled',{enabled:false});
  30  |   const other=await p.context().newPage();await other.goto('about:blank');await other.bringToFront();
  31  |   await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(false);
  32  |   await p.bringToFront();await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(true);await other.close();
  33  |   const events=await p.evaluate(()=>(window as any).__focus);
  34  |   expect(events.some((e:any)=>e.type==='blur'&&e.trusted)).toBe(true);
  35  |   expect(events.some((e:any)=>e.type==='focus'&&e.trusted)).toBe(true);
  36  | }
  37  | async function analyze(p:Page){await button(p,'Analyze Comparison').click();await expect(output(p)).toBeVisible();}
  38  | async function invariant(p:Page,id:string,before:any){expect(await readApi(p,`/projects/${id}/comparison`)).toEqual(before);expect((await readApi<any>(p,`/projects/${id}`)).preferred_supplier_id).toBeNull();}
  39  | function gate(){let release!:()=>void;const promise=new Promise<void>(r=>release=r);return {promise,release};}
  40  | for(const outcome of ['success','failure']) test(`native focus pending ${outcome}, repeated focus and keyboard retry`,async({page})=>{
  41  |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`),g=gate();let posts=0;
  42  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=outcome==='success'?await r.fetch():null;await g.promise;if(response)await r.fulfill({response});else await r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis could not be validated. Please retry.'}}});});
  43  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  44  |   await nativeFocus(page);await nativeFocus(page);await expect(button(page,'Analyzing…')).toBeDisabled();expect(posts).toBe(1);g.release();
  45  |   if(outcome==='success')await expect(output(page)).toBeVisible();else await expect(button(page,'Retry analysis')).toBeEnabled();
  46  |   await nativeFocus(page);await nativeFocus(page);
  47  |   if(outcome==='success')await expect(output(page)).toBeVisible();else {
  48  |     await expect(region(page)).toContainText('could not be validated');expect(posts).toBe(1);
  49  |     await page.unroute(`**/api/projects/${id}/comparison/advice`);
  50  |     // Real Tab navigation, not locator.focus(), reaches Retry and Enter activates it.
  51  |     let reached=false;for(let i=0;i<350;i++){await page.keyboard.press('Tab');if(await button(page,'Retry analysis').evaluate(el=>el===document.activeElement)){reached=true;break;}}
  52  |     expect(reached).toBe(true);await page.keyboard.press('Enter');await expect(output(page)).toBeVisible();
  53  |   }
  54  |   expect(posts).toBe(1);await invariant(page,id,before);
  55  | });
  56  | test('failed freshness hides advice and GET-only recovery retains success',async({page})=>{
  57  |   const id=await setup(page);await analyze(page);let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++;});
  58  |   await page.route(`**/api/projects/${id}/comparison`,r=>r.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Comparison verification unavailable. Retry.'}}}));
  59  |   await nativeFocus(page);await expect(button(page,'Retry comparison')).toBeVisible();await expect(output(page)).toBeHidden();
  60  |   await page.screenshot({path:test.info().outputPath('verification-failed.png'),fullPage:true});
  61  |   await page.unroute(`**/api/projects/${id}/comparison`);await button(page,'Retry comparison').click();await expect(output(page)).toBeVisible();expect(posts).toBe(0);
  62  | });
  63  | test('competing focus and post-result reads cannot restore stale advice',async({page})=>{
  64  |   const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`),old=gate(),analysis=gate();let reads=0,posts=0;
  65  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await analysis.promise;await r.fulfill({response});});
  66  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  67  |   await page.route(`**/api/projects/${id}/comparison`,async r=>{reads++;if(reads===1){await old.promise;await r.fulfill({json:before});}else await r.fulfill({json:{...before,stale:true}});});
  68  |   await nativeFocus(page);await expect.poll(()=>reads).toBe(1);analysis.release();await expect(region(page)).toContainText('Comparison outdated');old.release();
  69  |   await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');expect(posts).toBe(1);
  70  | });
  71  | for(const change of ['quote','brief','shortlist','regeneration']) test(`${change} invalidation and replacement`,async({page})=>{
  72  |   const id=await setup(page);await analyze(page);const old=await readApi<any>(page,`/projects/${id}/comparison`);
  73  |   if(change==='quote'){const c=quoteCard(page,0);await c.getByRole('button',{name:'Edit confirmed PDF quote',exact:true}).click();await c.getByLabel('Unit price',{exact:true}).fill('4.65');await c.getByRole('button',{name:'Save quote',exact:true}).click();}
  74  |   if(change==='brief'){const b=page.getByRole('region',{name:'Sourcing Brief',exact:true});await b.getByLabel('Destination',{exact:true}).fill('Melbourne');await b.getByRole('button',{name:'Save Brief',exact:true}).click();}
  75  |   if(change==='shortlist'){const s=page.getByRole('region',{name:'Suppliers',exact:true});await s.getByRole('article').filter({has:page.getByRole('heading',{name:'Moss Thread Bags',exact:true})}).getByRole('button',{name:'Remove from shortlist',exact:true}).click();}
  76  |   if(change!=='regeneration'){await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');}
  77  |   if(change==='brief'){await page.getByRole('button',{name:'Re-discover and re-evaluate',exact:true}).click();await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();}
  78  |   if(change==='shortlist')await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();
  79  |   await comparison(page,true);await expect(output(page)).toBeHidden();const current=await readApi<any>(page,`/projects/${id}/comparison`);expect(current.id).not.toBe(old.id);
  80  |   await analyze(page);if(change==='quote')await expect(region(page).getByRole('table')).toContainText('USD 4.65');
  81  |   expect((await readApi<any>(page,`/projects/${id}`)).preferred_supplier_id).toBeNull();
  82  | });
  83  | test('project switch A to B to A rejects late result',async({page})=>{
  84  |   const b=await setup(page);const a=await setup(page),g=gate();let posts=0;
  85  |   await page.route(`**/api/projects/${a}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await g.promise;try{await r.fulfill({response});}catch{/* Browser aborted the old navigation-owned request. */}});
  86  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  87  |   await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${b}']`).first().click();await expect(output(page)).toBeHidden();
  88  |   await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${a}']`).first().click();g.release();
  89  |   await expect(button(page,'Analyze Comparison')).toBeEnabled();await nativeFocus(page);await expect(output(page)).toBeHidden();expect(posts).toBe(1);
  90  | });
  91  | test('backend deadline envelope permits explicit retry only',async({page})=>{
  92  |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  93  |   await page.route(`**/api/projects/${id}/comparison/advice`,r=>{posts++;return r.fulfill({status:504,json:{error:{code:'COMPARISON_ANALYSIS_TIMEOUT',message:'Analysis took too long. Please retry.'}}});});
  94  |   await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('Analysis took too long');await expect(button(page,'Retry analysis')).toBeEnabled();await nativeFocus(page);expect(posts).toBe(1);
  95  |   await page.unroute(`**/api/projects/${id}/comparison/advice`);await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();await invariant(page,id,before);
  96  | });
  97  | test('proxy disconnect envelope cooldown and no automatic retry',async({page})=>{
  98  |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  99  |   await page.clock.install();
  100 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  101 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'disconnect'});
  102 |   await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('may still be finishing');await expect(button(page,'Retry analysis')).toBeDisabled();await nativeFocus(page);expect(posts).toBe(1);
  103 |   await page.clock.fastForward(179000);await expect(button(page,'Retry analysis')).toBeDisabled();await page.clock.fastForward(1100);await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  104 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  105 | });
  106 | test('real backend deadline through actual proxy and explicit recovery',async({page})=>{
  107 |   test.setTimeout(240000);
  108 |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  109 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  110 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'deadline'});
  111 |   const response=page.waitForResponse(r=>r.url().endsWith('/comparison/advice'),{timeout:210000});
  112 |   const start=Date.now();await button(page,'Analyze Comparison').click();const result=await response;
  113 |   const body=await result.json();expect(result.status()).toBe(504);expect(body.error.code).toBe('COMPARISON_ANALYSIS_TIMEOUT');
  114 |   writeFileSync(test.info().outputPath('deadline.json'),JSON.stringify({elapsed_ms:Date.now()-start,status:result.status(),code:body.error.code,posts},null,2));
  115 |   await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  116 |   await page.screenshot({path:test.info().outputPath('deadline-error.png'),fullPage:true});
  117 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  118 | });
  119 | test('existing human preference survives advice and failures',async({page})=>{
  120 |   const id=await setup(page),d=page.getByRole('region',{name:'Decision',exact:true});
  121 |   await d.getByLabel('Preferred supplier',{exact:true}).selectOption({label:'Willow Stitch Studio'});await d.getByLabel('Decision notes').fill('QA human choice');await d.getByRole('button',{name:'Mark as Preferred Supplier',exact:true}).click();await expect(d).toContainText('Preferred supplier saved.');
```