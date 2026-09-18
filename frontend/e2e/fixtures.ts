import { test as base, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';

// A separate loopback server/database/worker per test gives each scenario a real
// application lifecycle and production rate limits. No rate-limit bypass/reset
// endpoint is added to the application. No state leaks between device projects.
export const test = base.extend({
  baseURL: async ({}, use) => {
    const socket = createServer();
    await new Promise<void>(resolve => socket.listen(0, '127.0.0.1', resolve));
    const address = socket.address();
    if (!address || typeof address === 'string') throw new Error('No fixture port allocated');
    const port = address.port;
    await new Promise<void>(resolve => socket.close(() => resolve()));
    const child = spawn(process.env.RELAY_TEST_PYTHON || 'python', ['../tests/workspace_browser_server.py', '--port', String(port)], {
      stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, ENABLE_OUTBOUND: 'false', OPENAI_API_KEY: '', WORKSPACE_API_KEY: '' },
    });
    let diagnostics = '';
    child.stdout.on('data', part => { diagnostics = (diagnostics + part.toString()).slice(-8000); });
    child.stderr.on('data', part => { diagnostics = (diagnostics + part.toString()).slice(-8000); });
    child.on('error', error => { diagnostics += error.message; });
    const url = `http://127.0.0.1:${port}`;
    try {
      await expect.poll(async () => {
        if (child.exitCode !== null) throw new Error(`Fixture exited: ${diagnostics}`);
        try { return (await fetch(`${url}/health`)).status; } catch { return 0; }
      }, { timeout: 20000, message: 'Start isolated fictional fixture' }).toBe(200);
      await use(url);
    } finally {
      const exited = new Promise<void>(resolve => { if (child.exitCode !== null) resolve(); else child.once('exit', () => resolve()); });
      child.kill('SIGTERM');
      const killTimer = setTimeout(() => child.kill('SIGKILL'), 5000);
      await exited;
      clearTimeout(killTimer);
    }
  },
});
export { expect };
