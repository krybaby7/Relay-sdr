import { test, expect } from '@playwright/test';
import { changeGeometry, settleGeometry } from '../src/geometry';
import type { Geometry } from '../src/types';
const stack: Geometry[] = [
  {i: 'a', x: 0, y: 0, w: 4, h: 10},
  {i: 'b', x: 0, y: 10, w: 4, h: 10},
  {i: 'c', x: 0, y: 20, w: 4, h: 10},
];
test('keyboard up moves before its neighbour instead of snapping back', () => {
  const result = changeGeometry(stack, 'b', 'up', new Set(), 4);
  expect(result.map(g => g.y)).toEqual([10, 0, 20]);
  expect(stack.map(g => g.y)).toEqual([0, 10, 20]);
});
test('keyboard down moves past its neighbour without overlapping', () => {
  expect(changeGeometry(stack, 'a', 'down', new Set(), 4).map(g => g.y)).toEqual([20, 10, 30]);
});
test('resizing cascades through unpinned peers', () => {
  expect(changeGeometry(stack, 'a', 'taller', new Set(), 4).map(g => [g.y,g.h])).toEqual([[0,11],[11,10],[21,10]]);
});
test('pins cannot be moved directly or by a conflicting neighbour', () => {
  expect(() => changeGeometry(stack, 'a', 'down', new Set(['a']), 4)).toThrow('not movable');
  expect(() => changeGeometry(stack, 'b', 'up', new Set(['a']), 4)).toThrow('pinned');
  expect(() => changeGeometry(stack, 'a', 'taller', new Set(['b']), 4)).toThrow('pinned');
  expect(stack.map(g => g.y)).toEqual([0,10,20]);
});
test('cascade skips over a pinned obstacle without changing it', () => {
  const result = changeGeometry(stack, 'a', 'taller', new Set(['c']), 4);
  expect(result.find(g => g.i === 'c')).toEqual(stack[2]);
  expect(result.find(g => g.i === 'b')!.y).toBe(30);
});
test('width and height constraints match persisted geometry bounds', () => {
  expect(changeGeometry(stack, 'a', 'wider', new Set(), 4)[0].w).toBe(4);
  expect(changeGeometry(stack, 'a', 'narrower', new Set(), 4)[0].w).toBe(4);
  expect(changeGeometry([{...stack[0],h:4}], 'a', 'shorter', new Set(), 4)[0].h).toBe(4);
  expect(changeGeometry([{...stack[0],h:30}], 'a', 'taller', new Set(), 4)[0].h).toBe(30);
});
test('invalid IDs and overflowing canvas changes fail without mutation', () => {
  expect(() => changeGeometry(stack, 'absent', 'up', new Set(), 4)).toThrow();
  expect(() => changeGeometry([{...stack[0],y:500}], 'a', 'down', new Set(), 4)).toThrow('height limit');
});

test('pointer resize displacement uses the same collision rules without compacting gaps', () => {
  const pointer = [{...stack[0],h:11}, stack[1], {...stack[2],y:40}];
  expect(settleGeometry(pointer, 'a', new Set()).map(g => g.y)).toEqual([0,11,40]);
  expect(() => settleGeometry(pointer, 'a', new Set(['b']))).toThrow('pinned');
});
