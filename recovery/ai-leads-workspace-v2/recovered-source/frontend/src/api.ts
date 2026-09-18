export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
export async function api<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const token = sessionStorage.getItem('relay-token') || '';
  const response = await fetch(path, { method, signal, headers: {
    Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
  }, body: body === undefined ? undefined : JSON.stringify(body), credentials: 'same-origin' });
  if (!response.ok) {
    const error: { detail?: unknown } = await response.json().catch(() => ({}));
    const detail = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail || `HTTP ${response.status}`);
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
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
    await new Promise<void>(resolve => { const timer = setTimeout(resolve, 3000); signal.addEventListener('abort', () => { clearTimeout(timer); resolve(); }, { once: true }); });
  }
}
