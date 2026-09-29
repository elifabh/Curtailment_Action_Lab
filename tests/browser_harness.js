/* Browser harness support for the final Action Lab smoke test. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');

async function waitFor(check, message, timeoutMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try { if (await check()) return; } catch (_) { /* server may not be ready */ }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(message);
}

async function startServer(project, port) {
  const python = process.env.PYTHON || 'python';
  const child = spawn(python, ['server.py', '--port', String(port)], {
    cwd: project, env: process.env, stdio: ['ignore', 'pipe', 'pipe'],
  });
  let log = '';
  child.stdout.on('data', b => { log += b.toString(); });
  child.stderr.on('data', b => { log += b.toString(); });
  child.on('error', e => { log += e.message; });
  try {
    await waitFor(async () => {
      if (child.exitCode !== null) throw new Error('Server exited.');
      const r = await fetch(`http://127.0.0.1:${port}/api/config`);
      return r.ok;
    }, 'Local server did not become ready. ' + log);
  } catch (e) { child.kill(); throw e; }
  return { child, log: () => log };
}

async function withBrowser({ project, port, output, run }) {
  fs.mkdirSync(output, { recursive: true });
  let playwright;
  try { playwright = require('playwright'); }
  catch (_) {
    if (!process.env.PLAYWRIGHT_MODULE) throw new Error('Install Playwright first: npm install playwright && npx playwright install chromium');
    playwright = require(process.env.PLAYWRIGHT_MODULE);
  }
  let browser, server;
  const result = { created_at_utc: new Date().toISOString(), kind: 'rendered_browser', browser_started: false, checks: [], errors: [] };
  try {
    browser = await playwright.chromium.launch({
      headless: true,
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {}),
    });
    result.browser_started = true;
    result.browser_version = browser.version();
    server = await startServer(project, port);
    await run({ browser, base: `http://127.0.0.1:${port}`, output, result, assert, waitFor });
    result.passed = true;
  } catch (e) {
    result.passed = false;
    result.errors.push(e.stack || String(e));
  } finally {
    if (browser) await browser.close();
    if (server) server.child.kill();
    fs.writeFileSync(path.join(output, 'browser_report.json'), JSON.stringify(result, null, 2));
  }
  return result;
}

module.exports = { waitFor, startServer, withBrowser };
