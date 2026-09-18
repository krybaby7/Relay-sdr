# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: workspace.spec.ts >> typed fields, confirmed human corrections and exact human source navigation
- Location: e2e/workspace.spec.ts:114:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.leads-table')
Expected: visible
Timeout: 8000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 8000ms
  - waiting for locator('.leads-table')

```

```yaml
- complementary:
  - link "r relay SDR":
    - /url: /#overview
  - navigation "Main navigation":
    - link "Leads":
      - /url: /leads
    - link "Voice lab":
      - /url: /#lab
- main:
  - text: Workspace /
  - strong: Leads
  - button "Workspace agent connected"
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
    - button "Submit internal organization command" [disabled]
    - button "Callbacks due today ↗"
    - button "Procurement blockers ↗"
    - button "Where I can unblock progress ↗"
  - alert:
    - text: Too many requests. Try again in a minute. The last valid saved workspace is retained.
    - button "Dismiss error"
  - navigation "Saved views":
    - button "Today"
    - button "All leads"
    - button "Highest potential"
    - button "Follow-ups"
    - button "Needs qualification"
    - button "Needs review"
    - button "Do not call"
    - button "Practice / demo"
    - button "Create saved view"
  - paragraph: Every real lead, including uncalled, unassessed, suppressed and failed-analysis records.
  - button "View definition"
  - region "Evidence-backed overview":
    - text: Leads in this view
    - strong: —
    - text: All matching records, not just the page Promising opportunities
    - strong: —
    - text: Supported need and product fit Commitments due
    - strong: —
    - text: Due today or overdue; no outreach performed Needs review
    - strong: —
    - text: Coverage, freshness or conflicting evidence
  - textbox "Search leads":
    - /placeholder: Search names, companies or phone numbers
  - button "Filters"
  - button "Customize canvas"
  - group: •••
  - text: Sources stay separate from assessments. Assessments stay separate from layout. Saved workspace v11 · UTC
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
> 15  |   await expect(page.locator('.leads-table')).toBeVisible();
      |                                              ^ Error: expect(locator).toBeVisible() failed
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
```