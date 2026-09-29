'use strict';
// Rendered UI, real local calculations, and explicitly mocked Azure replies.
// No Azure key or provider request is used by this acceptance test.
const fs=require('node:fs'),path=require('node:path');
const {withBrowser}=require('./browser_harness');
const project=path.resolve(__dirname,'..');
const output=process.env.QA_OUTPUT_DIR||path.join(project,'browser-qa-results/demo');
for(const key of ['AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_API_KEY','AZURE_OPENAI_DEPLOYMENT'])process.env[key]='';
withBrowser({project,port:Number(process.env.QA_PORT||8884),output,run:async({browser,base,assert,result})=>{
 const mark=name=>{result.checks.push({name,passed:true});console.log('PASS '+name);};
 result.live_azure_tested=false;result.azure_ui_source='scripted response fixtures';
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.setDefaultTimeout(20000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function download(id,name,json=true){const waiting=page.waitForEvent('download');await page.locator('#'+id).click();const d=await waiting;const f=path.join(output,name);await d.saveAs(f);return json?JSON.parse(fs.readFileSync(f,'utf8')):fs.readFileSync(f,'utf8');}
 await page.goto(base);
 await page.locator('#start-offer-comparison').click();
 await page.locator('#decision-run').click();
 await page.locator('#decision-results').waitFor({state:'visible'});
 await page.locator('#challenge-rule').click();
 await page.waitForFunction(()=>document.querySelector('#challenge-status').textContent.includes('Rule-based audit completed'));
 let exported=await download('decision-export-after-audit','rule.json');
 assert.equal(exported.audit.record_reads,4);mark('Offer comparison and four-read rule audit work with real HTTP');
 // Enable only the UI using a test fixture; real Azure remains disabled.
 await page.route('**/api/decision-config',async route=>{const r=await route.fetch();const j=await r.json();j.ai={enabled:true,status:'configured',live_tested:false};await route.fulfill({json:j});});
 await page.reload();await page.locator('#decision-view-button').click();await page.locator('#decision-run').click();
 await page.locator('#decision-results').waitFor({state:'visible'});
 await page.locator('#challenge-rule').click();await page.waitForFunction(()=>!document.querySelector('#challenge-rule').disabled);
 const decision=(await download('decision-export-after-audit','decision.json')).decision;
 const records=['delivery_half','demand_lower','delivery_zero'].map(s=>decision.nominal_offer_audit.find(x=>x.scenario_id===s));
 assert.ok(records.every(Boolean));
 let fixture={mode:'azure',status:'provider_error',budget:4,records,record_reads:3,provider_calls:4,is_live_provider:true,partial:true,counterexamples_found:1,new_power_flows_run:0,error:{code:'azure_http_429',http_status:429,message:'Azure rate limit reached (HTTP 429).'},rejected:['Azure rate limit reached (HTTP 429).'],summary:'Inspected three recorded conditions; one failed the declared offer requirements.'};
 await page.route('**/api/challenge-audit',async route=>{
  if(route.request().postDataJSON().mode==='azure')await route.fulfill({json:fixture});else await route.continue();
 });
 await page.locator('#challenge-ai').click();await page.waitForFunction(()=>document.querySelector('#challenge-status').textContent.startsWith('Partial audit:'));
 assert.equal(await page.locator('#challenge-results tbody tr').count(),3);
 assert.equal(await page.locator('#challenge-comparison tbody tr').count(),2);
 assert.match(await page.locator('#challenge-results').innerText(),/HTTP 429/);
 exported=await download('decision-export-after-audit','partial-audit.json');assert.equal(exported.audits.deterministic.record_reads,4);assert.equal(exported.audits.azure.record_reads,3);assert.equal(exported.audit.partial,true);
 const report=await download('decision-report-after-audit','partial-audit.html',false);assert.match(report,/audit is incomplete/);assert.match(report,/HTTP 429/);
 await page.locator('#decision-ai-panel').screenshot({path:path.join(output,'partial-audit.png')});
 mark('Interrupted Azure fixture preserves partial checks, diagnosis, both runs, and readable export');
 fixture={...fixture,status:'completed',records:decision.nominal_offer_audit.filter(x=>x.scenario_id!=='nominal').slice(0,4),record_reads:4,partial:false,error:null,rejected:[]};
 await page.locator('#challenge-ai').click();await page.waitForFunction(()=>document.querySelector('#challenge-status').textContent.startsWith('Microsoft AI audit completed.'));
 assert.equal(await page.locator('#challenge-results tbody tr').count(),4);
 assert.equal(await page.locator('#challenge-comparison tbody tr').count(),2);mark('Successful rerun replaces the partial AI result and preserves the rule result');
 await page.locator('#decision-budget').fill('501');assert.equal(await page.locator('#decision-results').isHidden(),true);mark('Changed offer inputs invalidate prior audits');
 await page.goto(base+'/extension');await page.waitForFunction(()=>!document.querySelector('#example').disabled);
 for(const recording of ['snapshot_example','pilot_fixed_demand','pilot_observed_demand']){
  await page.locator('#recording').selectOption(recording);await page.locator('#example').click();await page.waitForFunction(()=>!document.querySelector('#example').disabled&&!document.querySelector('#result').hidden);
  const r=await download('download-json',recording+'.json');assert.ok(r.calculation_id);assert.match(await page.locator('#result .tag').innerText(),/SAVED/);
  const html=await download('download-report',recording+'.html',false);assert.match(html,/Curtailment Action Lab/);
 }
 mark('All three saved Irish experiments open and export JSON/readable reports');
 // A transport error during polling must not discard the live job.
 let dropped=false;
 await page.route('**/api/extension-status',async route=>{if(!dropped){dropped=true;await route.abort('connectionreset');}else await route.continue();});
 const runFresh=async(name)=>{
  await page.locator('#run').click();
  await page.waitForFunction(()=>!document.querySelector('#run').disabled,null,{timeout:1800000});
  if(await page.locator('#error').isVisible())throw Error(await page.locator('#error').innerText());
  assert.match(await page.locator('#result .tag').innerText(),/FRESH CALCULATION/);
  const r=await download('download-json',name+'.json');assert.ok(r.new_power_flows_run>0);return r;
 };
 const snapshot=await runFresh('fresh-default');
 assert.equal(snapshot.inputs.wind_available_MW,200);assert.equal(snapshot.comparison.additional_hypothetical_wind_MW,20.703125);
 mark('Fresh Irish default reproduces 20.703125 MW and survives a dropped status request');
 await page.locator('#kind').selectOption('pilot');
 let pilot=await runFresh('fresh-pilot-fixed');assert.equal(pilot.interval_results.length,12);assert.equal(pilot.inputs.profile_mode,'wind_shape_fixed_demand');
 mark('Fresh six-hour fixed-demand pilot completes all twelve intervals');
 await page.locator('#profile').selectOption('observed_demand_assumed_redispatch');
 pilot=await runFresh('fresh-pilot-observed');assert.equal(pilot.interval_results.length,12);assert.equal(pilot.inputs.profile_mode,'observed_demand_assumed_redispatch');
 mark('Fresh six-hour observed-demand pilot completes all twelve intervals');
 result.fresh_results={snapshot:{seconds:snapshot.elapsed_seconds,power_flows:snapshot.new_power_flows_run,difference_MW:snapshot.comparison.additional_hypothetical_wind_MW},observed_pilot:{seconds:pilot.elapsed_seconds,power_flows:pilot.new_power_flows_run,summary:pilot.summary}};
 await page.screenshot({path:path.join(output,'extension-desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});const dim=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));assert.ok(dim.scroll<=dim.width+1);
 assert.deepEqual(errors,[]);mark('Extension has no page-level mobile overflow or JavaScript exceptions');
 await page.close();
}}).then(r=>{console.log(JSON.stringify({passed:r.passed,checks:r.checks.length,errors:r.errors,live_azure_tested:false}));if(!r.passed)process.exitCode=1;});
