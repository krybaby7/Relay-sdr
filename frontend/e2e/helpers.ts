import { expect, type APIRequestContext, type Page } from '@playwright/test';
import type { Bootstrap } from '../src/types';
export const token = 'relay-browser-fixture-token-not-a-production-secret';
export const headers = { Authorization: `Bearer ${token}` };
export async function state(request: APIRequestContext): Promise<Bootstrap> {
  const response = await request.get('/api/workspace', { headers });
  expect(response.ok()).toBeTruthy();
  return response.json();
}
export async function authenticate(page: Page) {
  await page.addInitScript(value => {
    if (location.protocol === 'http:' && location.hostname === '127.0.0.1') sessionStorage.setItem('relay-token', value);
  }, token);
}
export async function login(page: Page) {
  await authenticate(page); await page.goto('/leads');
  await expect(page.locator('.leads-table')).toBeVisible();
}
export async function more(page: Page, name: string) {
  if (!await page.locator('.more-menu').getAttribute('open').then(value => value !== null)) {
    await page.getByLabel('More workspace options').click();
  }
  await page.getByRole('button', { name, exact: true }).click();
  // Close the originating menu without clicking through the modal backdrop.
  await page.locator('.more-menu').evaluate((element: HTMLDetailsElement) => { element.open = false; });
}
export async function createView(page: Page, name: string, emphasis = 'overview') {
  await page.getByRole('button', { name: 'Create saved view', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Create a saved view', exact: true });
  await dialog.getByLabel('View name').fill(name);
  await dialog.getByLabel('Lead detail emphasis').selectOption(emphasis);
  await dialog.getByRole('button', { name: 'Save view', exact: true }).click();
  await expect(dialog).not.toBeVisible();
}
export async function organize(page: Page, text: string, status = 'succeeded') {
  const response = page.waitForResponse(r => r.url().endsWith('/api/workspace/commands') && r.request().method() === 'POST');
  await page.getByLabel('Workspace instruction').fill(text);
  await page.getByRole('button', { name: 'Organize', exact: true }).click();
  const queued = await response; expect(queued.status()).toBe(200);
  const job = await queued.json() as {id:string};
  await expect.poll(async () => {
    const runs = await page.request.get('/api/workspace/jobs?limit=100', {headers});
    const data = await runs.json() as {items:{id:string;status:string}[]};
    return data.items.find(item => item.id === job.id)?.status;
  }).toBe(status.replaceAll(' ', '_'));
  // Hold automatic idle application, then deliberately accept the saved update.
  await page.getByLabel('Search leads').focus();
  await expect(page.locator('.job-status')).toContainText(status);
  await expect(page.getByRole('button', { name: 'Apply updates', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Apply updates', exact: true }).click();
}
