import type { Geometry } from './types';

export type GeometryChange = 'up' | 'down' | 'wider' | 'narrower' | 'taller' | 'shorter';
const overlapsX = (a: Geometry, b: Geometry) => a.x < b.x + b.w && a.x + a.w > b.x;
const overlaps = (a: Geometry, b: Geometry) => overlapsX(a, b) && a.y < b.y + b.h && a.y + a.h > b.y;

/** Keyboard operations use the same bounded geometry as pointer operations.
 * Move before/after a neighbouring panel, rather than moving two cells into a
 * collision and silently snapping back. Pins are immovable obstacles.
 */
export function changeGeometry(layout: Geometry[], id: string, change: GeometryChange, pinned: Set<string>, cols: number): Geometry[] {
  const next = structuredClone(layout);
  const item = next.find(g => g.i === id);
  if (!item || pinned.has(id)) throw new Error('This widget is not movable.');
  const peers = next.filter(g => g.i !== id && overlapsX(g, item)).sort((a, b) => a.y - b.y);
  if (change === 'up') {
    const previous = peers.filter(g => g.y < item.y).at(-1);
    item.y = previous?.y ?? Math.max(0, item.y - 2);
  }
  if (change === 'down') {
    const following = peers.find(g => g.y >= item.y);
    item.y = following ? following.y + following.h : item.y + 2;
  }
  if (change === 'wider') item.w = Math.min(cols - item.x, item.w + 1);
  if (change === 'narrower') item.w = Math.max(4, item.w - 1);
  if (change === 'taller') item.h = Math.min(30, item.h + 1);
  if (change === 'shorter') item.h = Math.max(4, item.h - 1);
  return settleGeometry(next, id, pinned);
}

/** react-grid-layout's noCompactor preserves gaps but does not displace peers
 * after a southeast resize. Normalize the stopped pointer gesture explicitly,
 * using the same collision and pin rules as the keyboard controls.
 */
export function settleGeometry(layout: Geometry[], id: string, pinned: Set<string>): Geometry[] {
  const next = structuredClone(layout); const item = next.find(g => g.i === id);
  if (!item || pinned.has(id)) throw new Error('This widget is not movable.');
  const fixed = next.filter(g => pinned.has(g.i));
  if (fixed.some(g => overlaps(item, g))) throw new Error('That change would overlap a pinned widget. Move elsewhere or unpin it first.');
  const placed = [...fixed, item];
  // Give the requested panel precedence; move only colliding, unlocked peers.
  for (const panel of next.filter(g => g.i !== id && !pinned.has(g.i)).sort((a, b) => a.y - b.y || a.x - b.x)) {
    for (let n = 0; n <= next.length; n++) {
      const collisions = placed.filter(g => overlaps(panel, g));
      if (!collisions.length) break;
      panel.y = Math.max(...collisions.map(g => g.y + g.h));
    }
    placed.push(panel);
  }
  if (next.some(g => g.y > 500)) throw new Error('The canvas height limit was reached. Remove or shorten a panel first.');
  return next;
}
