# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: workspace.spec.ts >> manual views, actual responsive resize, pins, model edits and reload share persisted state
- Location: e2e/workspace.spec.ts:61:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('button', { name: 'Agent-organized leads', exact: true })
Expected: visible
Timeout: 8000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 8000ms
  - waiting for getByRole('button', { name: 'Agent-organized leads', exact: true })

```

```yaml
- complementary:
  - link "r relay SDR":
    - /url: /#overview
  - text: WORKSPACE
  - navigation "Main navigation":
    - link "Overview":
      - /url: /#overview
    - link "Leads":
      - /url: /leads
    - link "Voice lab":
      - /url: /#lab
    - link "Playbook":
      - /url: /#playbook
    - link "Calls":
      - /url: /#calls
    - link "Connections":
      - /url: /#connections
  - text: R
  - strong: Private workspace
  - text: Local · single operator
  - button "Lock workspace"
- main:
  - text: Workspace /
  - strong: Leads
  - button "Workspace agent connected"
  - text: v5
  - paragraph: VERIFICATION DATASET — All people, call content and assessments shown here are fictional fixtures. No calls were placed.
  - text: YOUR PIPELINE, IN CONTEXT
  - heading "Leads workspace." [level=1]
  - paragraph: Evidence you can trace. Priorities you can act on.
  - button "Import CSV"
  - button "Add lead"
  - region "Workspace orchestrator":
    - strong: Organize with your workspace agent
    - text: Changes are saved, versioned and reversible. No outreach permissions. Organization mode
    - combobox "Organization mode":
      - option "Adaptive" [selected]
      - option "Suggest"
      - option "Manual"
    - textbox "Workspace instruction":
      - /placeholder: Show leads awaiting a proposal, grouped by priority…
    - button "Organize" [disabled]
    - button "Callbacks due today ↗"
    - button "Procurement blockers ↗"
    - button "Where I can unblock progress ↗"
    - status:
      - text: succeeded · Workspace applied. Saved changes will appear when it is safe to apply them.
      - button "Run details"
  - status:
    - text: Created view “Canvas chromium-desktop”
    - button "Dismiss notification"
  - navigation "Saved views":
    - button "Today"
    - button "All leads"
    - button "Highest potential"
    - button "Follow-ups"
    - button "Needs qualification"
    - button "Needs review"
    - button "Do not call"
    - button "Practice / demo"
    - button "Agent-organized leads 31"
    - button "Create saved view"
  - paragraph: A custom saved query. Filters and ordering are visible in Customize view.
  - button "View definition"
  - region "Evidence-backed overview":
    - text: Leads in this view
    - strong: "31"
    - text: All matching records, not just the page Promising opportunities
    - strong: "6"
    - text: Supported need and product fit Commitments due
    - strong: "5"
    - text: Due today or overdue; no outreach performed Needs review
    - strong: "6"
    - text: Coverage, freshness or conflicting evidence
  - textbox "Search leads":
    - /placeholder: Search names, companies or phone numbers
  - button "Filters"
  - button "Customize canvas"
  - group: •••
  - region "Lead directory":
    - heading "Lead directory" [level=2]
    - button "Pin Lead directory"
    - table:
      - rowgroup:
        - row "Select name company potential priority ↓ confidence eligibility":
          - columnheader "Select"
          - columnheader "name":
            - button "name"
          - columnheader "company":
            - button "company"
          - columnheader "potential":
            - button "potential"
          - columnheader "priority ↓":
            - button "priority ↓"
          - columnheader "confidence":
            - button "confidence"
          - columnheader "eligibility":
            - button "eligibility"
      - rowgroup:
        - row "Select Fictional Atlas FI Fictional Atlas Atlas Example Ltd strong overdue partial permission recorded":
          - cell "Select Fictional Atlas":
            - checkbox "Select Fictional Atlas"
          - cell "FI Fictional Atlas":
            - button "FI Fictional Atlas"
          - cell "Atlas Example Ltd"
          - cell "strong"
          - cell "overdue"
          - cell "partial"
          - cell "permission recorded"
        - row "Select Fictional Acme FI Fictional Acme Acme Example Ltd strong overdue partial permission recorded":
          - cell "Select Fictional Acme":
            - checkbox "Select Fictional Acme"
          - cell "FI Fictional Acme":
            - button "FI Fictional Acme"
          - cell "Acme Example Ltd"
          - cell "strong"
          - cell "overdue"
          - cell "partial"
          - cell "permission recorded"
        - row "Select Fictional Cedar FI Fictional Cedar Cedar Example Ltd strong overdue partial permission recorded":
          - cell "Select Fictional Cedar":
            - checkbox "Select Fictional Cedar"
          - cell "FI Fictional Cedar":
            - button "FI Fictional Cedar"
          - cell "Cedar Example Ltd"
          - cell "strong"
          - cell "overdue"
          - cell "partial"
          - cell "permission recorded"
        - row "Select Fictional Birch FI Fictional Birch Birch Example Ltd strong overdue partial permission recorded":
          - cell "Select Fictional Birch":
            - checkbox "Select Fictional Birch"
          - cell "FI Fictional Birch":
            - button "FI Fictional Birch"
          - cell "Birch Example Ltd"
          - cell "strong"
          - cell "overdue"
          - cell "partial"
          - cell "permission recorded"
        - row "Select Fictional Delta FI Fictional Delta Delta Example Ltd strong overdue partial permission recorded":
          - cell "Select Fictional Delta":
            - checkbox "Select Fictional Delta"
          - cell "FI Fictional Delta":
            - button "FI Fictional Delta"
          - cell "Delta Example Ltd"
          - cell "strong"
          - cell "overdue"
          - cell "partial"
          - cell "permission recorded"
        - row "Select Uncalled fixture 35 UN Uncalled fixture 35 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 35":
            - checkbox "Select Uncalled fixture 35"
          - cell "UN Uncalled fixture 35":
            - button "UN Uncalled fixture 35"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 44 UN Uncalled fixture 44 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 44":
            - checkbox "Select Uncalled fixture 44"
          - cell "UN Uncalled fixture 44":
            - button "UN Uncalled fixture 44"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 41 UN Uncalled fixture 41 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 41":
            - checkbox "Select Uncalled fixture 41"
          - cell "UN Uncalled fixture 41":
            - button "UN Uncalled fixture 41"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 23 UN Uncalled fixture 23 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 23":
            - checkbox "Select Uncalled fixture 23"
          - cell "UN Uncalled fixture 23":
            - button "UN Uncalled fixture 23"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 28 UN Uncalled fixture 28 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 28":
            - checkbox "Select Uncalled fixture 28"
          - cell "UN Uncalled fixture 28":
            - button "UN Uncalled fixture 28"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 38 UN Uncalled fixture 38 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 38":
            - checkbox "Select Uncalled fixture 38"
          - cell "UN Uncalled fixture 38":
            - button "UN Uncalled fixture 38"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 32 UN Uncalled fixture 32 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 32":
            - checkbox "Select Uncalled fixture 32"
          - cell "UN Uncalled fixture 32":
            - button "UN Uncalled fixture 32"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 26 UN Uncalled fixture 26 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 26":
            - checkbox "Select Uncalled fixture 26"
          - cell "UN Uncalled fixture 26":
            - button "UN Uncalled fixture 26"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 21 UN Uncalled fixture 21 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 21":
            - checkbox "Select Uncalled fixture 21"
          - cell "UN Uncalled fixture 21":
            - button "UN Uncalled fixture 21"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 22 UN Uncalled fixture 22 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 22":
            - checkbox "Select Uncalled fixture 22"
          - cell "UN Uncalled fixture 22":
            - button "UN Uncalled fixture 22"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 33 UN Uncalled fixture 33 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 33":
            - checkbox "Select Uncalled fixture 33"
          - cell "UN Uncalled fixture 33":
            - button "UN Uncalled fixture 33"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 30 UN Uncalled fixture 30 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 30":
            - checkbox "Select Uncalled fixture 30"
          - cell "UN Uncalled fixture 30":
            - button "UN Uncalled fixture 30"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 20 UN Uncalled fixture 20 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 20":
            - checkbox "Select Uncalled fixture 20"
          - cell "UN Uncalled fixture 20":
            - button "UN Uncalled fixture 20"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 24 UN Uncalled fixture 24 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 24":
            - checkbox "Select Uncalled fixture 24"
          - cell "UN Uncalled fixture 24":
            - button "UN Uncalled fixture 24"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 43 UN Uncalled fixture 43 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 43":
            - checkbox "Select Uncalled fixture 43"
          - cell "UN Uncalled fixture 43":
            - button "UN Uncalled fixture 43"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 25 UN Uncalled fixture 25 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 25":
            - checkbox "Select Uncalled fixture 25"
          - cell "UN Uncalled fixture 25":
            - button "UN Uncalled fixture 25"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 34 UN Uncalled fixture 34 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 34":
            - checkbox "Select Uncalled fixture 34"
          - cell "UN Uncalled fixture 34":
            - button "UN Uncalled fixture 34"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 39 UN Uncalled fixture 39 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 39":
            - checkbox "Select Uncalled fixture 39"
          - cell "UN Uncalled fixture 39":
            - button "UN Uncalled fixture 39"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 36 UN Uncalled fixture 36 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 36":
            - checkbox "Select Uncalled fixture 36"
          - cell "UN Uncalled fixture 36":
            - button "UN Uncalled fixture 36"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
        - row "Select Uncalled fixture 27 UN Uncalled fixture 27 Fictional Northwind unassessed none unknown permission missing":
          - cell "Select Uncalled fixture 27":
            - checkbox "Select Uncalled fixture 27"
          - cell "UN Uncalled fixture 27":
            - button "UN Uncalled fixture 27"
          - cell "Fictional Northwind"
          - cell "unassessed"
          - cell "none"
          - cell "unknown"
          - cell "permission missing"
    - text: 1–25 of 31
    - button "Previous" [disabled]
    - button "Next"
  - region "Pipeline by stage":
    - heading "Pipeline by stage" [level=2]
    - button "Pin Pipeline by stage"
    - heading "unassessed 25" [level=3]
    - button "Uncalled fixture 35 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 35
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 44 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 44
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 41 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 41
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 23 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 23
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 28 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 28
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 38 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 38
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 32 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 32
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 26 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 26
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 21 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 21
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 22 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 22
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 33 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 33
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 30 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 30
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 20 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 20
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 24 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 24
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 43 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 43
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 25 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 25
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 34 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 34
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 39 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 39
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 36 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 36
      - text: Fictional Northwind unassessed none
    - button "Uncalled fixture 27 Fictional Northwind unassessed none":
      - strong: Uncalled fixture 27
      - text: Fictional Northwind unassessed none
    - heading "qualification 0" [level=3]
    - heading "engaged 0" [level=3]
    - heading "proposal 6" [level=3]
    - button "Fictional Atlas Atlas Example Ltd strong overdue":
      - strong: Fictional Atlas
      - text: Atlas Example Ltd strong overdue
    - button "Fictional Acme Acme Example Ltd strong overdue":
      - strong: Fictional Acme
      - text: Acme Example Ltd strong overdue
    - button "Fictional Cedar Cedar Example Ltd strong overdue":
      - strong: Fictional Cedar
      - text: Cedar Example Ltd strong overdue
    - button "Fictional Birch Birch Example Ltd strong overdue":
      - strong: Fictional Birch
      - text: Birch Example Ltd strong overdue
    - button "Fictional Delta Delta Example Ltd strong overdue":
      - strong: Fictional Delta
      - text: Delta Example Ltd strong overdue
    - heading "decision 0" [level=3]
    - paragraph: Stage counts cover this view. Cards show the current directory page; open a card to inspect its evidence.
  - region "Recent changes":
    - heading "Recent changes" [level=2]
    - button "Pin Recent changes"
    - paragraph: Workspace command run succeeded. system · Sep 17, 11:13 PM
    - paragraph: Deterministic fixture organization — not a live model response. agent · Sep 17, 11:13 PM
    - paragraph: Created view “Canvas chromium-desktop” human · Sep 17, 11:13 PM
    - paragraph: Restored workspace revision 2. Lead records retained. human · Sep 17, 11:13 PM
    - paragraph: Fictional fixture starts on all records. human · Sep 17, 11:13 PM
    - paragraph: Permanent do-not-call suppression applied. system · Sep 17, 11:13 PM
    - paragraph: Workspace analysis run succeeded. system · Sep 17, 11:13 PM
    - paragraph: "Assessment updated: strong. Source coverage 2/2 chunks. agent · Sep 17, 11:13 PM"
    - paragraph: Workspace analysis run succeeded. system · Sep 17, 11:13 PM
    - paragraph: "Assessment updated: strong. Source coverage 1/1 chunks. agent · Sep 17, 11:13 PM"
    - paragraph: Workspace analysis run succeeded. system · Sep 17, 11:13 PM
    - paragraph: "Assessment updated: strong. Source coverage 1/1 chunks. agent · Sep 17, 11:13 PM"
    - paragraph: Workspace analysis run succeeded. system · Sep 17, 11:13 PM
    - paragraph: "Assessment updated: strong. Source coverage 1/1 chunks. agent · Sep 17, 11:13 PM"
    - paragraph: Workspace analysis run succeeded. system · Sep 17, 11:13 PM
    - paragraph: "Assessment updated: strong. Source coverage 1/1 chunks. agent · Sep 17, 11:13 PM"
    - paragraph: Workspace analysis run succeeded. system · Sep 17, 11:13 PM
    - paragraph: "Assessment updated: strong. Source coverage 1/1 chunks. agent · Sep 17, 11:13 PM"
    - paragraph: Captured call lifecycle or outcome changed. system · Sep 17, 11:13 PM
    - paragraph: Captured call lifecycle or outcome changed. system · Sep 17, 11:13 PM
  - text: Sources stay separate from assessments. Assessments stay separate from layout. Saved workspace v5 · UTC
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
  70  |   await page.getByRole('button', { name: 'Organize', exact: true }).click();
  71  |   await expect(page.locator('.job-status')).toContainText('succeeded');
  72  |   await page.getByLabel('Search leads').focus();
  73  |   await page.getByRole('button', { name: 'Apply updates', exact: true }).click();
  74  |   // Known historical failure: active tab name included a trailing count, e.g. "Agent-organized leads 31".
> 75  |   await expect(page.getByRole('button', { name: 'Agent-organized leads', exact: true })).toBeVisible();
      |                                                                                          ^ Error: expect(locator).toBeVisible() failed
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
  171 |   await expect(page.locator('.lead-name').filter({ hasText: 'Fictional Acme' })).toHaveCount(0);
  172 |   await page.getByRole('button', { name: 'All leads', exact: true }).click();
  173 |   await expect(page.locator('.metric').first().locator('strong')).toHaveText('31');
  174 |   expect(errors).toEqual([]);
  175 | });
```