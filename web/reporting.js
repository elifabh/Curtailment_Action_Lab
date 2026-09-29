/* Readable views derived only from returned numerical records. No model calls. */
(() => {
'use strict';
const arr = x => Array.isArray(x) ? x : [];
const number = x => typeof x === 'number' && Number.isFinite(x);
const fmt = x => number(x) ? new Intl.NumberFormat('en-IE', {maximumFractionDigits:2}).format(x) : 'Not measured';
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const scope = 'Conditional model results. These snapshots do not establish field curtailment savings, customer profit or operating permission.';
const glossary = 'Example sites A–H represent hypothetical locations for 20 MW of flexible demand. They are examples, not confirmed customers. The source network names and IDs remain in Technical details.';
const aliases = Object.freeze({1341:'Example site A',2072:'Example site B',1701:'Example site C',5191:'Example site D',1571:'Example site E',1761:'Example site F',1981:'Example site G',2870:'Example site H'});
const reasonLabels = {offer_unavailable:'Offer unavailable',insufficient_offered_energy:'Insufficient offered energy',over_budget:'Above budget',below_requested_wind_gain:'Below the required wind gain',negative_assumed_surplus:'Costs exceed the assumed wind value',baseline_unverified:'Baseline unresolved: no valid comparison'};
const reasons = row => row.passes === true ? 'Passes the entered requirements' : arr(row.reasons).map(x=>reasonLabels[x] || String(x).replaceAll('_',' ')).join('; ') || 'Not established';
function technicalPoint(bus, context = {}) {
  const entry = arr(context.points).find(p => String(p.bus) === String(bus));
  if (entry) return `${entry.name} (network ID ${bus})`;
  for (const p of arr(context.profiles)) {
    const a = arr(p.actions).find(a => a.id === 'flex_at_' + bus);
    if (a) return a.name.replace(/^20 MW at /,'').replace(/\(bus /,'(network ID ');
  }
  return `Connection point ${bus}`;
}
function point(bus) { return aliases[bus] || `Connection point ${bus}`; }
function mapping(context = {}) {
  const ids = arr(context.points).length ? context.points.map(p=>p.bus) : [...new Set(arr(context.profiles).flatMap(p=>arr(p.actions).map(a=>/^flex_at_(\d+)$/.exec(a.id||'')?.[1]).filter(Boolean)))];
  if(!ids.length)return '';
  return '<details><summary>Technical details: network names behind the examples</summary>'+table(['Example label','Source network name and ID'],ids.map(id=>[point(id),technicalPoint(id,context)]))+'</details>';
}
function action(id, context = {}) {
  const match = /^flex_at_(\d+)$/.exec(id || '');
  if (match) return point(match[1]);
  for (const p of arr(context.profiles)) {
    const a = arr(p.actions).find(a => a.id === id);
    if (a) return a.name;
  }
  return id ? String(id).replaceAll('_',' ') : 'Option not identified';
}
function cards(values) {
  return '<div class="readable-cards">' + values.map(([label,value,unit])=>`<article><span>${esc(label)}</span><strong>${esc(number(value)?fmt(value):value ?? 'Not measured')}</strong>${unit?`<small>${esc(unit)}</small>`:''}</article>`).join('') + '</div>';
}
function table(head, rows) {
  return `<div class="readable-table-wrap"><table><thead><tr>${head.map(x=>`<th scope="col">${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(x=>`<td>${esc(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function bars(rows, title, unit = 'MW') {
  const values = rows.map(r=>r.value).filter(number), low = Math.min(0,...values), high = Math.max(0,...values), span = high-low || 1, zero = -low/span*100;
  return `<section class="readable-chart" aria-label="${esc(title)}"><h3>${esc(title)}</h3><p class="readable-note">All bars use the same scale. Exact values are shown alongside.</p>${rows.map(r=>{
    const left=number(r.value)?Math.min(zero,(r.value-low)/span*100):0,width=number(r.value)?Math.abs(r.value)/span*100:0;
    return `<div class="readable-bar-row"><div class="readable-bar-title"><strong>${esc(r.label)}</strong>${r.note?`<small>${esc(r.note)}</small>`:''}</div><div class="readable-bar-track" aria-hidden="true"><i class="readable-zero" style="left:${zero}%"></i>${number(r.value)?`<i class="readable-bar ${r.ok===false?'readable-failed':''}" style="left:${left}%;width:${width}%"></i>`:''}</div><span class="readable-bar-value">${number(r.value)?`${esc(fmt(r.value))} ${esc(unit)}`:'Not established'}</span></div>`;
  }).join('')}</section>`;
}
function selectedEvaluation(all, profileId) {
  if (!all) return null;
  if (all.profile_id === profileId) return all;
  if (all.conditional_study?.profile_id === profileId) return all.conditional_study;
  return {profile_id:profileId,status:'not_available',live_ai_status:'not_run',summary:'No matching saved benchmark is available for this model profile.',metrics:[]};
}
function investigationRows(value, context = {}) {
  const records = arr(value?.records).length ? value.records : arr(value?.tool_trace).map(x=>({candidate:x.arguments,result:x.result}));
  return records.map(r=>({label:action(r.candidate?.action_id,context),id:r.candidate?.action_id,value:r.result?.accepted_wind_mw,ok:r.result?.eligible === true,checks:arr(r.result?.checks),candidate:r.candidate,result:r.result,record_id:r.id}));
}
function investigation(value, context = {}) {
  if (!value) return '<p>No investigation is included in this export.</p>';
  const rows=investigationRows(value,context),eligible=rows.filter(r=>r.ok&&number(r.value)),best=eligible.reduce((a,b)=>!a||b.value>a.value?b:a,null);
  const live=value.is_live_provider===true,complete=value.status==='completed';
  let html=`<p class="readable-kicker">${live?'LIVE MICROSOFT AI':'DETERMINISTIC OR RECORDED SEARCH'}</p><h3>${complete?'Investigation completed':'Investigation incomplete'}</h3>`;
  html+=`<p>${best?`Best of the ${rows.length} inspected options: <strong>${esc(best.label)}</strong>, accepting <strong>${esc(fmt(best.value))} MW</strong> in this modelled snapshot.`:'No eligible numeric result was returned.'}</p>`;
  html+=cards([['Options inspected',rows.length,'returned records'],['Provider calls',value.provider_calls,'calls'],['Elapsed time',value.elapsed_seconds,'seconds']]);
  html+=`<p class="readable-note">${esc(value.candidate_evaluation_mode==='precomputed_verified_study'?'The AI inspected saved network calculations. No new power flow ran in this request.':'Numbers come from the returned model records.')}</p>`;
  const base=rows.find(r=>r.id==='flex_at_2072'&&r.ok&&number(r.value));
  if(best&&base&&value.request?.profile==='irish_conditional_flex')html+=`<p>Compared with example site B, the inspected baseline: <strong>${esc(fmt(best.value-base.value))} MW</strong> more wind accepted, with the same 20 MW hypothetical flexible demand.</p>`;
  html+=bars(rows.map(r=>({...r,note:r.ok?'Declared model checks passed':'Not eligible under the reported checks'})),'Wind accepted by each inspected option');
  html+=`<p class="readable-note">${esc(glossary)}</p>${mapping(context)}<p class="readable-note">A completed live AI call does not establish an advantage over a simple search. Comparative AI performance is not established by this session.</p>`;
  const errors=[...arr(value.errors),...arr(value.rejected)];
  if(errors.length)html+=`<p class="readable-warning">${errors.map(esc).join('; ')}</p>`;
  return html;
}
function comparison(payload, context={}) {
  const result=payload?.response||payload?.result;if(!result)return '<p>No comparison is included in this export.</p>';
  const req=payload.request||result.request||{},metrics=arr(result.metrics),wind=metrics.find(x=>x.key==='accepted_wind_mw');
  const summary=String(result.summary||'Inspect the returned model checks.').replaceAll('Cruiserath','example site B (baseline)');
  let html=`<h3>${esc(result.title||'Model comparison')}</h3><p>${esc(summary)}</p>`;
  if(wind)html+=bars([{label:req.profile==='irish_conditional_flex'?'Example site B (baseline)':'Baseline',value:wind.baseline},{label:action(req.action_id,context),value:wind.selected}],'Wind acceptance in the same model conditions');
  html+=table(['Measure','Baseline','Selected option','Difference'],metrics.map(m=>[`${m.label} (${m.unit||''})`,fmt(m.baseline),fmt(m.selected),fmt(m.delta)]));
  const checks=arr(result.checks);html+=`<p>${checks.filter(x=>x.passed===true).length} of ${checks.length} reported checks passed. This count covers only the checks declared by the model.</p>`;
  if(checks.some(c=>c.passed!==true))html+=`<p class="readable-warning">${checks.filter(c=>c.passed!==true).map(c=>esc(c.label||c.id)).join('; ')}</p>`;
  return html+mapping(context);
}
const decisionTitles={retain:'Keep the original offer under the selected conditions',switch:'Select a different offer after the required tests',withdraw:'Withdraw the recommendation under the selected conditions',no_nominal_offer:'No offer meets the starting requirements'};
function decision(payload,context={}) {
  const d=payload?.decision;if(!d)return '<p>No current decision is available. Run the offer comparison first.</p>';
  const req=d.inputs||{},rows=arr(d.nominal_offer_audit),required=arr(req.required_scenarios);
  let html=`<h3>${esc(decisionTitles[d.status]||d.status)}</h3>`;
  html+=cards([['Original offer',d.nominal?point(d.nominal.bus,context):'None'],['Offer after required tests',d.guarded?point(d.guarded.bus,context):'None'],['Lowest gain in required conditions',d.guarded?.minimum_tested_gain_MW,'MW'],['Assumed reservation cost',d.guarded?.assumed_offer_cost_EUR,'EUR']]);
  html+=`<p class="readable-note">${esc(glossary)}</p>${mapping(context)}`;
  html+=bars(rows.map(r=>({label:r.scenario_name,value:r.additional_wind_MW,ok:r.passes,note:`${required.includes(r.scenario_id)?'Required':'Optional'}: ${reasons(r)}`})),'Original offer under each tested condition');
  html+=`<p class="readable-note">The chart tests the original offer. A failed optional condition does not automatically withdraw it. On a switch, the final offer is identified above.</p>`;
  html+=table(['Assumption','Entered value'],[['Budget',`${fmt(req.budget_EUR)} EUR`],['Event duration',`${fmt(req.duration_hours)} hours`],['Additional wind value',`${fmt(req.wind_value_EUR_MWh)} EUR/MWh`],['Minimum wind gain',`${fmt(req.minimum_gain_MW)} MW`],['Require nonnegative assumed surplus',req.require_nonnegative_surplus?'Yes':'No']]);
  html+=table(['Condition','Required','Added wind (MW)','Assumed surplus (EUR)','Outcome'],rows.map(r=>[r.scenario_name,required.includes(r.scenario_id)?'Yes':'No',fmt(r.additional_wind_MW),fmt(r.assumed_surplus_EUR),reasons(r)]));
  if(d.guarded&&d.nominal&&d.guarded.bus!==d.nominal.bus){const guarded=arr(d.all_offer_results).filter(r=>r.bus===d.guarded.bus&&required.includes(r.scenario_id));html+='<h3>Required tests for the final offer</h3>'+table(['Condition','Added wind (MW)','Outcome'],guarded.map(r=>[r.scenario_name,fmt(r.additional_wind_MW),reasons(r)]));}
  html+='<h3>Data to confirm before using this decision</h3>'+(arr(d.data_priorities).length?'<ul>'+d.data_priorities.map(p=>`<li><strong>${esc(p.requested_data)}</strong>: ${esc(p.action)}</li>`).join('')+'</ul>':'<p>No additional priority emerged from the tested conditions. The original model limitations still apply.</p>');
  const a=payload.audit;html+='<h3>Investigation of the original offer</h3>'+(a?`<p>${esc(a.is_live_provider?'Live Microsoft AI':'Rule-based or recorded')} investigation: ${esc(a.status)}. ${esc(fmt(a.record_reads))} records inspected.</p>`+table(['Condition','Added wind (MW)','Outcome'],arr(a.records).map(r=>[r.scenario_name,fmt(r.additional_wind_MW),reasons(r)])):'<p>No investigation is attached to this decision.</p>');
  if(a?.error?.message)html+=`<p>${esc(a.error.message)}</p>`;
  if(a?.partial)html+='<p>The audit is incomplete. Only the listed records were inspected; uninspected conditions are not assumed to pass.</p>';
  const runs=Object.values(payload.audits||{});
  if(runs.length)html+='<h3>Audit run comparison</h3>'+table(['Method','Maximum reads','Records inspected','Failed conditions','Status'],runs.map(r=>[r.mode==='azure'?'Microsoft AI':'Fixed rule',r.budget,r.record_reads,r.counterexamples_found??arr(r.records).filter(x=>!x.passes).length,r.status]))+'<p>Compare runs at the same maximum read budget and check their completion status. A single run does not establish AI superiority.</p>';
  return html;
}
function study(payload,context={}) {
  const c=payload?.case;if(!c)return '<p>No study case is selected.</p>';
  let html=`<h3>Recorded study case ${esc(c.id)}</h3><p>${esc(c.comparable?'Paired model comparison available':c.reason||'Comparison blocked')}</p>`;
  if(c.comparable)html+=bars([{label:'Example site B (baseline)',value:c.baseline_wind_MW},{label:point(c.selected_bus||1341),value:c.selected_wind_MW}],'Wind accepted in this recorded case');
  const v=payload.value;if(v?.status==='conditional_calculation')html+=cards([['Additional energy under assumed duration',v.extra_wind_MWh,'MWh'],['Assumed scenario surplus',v.scenario_surplus_EUR,'EUR'],['Break-even premium',v.break_even_premium_EUR_per_flexible_MWh,'EUR/flexible MWh']])+`<p class="readable-note">Duration and prices are assumptions. This is not a chronological schedule or measured customer profit.</p>`;
  else html+=`<p>${esc(v?.reason||'No current commercial value calculation is included.')}</p>`;
  return html+mapping(context);
}
function evidence(payload,context) {
  let html='<h3>Evidence summary</h3>';
  if(payload.comparison)html+=comparison(payload.comparison,context);
  if(payload.investigation)html+=investigation(payload.investigation,context);
  const profileId=payload.selected_profile||payload.comparison?.request?.profile||payload.investigation?.request?.profile||payload.evaluation?.profile_id;
  const ev=selectedEvaluation(payload.evaluation,profileId);
  if(ev){html+='<h3>Saved comparative benchmark</h3>'+`<p>Model: ${esc(ev.profile_id)}. ${esc(ev.summary||'')}</p>`+table(['Measure','Value','Unit'],arr(ev.metrics).map(x=>[x.label,fmt(x.value),x.unit||'']));}
  const sources=arr(payload.sources).length?payload.sources:arr(payload.evidence?.sources);
  html+='<h3>Data sources</h3>'+table(['Source','Reference'],sources.map(s=>[s.name||s.title||s.label||'Source',s.url||s.path||s.description||'See complete data']));
  html+='<h3>Interpretation</h3><p>Public network data define the model. Added wind, customer flexibility and quoted prices are declared scenario assumptions. Numerical results describe those conditions only.</p>';
  return html;
}
const css=`.readable-view{font:14px/1.6 Arial,sans-serif;color:#193e35;overflow-wrap:anywhere}.readable-view h3{font-size:18px;margin:22px 0 10px}.readable-view p{margin:10px 0}.readable-kicker{font-size:11px;font-weight:700;letter-spacing:.08em;color:#37624f}.readable-note{font-size:12px;color:#50645d}.readable-warning{padding:12px;background:#fff3df;color:#763d15;border-left:4px solid #b7742c}.readable-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}.readable-cards article{background:#eff6f1;border:1px solid #d7e4da;border-radius:10px;padding:16px;min-width:0}.readable-cards span,.readable-cards small{display:block;font-size:12px}.readable-cards strong{display:block;font-size:23px;line-height:1.3;margin:8px 0}.readable-chart{margin:18px 0}.readable-bar-row{display:grid;grid-template-columns:minmax(140px,1.1fr) minmax(80px,1.3fr) minmax(90px,.5fr);align-items:center;gap:12px;margin:14px 0}.readable-bar-title small{display:block;color:#586a62;font-size:11px}.readable-bar-track{position:relative;height:18px;background:#edf1eb;border-radius:4px;overflow:hidden}.readable-bar{position:absolute;top:0;height:100%;background:#34705b}.readable-failed{background:#b3783c}.readable-zero{position:absolute;top:0;bottom:0;width:1px;background:#4e665a;z-index:1}.readable-bar-value{text-align:right;font-weight:700}.readable-table-wrap{overflow-x:auto;margin:16px 0}.readable-view table{width:100%;border-collapse:collapse;font-size:12px}.readable-view td,.readable-view th{padding:10px;text-align:left;border-bottom:1px solid #dce4dc;vertical-align:top}.readable-view th{background:#edf3ed}.readable-view details{margin:20px 0}.readable-view pre{white-space:pre-wrap;font-size:11px;max-height:260px;overflow:auto}.readable-view summary{cursor:pointer}.report-button{margin:6px}.report-feedback{font-size:12px;color:#416656}.readable-trace-card{padding:15px;border:1px solid #dbe5db;border-radius:10px;margin:12px 0}.readable-trace-card h4{margin:0 0 8px}.readable-trace-card p{margin:6px 0}@media(max-width:580px){.readable-bar-row{grid-template-columns:minmax(0,1fr) 90px;gap:6px}.readable-bar-title{grid-column:1/-1}.readable-cards{grid-template-columns:1fr}}@media print{.readable-view{font-size:11px}details{display:none}.readable-chart,.readable-cards article,tr{break-inside:avoid}.readable-bar{-webkit-print-color-adjust:exact;print-color-adjust:exact}}`;
function content(kind,payload,context={}) {
  return ({decision,investigation,comparison,study,evidence}[kind]||evidence)(payload,context);
}
function html(kind,payload,context={}) {
  const titles={decision:'Offer decision report',investigation:'AI and search investigation',comparison:'Model comparison report',study:'Recorded scenario report',evidence:'Evidence report'},title=titles[kind]||'Evidence report';
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>${css}body{margin:0;background:#f4f6f2}main{max-width:980px;margin:24px auto;padding:32px;background:white;border:1px solid #dce6dc;border-radius:16px}h1{font-size:30px;line-height:1.2}header{border-bottom:3px solid #34705b;padding-bottom:18px}@media(max-width:580px){main{padding:18px;margin:0;border-radius:0}}@media print{body{background:white}main{border:0;margin:0;padding:0}}</style></head><body><main class="readable-view"><header><p class="readable-kicker">CURTAILMENT ACTION LAB</p><h1>${esc(title)}</h1><p>${esc(scope)}</p><p class="readable-note">Generated ${esc(new Date().toISOString())}. Open this file in a browser. Use Print / Save as PDF for a paper copy.</p></header>${content(kind,payload,context)}<details><summary>Complete technical data</summary><pre>${esc(JSON.stringify(payload,null,2))}</pre></details></main></body></html>`;
}
function mount(target,kind,payload,context={}) {target.classList.add('readable-view');target.innerHTML=content(kind,payload,context);}
function download(kind,payload,context={}) {
  const blob=new Blob([html(kind,payload,context)],{type:'text/html;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=`actionlab-${kind}-report.html`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function addButton(anchorId,id,kind,getPayload,getContext=()=>({})) {
  const anchor=document.getElementById(anchorId);if(!anchor||document.getElementById(id))return;
  const b=document.createElement('button');b.type='button';b.id=id;b.className='button button-secondary compact report-button';b.textContent='Download readable report';
  const feedback=document.createElement('span');feedback.className='report-feedback';feedback.setAttribute('role','status');
  b.addEventListener('click',()=>{if(anchor.disabled)return;const data=getPayload();if(!data){feedback.textContent='Run the calculation first.';return;}download(kind,data,getContext());feedback.textContent='Report requested. Open the HTML file from your downloads.';});anchor.after(b);b.after(feedback);
  const sync=()=>{b.disabled=anchor.disabled;if(b.disabled)feedback.textContent='';};sync();new MutationObserver(sync).observe(anchor,{attributes:true,attributeFilter:['disabled']});return b;
}
const style=document.createElement('style');style.textContent=css;document.head.append(style);
window.ActionLabReports={action,point,technicalPoint,mapping,fmt,escape:esc,glossary,cards,bars,table,selectedEvaluation,investigationRows,investigation,comparison,decision,study,html,mount,download,addButton};
})();
