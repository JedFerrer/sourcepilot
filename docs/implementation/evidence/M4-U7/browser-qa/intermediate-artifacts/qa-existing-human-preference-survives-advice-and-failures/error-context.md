# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: qa.spec.ts >> existing human preference survives advice and failures
- Location: qa.spec.ts:119:5

# Error details

```
Test timeout of 120000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 120000ms exceeded.
Call log:
  - waiting for getByRole('region', { name: 'Decision', exact: true }).getByLabel('Preferred supplier', { exact: true })

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - alert [ref=e2]
  - main [ref=e3]:
    - paragraph [ref=e4]: Demo session ready
    - region [ref=e5]:
      - link "Back to projects" [ref=e6] [cursor=pointer]:
        - /url: /
      - paragraph [ref=e7]: "Current stage: Decision"
      - generic "Next action" [ref=e8]:
        - paragraph [ref=e9]: Review the comparison and record your choice. AI analysis is optional.
        - 'link "Next: Review comparison and choose a preferred supplier" [ref=e10] [cursor=pointer]':
          - /url: "#decision-choice"
      - heading "E2E existing human preference survives advice and failures 0" [level=1] [ref=e11]
      - paragraph [ref=e12]: "Preferred supplier: No Decision Yet"
      - navigation "Sourcing workflow stages" [ref=e13]:
        - list [ref=e14]:
          - listitem [ref=e15]:
            - link [ref=e16] [cursor=pointer]:
              - /url: "#brief"
              - strong [ref=e17]: Brief
          - listitem [ref=e18]:
            - link [ref=e19] [cursor=pointer]:
              - /url: "#suppliers"
              - strong [ref=e20]: Suppliers
          - listitem [ref=e21]:
            - link [ref=e22] [cursor=pointer]:
              - /url: "#quotes"
              - strong [ref=e23]: Quotes
          - listitem [ref=e24]:
            - link [ref=e25] [cursor=pointer]:
              - /url: "#comparison"
              - strong [ref=e26]: Comparison
          - listitem [ref=e27]:
            - link [ref=e28] [cursor=pointer]:
              - /url: "#decision"
              - strong [ref=e29]: Decision
      - generic [ref=e30]:
        - generic [ref=e31]:
          - text: Rename project
          - textbox "Rename project" [ref=e32]: E2E existing human preference survives advice and failures 0
        - button "Save name" [ref=e33] [cursor=pointer]
      - region [ref=e34]:
        - heading "Original sourcing request" [level=2] [ref=e35]
        - paragraph [ref=e36]: Source 2,000 custom cosmetic travel bags made from recycled polyester with a custom logo. Target unit cost below USD 5, delivery to Sydney, preferred GRS certification. Delivery timing is not decided yet.
      - region [ref=e37]:
        - heading "Sourcing Brief" [level=2] [ref=e38]
        - paragraph [ref=e39]: "Readiness: Approved"
        - paragraph [ref=e40]: Approved on 11/4/2026
        - paragraph [ref=e41]: No required information is missing.
        - generic [ref=e42]:
          - heading "Product and delivery" [level=3] [ref=e43]
          - generic [ref=e44]:
            - text: Product name
            - textbox "Product name" [ref=e45]: custom cosmetic travel bags
          - generic [ref=e46]:
            - text: Category
            - textbox "Category" [ref=e47]: cosmetic travel bags
          - generic [ref=e48]:
            - text: Requested quantity
            - spinbutton "Requested quantity" [ref=e49]: "2000"
          - generic [ref=e50]:
            - text: Destination
            - textbox "Destination" [ref=e51]: Sydney
          - generic [ref=e52]:
            - text: Delivery target type
            - combobox "Delivery target type" [ref=e53]:
              - option "Not set"
              - option "Date" [selected]
              - option "Period"
          - generic [ref=e54]:
            - text: Delivery date
            - textbox "Delivery date" [ref=e55]: 2026-12-15
          - generic [ref=e56]:
            - text: Target unit price (optional)
            - spinbutton "Target unit price (optional)" [ref=e57]: "5.0000"
          - heading "Sourcing requirements" [level=3] [ref=e58]
          - group "Requirement 1" [ref=e59]:
            - generic [ref=e61]:
              - text: Kind
              - combobox "Kind" [ref=e62]:
                - option "MATERIAL"
                - option "CERTIFICATION" [selected]
                - option "MOQ"
                - option "QUANTITY"
                - option "UNIT PRICE"
                - option "PRODUCTION LEAD TIME"
                - option "DELIVERY"
                - option "CAPABILITY"
                - option "INFORMATIONAL"
            - generic [ref=e63]:
              - text: Value
              - textbox "Value" [ref=e64]: grs
            - generic [ref=e65]:
              - text: Importance
              - combobox "Importance" [ref=e66]:
                - option "Not set"
                - option "Required" [selected]
                - option "Preferred"
                - option "Informational"
            - generic [ref=e67]:
              - text: Notes (optional)
              - textbox "Notes (optional)" [ref=e68]
            - button "Remove requirement" [ref=e69] [cursor=pointer]
          - group "Requirement 2" [ref=e70]:
            - generic [ref=e72]:
              - text: Kind
              - combobox "Kind" [ref=e73]:
                - option "MATERIAL"
                - option "CERTIFICATION"
                - option "MOQ"
                - option "QUANTITY"
                - option "UNIT PRICE"
                - option "PRODUCTION LEAD TIME"
                - option "DELIVERY"
                - option "CAPABILITY" [selected]
                - option "INFORMATIONAL"
            - generic [ref=e74]:
              - text: Capability
              - combobox "Capability" [ref=e75]:
                - option "PRODUCT CATEGORY"
                - option "CUSTOM BRANDING" [selected]
                - option "BRANDING METHOD"
                - option "PRODUCT FEATURE"
                - option "MANUFACTURING CAPABILITY"
            - generic [ref=e76]:
              - text: Custom branding
              - combobox "Custom branding" [ref=e77]:
                - option "Yes" [selected]
                - option "No"
            - generic [ref=e78]:
              - text: Importance
              - combobox "Importance" [ref=e79]:
                - option "Not set"
                - option "Required" [selected]
                - option "Preferred"
                - option "Informational"
            - generic [ref=e80]:
              - text: Notes (optional)
              - textbox "Notes (optional)" [ref=e81]
            - button "Remove requirement" [ref=e82] [cursor=pointer]
          - group "Requirement 3" [ref=e83]:
            - generic [ref=e85]:
              - text: Kind
              - combobox "Kind" [ref=e86]:
                - option "MATERIAL" [selected]
                - option "CERTIFICATION"
                - option "MOQ"
                - option "QUANTITY"
                - option "UNIT PRICE"
                - option "PRODUCTION LEAD TIME"
                - option "DELIVERY"
                - option "CAPABILITY"
                - option "INFORMATIONAL"
            - generic [ref=e87]:
              - text: Value
              - textbox "Value" [ref=e88]: recycled polyester
            - generic [ref=e89]:
              - text: Importance
              - combobox "Importance" [ref=e90]:
                - option "Not set" [selected]
                - option "Required"
                - option "Preferred"
                - option "Informational"
            - generic [ref=e91]:
              - text: Notes (optional)
              - textbox "Notes (optional)" [ref=e92]
            - button "Remove requirement" [ref=e93] [cursor=pointer]
          - button "Add requirement" [ref=e94] [cursor=pointer]
          - heading "Informational attributes" [level=3] [ref=e95]
          - button "Add attribute" [ref=e96] [cursor=pointer]
          - button "Save Brief" [ref=e97] [cursor=pointer]
      - region [ref=e98]:
        - heading "Suppliers" [level=2] [ref=e99]
        - button "Re-discover and re-evaluate" [ref=e100] [cursor=pointer]
        - region [ref=e101]:
          - heading "Shortlist" [level=3] [ref=e102]
          - paragraph [ref=e103]: 3 selected · maximum 3 for approval
          - status [ref=e104]: Shortlist approved. The project is ready for Quotes.
          - button "Review selected suppliers" [ref=e105] [cursor=pointer]
        - article [ref=e106]:
          - heading "Cedar Pack Co" [level=3] [ref=e107]
          - paragraph [ref=e108]: Thailand · Fictional bag maker with a high general minimum order.
          - paragraph [ref=e109]: "MOQ: 5000 · Typical lead time: 28 days"
          - paragraph [ref=e110]: "Indicative price: 3.7000 USD"
          - paragraph [ref=e111]: "Capabilities: CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=e112]
          - list [ref=e113]:
            - listitem [ref=e114]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=e115]: UNKNOWN
            - listitem [ref=e116]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=e117]: UNKNOWN
            - listitem [ref=e118]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=e119]: UNKNOWN
          - paragraph [ref=e120]: "General MOQ compatibility: DOES NOT MEET"
          - group [ref=e121]:
            - generic "Available evidence" [ref=e122]
          - button "Explain this supplier" [ref=e124] [cursor=pointer]
          - generic [ref=e125]:
            - button "Add to shortlist" [ref=e126] [cursor=pointer]
            - button "Dismiss" [ref=e127] [cursor=pointer]
          - generic [ref=e128]:
            - generic [ref=e129]:
              - text: Private notes for Cedar Pack Co
              - textbox "Private notes for Cedar Pack Co" [ref=e130]
            - button "Save notes" [disabled] [ref=e131]
        - article [ref=e132]:
          - heading "Harbor Pouch Works" [level=3] [ref=e133]
          - paragraph [ref=e134]: Vietnam · Fictional maker of custom cosmetic travel bags and small textile accessories.
          - paragraph [ref=e135]: "MOQ: 1000 · Typical lead time: 32 days"
          - paragraph [ref=e136]: "Indicative price: 4.6000 USD"
          - paragraph [ref=e137]: "Capabilities: BRANDING_METHOD: screen print; CERTIFICATION: grs; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=e138]
          - list [ref=e139]:
            - listitem [ref=e140]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=e141]: MEETS
              - generic [ref=e142]: "· Evidence: Synthetic current GRS record"
            - listitem [ref=e143]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=e144]: MEETS
              - generic [ref=e145]: "· Evidence: Synthetic branding sheet"
            - listitem [ref=e146]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=e147]: MEETS
              - generic [ref=e148]: "· Evidence: Synthetic material sheet"
          - paragraph [ref=e149]: "General MOQ compatibility: MEETS"
          - group [ref=e150]:
            - generic "Available evidence" [ref=e151]
          - button "Explain this supplier" [ref=e153] [cursor=pointer]
          - generic [ref=e154]:
            - button "Remove from shortlist" [ref=e155] [cursor=pointer]
            - button "Dismiss" [ref=e156] [cursor=pointer]
          - generic [ref=e157]:
            - generic [ref=e158]:
              - text: Private notes for Harbor Pouch Works
              - textbox "Private notes for Harbor Pouch Works" [ref=e159]
            - button "Save notes" [disabled] [ref=e160]
        - article [ref=e161]:
          - heading "Moss Thread Bags" [level=3] [ref=e162]
          - paragraph [ref=e163]: Philippines · Fictional small-run pouch producer with unverified certification status.
          - paragraph [ref=e164]: "MOQ: 800 · Typical lead time: 37 days"
          - paragraph [ref=e165]: "Indicative price: Unknown"
          - paragraph [ref=e166]: "Capabilities: CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=e167]
          - list [ref=e168]:
            - listitem [ref=e169]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=e170]: UNKNOWN
            - listitem [ref=e171]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=e172]: UNKNOWN
            - listitem [ref=e173]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=e174]: MEETS
              - generic [ref=e175]: "· Evidence: Synthetic material sheet"
          - paragraph [ref=e176]: "General MOQ compatibility: UNKNOWN"
          - group [ref=e177]:
            - generic "Available evidence" [ref=e178]
          - button "Explain this supplier" [ref=e180] [cursor=pointer]
          - generic [ref=e181]:
            - button "Remove from shortlist" [ref=e182] [cursor=pointer]
            - button "Dismiss" [ref=e183] [cursor=pointer]
          - generic [ref=e184]:
            - generic [ref=e185]:
              - text: Private notes for Moss Thread Bags
              - textbox "Private notes for Moss Thread Bags" [ref=e186]
            - button "Save notes" [disabled] [ref=e187]
        - article [ref=e188]:
          - heading "Sunrise Textile Lab" [level=3] [ref=e189]
          - paragraph [ref=e190]: India · Fictional bag producer with conflicting current certification records.
          - paragraph [ref=e191]: "MOQ: 1500 · Typical lead time: 45 days"
          - paragraph [ref=e192]: "Indicative price: 4.1000 USD"
          - paragraph [ref=e193]: "Capabilities: CERTIFICATION: grs; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=e194]
          - list [ref=e195]:
            - listitem [ref=e196]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=e197]: CONFLICT
              - generic [ref=e198]: "· Evidence: Synthetic certification register B, Synthetic certification register A"
            - listitem [ref=e199]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=e200]: UNKNOWN
            - listitem [ref=e201]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=e202]: UNKNOWN
          - paragraph [ref=e203]: "General MOQ compatibility: UNKNOWN"
          - group [ref=e204]:
            - generic "Available evidence" [ref=e205]
          - button "Explain this supplier" [ref=e207] [cursor=pointer]
          - generic [ref=e208]:
            - button "Add to shortlist" [ref=e209] [cursor=pointer]
            - button "Dismiss" [ref=e210] [cursor=pointer]
          - generic [ref=e211]:
            - generic [ref=e212]:
              - text: Private notes for Sunrise Textile Lab
              - textbox "Private notes for Sunrise Textile Lab" [ref=e213]
            - button "Save notes" [disabled] [ref=e214]
        - article [ref=e215]:
          - heading "Willow Stitch Studio" [level=3] [ref=e216]
          - paragraph [ref=e217]: Indonesia · Fictional textile studio with cosmetic pouch and branding capabilities.
          - paragraph [ref=e218]: "MOQ: 1800 · Typical lead time: 40 days"
          - paragraph [ref=e219]: "Indicative price: 4.2000 USD"
          - paragraph [ref=e220]: "Capabilities: BRANDING_METHOD: embroidery; CUSTOM_BRANDING: true; MATERIAL: recycled polyester; PRODUCT_CATEGORY: cosmetic travel bag"
          - heading "Requirement fit" [level=4] [ref=e221]
          - list [ref=e222]:
            - listitem [ref=e223]:
              - text: "CERTIFICATION (REQUIRED): grs —"
              - strong [ref=e224]: UNKNOWN
            - listitem [ref=e225]:
              - text: "CAPABILITY (REQUIRED): true · CUSTOM_BRANDING —"
              - strong [ref=e226]: MEETS
              - generic [ref=e227]: "· Evidence: Synthetic branding sheet"
            - listitem [ref=e228]:
              - text: "MATERIAL (Informational): recycled polyester —"
              - strong [ref=e229]: MEETS
              - generic [ref=e230]: "· Evidence: Synthetic material sheet"
          - paragraph [ref=e231]: "General MOQ compatibility: UNKNOWN"
          - group [ref=e232]:
            - generic "Available evidence" [ref=e233]
          - button "Explain this supplier" [ref=e235] [cursor=pointer]
          - generic [ref=e236]:
            - button "Remove from shortlist" [ref=e237] [cursor=pointer]
            - button "Dismiss" [ref=e238] [cursor=pointer]
          - generic [ref=e239]:
            - generic [ref=e240]:
              - text: Private notes for Willow Stitch Studio
              - textbox "Private notes for Willow Stitch Studio" [ref=e241]
            - button "Save notes" [disabled] [ref=e242]
      - region [ref=e243]:
        - heading "Quotes" [level=2] [ref=e244]
        - group [ref=e246]:
          - article [ref=e247]:
            - heading "Harbor Pouch Works" [level=3] [ref=e248]
            - paragraph [ref=e249]: "Status: CONFIRMED"
            - status [ref=e250]: Confirmed PDF quote. Current values are ready for comparison.
            - paragraph [ref=e251]: Review the PDF source, AI extraction, and current values.
            - generic [ref=e252]:
              - generic [ref=e253]:
                - term [ref=e254]: Quoted quantity
                - definition [ref=e255]:
                  - paragraph [ref=e256]: "Extraction: Known"
                  - paragraph [ref=e257]: "AI extracted value: 2000"
                  - paragraph [ref=e258]: "Current confirmed value: 2000"
                  - paragraph [ref=e259]: "Current origin: AI EXTRACTED"
                  - generic [ref=e260]:
                    - paragraph [ref=e261]: "PDF source evidence:"
                    - list [ref=e262]:
                      - listitem [ref=e263]:
                        - paragraph [ref=e264]: Page 1, block p1-b4
                        - blockquote [ref=e265]: "Quoted quantity: 2,000 units"
                        - paragraph [ref=e266]: "Associated extracted value: 2000"
              - generic [ref=e267]:
                - term [ref=e268]: Unit price
                - definition [ref=e269]:
                  - paragraph [ref=e270]: "Extraction: Known"
                  - paragraph [ref=e271]: "AI extracted value: 4.60"
                  - paragraph [ref=e272]: "Current confirmed value: 4.60"
                  - paragraph [ref=e273]: "Current origin: AI EXTRACTED"
                  - generic [ref=e274]:
                    - paragraph [ref=e275]: "PDF source evidence:"
                    - list [ref=e276]:
                      - listitem [ref=e277]:
                        - paragraph [ref=e278]: Page 1, block p1-b5
                        - blockquote [ref=e279]: "Unit price: USD 4.60"
                        - paragraph [ref=e280]: "Associated extracted value: 4.60"
              - generic [ref=e281]:
                - term [ref=e282]: Original currency (three-letter code)
                - definition [ref=e283]:
                  - paragraph [ref=e284]: "Extraction: Known"
                  - paragraph [ref=e285]: "AI extracted value: USD"
                  - paragraph [ref=e286]: "Current confirmed value: USD"
                  - paragraph [ref=e287]: "Current origin: AI EXTRACTED"
                  - generic [ref=e288]:
                    - paragraph [ref=e289]: "PDF source evidence:"
                    - list [ref=e290]:
                      - listitem [ref=e291]:
                        - paragraph [ref=e292]: Page 1, block p1-b5
                        - blockquote [ref=e293]: "Unit price: USD 4.60"
                        - paragraph [ref=e294]: "Associated extracted value: USD"
              - generic [ref=e295]:
                - term [ref=e296]: Minimum order quantity
                - definition [ref=e297]:
                  - paragraph [ref=e298]: "Extraction: Known"
                  - paragraph [ref=e299]: "AI extracted value: 1000"
                  - paragraph [ref=e300]: "Current confirmed value: 1000"
                  - paragraph [ref=e301]: "Current origin: AI EXTRACTED"
                  - generic [ref=e302]:
                    - paragraph [ref=e303]: "PDF source evidence:"
                    - list [ref=e304]:
                      - listitem [ref=e305]:
                        - paragraph [ref=e306]: Page 1, block p1-b6
                        - blockquote [ref=e307]: "Minimum order quantity: 1,000 units"
                        - paragraph [ref=e308]: "Associated extracted value: 1000"
              - generic [ref=e309]:
                - term [ref=e310]: Sample cost
                - definition [ref=e311]:
                  - paragraph [ref=e312]: "Extraction: Known"
                  - paragraph [ref=e313]: "AI extracted value: 40"
                  - paragraph [ref=e314]: "Current confirmed value: 40"
                  - paragraph [ref=e315]: "Current origin: AI EXTRACTED"
                  - generic [ref=e316]:
                    - paragraph [ref=e317]: "PDF source evidence:"
                    - list [ref=e318]:
                      - listitem [ref=e319]:
                        - paragraph [ref=e320]: Page 1, block p1-b8
                        - blockquote [ref=e321]: "Sample cost: USD 40"
                        - paragraph [ref=e322]: "Associated extracted value: 40"
              - generic [ref=e323]:
                - term [ref=e324]: Tooling or setup cost
                - definition [ref=e325]:
                  - paragraph [ref=e326]: "Extraction: Known"
                  - paragraph [ref=e327]: "AI extracted value: 150"
                  - paragraph [ref=e328]: "Current confirmed value: 150"
                  - paragraph [ref=e329]: "Current origin: AI EXTRACTED"
                  - generic [ref=e330]:
                    - paragraph [ref=e331]: "PDF source evidence:"
                    - list [ref=e332]:
                      - listitem [ref=e333]:
                        - paragraph [ref=e334]: Page 1, block p1-b7
                        - blockquote [ref=e335]: "Tooling/setup cost: USD 150"
                        - paragraph [ref=e336]: "Associated extracted value: 150"
              - generic [ref=e337]:
                - term [ref=e338]: Packaging cost
                - definition [ref=e339]:
                  - paragraph [ref=e340]: "Extraction: Unknown"
                  - paragraph [ref=e341]: "AI extracted value: Unknown"
                  - paragraph [ref=e342]: "Current confirmed value: Unknown"
                  - paragraph [ref=e343]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e344]: No saved source citations available for this field.
              - generic [ref=e345]:
                - term [ref=e346]: Shipping cost
                - definition [ref=e347]:
                  - paragraph [ref=e348]: "Extraction: Known"
                  - paragraph [ref=e349]: "AI extracted value: 320"
                  - paragraph [ref=e350]: "Current confirmed value: 320"
                  - paragraph [ref=e351]: "Current origin: AI EXTRACTED"
                  - generic [ref=e352]:
                    - paragraph [ref=e353]: "PDF source evidence:"
                    - list [ref=e354]:
                      - listitem [ref=e355]:
                        - paragraph [ref=e356]: Page 1, block p1-b11
                        - blockquote [ref=e357]: "Shipping cost: USD 320 to Manila"
                        - paragraph [ref=e358]: "Associated extracted value: 320"
              - generic [ref=e359]:
                - term [ref=e360]: Sample lead time
                - definition [ref=e361]:
                  - paragraph [ref=e362]: "Extraction: Known"
                  - paragraph [ref=e363]: "AI extracted value: 7 days"
                  - paragraph [ref=e364]: "Current confirmed value: 7 days"
                  - paragraph [ref=e365]: "Current origin: AI EXTRACTED"
                  - generic [ref=e366]:
                    - paragraph [ref=e367]: "PDF source evidence:"
                    - list [ref=e368]:
                      - listitem [ref=e369]:
                        - paragraph [ref=e370]: Page 1, block p1-b9
                        - blockquote [ref=e371]: "Sample lead time: 7 days"
                        - paragraph [ref=e372]: "Associated extracted value: 7 days"
              - generic [ref=e373]:
                - term [ref=e374]: Production lead time
                - definition [ref=e375]:
                  - paragraph [ref=e376]: "Extraction: Known"
                  - paragraph [ref=e377]: "AI extracted value: 32 days after sample approval"
                  - paragraph [ref=e378]: "Current confirmed value: 32 days after sample approval"
                  - paragraph [ref=e379]: "Current origin: AI EXTRACTED"
                  - generic [ref=e380]:
                    - paragraph [ref=e381]: "PDF source evidence:"
                    - list [ref=e382]:
                      - listitem [ref=e383]:
                        - paragraph [ref=e384]: Page 1, block p1-b10
                        - blockquote [ref=e385]: "Production lead time: 32 days after sample approval"
                        - paragraph [ref=e386]: "Associated extracted value: 32 days after sample approval"
              - generic [ref=e387]:
                - term [ref=e388]: Shipping time
                - definition [ref=e389]:
                  - paragraph [ref=e390]: "Extraction: Known"
                  - paragraph [ref=e391]: "AI extracted value: 12 days after production"
                  - paragraph [ref=e392]: "Current confirmed value: 12 days after production"
                  - paragraph [ref=e393]: "Current origin: AI EXTRACTED"
                  - generic [ref=e394]:
                    - paragraph [ref=e395]: "PDF source evidence:"
                    - list [ref=e396]:
                      - listitem [ref=e397]:
                        - paragraph [ref=e398]: Page 1, block p1-b12
                        - blockquote [ref=e399]: "Shipping time: 12 days after production"
                        - paragraph [ref=e400]: "Associated extracted value: 12 days after production"
              - generic [ref=e401]:
                - term [ref=e402]: Total stated lead time
                - definition [ref=e403]:
                  - paragraph [ref=e404]: "Extraction: Unknown"
                  - paragraph [ref=e405]: "AI extracted value: Unknown"
                  - paragraph [ref=e406]: "Current confirmed value: Unknown"
                  - paragraph [ref=e407]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e408]: No saved source citations available for this field.
              - generic [ref=e409]:
                - term [ref=e410]: Payment terms
                - definition [ref=e411]:
                  - paragraph [ref=e412]: "Extraction: Known"
                  - paragraph [ref=e413]: "AI extracted value: 30% deposit, 70% before dispatch"
                  - paragraph [ref=e414]: "Current confirmed value: 30% deposit, 70% before dispatch"
                  - paragraph [ref=e415]: "Current origin: AI EXTRACTED"
                  - generic [ref=e416]:
                    - paragraph [ref=e417]: "PDF source evidence:"
                    - list [ref=e418]:
                      - listitem [ref=e419]:
                        - paragraph [ref=e420]: Page 1, block p1-b13
                        - blockquote [ref=e421]: "Payment terms: 30% deposit, 70% before dispatch"
                        - paragraph [ref=e422]: "Associated extracted value: 30% deposit, 70% before dispatch"
              - generic [ref=e423]:
                - term [ref=e424]: Incoterm
                - definition [ref=e425]:
                  - paragraph [ref=e426]: "Extraction: Unknown"
                  - paragraph [ref=e427]: "AI extracted value: Unknown"
                  - paragraph [ref=e428]: "Current confirmed value: Unknown"
                  - paragraph [ref=e429]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e430]: No saved source citations available for this field.
              - generic [ref=e431]:
                - term [ref=e432]: Quote validity
                - definition [ref=e433]:
                  - paragraph [ref=e434]: "Extraction: Known"
                  - paragraph [ref=e435]: "AI extracted value: 30 days"
                  - paragraph [ref=e436]: "Current confirmed value: 30 days"
                  - paragraph [ref=e437]: "Current origin: AI EXTRACTED"
                  - generic [ref=e438]:
                    - paragraph [ref=e439]: "PDF source evidence:"
                    - list [ref=e440]:
                      - listitem [ref=e441]:
                        - paragraph [ref=e442]: Page 1, block p1-b14
                        - blockquote [ref=e443]: "Quote validity: 30 days"
                        - paragraph [ref=e444]: "Associated extracted value: 30 days"
              - generic [ref=e445]:
                - term [ref=e446]: Warranty
                - definition [ref=e447]:
                  - paragraph [ref=e448]: "Extraction: Unknown"
                  - paragraph [ref=e449]: "AI extracted value: Unknown"
                  - paragraph [ref=e450]: "Current confirmed value: Unknown"
                  - paragraph [ref=e451]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e452]: No saved source citations available for this field.
              - generic [ref=e453]:
                - term [ref=e454]: Certifications
                - definition [ref=e455]:
                  - paragraph [ref=e456]: "Extraction: Known"
                  - paragraph [ref=e457]: "AI extracted value: Synthetic GRS record: current for this fictional supplier"
                  - paragraph [ref=e458]: "Current confirmed value: Synthetic GRS record: current for this fictional supplier"
                  - paragraph [ref=e459]: "Current origin: AI EXTRACTED"
                  - generic [ref=e460]:
                    - paragraph [ref=e461]: "PDF source evidence:"
                    - list [ref=e462]:
                      - listitem [ref=e463]:
                        - paragraph [ref=e464]: Page 2, block p2-b4
                        - blockquote [ref=e465]: "Synthetic GRS record: current for this fictional supplier"
                        - paragraph [ref=e466]: "Associated extracted value: Synthetic GRS record: current for this fictional supplier"
              - generic [ref=e467]:
                - term [ref=e468]: Compliance notes
                - definition [ref=e469]:
                  - paragraph [ref=e470]: "Extraction: Unknown"
                  - paragraph [ref=e471]: "AI extracted value: Unknown"
                  - paragraph [ref=e472]: "Current confirmed value: Unknown"
                  - paragraph [ref=e473]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e474]: No saved source citations available for this field.
              - generic [ref=e475]:
                - term [ref=e476]: Exclusions
                - definition [ref=e477]:
                  - paragraph [ref=e478]: "Extraction: Known"
                  - paragraph [ref=e479]: "AI extracted value: import duties are not included"
                  - paragraph [ref=e480]: "Current confirmed value: import duties are not included"
                  - paragraph [ref=e481]: "Current origin: AI EXTRACTED"
                  - generic [ref=e482]:
                    - paragraph [ref=e483]: "PDF source evidence:"
                    - list [ref=e484]:
                      - listitem [ref=e485]:
                        - paragraph [ref=e486]: Page 2, block p2-b7
                        - blockquote [ref=e487]: "Exclusion: import duties are not included"
                        - paragraph [ref=e488]: "Associated extracted value: import duties are not included"
              - generic [ref=e489]:
                - term [ref=e490]: Special conditions
                - definition [ref=e491]:
                  - paragraph [ref=e492]: "Extraction: Unknown"
                  - paragraph [ref=e493]: "AI extracted value: Unknown"
                  - paragraph [ref=e494]: "Current confirmed value: Unknown"
                  - paragraph [ref=e495]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e496]: No saved source citations available for this field.
              - generic [ref=e497]:
                - term [ref=e498]: Supplier notes
                - definition [ref=e499]:
                  - paragraph [ref=e500]: "Extraction: Unknown"
                  - paragraph [ref=e501]: "AI extracted value: Unknown"
                  - paragraph [ref=e502]: "Current confirmed value: Unknown"
                  - paragraph [ref=e503]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e504]: No saved source citations available for this field.
            - paragraph [ref=e505]: "Notes: None"
            - button "Edit confirmed PDF quote" [ref=e506] [cursor=pointer]
          - article [ref=e507]:
            - heading "Moss Thread Bags" [level=3] [ref=e508]
            - paragraph [ref=e509]: "Status: Not Added"
            - generic [ref=e510]:
              - text: Upload PDF quote
              - button "Upload PDF quote" [ref=e511]
            - generic [ref=e512]:
              - paragraph [ref=e513]: Leave a field blank if it is Unknown.
              - generic [ref=e514]:
                - text: Quoted quantity
                - spinbutton "Quoted quantity" [ref=e515]
              - generic [ref=e516]:
                - text: Unit price
                - spinbutton "Unit price" [ref=e517]
              - generic [ref=e518]:
                - text: Original currency (three-letter code)
                - textbox "Original currency (three-letter code)" [ref=e519]
              - generic [ref=e520]:
                - text: Minimum order quantity
                - spinbutton "Minimum order quantity" [ref=e521]
              - generic [ref=e522]:
                - text: Sample cost
                - spinbutton "Sample cost" [ref=e523]
              - generic [ref=e524]:
                - text: Tooling or setup cost
                - spinbutton "Tooling or setup cost" [ref=e525]
              - generic [ref=e526]:
                - text: Packaging cost
                - spinbutton "Packaging cost" [ref=e527]
              - generic [ref=e528]:
                - text: Shipping cost
                - spinbutton "Shipping cost" [ref=e529]
              - generic [ref=e530]:
                - text: Sample lead time
                - textbox "Sample lead time" [ref=e531]
              - generic [ref=e532]:
                - text: Production lead time
                - textbox "Production lead time" [ref=e533]
              - generic [ref=e534]:
                - text: Shipping time
                - textbox "Shipping time" [ref=e535]
              - generic [ref=e536]:
                - text: Total stated lead time
                - textbox "Total stated lead time" [ref=e537]
              - generic [ref=e538]:
                - text: Payment terms
                - textbox "Payment terms" [ref=e539]
              - generic [ref=e540]:
                - text: Incoterm
                - textbox "Incoterm" [ref=e541]
              - generic [ref=e542]:
                - text: Quote validity
                - textbox "Quote validity" [ref=e543]
              - generic [ref=e544]:
                - text: Warranty
                - textbox "Warranty" [ref=e545]
              - generic [ref=e546]:
                - text: Certifications
                - textbox "Certifications" [ref=e547]
              - generic [ref=e548]:
                - text: Compliance notes
                - textbox "Compliance notes" [ref=e549]
              - generic [ref=e550]:
                - text: Exclusions
                - textbox "Exclusions" [ref=e551]
              - generic [ref=e552]:
                - text: Special conditions
                - textbox "Special conditions" [ref=e553]
              - generic [ref=e554]:
                - text: Supplier notes
                - textbox "Supplier notes" [ref=e555]
              - generic [ref=e556]:
                - text: Quote notes
                - textbox "Quote notes" [ref=e557]
              - button "Create manual quote" [ref=e558] [cursor=pointer]
          - article [ref=e559]:
            - heading "Willow Stitch Studio" [level=3] [ref=e560]
            - paragraph [ref=e561]: "Status: CONFIRMED"
            - status [ref=e562]: Confirmed PDF quote. Current values are ready for comparison.
            - paragraph [ref=e563]: Review the PDF source, AI extraction, and current values.
            - generic [ref=e564]:
              - generic [ref=e565]:
                - term [ref=e566]: Quoted quantity
                - definition [ref=e567]:
                  - paragraph [ref=e568]: "Extraction: Known"
                  - paragraph [ref=e569]: "AI extracted value: 2000"
                  - paragraph [ref=e570]: "Current confirmed value: 2000"
                  - paragraph [ref=e571]: "Current origin: AI EXTRACTED"
                  - generic [ref=e572]:
                    - paragraph [ref=e573]: "PDF source evidence:"
                    - list [ref=e574]:
                      - listitem [ref=e575]:
                        - paragraph [ref=e576]: Page 1, block p1-b4
                        - blockquote [ref=e577]: "Quoted quantity: 2,000 units"
                        - paragraph [ref=e578]: "Associated extracted value: 2000"
              - generic [ref=e579]:
                - term [ref=e580]: Unit price
                - definition [ref=e581]:
                  - paragraph [ref=e582]: "Extraction: Known"
                  - paragraph [ref=e583]: "AI extracted value: 4.20"
                  - paragraph [ref=e584]: "Current confirmed value: 4.20"
                  - paragraph [ref=e585]: "Current origin: AI EXTRACTED"
                  - generic [ref=e586]:
                    - paragraph [ref=e587]: "PDF source evidence:"
                    - list [ref=e588]:
                      - listitem [ref=e589]:
                        - paragraph [ref=e590]: Page 1, block p1-b5
                        - blockquote [ref=e591]: "Unit price: USD 4.20"
                        - paragraph [ref=e592]: "Associated extracted value: 4.20"
              - generic [ref=e593]:
                - term [ref=e594]: Original currency (three-letter code)
                - definition [ref=e595]:
                  - paragraph [ref=e596]: "Extraction: Known"
                  - paragraph [ref=e597]: "AI extracted value: USD"
                  - paragraph [ref=e598]: "Current confirmed value: USD"
                  - paragraph [ref=e599]: "Current origin: AI EXTRACTED"
                  - generic [ref=e600]:
                    - paragraph [ref=e601]: "PDF source evidence:"
                    - list [ref=e602]:
                      - listitem [ref=e603]:
                        - paragraph [ref=e604]: Page 1, block p1-b5
                        - blockquote [ref=e605]: "Unit price: USD 4.20"
                        - paragraph [ref=e606]: "Associated extracted value: USD"
              - generic [ref=e607]:
                - term [ref=e608]: Minimum order quantity
                - definition [ref=e609]:
                  - paragraph [ref=e610]: "Extraction: Known"
                  - paragraph [ref=e611]: "AI extracted value: 1800"
                  - paragraph [ref=e612]: "Current confirmed value: 1800"
                  - paragraph [ref=e613]: "Current origin: AI EXTRACTED"
                  - generic [ref=e614]:
                    - paragraph [ref=e615]: "PDF source evidence:"
                    - list [ref=e616]:
                      - listitem [ref=e617]:
                        - paragraph [ref=e618]: Page 1, block p1-b6
                        - blockquote [ref=e619]: "Minimum order quantity: 1,800 units"
                        - paragraph [ref=e620]: "Associated extracted value: 1800"
              - generic [ref=e621]:
                - term [ref=e622]: Sample cost
                - definition [ref=e623]:
                  - paragraph [ref=e624]: "Extraction: Known"
                  - paragraph [ref=e625]: "AI extracted value: 35"
                  - paragraph [ref=e626]: "Current confirmed value: 35"
                  - paragraph [ref=e627]: "Current origin: AI EXTRACTED"
                  - generic [ref=e628]:
                    - paragraph [ref=e629]: "PDF source evidence:"
                    - list [ref=e630]:
                      - listitem [ref=e631]:
                        - paragraph [ref=e632]: Page 1, block p1-b8
                        - blockquote [ref=e633]: "Sample cost: USD 35"
                        - paragraph [ref=e634]: "Associated extracted value: 35"
              - generic [ref=e635]:
                - term [ref=e636]: Tooling or setup cost
                - definition [ref=e637]:
                  - paragraph [ref=e638]: "Extraction: Known"
                  - paragraph [ref=e639]: "AI extracted value: 100"
                  - paragraph [ref=e640]: "Current confirmed value: 100"
                  - paragraph [ref=e641]: "Current origin: AI EXTRACTED"
                  - generic [ref=e642]:
                    - paragraph [ref=e643]: "PDF source evidence:"
                    - list [ref=e644]:
                      - listitem [ref=e645]:
                        - paragraph [ref=e646]: Page 1, block p1-b7
                        - blockquote [ref=e647]: "Tooling/setup cost: USD 100"
                        - paragraph [ref=e648]: "Associated extracted value: 100"
              - generic [ref=e649]:
                - term [ref=e650]: Packaging cost
                - definition [ref=e651]:
                  - paragraph [ref=e652]: "Extraction: Unknown"
                  - paragraph [ref=e653]: "AI extracted value: Unknown"
                  - paragraph [ref=e654]: "Current confirmed value: Unknown"
                  - paragraph [ref=e655]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e656]: No saved source citations available for this field.
              - generic [ref=e657]:
                - term [ref=e658]: Shipping cost
                - definition [ref=e659]:
                  - paragraph [ref=e660]: "Extraction: Known"
                  - paragraph [ref=e661]: "AI extracted value: 280"
                  - paragraph [ref=e662]: "Current confirmed value: 280"
                  - paragraph [ref=e663]: "Current origin: AI EXTRACTED"
                  - generic [ref=e664]:
                    - paragraph [ref=e665]: "PDF source evidence:"
                    - list [ref=e666]:
                      - listitem [ref=e667]:
                        - paragraph [ref=e668]: Page 1, block p1-b11
                        - blockquote [ref=e669]: "Shipping cost: USD 280 to Manila"
                        - paragraph [ref=e670]: "Associated extracted value: 280"
              - generic [ref=e671]:
                - term [ref=e672]: Sample lead time
                - definition [ref=e673]:
                  - paragraph [ref=e674]: "Extraction: Known"
                  - paragraph [ref=e675]: "AI extracted value: 10 days"
                  - paragraph [ref=e676]: "Current confirmed value: 10 days"
                  - paragraph [ref=e677]: "Current origin: AI EXTRACTED"
                  - generic [ref=e678]:
                    - paragraph [ref=e679]: "PDF source evidence:"
                    - list [ref=e680]:
                      - listitem [ref=e681]:
                        - paragraph [ref=e682]: Page 1, block p1-b9
                        - blockquote [ref=e683]: "Sample lead time: 10 days"
                        - paragraph [ref=e684]: "Associated extracted value: 10 days"
              - generic [ref=e685]:
                - term [ref=e686]: Production lead time
                - definition [ref=e687]:
                  - paragraph [ref=e688]: "Extraction: Known"
                  - paragraph [ref=e689]: "AI extracted value: 40 days after sample approval"
                  - paragraph [ref=e690]: "Current confirmed value: 40 days after sample approval"
                  - paragraph [ref=e691]: "Current origin: AI EXTRACTED"
                  - generic [ref=e692]:
                    - paragraph [ref=e693]: "PDF source evidence:"
                    - list [ref=e694]:
                      - listitem [ref=e695]:
                        - paragraph [ref=e696]: Page 1, block p1-b10
                        - blockquote [ref=e697]: "Production lead time: 40 days after sample approval"
                        - paragraph [ref=e698]: "Associated extracted value: 40 days after sample approval"
              - generic [ref=e699]:
                - term [ref=e700]: Shipping time
                - definition [ref=e701]:
                  - paragraph [ref=e702]: "Extraction: Known"
                  - paragraph [ref=e703]: "AI extracted value: 14 days after production"
                  - paragraph [ref=e704]: "Current confirmed value: 14 days after production"
                  - paragraph [ref=e705]: "Current origin: AI EXTRACTED"
                  - generic [ref=e706]:
                    - paragraph [ref=e707]: "PDF source evidence:"
                    - list [ref=e708]:
                      - listitem [ref=e709]:
                        - paragraph [ref=e710]: Page 1, block p1-b12
                        - blockquote [ref=e711]: "Shipping time: 14 days after production"
                        - paragraph [ref=e712]: "Associated extracted value: 14 days after production"
              - generic [ref=e713]:
                - term [ref=e714]: Total stated lead time
                - definition [ref=e715]:
                  - paragraph [ref=e716]: "Extraction: Unknown"
                  - paragraph [ref=e717]: "AI extracted value: Unknown"
                  - paragraph [ref=e718]: "Current confirmed value: Unknown"
                  - paragraph [ref=e719]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e720]: No saved source citations available for this field.
              - generic [ref=e721]:
                - term [ref=e722]: Payment terms
                - definition [ref=e723]:
                  - paragraph [ref=e724]: "Extraction: Known"
                  - paragraph [ref=e725]: "AI extracted value: 50% deposit, 50% before dispatch"
                  - paragraph [ref=e726]: "Current confirmed value: 50% deposit, 50% before dispatch"
                  - paragraph [ref=e727]: "Current origin: AI EXTRACTED"
                  - generic [ref=e728]:
                    - paragraph [ref=e729]: "PDF source evidence:"
                    - list [ref=e730]:
                      - listitem [ref=e731]:
                        - paragraph [ref=e732]: Page 1, block p1-b14
                        - blockquote [ref=e733]: "Payment terms: 50% deposit, 50% before dispatch"
                        - paragraph [ref=e734]: "Associated extracted value: 50% deposit, 50% before dispatch"
              - generic [ref=e735]:
                - term [ref=e736]: Incoterm
                - definition [ref=e737]:
                  - paragraph [ref=e738]: "Extraction: Unknown"
                  - paragraph [ref=e739]: "AI extracted value: Unknown"
                  - paragraph [ref=e740]: "Current confirmed value: Unknown"
                  - paragraph [ref=e741]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e742]: No saved source citations available for this field.
              - generic [ref=e743]:
                - term [ref=e744]: Quote validity
                - definition [ref=e745]:
                  - paragraph [ref=e746]: "Extraction: Known"
                  - paragraph [ref=e747]: "AI extracted value: 30 days"
                  - paragraph [ref=e748]: "Current confirmed value: 30 days"
                  - paragraph [ref=e749]: "Current origin: AI EXTRACTED"
                  - generic [ref=e750]:
                    - paragraph [ref=e751]: "PDF source evidence:"
                    - list [ref=e752]:
                      - listitem [ref=e753]:
                        - paragraph [ref=e754]: Page 1, block p1-b15
                        - blockquote [ref=e755]: "Quote validity: 30 days"
                        - paragraph [ref=e756]: "Associated extracted value: 30 days"
              - generic [ref=e757]:
                - term [ref=e758]: Warranty
                - definition [ref=e759]:
                  - paragraph [ref=e760]: "Extraction: Unknown"
                  - paragraph [ref=e761]: "AI extracted value: Unknown"
                  - paragraph [ref=e762]: "Current confirmed value: Unknown"
                  - paragraph [ref=e763]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e764]: No saved source citations available for this field.
              - generic [ref=e765]:
                - term [ref=e766]: Certifications
                - definition [ref=e767]:
                  - paragraph [ref=e768]: "Extraction: Unknown"
                  - paragraph [ref=e769]: "AI extracted value: Unknown"
                  - paragraph [ref=e770]: "Current confirmed value: Unknown"
                  - paragraph [ref=e771]: "Current origin: AI EXTRACTED"
                  - generic [ref=e772]:
                    - paragraph [ref=e773]: "PDF source evidence:"
                    - list [ref=e774]:
                      - listitem [ref=e775]:
                        - paragraph [ref=e776]: Page 1, block p1-b13
                        - blockquote [ref=e777]: "Preferred GRS certification: not stated in this quote"
              - generic [ref=e778]:
                - term [ref=e779]: Compliance notes
                - definition [ref=e780]:
                  - paragraph [ref=e781]: "Extraction: Unknown"
                  - paragraph [ref=e782]: "AI extracted value: Unknown"
                  - paragraph [ref=e783]: "Current confirmed value: Unknown"
                  - paragraph [ref=e784]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e785]: No saved source citations available for this field.
              - generic [ref=e786]:
                - term [ref=e787]: Exclusions
                - definition [ref=e788]:
                  - paragraph [ref=e789]: "Extraction: Unknown"
                  - paragraph [ref=e790]: "AI extracted value: Unknown"
                  - paragraph [ref=e791]: "Current confirmed value: Unknown"
                  - paragraph [ref=e792]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e793]: No saved source citations available for this field.
              - generic [ref=e794]:
                - term [ref=e795]: Special conditions
                - definition [ref=e796]:
                  - paragraph [ref=e797]: "Extraction: Unknown"
                  - paragraph [ref=e798]: "AI extracted value: Unknown"
                  - paragraph [ref=e799]: "Current confirmed value: Unknown"
                  - paragraph [ref=e800]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e801]: No saved source citations available for this field.
              - generic [ref=e802]:
                - term [ref=e803]: Supplier notes
                - definition [ref=e804]:
                  - paragraph [ref=e805]: "Extraction: Unknown"
                  - paragraph [ref=e806]: "AI extracted value: Unknown"
                  - paragraph [ref=e807]: "Current confirmed value: Unknown"
                  - paragraph [ref=e808]: "Current origin: AI EXTRACTED"
                  - paragraph [ref=e809]: No saved source citations available for this field.
            - paragraph [ref=e810]: "Notes: None"
            - button "Edit confirmed PDF quote" [ref=e811] [cursor=pointer]
      - region [ref=e812]:
        - heading "Comparison" [level=2] [ref=e813]
        - status [ref=e814]: Comparison is current.
        - table [ref=e816]:
          - caption [ref=e817]: Factual comparison of confirmed supplier quotes
          - rowgroup [ref=e818]:
            - row [ref=e819]:
              - columnheader "Criterion" [ref=e820]
              - columnheader "Willow Stitch Studio" [ref=e821]
              - columnheader "Harbor Pouch Works" [ref=e822]
          - rowgroup [ref=e823]:
            - row [ref=e824]:
              - rowheader "Unit price" [ref=e825]
              - cell "USD 4.20 Confirmed project quote price" [ref=e826]:
                - strong [ref=e827]: USD 4.20
                - generic [ref=e828]: Confirmed project quote price
                - group [ref=e829]:
                  - generic "Source details" [ref=e830]
              - cell "USD 4.60 Confirmed project quote price" [ref=e831]:
                - strong [ref=e832]: USD 4.60
                - generic [ref=e833]: Confirmed project quote price
                - group [ref=e834]:
                  - generic "Source details" [ref=e835]
            - row [ref=e836]:
              - rowheader "Quoted quantity" [ref=e837]
              - cell [ref=e838]:
                - strong [ref=e839]: "2000"
                - group [ref=e840]:
                  - generic "Source details" [ref=e841]
              - cell [ref=e842]:
                - strong [ref=e843]: "2000"
                - group [ref=e844]:
                  - generic "Source details" [ref=e845]
            - row [ref=e846]:
              - rowheader "Minimum order quantity" [ref=e847]
              - cell [ref=e848]:
                - strong [ref=e849]: "1800"
                - group [ref=e850]:
                  - generic "Source details" [ref=e851]
              - cell [ref=e852]:
                - strong [ref=e853]: "1000"
                - group [ref=e854]:
                  - generic "Source details" [ref=e855]
            - row [ref=e856]:
              - rowheader "Production lead time" [ref=e857]
              - cell [ref=e858]:
                - strong [ref=e859]: 40 days after sample approval
                - group [ref=e860]:
                  - generic "Source details" [ref=e861]
              - cell [ref=e862]:
                - strong [ref=e863]: 32 days after sample approval
                - group [ref=e864]:
                  - generic "Source details" [ref=e865]
            - row [ref=e866]:
              - rowheader "Delivery commitment" [ref=e867]
              - cell [ref=e868]:
                - strong [ref=e869]: Unknown
              - cell [ref=e870]:
                - strong [ref=e871]: Unknown
            - row [ref=e872]:
              - rowheader "Tooling or setup cost" [ref=e873]
              - cell [ref=e874]:
                - strong [ref=e875]: USD 100
                - group [ref=e876]:
                  - generic "Source details" [ref=e877]
              - cell [ref=e878]:
                - strong [ref=e879]: USD 150
                - group [ref=e880]:
                  - generic "Source details" [ref=e881]
            - row [ref=e882]:
              - rowheader "Shipping cost" [ref=e883]
              - cell [ref=e884]:
                - strong [ref=e885]: USD 280
                - group [ref=e886]:
                  - generic "Source details" [ref=e887]
              - cell [ref=e888]:
                - strong [ref=e889]: USD 320
                - group [ref=e890]:
                  - generic "Source details" [ref=e891]
            - row [ref=e892]:
              - 'rowheader "Certification Required Expected: grs" [ref=e893]':
                - text: Certification
                - generic [ref=e894]: Required
                - generic [ref=e895]: "Expected: grs"
              - cell [ref=e896]:
                - strong [ref=e897]: Unknown
              - cell [ref=e898]:
                - strong [ref=e899]: Meets
                - group [ref=e900]:
                  - generic "Source details" [ref=e901]
            - row [ref=e902]:
              - 'rowheader "Capability Required Expected: CUSTOM_BRANDING · Yes" [ref=e903]':
                - text: Capability
                - generic [ref=e904]: Required
                - generic [ref=e905]: "Expected: CUSTOM_BRANDING · Yes"
              - cell [ref=e906]:
                - strong [ref=e907]: Meets
                - group [ref=e908]:
                  - generic "Source details" [ref=e909]
              - cell [ref=e910]:
                - strong [ref=e911]: Meets
                - group [ref=e912]:
                  - generic "Source details" [ref=e913]
            - row [ref=e914]:
              - 'rowheader "Material Informational Expected: recycled polyester" [ref=e915]':
                - text: Material
                - generic [ref=e916]: Informational
                - generic [ref=e917]: "Expected: recycled polyester"
              - cell [ref=e918]:
                - strong [ref=e919]: Meets
                - group [ref=e920]:
                  - generic "Source details" [ref=e921]
              - cell [ref=e922]:
                - strong [ref=e923]: Meets
                - group [ref=e924]:
                  - generic "Source details" [ref=e925]
        - button "Analyze Comparison" [ref=e926] [cursor=pointer]
        - group [ref=e927]:
          - generic "Missing or conflicting information" [ref=e928]
        - button "Regenerate Comparison" [ref=e929] [cursor=pointer]
      - region [ref=e930]:
        - heading "Decision" [level=2] [ref=e931]
        - paragraph [ref=e932]:
          - text: "Current preference:"
          - strong [ref=e933]: No Decision Yet
        - paragraph [ref=e934]: This records your choice. It does not place an order or contact a supplier.
        - generic [ref=e935]:
          - generic [ref=e936]:
            - text: Preferred supplier
            - combobox "Preferred supplier" [ref=e937]:
              - option "Choose a shortlisted supplier" [selected]
              - option "Harbor Pouch Works"
              - option "Moss Thread Bags"
              - option "Willow Stitch Studio"
          - generic [ref=e938]:
            - text: Decision notes
            - textbox "Decision notes" [ref=e939]
          - button "Mark as Preferred Supplier" [disabled] [ref=e940]
          - button "Save decision notes" [ref=e941] [cursor=pointer]
```

# Test source

```ts
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
  103 | });
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
> 121 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
      |                                                         ^ Error: locator.selectOption: Test timeout of 120000ms exceeded.
  122 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'disconnect'});
  123 |   await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('may still be finishing');await expect(button(page,'Retry analysis')).toBeDisabled();await button(page,'Retry analysis').scrollIntoViewIfNeeded();await page.screenshot({path:test.info().outputPath('disconnect-cooldown.png')});await nativeFocus(page);expect(posts).toBe(1);
  124 |   await expect(button(page,'Retry analysis')).toBeDisabled();
  125 |   await page.clock.fastForward(170000);await expect(button(page,'Retry analysis')).toBeDisabled();await page.clock.fastForward(10100);await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  126 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  127 | });
  128 | test('real backend deadline through actual proxy and explicit recovery',async({page})=>{
  129 |   test.setTimeout(240000);
  130 |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  131 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  132 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'deadline'});
  133 |   const response=page.waitForResponse(r=>r.url().endsWith('/comparison/advice'),{timeout:210000});
  134 |   const start=Date.now();await button(page,'Analyze Comparison').click();const result=await response;
  135 |   const body=await result.json();expect(result.status()).toBe(504);expect(body.error.code).toBe('COMPARISON_ANALYSIS_TIMEOUT');
  136 |   writeFileSync(test.info().outputPath('deadline.json'),JSON.stringify({elapsed_ms:Date.now()-start,status:result.status(),code:body.error.code,posts},null,2));
  137 |   await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  138 |   await page.screenshot({path:test.info().outputPath('deadline-error.png'),fullPage:true});
  139 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  140 | });
  141 | test('existing human preference survives advice and failures',async({page})=>{
  142 |   const id=await setup(page),d=page.getByRole('region',{name:'Decision',exact:true});
  143 |   await d.getByLabel('Preferred supplier',{exact:true}).selectOption({label:'Willow Stitch Studio'});await d.getByLabel('Decision notes').fill('QA human choice');await d.getByRole('button',{name:'Mark as Preferred Supplier',exact:true}).click();await expect(d).toContainText('Preferred supplier saved.');
  144 |   const before=await readApi<any>(page,`/projects/${id}`);await analyze(page);await nativeFocus(page);await expect(output(page)).toBeVisible();
  145 |   await page.route(`**/api/projects/${id}/comparison/advice`,r=>r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis unavailable. Please retry.'}}}));
  146 |   await button(page,'Analyze Comparison').click();await expect(button(page,'Retry analysis')).toBeEnabled();
  147 |   const after=await readApi<any>(page,`/projects/${id}`);expect(after.preferred_supplier_id).toBe(before.preferred_supplier_id);expect(after.decision_notes).toBe(before.decision_notes);await expect(d).toContainText('Willow Stitch Studio');
  148 | });
  149 | for(const suggestion of [false,true])test(`${suggestion?'suggestion':'null-success'} disclosures sources facts and preference`,async({page})=>{
  150 |   const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`);
  151 |   if(suggestion)await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{const response=await r.fetch(),body=await response.json();body.suggestion.supplier_id=before.comparison_payload.suppliers[0].supplier_id;body.suggestion.supporting_reasons=[body.analysis.supplier_summaries[0]];body.suggestion.tradeoffs=[body.analysis.key_tradeoffs[0]];await r.fulfill({json:body});});
  152 |   await analyze(page);await expect(output(page)).toContainText(suggestion?'Suggested Supplier to Investigate First':'No supplier suggested yet');await expect(output(page)).toContainText('You remain responsible for the supplier decision');await expect(output(page)).toContainText('Important unknowns');await expect(region(page).getByRole('table')).toBeVisible();
  153 |   await output(page).getByText('Source details',{exact:true}).first().click();await expect(output(page)).toContainText('Supporting PDF evidence: page 1, block 5');await invariant(page,id,before);
  154 | });
  155 | 
  156 | 
  157 | 
  158 | 
  159 | 
```