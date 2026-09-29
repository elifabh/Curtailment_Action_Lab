'use strict';
// DOM execution + real HTTP API integration. This is not rendered-browser QA.
const { JSDOM, VirtualConsole } = require('jsdom');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { startServer, waitFor } = require('./browser_harness');
const project = path.resolve(__dirname, '..');
const out = path.join(project, 'dom-qa-results');
fs.mkdirSync(out, { recursive: true });
const port = Number(process.env.QA_PORT || 8878);
const base = `http://127.0.0.1:${port}`;
const result = { method: 'jsdom + actual local HTTP API', visual_qa: false, browser_rendering: false,
  date_utc: new Date().toISOString(), checks: [], errors: [], unhandled_errors: [] };
process.on('unhandledRejection', e => { result.unhandled_errors.push({ name: e.name, message: e.message, stack: e.stack }); console.error('Unhandled rejection', e.name, e.message, e.stack); });
let server, dom, offline;
const check = name => result.checks.push({ name, passed: true });
let httpCalls = [], blobs = [], downloadNames = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', e => result.unhandled_errors.push(e.message));

function options(url) {
  return { url, runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true, virtualConsole,
    beforeParse(window) {
      window.structuredClone = global.structuredClone;
      window.AbortController = global.AbortController;
      window.AbortSignal = global.AbortSignal;
      window.fetch = async (input, init) => {
        const target = new URL(input, url).href;
        httpCalls.push({ url: target, method: init?.method || 'GET' });
        return fetch(target, init);
      };
      window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      window.HTMLElement.prototype.scrollIntoView = function () {};
      window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
      window.HTMLDialogElement.prototype.close = function () { this.open = false; };
      window.URL.createObjectURL = blob => { blobs.push(blob); return 'blob:qa-' + blobs.length; };
      window.URL.revokeObjectURL = () => {};
      window.HTMLAnchorElement.prototype.click = function () { if (this.download) downloadNames.push(this.download); };
    } };
}
const el = (d, id) => d.window.document.getElementById(id);
const click = (d, id) => { assert.ok(el(d, id), 'Missing element ' + id); el(d, id).click(); };
function setInput(d, id, value) {
  el(d, id).value = String(value);
  el(d, id).dispatchEvent(new d.window.Event('input', { bubbles: true }));
  el(d, id).dispatchEvent(new d.window.Event('change', { bubbles: true }));
}
function tabs(d, label) {
  for (const id of ['overview', 'lab', 'analyst', 'evidence']) {
    click(d, 'tab-' + id);
    assert.equal(el(d, id).hidden, false);
    assert.equal(el(d, 'tab-' + id).getAttribute('aria-selected'), 'true');
    assert.equal([...d.window.document.querySelectorAll('[role="tabpanel"]')].filter(p => !p.hidden).length, 1);
  }
  check(label + ': four tabs and accessible selected state');
}
async function readBlob(window, blob) {
  return new Promise((resolve, reject) => { const r = new window.FileReader(); r.onload = () => resolve(r.result); r.onerror = reject; r.readAsText(blob); });
}
async function waitReady(d) {
  await waitFor(() => el(d, 'profile-select').options.length >= 2 && !el(d, 'profile-select').disabled, 'UI configuration did not populate.');
}
async function waitResult(d) {
  await waitFor(() => !el(d, 'result-content').classList.contains('hidden') && el(d, 'result-region').getAttribute('aria-busy') === 'false', 'Comparison result did not complete. ' + el(d, 'global-error').textContent, 120000);
}


async function conditionalChecks(d, label) {
  await waitReady(d);
  click(d, 'tab-lab');
  setInput(d, 'profile-select', 'irish_conditional_flex');
  assert.equal(el(d, 'wind-input').disabled, true);
  assert.equal(el(d, 'load-input').disabled, true);
  click(d, 'evaluate-button');
  await waitResult(d);
  assert.match(el(d, 'metric-cards').textContent, /61\.72/);
  assert.match(el(d, 'metric-cards').textContent, /14\.06/);
  assert.match(el(d, 'result-context').textContent, /RECORDED/);
  assert.equal(el(d, 'check-count').textContent, '18 / 18 passed');
  assert.equal(el(d, 'wind-input').disabled, true);
  check(label + ': conditional Irish result, 14.06 MW difference, 18 scoped checks and fixed controls');
  click(d, 'sensitivity-button');
  await waitFor(() => el(d, 'sensitivity-content').querySelectorAll('tbody tr').length === 1,
    'Conditional study must show one fixed recorded point.');
  assert.equal(el(d, 'sensitivity-content').querySelectorAll('svg').length, 0);
  check(label + ': no invented sensitivity curve for the stored Irish pair');
  click(d, 'tab-analyst');
  setInput(d, 'ai-budget', 2);
  click(d, 'search-button');
  await waitFor(() => /no new power flow/i.test(el(d, 'agent-best').textContent),
    'Conditional lookup must disclose that it reads stored records.');
  assert.equal(el(d, 'agent-best').querySelectorAll('.readable-bar-row').length, 2);
  await waitFor(() => /Irish stored-study benchmark/.test(el(d, 'evaluation-content').textContent),
    'Irish AI benchmark must not display the reference-network result.');
  assert.match(el(d, 'evaluation-content').textContent, /Best recorded acceptance/);
  check(label + ': deterministic study lookup and profile-specific benchmark are labelled');
  click(d, 'tab-evidence');
  assert.match(el(d, 'evidence-content').textContent, /Irish conditional flexibility study/);
  check(label + ': new Irish assumptions and source audit available in Evidence');
  click(d, 'tab-lab');
  await waitReady(d);
  setInput(d, 'profile-select', 'irish_winter_2024');
  assert.equal(el(d, 'evaluate-button').disabled, true);
  assert.equal(el(d, 'search-button').disabled, true);
  check(label + ': superseded Irish calculation disabled');
}


let onlineValue=null;
async function studyChecks(d,label){
  await waitReady(d);
  click(d,'tab-lab');
  click(d,'study-view-button');
  await waitFor(()=>el(d,'study-view').dataset.ready==='true','Extended study did not load.');
  assert.equal(el(d,'single-comparison-view').hidden,true);
  assert.match(el(d,'study-status').textContent,/14\.06/);
  assert.equal(el(d,'study-portfolio').querySelectorAll('tbody tr').length,8);
  assert.equal(el(d,'study-baselines').querySelectorAll('tbody tr').length,4);
  assert.equal(el(d,'study-all-pairs').querySelectorAll('tbody tr').length,60);
  check(label+': extended study shows the actual 60 conditions, eight candidates and four comparators');
  setInput(d,'study-flex',0);
  assert.match(el(d,'study-status').textContent,/0 MW additional wind/);
  setInput(d,'study-flex',20);
  check(label+': zero-flexibility control has zero additional wind');
  for(const[id,value]of[['value-hours',4],['value-wind',50],['value-premium',100],['value-limit',80]])setInput(d,id,value);
  click(d,'value-run');
  await waitFor(()=>/entered extra costs exceed/.test(el(d,'value-status').textContent),'Negative scenario value not displayed.');
  click(d,'study-export');
  const exported=JSON.parse(await readBlob(d.window,blobs.at(-1)));
  assert.equal(exported.value.field_savings,false);
  assert.equal(exported.value.customer_profit_established,false);
  assert.equal(exported.value.extra_wind_MWh,56.25);
  assert.equal(exported.value.scenario_surplus_EUR,-5187.5);
  if(label==='Local application')onlineValue=exported.value;
  else for(const key of ['extra_wind_MWh','scenario_surplus_EUR','break_even_premium_EUR_per_flexible_MWh'])assert.equal(exported.value[key],onlineValue[key]);
  check(label+': negative economics retained, explicit assumptions exported and online/offline arithmetic agrees');
  setInput(d,'value-limit',79);click(d,'value-run');
  await waitFor(()=>/exceeds the entered/.test(el(d,'value-status').textContent),'Energy envelope did not block the event.');
  assert.equal(el(d,'value-metrics').children.length,0);
  check(label+': insufficient event energy blocks the value illustration');
  const study=JSON.parse(fs.readFileSync(path.join(project,'evidence_v4/study_summary.json'),'utf8'));
  setInput(d,'study-case-source','portfolio_'+study.best_candidate_bus);
  assert.equal(el(d,'study-wind').disabled,true);
  setInput(d,'value-limit',80);setInput(d,'value-premium',10);click(d,'value-run');
  await waitFor(()=>/Value depends/.test(el(d,'value-status').textContent),'Portfolio conditional value did not complete.');
  click(d,'study-export');
  const portfolioValue=JSON.parse(await readBlob(d.window,blobs.at(-1)));
  assert.equal(portfolioValue.case.selected_bus,study.best_candidate_bus);
  assert.equal(portfolioValue.value.extra_wind_MWh,82.8125);
  assert.equal(portfolioValue.value.scenario_surplus_EUR,3340.625);
  check(label+': best connection uses its own checked wind difference in the conditional value calculation');
  setInput(d,'study-case-source','grid');
  const blocked=study.pairs.find(x=>!x.comparable);
  assert.ok(blocked,'Expected the retained blocked study condition');
  setInput(d,'study-wind',blocked.wind_available_MW);setInput(d,'study-flex',blocked.flex_MW);setInput(d,'study-line',blocked.line_outage?'outage':'in_service');
  assert.equal(el(d,'value-run').disabled,true);
  assert.match(el(d,'study-status').textContent,/comparison blocked/);
  check(label+': physically unverified pair cannot generate a monetary claim');
  click(d,'inspect-best-candidate');
  await waitResult(d);
  assert.equal(el(d,'study-view').hidden,true);
  assert.equal(el(d,'action-select').value,'flex_at_'+study.best_candidate_bus);
  const best=study.portfolio.find(x=>x.bus===study.best_candidate_bus);
  assert.ok(el(d,'metric-cards').textContent.includes(best.best_tested_wind_MW.toFixed(2)));
  check(label+': best portfolio point opens its exact paired comparison');
}

(async () => {
  for (const key of ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_DEPLOYMENT']) process.env[key] = '';
  server = await startServer(project, port);
  const onlineOptions = options(base); delete onlineOptions.url;
  dom = await JSDOM.fromURL(base, onlineOptions);
  await waitReady(dom);
  check('Application configuration populated profiles from actual HTTP API');
  setInput(dom, 'profile-select', 'reference_9bus');
  tabs(dom, 'Local application');
  click(dom, 'tab-lab');
  click(dom, 'evaluate-button');
  await waitResult(dom);
  assert.ok(el(dom, 'metric-cards').textContent.trim());
  assert.ok(el(dom, 'result-checks').textContent.trim());
  check('Default comparison displays solver metrics and checks');
  const beforeInvalid = httpCalls.filter(c => c.url.endsWith('/api/evaluate')).length;
  const originalWind = el(dom, 'wind-input').value;
  setInput(dom, 'wind-input', Number(el(dom, 'wind-input').max) + 1);
  assert.equal(el(dom, 'wind-input').validity.rangeOverflow, true);
  click(dom, 'evaluate-button');
  await new Promise(r => setTimeout(r, 50));
  assert.equal(httpCalls.filter(c => c.url.endsWith('/api/evaluate')).length, beforeInvalid);
  setInput(dom, 'wind-input', originalWind);
  check('Invalid wind input prevented a new solver request');
  click(dom, 'sensitivity-button');
  await waitFor(() => el(dom, 'sensitivity-content').querySelectorAll('tbody tr').length > 0, 'Sensitivity results did not appear. ' + el(dom, 'global-error').textContent, 180000);
  check('Wind sensitivity renders returned model points');
  click(dom, 'result-export');
  assert.ok(blobs.length > 0);
  const comparisonExport = JSON.parse(await readBlob(dom.window, blobs.at(-1)));
  assert.ok(comparisonExport.request || comparisonExport.result || comparisonExport.comparison);
  check('Comparison export contains parseable result JSON');
  click(dom, 'tab-analyst');
  assert.equal(el(dom, 'agent-button').disabled, true);
  assert.ok(/not configured/i.test(el(dom, 'ai-top-status').textContent));
  check('Cloud AI visibly disabled when Azure credentials are absent');
  setInput(dom, 'ai-budget', 2);
  click(dom, 'search-button');
  await waitFor(() => !el(dom, 'agent-results').classList.contains('hidden') && el(dom, 'agent-trace').textContent.trim(), 'Deterministic search did not finish. ' + el(dom, 'global-error').textContent, 120000);
  check('Deterministic search returned a calculation trail without AI credentials');
  click(dom, 'tab-evidence');
  click(dom, 'evidence-export');
  JSON.parse(await readBlob(dom.window, blobs.at(-1)));
  check('Evidence export contains parseable JSON');
  click(dom, 'presentation-open');
  assert.equal(el(dom, 'presentation-dialog').open, true);
  const step = el(dom, 'presentation-progress').textContent;
  click(dom, 'presentation-next');
  assert.notEqual(el(dom, 'presentation-progress').textContent, step);
  click(dom, 'presentation-close');
  assert.equal(el(dom, 'presentation-dialog').open, false);
  check('Presentation state opens, advances and closes (dialog API emulated)');
  await conditionalChecks(dom, 'Local application');
  await studyChecks(dom, 'Local application');
  const offlinePath = path.join(project, 'OPEN_DEMO.html');
  assert.ok(fs.existsSync(offlinePath), 'Offline bundle exists');
  const callsBeforeOffline = httpCalls.length;
  offline = new JSDOM(fs.readFileSync(offlinePath, 'utf8'), options('file://' + offlinePath));
  await waitReady(offline);
  assert.equal(el(offline, 'offline-banner').classList.contains('hidden'), false);
  setInput(offline, 'profile-select', 'reference_9bus');
  tabs(offline, 'Offline HTML');
  click(offline, 'tab-lab');
  click(offline, 'evaluate-button');
  await waitResult(offline);
  assert.equal(el(offline, 'agent-button').disabled, true);
  assert.equal(httpCalls.length, callsBeforeOffline, 'Offline must not make HTTP requests');
  check('Offline HTML displays recorded results without network calls');
  setInput(offline, 'wind-input', 170);
  click(offline, 'evaluate-button');
  await waitFor(() => /no recorded result/i.test(el(offline, 'global-error').textContent), 'Unrecorded inputs must show a clear error.');
  assert.equal(el(offline, 'stale-result').classList.contains('hidden'), false);
  check('Offline rejects unrecorded inputs instead of substituting another result');
  setInput(offline, 'wind-input', 200);
  click(offline, 'sensitivity-button');
  await waitFor(() => el(offline, 'sensitivity-content').querySelectorAll('tbody tr').length > 0, 'Recorded sensitivity did not render.');
  check('Offline wind sensitivity uses saved model points');
  click(offline, 'tab-analyst');
  setInput(offline, 'ai-budget', 2);
  click(offline, 'search-button');
  await waitFor(() => el(offline, 'agent-trace').textContent.trim(), 'Recorded deterministic search did not render.');
  assert.equal(httpCalls.length, callsBeforeOffline);
  check('Offline deterministic search shows a saved calculation trail without network calls');
  await conditionalChecks(offline, 'Offline HTML');
  await studyChecks(offline, 'Offline HTML');
  assert.equal(httpCalls.length, callsBeforeOffline);
  assert.deepEqual(result.unhandled_errors, []);
  check('No unhandled JavaScript exceptions in tested DOM flows');
  result.passed = true;
})().catch(e => { result.passed = false; result.errors.push(e.stack || String(e)); process.exitCode = 1; }).finally(() => {
  result.ui_error = dom ? el(dom, 'global-error').textContent : null;
  result.profile_state = dom ? { options: el(dom, 'profile-select').options.length, disabled: el(dom, 'profile-select').disabled } : null;
  if (dom) dom.window.close();
  if (offline) offline.window.close();
  if (server) server.child.kill();
  result.http_calls = httpCalls;
  result.download_names = downloadNames;
  fs.writeFileSync(path.join(out, 'dom_report.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ passed: result.passed, checks: result.checks.length, errors: result.errors, visual_qa: false, report: path.join(out, 'dom_report.json') }, null, 2));
});
