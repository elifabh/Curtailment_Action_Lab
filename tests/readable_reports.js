'use strict';
// DOM and HTTP regression tests. Captured Azure replies are fixtures, not live calls.
const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {startServer,waitFor}=require('./browser_harness');
const project=path.resolve(__dirname,'..'),fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/readable_session.json'),'utf8'));
const report={method:'DOM, local HTTP and captured provider response fixtures',live_provider_test:false,visual_qa:false,checks:[],errors:[]};
const check=name=>report.checks.push({name,passed:true});
let server,dom,blobs=[],failAgent=false;
const vc=new VirtualConsole();vc.on('jsdomError',e=>report.errors.push(e.message));
const el=id=>dom.window.document.getElementById(id),click=id=>{assert.ok(el(id),id);el(id).click();};
function change(id,value){const e=el(id);if(e.type==='checkbox')e.checked=value;else e.value=String(value);e.dispatchEvent(new dom.window.Event('input',{bubbles:true}));e.dispatchEvent(new dom.window.Event('change',{bubbles:true}));}
async function blobText(){const item=blobs.at(-1);assert.ok(item,'Download blob');return new Promise((yes,no)=>{const r=new dom.window.FileReader();r.onload=()=>yes(r.result);r.onerror=no;r.readAsText(item);});}
function parseHTML(text){return new JSDOM(text);}
async function runDecision(){click('decision-run');await waitFor(()=>!el('decision-results').hidden&&!el('decision-run').disabled,'Offer decision did not finish');}
(async()=>{
 for(const key of ['AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_API_KEY','AZURE_OPENAI_DEPLOYMENT'])process.env[key]='';
 const port=Number(process.env.QA_PORT||8881),base=`http://127.0.0.1:${port}`;server=await startServer(project,port);
 dom=await JSDOM.fromURL(base,{runScripts:'dangerously',resources:'usable',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
   w.structuredClone=structuredClone;w.AbortController=AbortController;w.AbortSignal=AbortSignal;
   w.fetch=async(u,options)=>{const url=new URL(u,base);if(url.pathname==='/api/agent'){if(failAgent)throw new Error('Injected provider connection failure');return {ok:true,json:async()=>structuredClone(fixture.investigation)};}
     const res=await fetch(url,options);if(url.pathname==='/api/config'){const value=await res.json();value.ai={...value.ai,enabled:true,status:'configured',description:'Fixture-only AI configuration for UI tests'};return {ok:res.ok,json:async()=>value};}return res;};
   w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});w.HTMLElement.prototype.scrollIntoView=function(){};
   w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
   w.URL.createObjectURL=b=>{blobs.push(b);return 'blob:qa-'+blobs.length;};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=function(){};w.open=()=>{};
 }});
 await waitFor(()=>el('decision-view')?.dataset.ready==='true'&&el('profile-select').options.length===3,'UI did not load');
 assert.ok(dom.window.ActionLabReports);assert.equal(dom.window.document.querySelectorAll('.report-button').length,6);check('Readable report controls exist for all five export types and both decision positions');
 click('tab-analyst');change('ai-profile','irish_conditional_flex');change('ai-prompt','Compare the allowed example sites');
 await waitFor(()=>!el('agent-button').disabled,'Mock AI button did not enable');click('agent-button');
 await waitFor(()=>el('agent-status').textContent==='Live AI completed'&&!el('agent-button').disabled,'Captured investigation did not render');
 assert.equal(el('agent-best').querySelectorAll('.readable-bar-row').length,4);
 for(const text of ['Example site A','Example site B','Example site C','Example site D','68.36','61.72','47.66','63.28'])assert.ok(el('agent-best').textContent.includes(text),text);
 assert.ok(el('agent-best').textContent.includes('20.7 MW'));assert.equal(el('agent-trace').querySelectorAll('details[open]').length,0);check('Captured investigation shows four correctly labelled bars, matching numbers and collapsed technical records');
 assert.match(el('evaluation-content').textContent,/Live Azure investigation completed/);assert.match(el('evaluation-content').textContent,/not been established/);check('Live connection completion and comparative AI performance have distinct labels');
 click('agent-report');let html=await blobText(),parsed=parseHTML(html);assert.equal(parsed.window.document.querySelectorAll('.readable-bar-row').length,4);assert.match(parsed.window.document.body.textContent,/Example site C/);assert.equal(parsed.window.document.querySelectorAll('script').length,0);parsed.window.close();check('Investigation downloads a standalone readable HTML report with all inspected options');
 click('tab-evidence');click('evidence-export');const evidence=JSON.parse(await blobText());assert.equal(evidence.selected_profile,'irish_conditional_flex');assert.equal(evidence.evaluation.profile_id,'irish_conditional_flex');assert.equal(evidence.evaluation.live_ai_status,'not_run');assert.equal(evidence.investigation.is_live_provider,true);check('Evidence export uses the selected Irish benchmark and keeps captured live-session evidence separate');
 click('evidence-report');html=await blobText();assert.match(html,/Saved comparative benchmark/);assert.match(html,/Irish stored-study benchmark/);assert.match(html,/Example site C/);check('Evidence report includes the selected benchmark, source references and readable investigation');
 click('tab-lab');click('single-view-button');change('profile-select','irish_conditional_flex');change('action-select','flex_at_1701');click('evaluate-button');
 await waitFor(()=>el('result-region').getAttribute('aria-busy')==='false'&&!el('result-content').classList.contains('hidden'),'Comparison failed');
 click('result-report');html=await blobText();assert.match(html,/68\.36/);assert.match(html,/47\.66/);assert.match(html,/20\.7/);check('Comparison report preserves baseline, selected value and difference');
 click('decision-view-button');await runDecision();assert.match(el('decision-metrics').textContent,/Example site C/);assert.equal(el('decision-condition-chart').querySelectorAll('.readable-bar-row').length,8);
 click('decision-report-after-audit');html=await blobText();assert.match(html,/9\.57/);assert.match(html,/Optional/);assert.match(html,/No investigation is attached/);check('Offer report and on-screen chart distinguish optional tests, minimum required gain and absent audit');
 change('required-delivery_zero',true);await runDecision();click('decision-report');html=await blobText();assert.match(html,/Withdraw the recommendation/);check('Withdrawn offer report never presents a retained final offer');
 change('required-delivery_zero',false);const quote={1341:5,2072:0,1701:25,5191:7,1571:9,1761:14,1981:12,2870:18};for(const[bus,value]of Object.entries(quote))change('offer-price-'+bus,value);
 await runDecision();click('decision-report');html=await blobText();assert.match(html,/Select a different offer/);assert.match(html,/Example site H/);assert.match(html,/Required tests for the final offer/);check('A switched decision identifies the final offer and its own required-condition results');
 const count=blobs.length;change('decision-budget',501);click('decision-report');assert.equal(blobs.length,count);check('Changed inputs cannot export a stale human-readable decision');
 click('study-view-button');await waitFor(()=>el('study-view').dataset.ready==='true','Study not ready');click('study-report');html=await blobText();assert.match(html,/Recorded study case/);assert.match(html,/No current commercial value calculation/);check('Study export represents a missing cost calculation explicitly');
 click('tab-analyst');change('ai-profile','irish_conditional_flex');failAgent=true;click('agent-button');await waitFor(()=>el('agent-status').textContent==='Investigation failed'&&!el('search-button').disabled,'Injected failure did not finish');assert.equal(el('agent-export').disabled,true);assert.equal(el('agent-report').disabled,true);check('A failed new investigation cannot export the previous successful run');
 const R=dom.window.ActionLabReports;html=R.bars([{label:'Negative',value:-5},{label:'Missing',value:null},{label:'Positive',value:10}],'Signed values');parsed=parseHTML(html);assert.equal(parsed.window.document.querySelectorAll('.readable-bar').length,2);assert.match(parsed.window.document.body.textContent,/Not established/);assert.match(parsed.window.document.body.textContent,/-5 MW/);parsed.window.close();check('Negative values retain their sign and missing results are never rendered as zero');
 const unsafe=structuredClone(fixture.investigation);unsafe.records[0].candidate.action_id='<img src=x onerror="alert(1)">';html=R.html('investigation',unsafe,{profiles:fixture.profiles});parsed=parseHTML(html);assert.equal(parsed.window.document.querySelectorAll('img,script').length,0);parsed.window.close();check('Untrusted text is escaped in downloaded reports');
 change('ai-profile','reference_9bus');await waitFor(()=>/Baseline accepted wind/.test(el('evaluation-content').textContent),'Reference benchmark did not load');click('evidence-export');assert.equal(JSON.parse(await blobText()).evaluation.profile_id,'reference_9bus');check('Switching models also changes the exported benchmark profile');
 fs.mkdirSync(path.join(project,'readability-qa-results'),{recursive:true});
 fs.writeFileSync(path.join(project,'readability-qa-results/Example_AI_Report_EN.html'),R.html('investigation',fixture.investigation,{profiles:fixture.profiles}));
 assert.deepEqual(report.errors,[]);report.passed=true;
})().catch(e=>{report.passed=false;report.errors.push(e.stack||String(e));process.exitCode=1;}).finally(()=>{dom?.window.close();server?.child.kill();fs.mkdirSync(path.join(project,'validation'),{recursive:true});fs.writeFileSync(path.join(project,'validation/readable_reports.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,errors:report.errors,live_provider_test:false,visual_qa:false},null,2));});
