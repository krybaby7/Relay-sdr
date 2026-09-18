import { test, expect } from './fixtures';
import { authenticate, createView, headers, login, more, organize, state } from './helpers';
import type { Breakpoint } from '../src/types';

test.describe('complete shared-workspace acceptance', () => {
  // These are multi-command end-to-end scenarios, with no retries or skipped steps.
  test.setTimeout(90000);

  test('AI geometry, keyboard reorder, pointer drag/resize, pin and later AI edits persist', async ({ page, request }, info) => {
    await login(page);
    const name = `Shared geometry ${info.project.name}`;
    await createView(page, name, 'decision_process');
    const initial = await state(request);
    const view = initial.spec.views.find(v => v.name === name)!;
    expect(view.emphasis).toBe('decision_process');
    const table = view.widgets.find(id => initial.spec.widgets[id].kind === 'LeadsTable')!;
    const changes = view.widgets.find(id => initial.spec.widgets[id].kind === 'RecentChanges')!;
    await organize(page, 'Rearrange canvas');
    const planned = await state(request);
    const plan = planned.spec.views.find(v => v.id === view.id)!;
    for (const bp of ['lg','md','sm'] as Breakpoint[]) {
      expect(plan.layouts[bp]).not.toEqual(view.layouts[bp]);
      expect(plan.layouts[bp].find(g => g.i === changes)!.y).toBe(0);
    }
    const tablePanel = page.locator(`[data-widget-id="${table}"]`);
    const changesPanel = page.locator(`[data-widget-id="${changes}"]`);
    // Assert rendered geometry after the asynchronous refresh/transition, not
    // its intermediate animation frame. The saved-layout assertions stay above.
    await expect.poll(async () => {
      const changed = await changesPanel.boundingBox(), directory = await tablePanel.boundingBox();
      return changed && directory ? directory.y - changed.y : -1;
    }).toBeGreaterThan(0);
    await page.getByRole('button', { name: 'Customize canvas', exact: true }).click();
    // Exercise a real keyboard activation, not a direct state/API layout write.
    await page.getByRole('button', { name: 'Up Lead directory', exact: true }).focus();
    await page.keyboard.press('Enter');
    await page.getByRole('button', { name: 'Save layout', exact: true }).click();
    await expect(page.getByText('Layout changes are not saved yet')).not.toBeVisible();
    const reordered = await state(request);
    const bp: Breakpoint = info.project.name.includes('mobile') ? 'sm' : 'lg';
    const geometry = reordered.spec.views.find(v => v.id === view.id)!.layouts[bp];
    expect(geometry.find(g => g.i === table)!.y).toBeLessThan(geometry.find(g => g.i === changes)!.y);
    const height = geometry.find(g => g.i === table)!.h;
    if (info.project.name.includes('desktop')) {
      const handle = tablePanel.locator('.react-resizable-handle').last();
      await handle.scrollIntoViewIfNeeded(); const box = (await handle.boundingBox())!;
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2 + 44, { steps: 10 });
      await page.mouse.up();
    } else {
      await page.getByRole('button', { name: 'Taller Lead directory', exact: true }).click();
    }
    await page.getByRole('button', { name: 'Save layout', exact: true }).click();
    await expect(page.getByText('Layout changes are not saved yet')).not.toBeVisible();
    const resized = await state(request);
    expect(resized.spec.views.find(v => v.id === view.id)!.layouts[bp].find(g => g.i === table)!.h).toBeGreaterThan(height);
    await page.getByLabel('Pin Lead directory', { exact: true }).click();
    await expect(page.getByLabel('Unpin Lead directory', { exact: true })).toBeVisible();
    if (info.project.name.includes('desktop')) {
      const beforeDrag = await state(request);
      const layout = beforeDrag.spec.views.find(v => v.id === view.id)!.layouts.lg;
      const handle = changesPanel.locator('.widget-drag-handle');
      await handle.scrollIntoViewIfNeeded(); const box = (await handle.boundingBox())!;
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2 + 66, { steps: 12 });
      await page.mouse.up();
      await page.getByRole('button', { name: 'Save layout', exact: true }).click();
      await expect(page.getByText('Layout changes are not saved yet')).not.toBeVisible();
      const dragged = (await state(request)).spec.views.find(v => v.id === view.id)!.layouts.lg;
      expect(dragged.find(g => g.i === changes)!.y).toBeGreaterThan(layout.find(g => g.i === changes)!.y);
      expect(dragged.find(g => g.i === table)).toEqual(layout.find(g => g.i === table));
    }
    await page.getByRole('button', { name: 'Finish customizing', exact: true }).click();
    const pinned = await state(request);
    await organize(page, 'Adjust unpinned canvas');
    const after = await state(request);
    expect(after.spec.widgets[table]).toEqual(pinned.spec.widgets[table]);
    const finalView = after.spec.views.find(v => v.id === view.id)!;
    expect(finalView.widgets).toEqual(view.widgets);
    for (const breakpoint of ['lg','md','sm'] as Breakpoint[]) {
      const saved = pinned.spec.views.find(v => v.id === view.id)!.layouts[breakpoint];
      expect(finalView.layouts[breakpoint].find(g => g.i === table)).toEqual(saved.find(g => g.i === table));
      expect(finalView.layouts[breakpoint]).not.toEqual(saved);
    }
    await page.reload();
    await page.getByRole('button', { name, exact: true }).click();
    await expect(page.getByLabel('Unpin Lead directory', { exact: true })).toBeVisible();
    expect((await state(request)).spec.views.find(v => v.id === view.id)).toEqual(finalView);
    await page.screenshot({path: `test-results/${info.project.name}-shared-layout.png`, fullPage: true, animations: 'disabled'});
  });

  test('suggestions require approval; locked views reject agent and manual changes', async ({ page, request }) => {
    await login(page);
    await page.getByLabel('Organization mode', { exact: true }).selectOption('suggest');
    await expect.poll(async () => (await state(request)).spec.mode).toBe('suggest');
    const before = await state(request);
    await organize(page, 'Show leads awaiting a proposal, grouped by priority');
    const proposed = await state(request);
    expect(proposed.version).toBe(before.version);
    expect(proposed.spec.views.some(v => v.id === 'fixture_proposals')).toBe(false);
    expect(proposed.proposals).toHaveLength(1);
    await page.getByRole('button', { name: 'Review changes', exact: true }).click();
    const review = page.getByRole('dialog', { name: 'Review organization changes' });
    await expect(review.locator('pre')).toContainText('awaiting_proposal');
    await review.getByRole('button', { name: 'Approve saved change' }).click();
    await expect.poll(async () => (await state(request)).spec.views.some(v => v.id === 'fixture_proposals')).toBe(true);
    await review.getByRole('button', { name: 'Close Review organization changes' }).click();
    await page.getByRole('button', { name: 'Awaiting proposals', exact: true }).click();
    await expect(page.locator('.group-row').first()).toBeVisible();
    expect((await state(request)).spec.views.find(v => v.id === 'fixture_proposals')!.query.group).toBe('priority');
    await more(page, 'Lock view');
    const locked = await state(request);
    expect(locked.spec.views.find(v => v.id === 'fixture_proposals')!.locked).toBe(true);
    await page.getByRole('button', { name: 'Customize canvas', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Taller Lead directory', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Finish customizing', exact: true }).click();
    // The model tries a forbidden layout patch. The real worker rejects it;
    // no proposal or partial layout can escape server validation.
    await page.getByLabel('Workspace instruction').fill('Rearrange canvas');
    await page.getByRole('button', { name: 'Organize', exact: true }).click();
    await expect(page.locator('.job-status')).toContainText(/retry|failed/);
    const unchanged = await state(request);
    expect(unchanged.version).toBe(locked.version);
    expect(unchanged.spec).toEqual(locked.spec);
    expect(unchanged.proposals).toHaveLength(0);
    await more(page, 'Unlock view');
    await expect.poll(async () => (await state(request)).spec.views.find(v => v.id === 'fixture_proposals')!.locked).toBe(false);
  });

  test('columns, board-only pagination, history undo and reset retain records', async ({ page, request }, info) => {
    await login(page); await createView(page, 'Manual composition');
    await page.getByRole('button', { name: 'Customize canvas', exact: true }).click();
    await page.getByLabel('Configure Lead directory', { exact: true }).click();
    const editor = page.getByRole('dialog', { name: 'Configure widget' });
    await editor.getByLabel('Title', { exact: true }).fill('Configured directory');
    await editor.getByLabel('company column width').fill('230');
    await editor.getByLabel('Move company left', { exact: true }).click();
    await editor.getByLabel('confidence', { exact: true }).uncheck();
    await editor.getByRole('button', { name: 'Save widget', exact: true }).click();
    await expect(editor).not.toBeVisible();
    const columns = await state(request);
    const view = columns.spec.views.find(v => v.name === 'Manual composition')!;
    const tableId = view.widgets.find(id => columns.spec.widgets[id].kind === 'LeadsTable')!;
    const table = columns.spec.widgets[tableId];
    expect(table.columns[0]).toMatchObject({field:'company', width:230, visible:true});
    expect(table.columns.find(c => c.field === 'confidence')!.visible).toBe(false);
    await expect(page.locator('.leads-table th').nth(1)).toContainText('company');
    await expect(page.locator('.leads-table thead')).not.toContainText('confidence');
    await page.getByRole('button', { name: 'Remove Configured directory', exact: true }).click();
    await expect(page.locator('.leads-table')).toHaveCount(0);
    await page.getByRole('button', { name: 'Finish customizing', exact: true }).click();
    const board = page.locator('.board').locator('..');
    await expect(board.locator('.board-card')).toHaveCount(25);
    await board.getByRole('button', { name: 'Next', exact: true }).click();
    await expect(board.locator('.board-card')).toHaveCount(6);
    await expect(board.getByLabel('Lead directory pages')).toContainText('26–31 of 31');
    await board.locator('.board-card').first().click();
    const detail = page.locator('dialog[open]');
    await expect(detail).toContainText('All calls');
    await page.keyboard.press('Escape');
    await more(page, 'History / undo / reset');
    await page.getByRole('button', { name: 'Undo last workspace change', exact: true }).click();
    await expect(page.locator('.leads-table')).toBeVisible();
    expect((await state(request)).spec.widgets[tableId]).toEqual(table);
    await more(page, 'History / undo / reset');
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Reset layout', exact: true }).click();
    const reset = await state(request);
    expect(reset.spec.views.some(v => v.id === view.id)).toBe(false);
    const records = await request.post('/api/workspace/query', { headers, data: {view_id:'all'} });
    expect((await records.json()).total).toBe(31);
    await page.getByRole('button', {name:'All leads', exact:true}).click();
    await page.screenshot({path: `test-results/${info.project.name}-reset.png`, fullPage:true,animations:'disabled'});
  });

  test('initial read failure is retryable; model outage leaves manual editing available', async ({ page, request }) => {
    const original = await state(request);
    await authenticate(page);
    await page.route('**/api/workspace', route => route.fulfill({status:503, contentType:'application/json', body:JSON.stringify({detail:'Fictional temporary workspace read failure.'})}), {times:1});
    await page.goto('/leads');
    await expect(page.getByRole('alert')).toContainText('temporary workspace read failure');
    await page.getByRole('button', {name:'Retry opening workspace'}).click();
    await expect(page.locator('.leads-table')).toBeVisible();
    expect((await state(request)).spec).toEqual(original.spec);
    await organize(page, 'Provider unavailable', 'waiting configuration');
    expect((await state(request)).spec).toEqual(original.spec);
    await createView(page, 'Manual during outage');
    await page.getByLabel('Search leads').fill('Acme');
    await expect(page.locator('.lead-name')).toHaveCount(1);
    await page.getByLabel('Pin Lead directory', {exact:true}).click();
    await expect(page.getByLabel('Search leads')).toHaveValue('Acme');
    await expect(page.locator('.lead-name')).toHaveCount(1);
    await page.reload();
    await page.getByRole('button', {name:'Manual during outage',exact:true}).click();
    await expect(page.getByLabel('Unpin Lead directory', {exact:true})).toBeVisible();
  });

  test('competing edits fail atomically and selection evidence clears across practice', async ({ page, request }) => {
    await login(page); await createView(page, 'Conflict check');
    await page.getByRole('button', {name:'Customize canvas',exact:true}).click();
    await page.getByLabel('Configure Lead directory', {exact:true}).click();
    const editor = page.getByRole('dialog', {name:'Configure widget'});
    await editor.getByLabel('Title', {exact:true}).fill('Must not overwrite');
    const before = await state(request);
    const view = before.spec.views.find(v => v.name === 'Conflict check')!;
    const external = await request.post('/api/workspace/changes', {headers, data:{base_version:before.version, reason:'Second operator edit in isolated fixture', operations:[{op:'edit_view',view_id:view.id,name:'Newer operator name'}]}});
    expect(external.status()).toBe(200);
    await editor.getByRole('button', {name:'Save widget',exact:true}).click();
    await expect(editor.getByRole('alert')).toContainText('Workspace changed');
    expect((await state(request)).spec.widgets).toEqual(before.spec.widgets);
    await editor.getByRole('button', {name:'Cancel',exact:true}).click();
    await page.getByRole('button', {name:'Finish customizing',exact:true}).click();
    await page.getByLabel('Search leads').focus();
    await page.getByRole('button', {name:'Apply updates',exact:true}).click();
    await expect(page.getByRole('button', {name:'Newer operator name',exact:true})).toBeVisible();
    await page.getByRole('button', {name:'Highest potential',exact:true}).click();
    await page.locator('.lead-name').filter({hasText:'Fictional Acme'}).click();
    const leadDialog = page.getByRole('dialog', {name:'Fictional Acme',exact:true});
    await expect(leadDialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(leadDialog).not.toBeVisible();
    await expect(page.locator('.evidence-widget')).toContainText('manual follow-up');
    await page.getByRole('button', {name:'Practice / demo',exact:true}).click();
    await page.getByRole('button', {name:'Highest potential',exact:true}).click();
    await expect(page.locator('.evidence-widget')).toHaveCount(0);
    await expect(page.getByText('Select a lead to inspect the reasons')).toBeVisible();
  });
  test('all application sections and tab locking remain reachable on small screens', async ({ page }, info) => {
    await login(page);
    const mobile = info.project.name.includes('mobile');
    if (mobile) await page.getByLabel('Open navigation', {exact:true}).click();
    const navigation = page.getByRole('navigation', {name: mobile ? 'Mobile navigation' : 'Main navigation', exact:true});
    for (const name of ['Overview','Leads','Voice lab','Playbook','Calls','Connections']) {
      await expect(navigation.getByRole('link', {name,exact:true})).toBeVisible();
    }
    await navigation.getByRole('link', {name:'Connections',exact:true}).click();
    await expect(page.getByRole('heading', {name:'Bring your tools. Keep the boundaries clear.'})).toBeVisible();
    await page.goto('/leads');
    await expect(page.locator('.leads-table')).toBeVisible();
    if (mobile) await page.getByLabel('Open navigation', {exact:true}).click();
    await page.getByRole('button', {name:'Lock workspace',exact:true}).click();
    await expect(page.getByRole('heading', {name:'Your private sales workspace',exact:true})).toBeVisible();
    expect(await page.evaluate(() => sessionStorage.getItem('relay-token'))).toBeNull();
    await expect(page.locator('.leads-table')).toHaveCount(0);
  });

});
