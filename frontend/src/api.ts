export class ApiError extends Error {
  constructor(message: string, public status: number, public retryAfter = 1) { super(message); }
}
export async function api<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const token = sessionStorage.getItem('relay-token') || '';
  const response = await fetch(path, { method, signal, headers: {
    Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
  }, body: body === undefined ? undefined : JSON.stringify(body), credentials: 'same-origin' });
  if (!response.ok) {
    const error: { detail?: unknown } = await response.json().catch(() => ({}));
    const detail = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail || `HTTP ${response.status}`);
    const seconds = Number(response.headers.get('Retry-After') || '1');
    throw new ApiError(detail, response.status, Number.isFinite(seconds) ? Math.max(1, Math.min(seconds, 60)) : 1);
  }
  const value = await response.json() as T;
  if (signal?.aborted || sessionStorage.getItem('relay-token') !== token) throw new DOMException('Request superseded', 'AbortError');
  return value;
}
// Only explicitly allowlisted read-only endpoints may be retried, including
// POST queries. Never replay a command, correction, booking or other mutation.
const READ_POSTS = new Set(['/api/workspace/dataset', '/api/workspace/query', '/api/workspace/aggregates', '/api/workspace/tasks/query', '/api/workspace/calls/query']);
function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const abort = () => { clearTimeout(timer); reject(new DOMException('Request cancelled', 'AbortError')); };
    const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, ms);
    if (signal?.aborted) abort(); else signal?.addEventListener('abort', abort, { once: true });
  });
}
export async function readApi<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  if (!(method === 'GET' && path.startsWith('/api/workspace')) && !(method === 'POST' && READ_POSTS.has(path))) {
    throw new Error('Only workspace reads can be retried.');
  }
  const token = sessionStorage.getItem('relay-token');
  for (let attempt = 0; ; attempt++) {
    try { return await api<T>(path, method, body, signal); }
    catch (error) {
      if (!(error instanceof ApiError) || error.status !== 429 || attempt >= 2) throw error;
      await delay(error.retryAfter * 1000, signal);
      if (sessionStorage.getItem('relay-token') !== token) throw new DOMException('Session changed', 'AbortError');
    }
  }
}
export const label = (value: unknown) => value === undefined || value === null || value === '' ? 'Unknown' : String(value).replaceAll('_', ' ');
export function date(value: string | null | undefined, zone = 'Africa/Cairo') {
  if (!value) return 'Not provided';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: zone }).format(parsed);
}
export function identifier(prefix: string) { return `${prefix}_${crypto.randomUUID().replaceAll('-', '').slice(0, 16)}`; }
export async function events(after: number, signal: AbortSignal, receive: (cursor: number) => void) {
  let cursor = after;
  while (!signal.aborted) {
    try {
      const response = await fetch(`/api/workspace/events?after=${cursor}`, { headers: { Authorization: `Bearer ${sessionStorage.getItem('relay-token') || ''}` }, signal });
      if (!response.ok || !response.body) throw new ApiError('Workspace event connection unavailable.', response.status);
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let pending = '';
      while (!signal.aborted) {
        const { value, done } = await reader.read(); if (done) break;
        pending += decoder.decode(value, { stream: true });
        const messages = pending.split('\n\n'); pending = messages.pop() || '';
        for (const message of messages) if (message.startsWith('data: ')) {
          const data = JSON.parse(message.slice(6)) as { cursor: number };
          cursor = data.cursor; receive(cursor);
        }
      }
    } catch (error) {
      if (signal.aborted) return;
      if (error instanceof ApiError && [401, 403].includes(error.status)) return;
    }
    await delay(3000, signal).catch(() => undefined);
  }
}
