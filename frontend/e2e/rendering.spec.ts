import { test, expect } from './fixtures';
import { login } from './helpers';

test('settled rendered geometry is non-overlapping and fits the viewport', async ({ page }, info) => {
  await login(page);
  const table = page.locator('[data-widget-id="all_w1"]');
  const board = page.locator('[data-widget-id="all_w2"]');
  const changes = page.locator('[data-widget-id="all_w3"]');
  const mobile = info.project.name.includes('mobile');
  // Wait for actual measured geometry, not just visible table text or a saved
  // JSON layout. Initial CSS transitions must not become misleading screenshots.
  await expect.poll(async () => {
    const a = await table.boundingBox(), b = await board.boundingBox();
    if (!a || !b) return false;
    return mobile ? b.y >= a.y + a.height && Math.abs(a.x - b.x) < 1
      : b.x >= a.x + a.width && Math.abs(a.y - b.y) < 1;
  }).toBe(true);
  const panels = page.locator('[data-widget-id]');
  await expect.poll(async () => panels.evaluateAll(elements => {
    const boxes = elements.map(e => e.getBoundingClientRect());
    return boxes.flatMap((a, index) => boxes.slice(index + 1).filter(b =>
      Math.min(a.right,b.right) - Math.max(a.left,b.left) > 1 &&
      Math.min(a.bottom,b.bottom) - Math.max(a.top,b.top) > 1)).length;
  })).toBe(0);
  const a = (await table.boundingBox())!, b = (await board.boundingBox())!;
  const c = (await changes.boundingBox())!;
  expect(c.y).toBeGreaterThanOrEqual(Math.max(a.y+a.height,b.y+b.height));
  const viewport = page.viewportSize()!;
  for (const box of [a,b,c]) {
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x+box.width).toBeLessThanOrEqual(viewport.width);
  }
  await page.screenshot({path:`test-results/${info.project.name}-rendered-overview.png`,fullPage:true,animations:'disabled'});
});
