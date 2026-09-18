# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: workspace.spec.ts >> manual views, actual responsive resize, pins, model edits and reload share persisted state
- Location: e2e/workspace.spec.ts:61:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: 'Organize', exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - link "r relay SDR" [ref=e5] [cursor=pointer]:
      - /url: /#overview
      - generic [ref=e6]: r
      - generic [ref=e7]: relay SDR
    - navigation "Main navigation" [ref=e8]:
      - link "Leads" [ref=e9] [cursor=pointer]:
        - /url: /leads
      - link "Voice lab" [ref=e12] [cursor=pointer]:
        - /url: /#lab
  - main [ref=e15]:
    - generic [ref=e16]:
      - generic [ref=e17]:
        - text: Workspace /
        - strong [ref=e18]: Leads
      - button "Workspace agent connected" [ref=e21] [cursor=pointer]
    - paragraph [ref=e22]: VERIFICATION DATASET — All people, call content and assessments shown here are fictional fixtures. No calls were placed.
    - generic [ref=e23]:
      - generic [ref=e24]:
        - text: YOUR PIPELINE, IN CONTEXT
        - heading "Leads workspace." [level=1] [ref=e25]
        - paragraph [ref=e26]: Evidence you can trace. Priorities you can act on.
      - generic [ref=e27]:
        - button "Import CSV" [ref=e28] [cursor=pointer]
        - button "Add lead" [ref=e29] [cursor=pointer]
    - region "Workspace orchestrator" [ref=e32]:
      - generic [ref=e33]:
        - generic [ref=e37]:
          - strong [ref=e38]: Organize with your workspace agent
          - generic [ref=e39]: Changes are saved, versioned and reversible. No outreach permissions.
        - generic [ref=e40]:
          - generic [ref=e41]: Organization mode
          - combobox "Organization mode" [ref=e42]:
            - option "Adaptive" [selected]
            - option "Suggest"
            - option "Manual"
      - generic [ref=e43]:
        - textbox "Workspace instruction" [active] [ref=e44]:
          - /placeholder: Show leads awaiting a proposal, grouped by priority…
          - text: Focus the workspace on evidence
        - button "Submit internal organization command" [ref=e45] [cursor=pointer]
      - generic [ref=e48]:
        - button "Callbacks due today ↗" [ref=e49] [cursor=pointer]:
          - text: Callbacks due today
          - generic [ref=e50]: ↗
        - button "Procurement blockers ↗" [ref=e51] [cursor=pointer]:
          - text: Procurement blockers
          - generic [ref=e52]: ↗
        - button "Where I can unblock progress ↗" [ref=e53] [cursor=pointer]:
          - text: Where I can unblock progress
          - generic [ref=e54]: ↗
    - status [ref=e55]:
      - generic [ref=e58]: Created view “Canvas chromium-mobile”
      - button "Dismiss notification" [ref=e59] [cursor=pointer]
    - status [ref=e62]:
      - generic [ref=e65]: Saved updates are ready. Updates apply after a brief idle period.
      - button "Apply updates" [ref=e66] [cursor=pointer]
    - navigation "Saved views" [ref=e67]:
      - button "Today" [ref=e68] [cursor=pointer]
      - button "All leads" [ref=e70] [cursor=pointer]
      - button "Highest potential" [ref=e72] [cursor=pointer]
      - button "Follow-ups" [ref=e74] [cursor=pointer]
      - button "Needs qualification" [ref=e76] [cursor=pointer]
      - button "Needs review" [ref=e78] [cursor=pointer]
      - button "Do not call" [ref=e80] [cursor=pointer]
      - button "Practice / demo" [ref=e82] [cursor=pointer]
      - button "Canvas chromium-mobile 31" [ref=e84] [cursor=pointer]:
        - generic [ref=e85]: Canvas chromium-mobile
        - generic [ref=e86]: "31"
      - button "Create saved view" [ref=e87] [cursor=pointer]
    - generic [ref=e90]:
      - paragraph [ref=e91]: A custom saved query. Filters and ordering are visible in Customize view.
      - button "View definition" [ref=e92] [cursor=pointer]
    - region "Evidence-backed overview" [ref=e95]:
      - generic [ref=e96]:
        - generic [ref=e97]: Leads in this view
        - strong [ref=e98]: "31"
        - generic [ref=e99]: All matching records, not just the page
      - generic [ref=e100]:
        - generic [ref=e101]: Promising opportunities
        - strong [ref=e102]: "6"
        - generic [ref=e103]: Supported need and product fit
      - generic [ref=e104]:
        - generic [ref=e105]: Commitments due
        - strong [ref=e106]: "5"
        - generic [ref=e107]: Due today or overdue; no outreach performed
      - generic [ref=e108]:
        - generic [ref=e109]: Needs review
        - strong [ref=e110]: "6"
        - generic [ref=e111]: Coverage, freshness or conflicting evidence
    - generic [ref=e112]:
      - textbox "Search leads" [ref=e116]:
        - /placeholder: Search names, companies or phone numbers
      - generic [ref=e117]:
        - button "Filters" [ref=e118] [cursor=pointer]
        - button "Customize canvas" [ref=e121] [cursor=pointer]
        - group [ref=e124]:
          - generic "More workspace options" [ref=e125] [cursor=pointer]: •••
    - generic [ref=e128]:
      - region "Lead directory" [ref=e129]:
        - generic [ref=e130]:
          - heading "Lead directory" [level=2] [ref=e134]
          - button "Pin Lead directory" [ref=e136] [cursor=pointer]
        - generic [ref=e139]:
          - table [ref=e141]:
            - rowgroup [ref=e142]:
              - row [ref=e143]:
                - columnheader "Select" [ref=e144]
                - columnheader [ref=e146]:
                  - button "name" [ref=e147] [cursor=pointer]
                - columnheader [ref=e148]:
                  - button "company" [ref=e149] [cursor=pointer]
                - columnheader [ref=e150]:
                  - button "potential" [ref=e151] [cursor=pointer]
                - columnheader [ref=e152]:
                  - button "priority ↓" [ref=e153] [cursor=pointer]
                - columnheader [ref=e154]:
                  - button "confidence" [ref=e155] [cursor=pointer]
                - columnheader [ref=e156]:
                  - button "eligibility" [ref=e157] [cursor=pointer]
            - rowgroup [ref=e158]:
              - row [ref=e159]:
                - cell [ref=e160]:
                  - checkbox "Select Fictional Atlas" [ref=e161]
                - cell [ref=e162]:
                  - button "FI Fictional Atlas" [ref=e163] [cursor=pointer]:
                    - generic [ref=e164]: FI
                    - generic [ref=e165]: Fictional Atlas
                - cell "Atlas Example Ltd" [ref=e166]
                - cell "strong" [ref=e167]
                - cell "overdue" [ref=e169]
                - cell "partial" [ref=e171]
                - cell "permission recorded" [ref=e173]
              - row [ref=e175]:
                - cell [ref=e176]:
                  - checkbox "Select Fictional Acme" [ref=e177]
                - cell [ref=e178]:
                  - button "FI Fictional Acme" [ref=e179] [cursor=pointer]:
                    - generic [ref=e180]: FI
                    - generic [ref=e181]: Fictional Acme
                - cell "Acme Example Ltd" [ref=e182]
                - cell "strong" [ref=e183]
                - cell "overdue" [ref=e185]
                - cell "partial" [ref=e187]
                - cell "permission recorded" [ref=e189]
              - row [ref=e191]:
                - cell [ref=e192]:
                  - checkbox "Select Fictional Cedar" [ref=e193]
                - cell [ref=e194]:
                  - button "FI Fictional Cedar" [ref=e195] [cursor=pointer]:
                    - generic [ref=e196]: FI
                    - generic [ref=e197]: Fictional Cedar
                - cell "Cedar Example Ltd" [ref=e198]
                - cell "strong" [ref=e199]
                - cell "overdue" [ref=e201]
                - cell "partial" [ref=e203]
                - cell "permission recorded" [ref=e205]
              - row [ref=e207]:
                - cell [ref=e208]:
                  - checkbox "Select Fictional Birch" [ref=e209]
                - cell [ref=e210]:
                  - button "FI Fictional Birch" [ref=e211] [cursor=pointer]:
                    - generic [ref=e212]: FI
                    - generic [ref=e213]: Fictional Birch
                - cell "Birch Example Ltd" [ref=e214]
                - cell "strong" [ref=e215]
                - cell "overdue" [ref=e217]
                - cell "partial" [ref=e219]
                - cell "permission recorded" [ref=e221]
              - row [ref=e223]:
                - cell [ref=e224]:
                  - checkbox "Select Fictional Delta" [ref=e225]
                - cell [ref=e226]:
                  - button "FI Fictional Delta" [ref=e227] [cursor=pointer]:
                    - generic [ref=e228]: FI
                    - generic [ref=e229]: Fictional Delta
                - cell "Delta Example Ltd" [ref=e230]
                - cell "strong" [ref=e231]
                - cell "overdue" [ref=e233]
                - cell "partial" [ref=e235]
                - cell "permission recorded" [ref=e237]
              - row [ref=e239]:
                - cell [ref=e240]:
                  - checkbox "Select Uncalled fixture 35" [ref=e241]
                - cell [ref=e242]:
                  - button "UN Uncalled fixture 35" [ref=e243] [cursor=pointer]:
                    - generic [ref=e244]: UN
                    - generic [ref=e245]: Uncalled fixture 35
                - cell "Fictional Northwind" [ref=e246]
                - cell "unassessed" [ref=e247]
                - cell "none" [ref=e249]
                - cell "unknown" [ref=e251]
                - cell "permission missing" [ref=e253]
              - row [ref=e255]:
                - cell [ref=e256]:
                  - checkbox "Select Uncalled fixture 44" [ref=e257]
                - cell [ref=e258]:
                  - button "UN Uncalled fixture 44" [ref=e259] [cursor=pointer]:
                    - generic [ref=e260]: UN
                    - generic [ref=e261]: Uncalled fixture 44
                - cell "Fictional Northwind" [ref=e262]
                - cell "unassessed" [ref=e263]
                - cell "none" [ref=e265]
                - cell "unknown" [ref=e267]
                - cell "permission missing" [ref=e269]
              - row [ref=e271]:
                - cell [ref=e272]:
                  - checkbox "Select Uncalled fixture 41" [ref=e273]
                - cell [ref=e274]:
                  - button "UN Uncalled fixture 41" [ref=e275] [cursor=pointer]:
                    - generic [ref=e276]: UN
                    - generic [ref=e277]: Uncalled fixture 41
                - cell "Fictional Northwind" [ref=e278]
                - cell "unassessed" [ref=e279]
                - cell "none" [ref=e281]
                - cell "unknown" [ref=e283]
                - cell "permission missing" [ref=e285]
              - row [ref=e287]:
                - cell [ref=e288]:
                  - checkbox "Select Uncalled fixture 23" [ref=e289]
                - cell [ref=e290]:
                  - button "UN Uncalled fixture 23" [ref=e291] [cursor=pointer]:
                    - generic [ref=e292]: UN
                    - generic [ref=e293]: Uncalled fixture 23
                - cell "Fictional Northwind" [ref=e294]
                - cell "unassessed" [ref=e295]
                - cell "none" [ref=e297]
                - cell "unknown" [ref=e299]
                - cell "permission missing" [ref=e301]
              - row [ref=e303]:
                - cell [ref=e304]:
                  - checkbox "Select Uncalled fixture 28" [ref=e305]
                - cell [ref=e306]:
                  - button "UN Uncalled fixture 28" [ref=e307] [cursor=pointer]:
                    - generic [ref=e308]: UN
                    - generic [ref=e309]: Uncalled fixture 28
                - cell "Fictional Northwind" [ref=e310]
                - cell "unassessed" [ref=e311]
                - cell "none" [ref=e313]
                - cell "unknown" [ref=e315]
                - cell "permission missing" [ref=e317]
              - row [ref=e319]:
                - cell [ref=e320]:
                  - checkbox "Select Uncalled fixture 38" [ref=e321]
                - cell [ref=e322]:
                  - button "UN Uncalled fixture 38" [ref=e323] [cursor=pointer]:
                    - generic [ref=e324]: UN
                    - generic [ref=e325]: Uncalled fixture 38
                - cell "Fictional Northwind" [ref=e326]
                - cell "unassessed" [ref=e327]
                - cell "none" [ref=e329]
                - cell "unknown" [ref=e331]
                - cell "permission missing" [ref=e333]
              - row [ref=e335]:
                - cell [ref=e336]:
                  - checkbox "Select Uncalled fixture 32" [ref=e337]
                - cell [ref=e338]:
                  - button "UN Uncalled fixture 32" [ref=e339] [cursor=pointer]:
                    - generic [ref=e340]: UN
                    - generic [ref=e341]: Uncalled fixture 32
                - cell "Fictional Northwind" [ref=e342]
                - cell "unassessed" [ref=e343]
                - cell "none" [ref=e345]
                - cell "unknown" [ref=e347]
                - cell "permission missing" [ref=e349]
              - row [ref=e351]:
                - cell [ref=e352]:
                  - checkbox "Select Uncalled fixture 26" [ref=e353]
                - cell [ref=e354]:
                  - button "UN Uncalled fixture 26" [ref=e355] [cursor=pointer]:
                    - generic [ref=e356]: UN
                    - generic [ref=e357]: Uncalled fixture 26
                - cell "Fictional Northwind" [ref=e358]
                - cell "unassessed" [ref=e359]
                - cell "none" [ref=e361]
                - cell "unknown" [ref=e363]
                - cell "permission missing" [ref=e365]
              - row [ref=e367]:
                - cell [ref=e368]:
                  - checkbox "Select Uncalled fixture 21" [ref=e369]
                - cell [ref=e370]:
                  - button "UN Uncalled fixture 21" [ref=e371] [cursor=pointer]:
                    - generic [ref=e372]: UN
                    - generic [ref=e373]: Uncalled fixture 21
                - cell "Fictional Northwind" [ref=e374]
                - cell "unassessed" [ref=e375]
                - cell "none" [ref=e377]
                - cell "unknown" [ref=e379]
                - cell "permission missing" [ref=e381]
              - row [ref=e383]:
                - cell [ref=e384]:
                  - checkbox "Select Uncalled fixture 22" [ref=e385]
                - cell [ref=e386]:
                  - button "UN Uncalled fixture 22" [ref=e387] [cursor=pointer]:
                    - generic [ref=e388]: UN
                    - generic [ref=e389]: Uncalled fixture 22
                - cell "Fictional Northwind" [ref=e390]
                - cell "unassessed" [ref=e391]
                - cell "none" [ref=e393]
                - cell "unknown" [ref=e395]
                - cell "permission missing" [ref=e397]
              - row [ref=e399]:
                - cell [ref=e400]:
                  - checkbox "Select Uncalled fixture 33" [ref=e401]
                - cell [ref=e402]:
                  - button "UN Uncalled fixture 33" [ref=e403] [cursor=pointer]:
                    - generic [ref=e404]: UN
                    - generic [ref=e405]: Uncalled fixture 33
                - cell "Fictional Northwind" [ref=e406]
                - cell "unassessed" [ref=e407]
                - cell "none" [ref=e409]
                - cell "unknown" [ref=e411]
                - cell "permission missing" [ref=e413]
              - row [ref=e415]:
                - cell [ref=e416]:
                  - checkbox "Select Uncalled fixture 30" [ref=e417]
                - cell [ref=e418]:
                  - button "UN Uncalled fixture 30" [ref=e419] [cursor=pointer]:
                    - generic [ref=e420]: UN
                    - generic [ref=e421]: Uncalled fixture 30
                - cell "Fictional Northwind" [ref=e422]
                - cell "unassessed" [ref=e423]
                - cell "none" [ref=e425]
                - cell "unknown" [ref=e427]
                - cell "permission missing" [ref=e429]
              - row [ref=e431]:
                - cell [ref=e432]:
                  - checkbox "Select Uncalled fixture 20" [ref=e433]
                - cell [ref=e434]:
                  - button "UN Uncalled fixture 20" [ref=e435] [cursor=pointer]:
                    - generic [ref=e436]: UN
                    - generic [ref=e437]: Uncalled fixture 20
                - cell "Fictional Northwind" [ref=e438]
                - cell "unassessed" [ref=e439]
                - cell "none" [ref=e441]
                - cell "unknown" [ref=e443]
                - cell "permission missing" [ref=e445]
              - row [ref=e447]:
                - cell [ref=e448]:
                  - checkbox "Select Uncalled fixture 24" [ref=e449]
                - cell [ref=e450]:
                  - button "UN Uncalled fixture 24" [ref=e451] [cursor=pointer]:
                    - generic [ref=e452]: UN
                    - generic [ref=e453]: Uncalled fixture 24
                - cell "Fictional Northwind" [ref=e454]
                - cell "unassessed" [ref=e455]
                - cell "none" [ref=e457]
                - cell "unknown" [ref=e459]
                - cell "permission missing" [ref=e461]
              - row [ref=e463]:
                - cell [ref=e464]:
                  - checkbox "Select Uncalled fixture 43" [ref=e465]
                - cell [ref=e466]:
                  - button "UN Uncalled fixture 43" [ref=e467] [cursor=pointer]:
                    - generic [ref=e468]: UN
                    - generic [ref=e469]: Uncalled fixture 43
                - cell "Fictional Northwind" [ref=e470]
                - cell "unassessed" [ref=e471]
                - cell "none" [ref=e473]
                - cell "unknown" [ref=e475]
                - cell "permission missing" [ref=e477]
              - row [ref=e479]:
                - cell [ref=e480]:
                  - checkbox "Select Uncalled fixture 25" [ref=e481]
                - cell [ref=e482]:
                  - button "UN Uncalled fixture 25" [ref=e483] [cursor=pointer]:
                    - generic [ref=e484]: UN
                    - generic [ref=e485]: Uncalled fixture 25
                - cell "Fictional Northwind" [ref=e486]
                - cell "unassessed" [ref=e487]
                - cell "none" [ref=e489]
                - cell "unknown" [ref=e491]
                - cell "permission missing" [ref=e493]
              - row [ref=e495]:
                - cell [ref=e496]:
                  - checkbox "Select Uncalled fixture 34" [ref=e497]
                - cell [ref=e498]:
                  - button "UN Uncalled fixture 34" [ref=e499] [cursor=pointer]:
                    - generic [ref=e500]: UN
                    - generic [ref=e501]: Uncalled fixture 34
                - cell "Fictional Northwind" [ref=e502]
                - cell "unassessed" [ref=e503]
                - cell "none" [ref=e505]
                - cell "unknown" [ref=e507]
                - cell "permission missing" [ref=e509]
              - row [ref=e511]:
                - cell [ref=e512]:
                  - checkbox "Select Uncalled fixture 39" [ref=e513]
                - cell [ref=e514]:
                  - button "UN Uncalled fixture 39" [ref=e515] [cursor=pointer]:
                    - generic [ref=e516]: UN
                    - generic [ref=e517]: Uncalled fixture 39
                - cell "Fictional Northwind" [ref=e518]
                - cell "unassessed" [ref=e519]
                - cell "none" [ref=e521]
                - cell "unknown" [ref=e523]
                - cell "permission missing" [ref=e525]
              - row [ref=e527]:
                - cell [ref=e528]:
                  - checkbox "Select Uncalled fixture 36" [ref=e529]
                - cell [ref=e530]:
                  - button "UN Uncalled fixture 36" [ref=e531] [cursor=pointer]:
                    - generic [ref=e532]: UN
                    - generic [ref=e533]: Uncalled fixture 36
                - cell "Fictional Northwind" [ref=e534]
                - cell "unassessed" [ref=e535]
                - cell "none" [ref=e537]
                - cell "unknown" [ref=e539]
                - cell "permission missing" [ref=e541]
              - row [ref=e543]:
                - cell [ref=e544]:
                  - checkbox "Select Uncalled fixture 27" [ref=e545]
                - cell [ref=e546]:
                  - button "UN Uncalled fixture 27" [ref=e547] [cursor=pointer]:
                    - generic [ref=e548]: UN
                    - generic [ref=e549]: Uncalled fixture 27
                - cell "Fictional Northwind" [ref=e550]
                - cell "unassessed" [ref=e551]
                - cell "none" [ref=e553]
                - cell "unknown" [ref=e555]
                - cell "permission missing" [ref=e557]
          - generic [ref=e559]:
            - generic [ref=e560]: 1–25 of 31
            - generic [ref=e561]:
              - button "Previous" [disabled] [ref=e562]
              - button "Next" [ref=e563] [cursor=pointer]
      - region "Pipeline by stage" [ref=e564]:
        - generic [ref=e565]:
          - heading "Pipeline by stage" [level=2] [ref=e569]
          - button "Pin Pipeline by stage" [ref=e571] [cursor=pointer]
        - generic [ref=e574]:
          - generic [ref=e575]:
            - generic [ref=e576]:
              - heading "unassessed 25" [level=3] [ref=e577]:
                - text: unassessed
                - generic [ref=e578]: "25"
              - button "Uncalled fixture 35 Fictional Northwind unassessed none" [ref=e579] [cursor=pointer]:
                - strong [ref=e580]: Uncalled fixture 35
                - generic [ref=e581]: Fictional Northwind
                - generic [ref=e582]: unassessed
                - generic [ref=e583]: none
              - button "Uncalled fixture 44 Fictional Northwind unassessed none" [ref=e584] [cursor=pointer]:
                - strong [ref=e585]: Uncalled fixture 44
                - generic [ref=e586]: Fictional Northwind
                - generic [ref=e587]: unassessed
                - generic [ref=e588]: none
              - button "Uncalled fixture 41 Fictional Northwind unassessed none" [ref=e589] [cursor=pointer]:
                - strong [ref=e590]: Uncalled fixture 41
                - generic [ref=e591]: Fictional Northwind
                - generic [ref=e592]: unassessed
                - generic [ref=e593]: none
              - button "Uncalled fixture 23 Fictional Northwind unassessed none" [ref=e594] [cursor=pointer]:
                - strong [ref=e595]: Uncalled fixture 23
                - generic [ref=e596]: Fictional Northwind
                - generic [ref=e597]: unassessed
                - generic [ref=e598]: none
              - button "Uncalled fixture 28 Fictional Northwind unassessed none" [ref=e599] [cursor=pointer]:
                - strong [ref=e600]: Uncalled fixture 28
                - generic [ref=e601]: Fictional Northwind
                - generic [ref=e602]: unassessed
                - generic [ref=e603]: none
              - button "Uncalled fixture 38 Fictional Northwind unassessed none" [ref=e604] [cursor=pointer]:
                - strong [ref=e605]: Uncalled fixture 38
                - generic [ref=e606]: Fictional Northwind
                - generic [ref=e607]: unassessed
                - generic [ref=e608]: none
              - button "Uncalled fixture 32 Fictional Northwind unassessed none" [ref=e609] [cursor=pointer]:
                - strong [ref=e610]: Uncalled fixture 32
                - generic [ref=e611]: Fictional Northwind
                - generic [ref=e612]: unassessed
                - generic [ref=e613]: none
              - button "Uncalled fixture 26 Fictional Northwind unassessed none" [ref=e614] [cursor=pointer]:
                - strong [ref=e615]: Uncalled fixture 26
                - generic [ref=e616]: Fictional Northwind
                - generic [ref=e617]: unassessed
                - generic [ref=e618]: none
              - button "Uncalled fixture 21 Fictional Northwind unassessed none" [ref=e619] [cursor=pointer]:
                - strong [ref=e620]: Uncalled fixture 21
                - generic [ref=e621]: Fictional Northwind
                - generic [ref=e622]: unassessed
                - generic [ref=e623]: none
              - button "Uncalled fixture 22 Fictional Northwind unassessed none" [ref=e624] [cursor=pointer]:
                - strong [ref=e625]: Uncalled fixture 22
                - generic [ref=e626]: Fictional Northwind
                - generic [ref=e627]: unassessed
                - generic [ref=e628]: none
              - button "Uncalled fixture 33 Fictional Northwind unassessed none" [ref=e629] [cursor=pointer]:
                - strong [ref=e630]: Uncalled fixture 33
                - generic [ref=e631]: Fictional Northwind
                - generic [ref=e632]: unassessed
                - generic [ref=e633]: none
              - button "Uncalled fixture 30 Fictional Northwind unassessed none" [ref=e634] [cursor=pointer]:
                - strong [ref=e635]: Uncalled fixture 30
                - generic [ref=e636]: Fictional Northwind
                - generic [ref=e637]: unassessed
                - generic [ref=e638]: none
              - button "Uncalled fixture 20 Fictional Northwind unassessed none" [ref=e639] [cursor=pointer]:
                - strong [ref=e640]: Uncalled fixture 20
                - generic [ref=e641]: Fictional Northwind
                - generic [ref=e642]: unassessed
                - generic [ref=e643]: none
              - button "Uncalled fixture 24 Fictional Northwind unassessed none" [ref=e644] [cursor=pointer]:
                - strong [ref=e645]: Uncalled fixture 24
                - generic [ref=e646]: Fictional Northwind
                - generic [ref=e647]: unassessed
                - generic [ref=e648]: none
              - button "Uncalled fixture 43 Fictional Northwind unassessed none" [ref=e649] [cursor=pointer]:
                - strong [ref=e650]: Uncalled fixture 43
                - generic [ref=e651]: Fictional Northwind
                - generic [ref=e652]: unassessed
                - generic [ref=e653]: none
              - button "Uncalled fixture 25 Fictional Northwind unassessed none" [ref=e654] [cursor=pointer]:
                - strong [ref=e655]: Uncalled fixture 25
                - generic [ref=e656]: Fictional Northwind
                - generic [ref=e657]: unassessed
                - generic [ref=e658]: none
              - button "Uncalled fixture 34 Fictional Northwind unassessed none" [ref=e659] [cursor=pointer]:
                - strong [ref=e660]: Uncalled fixture 34
                - generic [ref=e661]: Fictional Northwind
                - generic [ref=e662]: unassessed
                - generic [ref=e663]: none
              - button "Uncalled fixture 39 Fictional Northwind unassessed none" [ref=e664] [cursor=pointer]:
                - strong [ref=e665]: Uncalled fixture 39
                - generic [ref=e666]: Fictional Northwind
                - generic [ref=e667]: unassessed
                - generic [ref=e668]: none
              - button "Uncalled fixture 36 Fictional Northwind unassessed none" [ref=e669] [cursor=pointer]:
                - strong [ref=e670]: Uncalled fixture 36
                - generic [ref=e671]: Fictional Northwind
                - generic [ref=e672]: unassessed
                - generic [ref=e673]: none
              - button "Uncalled fixture 27 Fictional Northwind unassessed none" [ref=e674] [cursor=pointer]:
                - strong [ref=e675]: Uncalled fixture 27
                - generic [ref=e676]: Fictional Northwind
                - generic [ref=e677]: unassessed
                - generic [ref=e678]: none
            - heading "qualification 0" [level=3] [ref=e680]:
              - text: qualification
              - generic [ref=e681]: "0"
            - heading "engaged 0" [level=3] [ref=e683]:
              - text: engaged
              - generic [ref=e684]: "0"
            - generic [ref=e685]:
              - heading "proposal 6" [level=3] [ref=e686]:
                - text: proposal
                - generic [ref=e687]: "6"
              - button "Fictional Atlas Atlas Example Ltd strong overdue" [ref=e688] [cursor=pointer]:
                - strong [ref=e689]: Fictional Atlas
                - generic [ref=e690]: Atlas Example Ltd
                - generic [ref=e691]: strong
                - generic [ref=e692]: overdue
              - button "Fictional Acme Acme Example Ltd strong overdue" [ref=e693] [cursor=pointer]:
                - strong [ref=e694]: Fictional Acme
                - generic [ref=e695]: Acme Example Ltd
                - generic [ref=e696]: strong
                - generic [ref=e697]: overdue
              - button "Fictional Cedar Cedar Example Ltd strong overdue" [ref=e698] [cursor=pointer]:
                - strong [ref=e699]: Fictional Cedar
                - generic [ref=e700]: Cedar Example Ltd
                - generic [ref=e701]: strong
                - generic [ref=e702]: overdue
              - button "Fictional Birch Birch Example Ltd strong overdue" [ref=e703] [cursor=pointer]:
                - strong [ref=e704]: Fictional Birch
                - generic [ref=e705]: Birch Example Ltd
                - generic [ref=e706]: strong
                - generic [ref=e707]: overdue
              - button "Fictional Delta Delta Example Ltd strong overdue" [ref=e708] [cursor=pointer]:
                - strong [ref=e709]: Fictional Delta
                - generic [ref=e710]: Delta Example Ltd
                - generic [ref=e711]: strong
                - generic [ref=e712]: overdue
            - heading "decision 0" [level=3] [ref=e714]:
              - text: decision
              - generic [ref=e715]: "0"
          - paragraph [ref=e716]: Stage counts cover this view. Cards show the current directory page; open a card to inspect its evidence.
      - region "Recent changes" [ref=e717]:
        - generic [ref=e718]:
          - heading "Recent changes" [level=2] [ref=e722]
          - button "Pin Recent changes" [ref=e724] [cursor=pointer]
        - generic [ref=e728]:
          - paragraph [ref=e733]:
            - text: Created view “Canvas chromium-mobile”
            - generic [ref=e734]: human · Sep 17, 11:13 PM
          - paragraph [ref=e739]:
            - text: Restored workspace revision 2. Lead records retained.
            - generic [ref=e740]: human · Sep 17, 11:13 PM
          - paragraph [ref=e745]:
            - text: Independent operator version for UI hold test
            - generic [ref=e746]: human · Sep 17, 11:13 PM
          - paragraph [ref=e751]:
            - text: Restored workspace revision 2. Lead records retained.
            - generic [ref=e752]: human · Sep 17, 11:13 PM
          - paragraph [ref=e757]:
            - text: Workspace analysis run succeeded.
            - generic [ref=e758]: system · Sep 17, 11:13 PM
          - paragraph [ref=e763]:
            - text: "Assessment updated: strong. Source coverage 1/1 chunks."
            - generic [ref=e764]: agent · Sep 17, 11:13 PM
          - paragraph [ref=e769]:
            - text: Confirmed human correction retained
            - generic [ref=e770]: human · Sep 17, 11:13 PM
          - paragraph [ref=e775]:
            - text: Updated custom field
            - generic [ref=e776]: human · Sep 17, 11:13 PM
          - paragraph [ref=e781]:
            - text: Created field definition; values remain unknown.
            - generic [ref=e782]: human · Sep 17, 11:13 PM
          - paragraph [ref=e787]:
            - text: Restored workspace revision 2. Lead records retained.
            - generic [ref=e788]: human · Sep 17, 11:13 PM
          - paragraph [ref=e793]:
            - text: Workspace command run succeeded.
            - generic [ref=e794]: system · Sep 17, 11:13 PM
          - paragraph [ref=e799]:
            - text: Deterministic fixture organization — not a live model response.
            - generic [ref=e800]: agent · Sep 17, 11:13 PM
          - paragraph [ref=e805]:
            - text: Created view “Canvas chromium-desktop”
            - generic [ref=e806]: human · Sep 17, 11:13 PM
          - paragraph [ref=e811]:
            - text: Restored workspace revision 2. Lead records retained.
            - generic [ref=e812]: human · Sep 17, 11:13 PM
          - paragraph [ref=e817]:
            - text: Fictional fixture starts on all records.
            - generic [ref=e818]: human · Sep 17, 11:13 PM
          - paragraph [ref=e823]:
            - text: Permanent do-not-call suppression applied.
            - generic [ref=e824]: system · Sep 17, 11:13 PM
          - paragraph [ref=e829]:
            - text: Workspace analysis run succeeded.
            - generic [ref=e830]: system · Sep 17, 11:13 PM
          - paragraph [ref=e835]:
            - text: "Assessment updated: strong. Source coverage 2/2 chunks."
            - generic [ref=e836]: agent · Sep 17, 11:13 PM
          - paragraph [ref=e841]:
            - text: Workspace analysis run succeeded.
            - generic [ref=e842]: system · Sep 17, 11:13 PM
          - paragraph [ref=e847]:
            - text: "Assessment updated: strong. Source coverage 1/1 chunks."
            - generic [ref=e848]: agent · Sep 17, 11:13 PM
    - generic [ref=e849]:
      - generic [ref=e850]: Sources stay separate from assessments. Assessments stay separate from layout.
      - generic [ref=e851]: Saved workspace v10 · UTC
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | import type { APIRequestContext, Page } from '@playwright/test';
  3   | import type { Bootstrap, Detail, RecordPage } from '../src/types';
  4   | 
  5   | // Recovered WIP acceptance suite. A previous run had failures; this is not a pass claim.
  6   | const token = 'relay-browser-fixture-token-not-a-production-secret';
  7   | const headers = { Authorization: `Bearer ${token}`, Origin: 'http://127.0.0.1:8091' };
  8   | 
  9   | async function state(request: APIRequestContext): Promise<Bootstrap> {
  10  |   return (await request.get('/api/workspace', { headers })).json();
  11  | }
  12  | async function login(page: Page) {
  13  |   await page.addInitScript(value => sessionStorage.setItem('relay-token', value), token);
  14  |   await page.goto('/leads');
  15  |   await expect(page.locator('.leads-table')).toBeVisible();
  16  | }
  17  | async function reset(request: APIRequestContext) {
  18  |   const boot = await state(request);
  19  |   const response = await request.post('/api/workspace/restore', { headers, data: { base_version: boot.version, target_version: 2 } });
  20  |   expect(response.ok()).toBeTruthy();
  21  | }
  22  | async function more(page: Page, name: string) {
  23  |   await page.getByLabel('More workspace options').click();
  24  |   await page.getByRole('button', { name, exact: true }).click();
  25  | }
  26  | 
  27  | test('real rendered workspace loads, navigates and exposes source evidence', async ({ page }, info) => {
  28  |   const errors: string[] = [];
  29  |   page.on('pageerror', e => errors.push(e.message));
  30  |   await page.goto('/leads');
  31  |   await page.getByLabel('Workspace token').fill(token);
  32  |   await page.getByRole('button', { name: 'Open workspace' }).click();
  33  |   await expect(page.getByRole('button', { name: 'All leads', exact: true })).toBeVisible();
  34  |   await expect(page.locator('.lead-name').filter({ hasText: 'Fictional Acme' })).toBeVisible();
  35  |   await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2)).toBe(false);
  36  |   await page.screenshot({ path: `test-results/${info.project.name}-workspace.png`, fullPage: true });
  37  |   await page.locator('.lead-name').filter({ hasText: 'Fictional Acme' }).click();
  38  |   const detail = page.getByRole('dialog', { name: 'Fictional Acme', exact: true });
  39  |   await expect(detail.getByRole('heading', { name: 'Why this assessment?' })).toBeVisible();
  40  |   await detail.getByRole('button', { name: 'View source', exact: true }).first().click();
  41  |   const call = page.getByRole('dialog', { name: 'Call evidence', exact: true });
  42  |   await expect(call.locator('.source-highlight')).toBeVisible();
  43  |   await expect(call.locator('.transcript')).toContainText('follow-up work.');
  44  |   await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2)).toBe(false);
  45  |   await page.screenshot({ path: `test-results/${info.project.name}-evidence.png`, fullPage: true });
  46  |   await call.getByRole('button', { name: 'Close Call evidence' }).click();
  47  |   await detail.getByRole('button', { name: 'All calls', exact: true }).click();
  48  |   await expect(detail.locator('.call-history-row')).toHaveCount(25);
  49  |   await detail.getByRole('button', { name: 'Next page' }).click();
  50  |   await expect(detail.getByText('Page 2', { exact: true })).toBeVisible();
  51  |   await detail.getByRole('button', { name: 'Notes & corrections' }).click();
  52  |   await expect(detail.locator('.human-note')).toHaveCount(25);
  53  |   await detail.getByRole('button', { name: 'Next page' }).click();
  54  |   await expect(detail.locator('.human-note')).toHaveCount(5);
  55  |   await detail.getByRole('button', { name: 'Close Fictional Acme' }).click();
  56  |   await expect(page.locator('body')).not.toHaveJSProperty('scrollWidth', 0);
  57  |   expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2)).toBe(false);
  58  |   expect(errors).toEqual([]);
  59  | });
  60  | 
  61  | test('manual views, actual responsive resize, pins, model edits and reload share persisted state', async ({ page, request }, info) => {
  62  |   await reset(request); await login(page);
  63  |   const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  64  |   await page.getByRole('button', { name: 'Create saved view', exact: true }).click();
  65  |   const create = page.getByRole('dialog', { name: 'Create a saved view', exact: true });
  66  |   await create.getByLabel('View name').fill(`Canvas ${info.project.name}`);
  67  |   await create.getByRole('button', { name: 'Save view', exact: true }).click();
  68  |   await expect(create).not.toBeVisible();
  69  |   await page.getByLabel('Workspace instruction').fill('Focus the workspace on evidence');
> 70  |   await page.getByRole('button', { name: 'Organize', exact: true }).click();
      |                                                                     ^ Error: locator.click: Test timeout of 30000ms exceeded.
  71  |   await expect(page.locator('.job-status')).toContainText('succeeded');
  72  |   await page.getByLabel('Search leads').focus();
  73  |   await page.getByRole('button', { name: 'Apply updates', exact: true }).click();
  74  |   // Known historical failure: active tab name included a trailing count, e.g. "Agent-organized leads 31".
  75  |   await expect(page.getByRole('button', { name: 'Agent-organized leads', exact: true })).toBeVisible();
  76  |   const current = await state(request);
  77  |   const view = current.spec.views.find(v => v.name === 'Agent-organized leads')!;
  78  |   const tableId = view.widgets.find(id => current.spec.widgets[id].kind === 'LeadsTable')!;
  79  |   const tableTitle = current.spec.widgets[tableId].title;
  80  |   await page.getByRole('button', { name: 'Customize canvas', exact: true }).click();
  81  |   if (info.project.name.includes('desktop')) {
  82  |     const handle = page.locator(`[data-widget-id="${tableId}"] .react-resizable-handle`).last();
  83  |     await handle.scrollIntoViewIfNeeded(); const box = await handle.boundingBox();
  84  |     expect(box).not.toBeNull();
  85  |     await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  86  |     await page.mouse.down();
  87  |     await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2 + 44, { steps: 10 });
  88  |     await page.mouse.up();
  89  |   } else {
  90  |     await page.getByRole('button', { name: `Taller ${tableTitle}`, exact: true }).click();
  91  |   }
  92  |   await expect(page.getByText('Layout changes are not saved yet')).toBeVisible();
  93  |   await page.getByRole('button', { name: 'Save layout', exact: true }).click();
  94  |   await expect(page.getByText('Layout changes are not saved yet')).not.toBeVisible();
  95  |   await page.getByLabel(`Pin ${tableTitle}`, { exact: true }).click();
  96  |   await expect(page.getByLabel(`Unpin ${tableTitle}`, { exact: true })).toBeVisible();
  97  |   await page.getByRole('button', { name: 'Finish customizing', exact: true }).click();
  98  |   const pinned = await state(request);
  99  |   const storedLayouts = pinned.spec.views.find(v => v.id === view.id)!.layouts;
  100 |   await page.goto('about:blank');
  101 |   const queued = await request.post('/api/workspace/commands', { headers, data: { text: 'Focus again while browser is closed', view_id: view.id, base_version: pinned.version } });
  102 |   expect(queued.status()).toBe(200);
  103 |   const { id } = await queued.json();
  104 |   await expect.poll(async () => (await (await request.get('/api/workspace/jobs', { headers })).json()).items.find((job: { id: string }) => job.id === id)?.status).toBe('succeeded');
  105 |   const saved = await state(request);
  106 |   expect(saved.spec.widgets[tableId].pinned).toBe(true);
  107 |   expect(saved.spec.views.find(v => v.id === view.id)!.layouts).toEqual(storedLayouts);
  108 |   await page.goto('/leads');
  109 |   await page.getByRole('button', { name: 'Agent-organized leads', exact: true }).click();
  110 |   await expect(page.getByLabel(`Unpin ${tableTitle}`, { exact: true })).toBeVisible();
  111 |   expect(errors).toEqual([]);
  112 | });
  113 | 
  114 | test('typed fields, confirmed human corrections and exact human source navigation', async ({ page, request }, info) => {
  115 |   await reset(request); await login(page);
  116 |   const fieldName = `Expected value ${info.project.name.includes('desktop') ? 'desktop' : 'mobile'}`;
  117 |   await more(page, 'Custom field');
  118 |   const field = page.getByRole('dialog', { name: 'Create a custom lead field' });
  119 |   await field.getByLabel('Field name').fill(fieldName);
  120 |   await field.getByLabel('Value type').selectOption('number');
  121 |   await field.getByRole('button', { name: 'Create field', exact: true }).click();
  122 |   await expect(field).not.toBeVisible();
  123 |   await page.locator('.lead-name').filter({ hasText: 'Fictional Atlas' }).click();
  124 |   const detail = page.getByRole('dialog', { name: 'Fictional Atlas', exact: true });
  125 |   await detail.getByRole('button', { name: 'Custom fields', exact: true }).click();
  126 |   const row = detail.locator('.field-value').filter({ hasText: fieldName });
  127 |   await expect(row.locator('input')).toHaveValue('');
  128 |   await row.locator('input').fill('12.5');
  129 |   await row.getByRole('button', { name: 'Save value' }).click();
  130 |   await detail.getByRole('button', { name: 'Notes & corrections' }).click();
  131 |   await detail.getByLabel('New note').fill('Confirmed human correction: procurement does not need a separate review.');
  132 |   await detail.getByRole('combobox', { name: 'Topic', exact: true }).selectOption('procurement');
  133 |   await detail.getByLabel('Criterion answer').selectOption('no');
  134 |   await detail.getByLabel('This is a confirmed human correction').check();
  135 |   await detail.getByRole('button', { name: 'Save human note' }).click();
  136 |   await expect(detail.locator('.human-note')).toContainText(['Confirmed human correction: procurement']);
  137 |   const records: RecordPage = await (await request.post('/api/workspace/query', { headers, data: { view_id: 'all', query: { scope: 'real', search: 'Fictional Atlas' }, page_size: 25 } })).json();
  138 |   const leadId = records.items[0].id;
  139 |   await expect.poll(async () => {
  140 |     const value: Detail = await (await request.get(`/api/workspace/leads/${leadId}`, { headers })).json();
  141 |     return !value.stale && value.assessment?.data.human_facts?.some(f => f.topic === 'procurement' && f.value === 'no');
  142 |   }).toBe(true);
  143 |   await detail.getByRole('button', { name: 'Close Fictional Atlas' }).click();
  144 |   await page.locator('.lead-name').filter({ hasText: 'Fictional Atlas' }).click();
  145 |   await expect(detail.getByRole('heading', { name: 'Human-confirmed facts' })).toBeVisible();
  146 |   await detail.getByRole('button', { name: 'Human note', exact: true }).first().click();
  147 |   await expect(page.getByRole('dialog', { name: 'Human source note' })).toContainText('Confirmed human correction');
  148 |   await page.getByRole('button', { name: 'Close Human source note' }).click();
  149 |   await detail.getByRole('button', { name: 'Custom fields', exact: true }).click();
  150 |   await expect(detail.locator('.field-value').filter({ hasText: fieldName }).locator('input')).toHaveValue('12.5');
  151 | });
  152 | 
  153 | test('search, empty states and practice remain scoped; busy interaction holds updates', async ({ page, request }) => {
  154 |   await reset(request); await login(page);
  155 |   const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  156 |   await page.getByLabel('Search leads').fill('nobody-matches-this-unique-record');
  157 |   await expect(page.locator('.metric').first().locator('strong')).toHaveText('0');
  158 |   await expect(page.getByText('No leads match this view')).toBeVisible();
  159 |   const before = await state(request);
  160 |   const response = await request.post('/api/workspace/changes', { headers, data: { base_version: before.version, reason: 'Independent operator version for UI hold test', operations: [{ op: 'edit_view', view_id: 'all', name: 'All leads' }] } });
  161 |   expect(response.status()).toBe(200);
  162 |   await page.getByRole('button', { name: 'Filters', exact: true }).click();
  163 |   await expect(page.getByRole('button', { name: 'Apply updates', exact: true })).toBeDisabled();
  164 |   await page.getByRole('button', { name: 'Close Search, filter & group' }).click();
  165 |   await page.getByRole('button', { name: 'Apply updates', exact: true }).click();
  166 |   await expect(page.getByLabel('Search leads')).toHaveValue('nobody-matches-this-unique-record');
  167 |   await page.getByLabel('Clear search').click();
  168 |   await page.getByRole('button', { name: 'Practice / demo', exact: true }).click();
  169 |   await expect(page.locator('.metric').first().locator('strong')).toHaveText('1');
  170 |   await expect(page.getByText('Practice-only sample').first()).toBeVisible();
```