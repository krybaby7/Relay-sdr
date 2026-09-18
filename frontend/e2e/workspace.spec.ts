import { test, expect } from './fixtures';
import type { APIRequestContext, Page } from '@playwright/test';
import type { Bootstrap, Detail, RecordPage } from '../src/types';

// Full production-route acceptance with a clearly labeled deterministic model.
const token = 'relay-browser-fixture-token-not-a-production-secret';
const headers = { Authorization: `Bearer ${token}` };

async function state(request: APIRequestContext): Promise<Bootstrap> {
  return (await request.get('/api/workspace', { headers })).json();
}
async function login(page: Page) {
  await page.addInitScript(value => {
    if (location.protocol === 'http:' && location.hostname === '127.0.0.1') sessionStorage.setItem('relay-token', value);
  }, token);
  await page.goto('/leads');
  await expect(page.locator('.leads-table')).toBeVisible();
}
async function reset(request: APIRequestContext) {
  const boot = await state(request);
  const response = await request.post('/api/workspace/restore', { headers, data: { base_version: boot.version, target_version: 2 } });
  expect(response.ok()).toBeTruthy();
}
async function more(page: Page, name: string) {
  await page.getByLabel('More workspace options').click();
  await page.getByRole('button', { name, exact: true }).click();
}

test('real rendered workspace loads, navigates and exposes source evidence', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/leads');
  await page.getByLabel('Workspace token').fill(token);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  await expect(page.getByRole('button', { name: 'All leads', exact: true })).toBeVisible();
  await expect(page.locator('.lead-name').filter({ hasText: 'Fictional Acme' })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2)).toBe(false);
  await page.screenshot({ path: `test-results/${info.project.name}-workspace.png`, fullPage: true });
  await page.locator('.lead-name').filter({ hasText: 'Fictional Acme' }).click();
  const detail = page.getByRole('dialog', { name: 'Fictional Acme', exact: true });
  await expect(detail.getByRole('heading', { name: 'Why this assessment?' })).toBeVisible();
  await detail.getByRole('button', { name: 'View source', exact: true }).first().click();
  const call = page.getByRole('dialog', { name: 'Call evidence', exact: true });
  await expect(call.locator('.source-highlight')).toBeVisible();
  await expect(call.locator('.transcript')).toContainText('follow-up work.');
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2)).toBe(false);
  await page.screenshot({ path: `test-results/${info.project.name}-evidence.png`, fullPage: true });
  await call.getByRole('button', { name: 'Close Call evidence' }).click();
  await detail.getByRole('button', { name: 'All calls', exact: true }).click();
  await expect(detail.locator('.call-history-row')).toHaveCount(25);
  await detail.getByRole('button', { name: 'Next page' }).click();
  await expect(detail.getByText('Page 2', { exact: true })).toBeVisible();
  await detail.getByRole('button', { name: 'Notes & corrections' }).click();
  await expect(detail.locator('.human-note')).toHaveCount(25);
  await detail.getByRole('button', { name: 'Next page' }).click();
  await expect(detail.locator('.human-note')).toHaveCount(5);
  await detail.getByRole('button', { name: 'Close Fictional Acme' }).click();
  await expect(page.locator('body')).not.toHaveJSProperty('scrollWidth', 0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2)).toBe(false);
  expect(errors).toEqual([]);
});

test('manual views, actual responsive resize, pins, model edits and reload share persisted state', async ({ page, request }, info) => {
  await reset(request); await login(page);
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.getByRole('button', { name: 'Create saved view', exact: true }).click();
  const create = page.getByRole('dialog', { name: 'Create a saved view', exact: true });
  await create.getByLabel('View name').fill(`Canvas ${info.project.name}`);
  await create.getByRole('button', { name: 'Save view', exact: true }).click();
  await expect(create).not.toBeVisible();
  await page.getByLabel('Workspace instruction').fill('Focus the workspace on evidence');
  await page.getByRole('button', { name: 'Organize', exact: true }).click();
  await expect(page.locator('.job-status')).toContainText('succeeded');
  await page.getByLabel('Search leads').focus();
  await page.getByRole('button', { name: 'Apply updates', exact: true }).click();
  // View accessible names remain stable as matching counts change.
  await expect(page.getByRole('button', { name: 'Agent-organized leads', exact: true })).toBeVisible();
  const current = await state(request);
  const view = current.spec.views.find(v => v.name === 'Agent-organized leads')!;
  const tableId = view.widgets.find(id => current.spec.widgets[id].kind === 'LeadsTable')!;
  const tableTitle = current.spec.widgets[tableId].title;
  await page.getByRole('button', { name: 'Customize canvas', exact: true }).click();
  if (info.project.name.includes('desktop')) {
    const handle = page.locator(`[data-widget-id="${tableId}"] .react-resizable-handle`).last();
    await handle.scrollIntoViewIfNeeded(); const box = await handle.boundingBox();
    expect(box).not.toBeNull();
    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await page.mouse.down();
    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2 + 44, { steps: 10 });
    await page.mouse.up();
  } else {
    await page.getByRole('button', { name: `Taller ${tableTitle}`, exact: true }).click();
  }
  await expect(page.getByText('Layout changes are not saved yet')).toBeVisible();
  await page.getByRole('button', { name: 'Save layout', exact: true }).click();
  await expect(page.getByText('Layout changes are not saved yet')).not.toBeVisible();
  await page.getByLabel(`Pin ${tableTitle}`, { exact: true }).click();
  await expect(page.getByLabel(`Unpin ${tableTitle}`, { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Finish customizing', exact: true }).click();
  const pinned = await state(request);
  const storedLayouts = pinned.spec.views.find(v => v.id === view.id)!.layouts;
  await page.goto('about:blank');
  const queued = await request.post('/api/workspace/commands', { headers, data: { text: 'Focus again while browser is closed', view_id: view.id, base_version: pinned.version } });
  expect(queued.status()).toBe(200);
  const { id } = await queued.json();
  await expect.poll(async () => (await (await request.get('/api/workspace/jobs', { headers })).json()).items.find((job: { id: string }) => job.id === id)?.status).toBe('succeeded');
  const saved = await state(request);
  expect(saved.spec.widgets[tableId].pinned).toBe(true);
  expect(saved.spec.views.find(v => v.id === view.id)!.layouts).toEqual(storedLayouts);
  await page.goto('/leads');
  await page.getByRole('button', { name: 'Agent-organized leads', exact: true }).click();
  await expect(page.getByLabel(`Unpin ${tableTitle}`, { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('typed fields, confirmed human corrections and exact human source navigation', async ({ page, request }, info) => {
  await reset(request); await login(page);
  const fieldName = `Expected value ${info.project.name.includes('desktop') ? 'desktop' : 'mobile'}`;
  await more(page, 'Custom field');
  const field = page.getByRole('dialog', { name: 'Create a custom lead field' });
  await field.getByLabel('Field name').fill(fieldName);
  await field.getByLabel('Value type').selectOption('number');
  await field.getByRole('button', { name: 'Create field', exact: true }).click();
  await expect(field).not.toBeVisible();
  await page.locator('.lead-name').filter({ hasText: 'Fictional Atlas' }).click();
  const detail = page.getByRole('dialog', { name: 'Fictional Atlas', exact: true });
  await detail.getByRole('button', { name: 'Custom fields', exact: true }).click();
  const row = detail.locator('.field-value').filter({ hasText: fieldName });
  await expect(row.locator('input')).toHaveValue('');
  await row.locator('input').fill('12.5');
  await row.getByRole('button', { name: 'Save value' }).click();
  await detail.getByRole('button', { name: 'Notes & corrections' }).click();
  await detail.getByLabel('New note').fill('Confirmed human correction: procurement does not need a separate review.');
  await detail.getByRole('combobox', { name: 'Topic', exact: true }).selectOption('procurement');
  await detail.getByLabel('Criterion answer').selectOption('no');
  await detail.getByLabel('This is a confirmed human correction').check();
  await detail.getByRole('button', { name: 'Save human note' }).click();
  await expect(detail.locator('.human-note')).toContainText(['Confirmed human correction: procurement']);
  const records: RecordPage = await (await request.post('/api/workspace/query', { headers, data: { view_id: 'all', query: { scope: 'real', search: 'Fictional Atlas' }, page_size: 25 } })).json();
  const leadId = records.items[0].id;
  await expect.poll(async () => {
    const value: Detail = await (await request.get(`/api/workspace/leads/${leadId}`, { headers })).json();
    return !value.stale && value.assessment?.data.human_facts?.some(f => f.topic === 'procurement' && f.value === 'no');
  }).toBe(true);
  await detail.getByRole('button', { name: 'Close Fictional Atlas' }).click();
  await page.locator('.lead-name').filter({ hasText: 'Fictional Atlas' }).click();
  await expect(detail.getByRole('heading', { name: 'Human-confirmed facts' })).toBeVisible();
  await detail.getByRole('button', { name: 'Human note', exact: true }).first().click();
  await expect(page.getByRole('dialog', { name: 'Human source note' })).toContainText('Confirmed human correction');
  await page.getByRole('button', { name: 'Close Human source note' }).click();
  await detail.getByRole('button', { name: 'Custom fields', exact: true }).click();
  await expect(detail.locator('.field-value').filter({ hasText: fieldName }).locator('input')).toHaveValue('12.5');
});

test('search, empty states and practice remain scoped; busy interaction holds updates', async ({ page, request }) => {
  await reset(request); await login(page);
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.getByLabel('Search leads').fill('nobody-matches-this-unique-record');
  await expect(page.locator('.metric').first().locator('strong')).toHaveText('0');
  await expect(page.getByText('No leads match this view')).toBeVisible();
  const before = await state(request);
  const response = await request.post('/api/workspace/changes', { headers, data: { base_version: before.version, reason: 'Independent operator version for UI hold test', operations: [{ op: 'edit_view', view_id: 'all', name: 'All leads' }] } });
  expect(response.status()).toBe(200);
  await page.getByRole('button', { name: 'Filters', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Apply updates', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Close Search, filter & group' }).click();
  await page.getByRole('button', { name: 'Apply updates', exact: true }).click();
  await expect(page.getByLabel('Search leads')).toHaveValue('nobody-matches-this-unique-record');
  await page.getByLabel('Clear search').click();
  await page.getByRole('button', { name: 'Practice / demo', exact: true }).click();
  await expect(page.locator('.metric').first().locator('strong')).toHaveText('1');
  await expect(page.getByText('Practice-only sample').first()).toBeVisible();
  await expect(page.locator('.lead-name').filter({ hasText: 'Fictional Acme' })).toHaveCount(0);
  await page.getByRole('button', { name: 'All leads', exact: true }).click();
  await expect(page.locator('.metric').first().locator('strong')).toHaveText('31');
  expect(errors).toEqual([]);
});
