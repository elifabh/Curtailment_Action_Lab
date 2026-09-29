#!/usr/bin/env node
/* Optional rendered-browser acceptance test.
 * npm install playwright
 * npx playwright install chromium
 * node tests/browser_smoke.js
 * Requires the app's Python dependencies for fresh calculations.
 * No Azure request is made by this test.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const project = path.resolve(__dirname, '..');
const output = path.resolve(process.env.QA_OUTPUT_DIR || path.join(project, 'browser-qa-results'));
const port = Number(process.env.QA_PORT || 8877);
const base = `http://127.0.0.1:${port}`;
const report = { created_at_utc: new Date().toISOString(), method: 'Playwright Chromium', rendered_browser_started: false, screenshots: [], checks: [], errors: [] };
fs.mkdirSync(output, { recursive: true });
let browser, server, serverLog = '';
const mark = name => report.checks.push({ name, passed: true });

async function waitFor(check, message, timeoutMs = 20000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try { if (await check()) return; } catch (_) { /* startup is asynchronous */ }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(message);
}
async function screenshot(page, name) {
  await page.screenshot({ path: path.join(output, name + '.png'), fullPage: true });
  report.screenshots.push(name + '.png');
}
async function checkTabs(page, label) {
  for (const id of ['overview', 'lab', 'analyst', 'evidence']) {
    await page.locator('#tab-' + id).click();
    assert.equal(await page.locator('#' + id).isVisible(), true, `${label}: ${id} panel`);
    assert.equal(await page.locator('#tab-' + id).getAttribute('aria-selected'), 'true');
    assert.equal(await page.locator('[role="tabpanel"]:visible').count(), 1);
  }
  mark(label + ': four tabs and selected state');
}
async function checkOverflow(page, label) {
  const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: innerWidth }));
  assert.ok(dimensions.scroll <= dimensions.width + 1, `${label}: horizontal overflow ${dimensions.scroll} > ${dimensions.width}`);
  mark(label + ': no page-level horizontal overflow');
}
async function downloadJSON(page, selector, filename) {
  const waiting = page.waitForEvent('download');
  await page.locator(selector).click();
  const download = await waiting;
  const target = path.join(output, filename);
  await download.saveAs(target);
  const parsed = JSON.parse(fs.readFileSync(target, 'utf8'));
  assert.ok(parsed && typeof parsed === 'object');
  return parsed;
}

async function checkOffers(page,label){
  await page.locator('#tab-lab').click();
  await page.locator('#decision-view-button').click();
  await page.waitForFunction(()=>document.querySelector('#decision-view').dataset.ready==='true');
  await page.locator('#decision-run').click();
  await page.waitForFunction(()=>!document.querySelector('#decision-results').hidden&&!document.querySelector('#decision-run').disabled);
  assert.match(await page.locator('#decision-metrics').innerText(),/9\.57/);
  assert.equal(await page.locator('#challenge-ai').isDisabled(),true);
  const r=await downloadJSON(page,'#decision-export',label+'-offer.json');
  assert.equal(r.decision.status,'retain');
  await checkOverflow(page,label+' offers');
  await screenshot(page,label+'-offers');
  await page.locator('#required-demand_higher').check();
  await page.locator('#decision-run').click();
  await page.waitForFunction(()=>document.querySelector('#decision-title').textContent.includes('withdrawn')&&!document.querySelector('#decision-run').disabled);
  await screenshot(page,label+'-withdrawal');
  mark(label+': offer decision, actual export and blocked-baseline withdrawal');
}

(async () => {
  let playwright;
  try { playwright = require('playwright'); }
  catch (_) {
    if (!process.env.PLAYWRIGHT_MODULE) throw new Error('Install Playwright: npm install playwright && npx playwright install chromium');
    playwright = require(process.env.PLAYWRIGHT_MODULE);
  }
  browser = await playwright.chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {}) });
  report.rendered_browser_started = true;
  report.browser_version = browser.version();
  const env = { ...process.env };
  // The acceptance run intentionally exercises the no-credentials state.
  // Empty values also override credentials loaded from a project-local .env.
  for (const key of ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_DEPLOYMENT']) env[key] = '';
  server = spawn(process.env.PYTHON || 'python', ['server.py', '--port', String(port)], { cwd: project, env, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stdout.on('data', b => { serverLog += b.toString(); });
  server.stderr.on('data', b => { serverLog += b.toString(); });
  server.on('error', e => { serverLog += e.message; });
  await waitFor(async () => (await fetch(base + '/api/config')).ok, 'Local server did not start.');
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  page.setDefaultTimeout(30000);
  const exceptions = [];
  page.on('pageerror', e => exceptions.push(e.message));
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.querySelector('#profile-select').options.length >= 2 && !document.querySelector('#profile-select').disabled);
  await screenshot(page, '01-overview-desktop');
  await checkOverflow(page, 'Desktop Overview');
  await checkTabs(page, 'Local app');
  await page.locator('#tab-lab').click();
  await page.locator('#single-view-button').click();
  await page.locator('#profile-select').selectOption('reference_9bus');

  await page.locator('#tab-lab').click();
  let requests = 0;
  page.on('request', req => { if (req.url().endsWith('/api/evaluate') && req.method() === 'POST') requests++; });
  await page.locator('#evaluate-button').click();
  await page.locator('#result-content').waitFor({ state: 'visible', timeout: 120000 });
  assert.ok((await page.locator('#metric-cards').innerText()).trim().length > 0);
  mark('Default numerical comparison populates metrics and checks');
  await screenshot(page, '02-comparison-desktop');

  const originalWind = await page.locator('#wind-input').inputValue();
  const upper = Number(await page.locator('#wind-input').getAttribute('max'));
  const beforeInvalid = requests;
  await page.locator('#wind-input').fill(String(upper + 1));
  await page.locator('#evaluate-button').click();
  assert.equal(await page.locator('#wind-input').evaluate(el => el.validity.rangeOverflow), true);
  assert.equal(requests, beforeInvalid, 'Invalid wind must not invoke solver');
  await page.locator('#wind-input').fill(originalWind);
  mark('Out-of-range wind blocked before solver call');

  await page.locator('#sensitivity-button').click();
  await page.waitForFunction(() => document.querySelector('#sensitivity-content').querySelectorAll('tbody tr').length > 0, null, { timeout: 180000 });
  mark('Sensitivity returns a table of actual model results');
  await screenshot(page, '03-sensitivity-desktop');
  const exported = await downloadJSON(page, '#result-export', 'comparison-export.json');
  assert.ok(exported.request || exported.result || exported.comparison, 'Comparison export must contain a result');
  mark('Comparison JSON export parses');

  await page.locator('#tab-analyst').click();
  assert.equal(await page.locator('#agent-button').isDisabled(), true, 'AI must be disabled without credentials');
  assert.ok(/not configured/i.test(await page.locator('#ai-top-status').innerText()));
  mark('AI is explicitly unavailable without Azure credentials');
  await page.locator('#ai-budget').fill('2');
  await page.locator('#search-button').click();
  await page.locator('#agent-results').waitFor({ state: 'visible', timeout: 120000 });
  await page.waitForFunction(() => document.querySelector('#agent-trace').textContent.trim().length > 0 && !document.querySelector('#search-button').disabled, null, { timeout: 120000 });
  assert.ok((await page.locator('#agent-trace').innerText()).trim().length > 0);
  mark('Deterministic search remains usable without AI');
  await screenshot(page, '04-ai-analyst-desktop');

  await page.locator('#tab-evidence').click();
  await downloadJSON(page, '#evidence-export', 'evidence-export.json');
  mark('Evidence JSON export parses');
  await screenshot(page, '05-evidence-desktop');
  await page.locator('#presentation-open').click();
  assert.equal(await page.locator('#presentation-dialog').evaluate(el => el.open), true);
  const slide = await page.locator('#presentation-progress').innerText();
  await page.locator('#presentation-next').click();
  assert.notEqual(await page.locator('#presentation-progress').innerText(), slide);
  await screenshot(page, '06-presentation');
  await page.locator('#presentation-close').click();
  assert.equal(await page.locator('#presentation-dialog').evaluate(el => el.open), false);
  mark('Presentation opens, advances and closes');

  await page.locator('#tab-lab').click();
  await page.locator('#study-view-button').click();
  await page.waitForFunction(() => document.querySelector('#study-view').dataset.ready === 'true');
  assert.equal(await page.locator('#study-portfolio tbody tr').count(), 8);
  await screenshot(page, '07-robustness-desktop');
  await checkOverflow(page, 'Desktop robustness');
  await checkOffers(page,'desktop');
  await page.setViewportSize({ width: 390, height: 844 });
  for (const id of ['overview', 'lab', 'analyst', 'evidence']) {
    await page.locator('#tab-' + id).click();
    await checkOverflow(page, 'Mobile ' + id);
  }
  await screenshot(page, '07-mobile-evidence');
  await page.locator('#tab-lab').click();
  await screenshot(page, '07-mobile-robustness');
  await checkOverflow(page,'Mobile offer decisions');
  await screenshot(page,'09-mobile-offers');

  const offlinePath = path.join(project, 'OPEN_DEMO.html');
  assert.ok(fs.existsSync(offlinePath), 'Self-contained OPEN_DEMO.html exists');
  const offline = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  offline.on('pageerror', e => exceptions.push('Offline: ' + e.message));
  const offlineRequests = [];
  offline.on('request', req => { if (/^https?:/.test(req.url())) offlineRequests.push(req.url()); });
  await offline.goto(pathToFileURL(offlinePath).href, { waitUntil: 'load' });
  await offline.waitForFunction(() => document.querySelector('#profile-select').options.length >= 2 && !document.querySelector('#profile-select').disabled);
  assert.equal(await offline.locator('#offline-banner').isVisible(), true);
  await checkTabs(offline, 'Offline demo');
  await offline.locator('#tab-lab').click();
  await offline.locator('#single-view-button').click();
  await offline.locator('#profile-select').selectOption('reference_9bus');
  await offline.locator('#tab-lab').click();
  await offline.locator('#evaluate-button').click();
  await offline.locator('#result-content').waitFor({ state: 'visible' });
  assert.equal(await offline.locator('#agent-button').isDisabled(), true);
  assert.deepEqual(offlineRequests, [], 'Offline demo must not fetch external or local API resources');
  mark('Offline recorded comparison works without network access');
  await screenshot(offline, '08-offline-comparison');
  await offline.locator('#wind-input').fill('170');
  await offline.locator('#evaluate-button').click();
  await offline.waitForFunction(() => /no recorded result/i.test(document.querySelector('#global-error').textContent));
  assert.equal(await offline.locator('#stale-result').isVisible(), true);
  mark('Offline rejects unrecorded input instead of substituting another result');
  await checkOffers(offline,'offline');
  assert.deepEqual(exceptions, [], 'No unhandled JavaScript exceptions');
  mark('No unhandled browser JavaScript exceptions');
  report.passed = true;
})().catch(error => {
  report.passed = false;
  report.errors.push(error.stack || String(error));
  process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  if (server) server.kill();
  fs.writeFileSync(path.join(output, 'browser_report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ passed: report.passed, rendered_browser_started: report.rendered_browser_started, checks: report.checks.length, report: path.join(output, 'browser_report.json') }, null, 2));
});
