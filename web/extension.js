/* Fresh Irish planning experiments. Numerical answers only from the backend. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(v,d=2)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('en-IE',{minimumFractionDigits:d,maximumFractionDigits:d}):'Not established';
  let config=null,current=null,running=false,saved=false,timer=null;
  const resume=document.createElement('button');resume.id='resume-calculation';resume.type='button';resume.className='secondary';resume.textContent='Resume calculation status';resume.hidden=true;$('error').after(resume);
  const remember=job=>{try{if(job)sessionStorage.setItem('fresh_irish_job',job);else sessionStorage.removeItem('fresh_irish_job');}catch(_){/* The calculation still works when browser storage is unavailable. */}};
  const remembered=()=>{try{return sessionStorage.getItem('fresh_irish_job');}catch(_){return null;}};
  const timing=document.createElement('p');timing.className='help';timing.id='runtime-hint';$('run').before(timing);
  function modeFields(){const pilot=$('kind').value==='pilot';$('snapshot-fields').hidden=pilot;$('pilot-fields').hidden=!pilot;for(const id of ['wind','demand']){$(id).required=!pilot;$(id).disabled=running||pilot;}$('profile').disabled=running||!pilot;
    const id=!pilot?'snapshot_example':$('profile').value==='wind_shape_fixed_demand'?'pilot_fixed_demand':'pilot_observed_demand';const seconds=config?.saved_examples.find(x=>x.id===id)?.recorded_elapsed_seconds;
    timing.textContent=Number.isFinite(seconds)?`The included example took about ${seconds<90?Math.ceil(seconds)+' seconds':Math.ceil(seconds/60)+' minutes'} to calculate in its preparation environment. Runtime on this computer may differ. Opening a saved calculation does not rerun it.`:'';
  }
  const metric=(value,label,accent=false)=>`<div class="metric${accent?' accent':''}"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`;
  async function api(url,payload){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const r=await fetch(url,{...(payload?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}:{}),signal:controller.signal});
      const j=await r.json();if(!r.ok){const e=Error(j.error||'The request could not complete.');e.httpStatus=r.status;throw e;}return j;
    }finally{clearTimeout(timeout);}
  }
  function input(){
    const p={kind:$('kind').value,candidate_bus:Number($('candidate').value),flex_MW:Number($('flex').value),line_outage:$('outage').checked};
    if(p.kind==='snapshot')Object.assign(p,{wind_available_MW:Number($('wind').value),load_factor:Number($('demand').value)});
    else p.profile_mode=$('profile').value;
    return p;
  }
  function busy(value){
    running=value;document.querySelector('.results').setAttribute('aria-busy',String(value));
    $('run').disabled=value||!config?.available;$('example').disabled=value||!config?.example_available;
    for(const el of $('fresh-form').querySelectorAll('input,select'))el.disabled=value;
    modeFields();
  }
  function error(message){$('error').textContent=message;$('error').hidden=false;busy(false);}
  function failedChecks(curve){
    const totals={};for(const r of curve.tested_points||[]){
      if(r.passes_declared_snapshot_checks)continue;
      if(!r.solver_converged)totals['Non-converged or dispatch-blocked points']=(totals['Non-converged or dispatch-blocked points']||0)+1;
      for(const [k,v] of Object.entries(r.violations||{}))if(v)totals[k.replaceAll('_',' ')]=(totals[k.replaceAll('_',' ')]||0)+1;
    }
    return Object.entries(totals).map(([k,v])=>`${esc(k)}: ${v} tested points`).join('; ')||'No failed check among the returned search points.';
  }
  function checkRows(c){
    return ['baseline','selected'].map(side=>{const r=c[side].best_tested;
      return `<tr><td>${side==='baseline'?'Example B':'Selected site'}</td><td class="${r?'ok':'blocked'}">${r?'Passing point found':'No passing tested point'}</td><td>${r?esc(r.id):'—'}</td><td class="num">${r?fmt(r.direct_balance_max_MVA,8):'—'}</td></tr>`;}).join('');
  }
  function profileRows(rows){return rows.map(r=>{const c=r.comparison,a=c.baseline.best_tested,b=c.selected.best_tested;return `<tr><td>${esc(r.timestamp_utc.slice(11,16))}</td><td class="num">${fmt(r.assumed_local_wind_available_MW)}</td><td class="num">${a?fmt(a.wind_MW):'—'}</td><td class="num">${b?fmt(b.wind_MW):'—'}</td><td class="num">${c.comparable?fmt(c.additional_hypothetical_wind_MW):'—'}</td><td class="${c.comparable?'ok':'blocked'}">${c.comparable?'Comparable':'Blocked'}</td></tr>`;}).join('');}
  function chart(rows){
    const values=rows.flatMap(r=>['baseline','selected'].map(k=>r.comparison[k].best_tested?.wind_MW)).filter(Number.isFinite);
    if(!values.length)return '<p class="notice warning">No passing wind-acceptance points to plot.</p>';
    const W=760,H=230,L=55,R=15,T=20,B=35,max=Math.max(...values,1)*1.12;
    const x=i=>L+i*(W-L-R)/Math.max(1,rows.length-1),y=v=>H-B-v*(H-T-B)/max;
    const pieces=['baseline','selected'].map((key,j)=>{let parts=[],segment=[];
      rows.forEach((r,i)=>{const v=r.comparison[key].best_tested?.wind_MW;if(Number.isFinite(v)){segment.push(`${x(i)},${y(v)}`);}else if(segment.length){parts.push(segment);segment=[];}});if(segment.length)parts.push(segment);
      return parts.map(s=>`<polyline points="${s.join(' ')}" fill="none" stroke="${j?'#066d5e':'#8496a8'}" stroke-width="3"/>`).join('')+rows.map((r,i)=>{const v=r.comparison[key].best_tested?.wind_MW;return Number.isFinite(v)?`<circle cx="${x(i)}" cy="${y(v)}" r="3" fill="${j?'#066d5e':'#8496a8'}"/>`:'';}).join('');});
    return `<div class="chart"><div class="legend"><span><i></i>Example B</span><span><i class="selected"></i>Selected site</span></div><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Modelled hypothetical wind accepted over the pilot. Missing points are gaps."><path d="M${L},${T}V${H-B}H${W-R}" fill="none" stroke="#cad6db"/><text x="${L}" y="13" fill="#53686f" font-size="11">Wind accepted (MW)</text><text x="${L-8}" y="${H-B+4}" text-anchor="end" font-size="11">0</text><text x="${L-8}" y="${y(max*.8)+4}" text-anchor="end" font-size="11">${Math.round(max*.8)}</text>${pieces.join('')}${rows.filter((_,i)=>i%2===0).map(r=>{const i=rows.indexOf(r);return `<text x="${x(i)}" y="${H-12}" text-anchor="middle" fill="#53686f" font-size="11">${esc(r.timestamp_utc.slice(11,16))}</text>`;}).join('')}</svg><p class="help">UTC interval starts. Gaps are failed or unavailable model points, not zero wind.</p></div>`;
  }
  function render(result,isSaved=false){
    $('progress').hidden=true;$('progress').classList.remove('warning');
    current=result;saved=isSaved;$('empty').hidden=true;$('result').hidden=false;
    const p=result.inputs;
    let body=`<div class="panel"><div class="result-head"><div><h2>${p.kind==='snapshot'?'New-condition comparison':'Six-hour planning experiment'}</h2><p>${esc(result.calculation_id)} · ${result.new_power_flows_run} AC calculations in this run</p></div><span class="tag">${isSaved?'SAVED EXAMPLE':'FRESH CALCULATION'}</span></div>`;
    const site=config?.candidates.find(x=>x.bus===p.candidate_bus);
    body+=`<p class="help">Selected connection: ${esc(site?.name||'model node')} (${p.candidate_bus}). Baseline: Example B (2072). Assumed line 1341–1701 status: ${p.line_outage?'unavailable':'in service'}.</p>`;
    if(p.kind==='snapshot'){
      const c=result.comparison,a=c.baseline.best_tested,b=c.selected.best_tested;
      body+=`<p class="notice${c.comparable?'':' warning'}">${c.comparable?'Both alternatives have a passing tested point under the declared model checks.':esc(c.block_reason)}</p><div class="metrics">${metric(a?fmt(a.wind_MW)+' MW':'Not established','Example B: wind accepted')}${metric(b?fmt(b.wind_MW)+' MW':'Not established','Selected site: wind accepted')}${metric(c.comparable?fmt(c.additional_hypothetical_wind_MW)+' MW':'Blocked','Difference in hypothetical wind acceptance',true)}</div><p>${fmt(p.flex_MW)} MW load at each alternative; ${fmt(p.wind_available_MW)} MW hypothetical wind available; source demand ×${fmt(p.load_factor,3)}.</p><div class="table-wrap"><table><thead><tr><th>Alternative</th><th>Model checks</th><th>Record</th><th>Balance residual (MVA)</th></tr></thead><tbody>${checkRows(c)}</tbody></table></div><p class="help">Search resolution 0.25 MW. Best tested point; no global optimum certificate.</p><details><summary>Failed points and energy balance</summary><p class="help">Example B: ${failedChecks(c.baseline)}</p><p class="help">Selected site: ${failedChecks(c.selected)}</p><p class="help">Other generation change: ${fmt(c.change_other_generation_MW)} MW. Network-loss change: ${fmt(c.change_network_losses_MW)} MW. Paired balance difference: ${fmt(c.energy_balance_difference_MW,8)} MW.</p></details>`;
    }else{
      const s=result.summary;
      body+=`<p class="help">Period: ${esc(result.profile.start_utc)} to ${esc(result.profile.end_utc_exclusive)}. Twelve consecutive half-hours; end timestamp is exclusive.</p>`;
      body+=`<p class="notice${s.full_period_result_available?'':' warning'}">${s.full_period_result_available?'All twelve interval comparisons pass the declared checks.':'The full-period energy result is blocked because one or more interval comparisons did not pass.'}</p><div class="metrics">${metric(`${s.comparable_intervals} / ${s.intervals}`,'Comparable half-hours')}${metric(s.full_period_result_available?fmt(s.full_period_change_MWh)+' MWh':'Not established','Full-period change in hypothetical wind acceptance',true)}${metric(fmt(result.service.energy_each_alternative_MWh)+' MWh','Identical scheduled load energy at each site')}</div><p class="help">${p.profile_mode==='wind_shape_fixed_demand'?'Observed wind shape; source demand and dispatch remain fixed.':'Observed national demand is allocated using fixed source shares. Generator redispatch is an assumption.'} Local wind, line status and the flexible asset are model assumptions.</p>${chart(result.interval_results)}<div class="table-wrap"><table><thead><tr><th>UTC</th><th>Available MW</th><th>B MW</th><th>Selected MW</th><th>Change MW</th><th>Comparison</th></tr></thead><tbody>${profileRows(result.interval_results)}</tbody></table></div><p class="help">Signed subtotal over comparable intervals only: ${fmt(s.comparable_intervals_subtotal_MWh)} MWh. Blocked intervals: ${s.blocked_intervals}. Adverse comparable intervals: ${s.adverse_intervals}. A partial subtotal is not the six-hour total.</p><p class="help">The experiment does not establish annual avoided curtailment. Generator technology, ramping, commitment and local operational histories remain unverified.</p>`;
    }
    body+=`<details><summary>Assumptions and calculation limits</summary><ul>${result.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p class="help">Network source SHA-256: <code>${esc(result.source_sha256)}</code></p></details><div class="actions"><button id="download-json">Download calculation JSON</button><button id="download-report" class="secondary">Download readable report</button><button id="print-report" class="secondary">Print / save PDF</button></div></div>`;
    $('result').innerHTML=body;
    $('download-json').onclick=()=>download(JSON.stringify(current,null,2),'application/json',`${current.calculation_id}.json`);
    $('download-report').onclick=()=>{
      const report=$('result').cloneNode(true);report.querySelector('.actions')?.remove();report.querySelectorAll('details').forEach(x=>x.setAttribute('open',''));
      const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>Irish planning calculation</title><style>body{font:16px/1.55 system-ui,sans-serif;color:#16323b;max-width:1100px;margin:40px auto;padding:25px}h2{font-size:28px}.metrics{display:flex;gap:30px;margin:25px 0}.metric{flex:1}.metric strong,.metric span{display:block}.metric strong{font-size:28px}.metric span,.help{color:#566b73;font-size:13px}.notice{background:#edf5f2;padding:16px}.warning{background:#fff3da}td,th{padding:10px;border-bottom:1px solid #dae4e7;text-align:left}table{width:100%;border-collapse:collapse;font-size:13px}svg{width:100%;height:auto}code{overflow-wrap:anywhere}li{margin:8px 0}.tag{font-size:12px}details{margin-top:20px}.legend{font-size:12px}.legend i{display:inline-block;width:16px;height:3px;background:#8496a8;margin-right:5px}.legend i.selected{background:#066d5e}</style><h1>Curtailment Action Lab</h1><p>Conditional planning calculation. No field savings or operating clearance.</p>${report.innerHTML}</html>`;
      download(html,'text/html',`${current.calculation_id}_report.html`);
    };
    $('print-report').onclick=()=>window.print();
  }
  function download(data,type,name){const u=URL.createObjectURL(new Blob([data],{type}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);}
  async function poll(job,failures=0){
    clearTimeout(timer);resume.hidden=true;
    try{const r=await api('/api/extension-status',{job_id:job});
      $('error').hidden=true;
      $('progress').textContent=`Calculating… ${r.new_power_flows_run||0} new AC calculations.${r.total_intervals?` ${r.completed_intervals||0}/${r.total_intervals} intervals complete.`:''}${Number.isFinite(r.elapsed_seconds)?` ${Math.floor(r.elapsed_seconds)} seconds elapsed.`:''}`;
      if(r.status==='completed'){$('progress').hidden=true;busy(false);remember(null);render(r.result);return;}
      if(r.status==='failed'){remember(null);$('progress').hidden=true;error(r.error||'Calculation failed.');return;}
      timer=setTimeout(()=>poll(job),1500);
    }catch(e){
      if(e.httpStatus===400){remember(null);$('progress').hidden=true;error(e.message);return;}
      if(failures<3){$('progress').hidden=false;$('progress').textContent='Connection interrupted. Retrying the calculation status…';timer=setTimeout(()=>poll(job,failures+1),1500*(failures+1));return;}
      $('progress').hidden=true;error('Cannot read calculation status. The job may still be running. Resume the status check when the server is available.');resume.hidden=false;$('run').disabled=true;resume.onclick=()=>{$('error').hidden=true;busy(true);$('progress').hidden=false;poll(job);};
    }
  }
  $('kind').onchange=modeFields;
  $('profile').onchange=modeFields;
  $('fresh-form').onsubmit=async event=>{event.preventDefault();if(running)return;$('error').hidden=true;resume.hidden=true;busy(true);$('progress').hidden=false;$('progress').textContent='Starting a fresh calculation…';try{const r=await api('/api/extension-start',input());remember(r.job_id);poll(r.job_id);}catch(e){$('progress').hidden=true;error(e.message);}};
  $('example').onclick=async()=>{if(running)return;busy(true);try{$('error').hidden=true;const route={snapshot_example:'/api/extension-example',pilot_fixed_demand:'/api/extension-pilot-fixed',pilot_observed_demand:'/api/extension-pilot-demand'}[$('recording').value];const r=await api(route);render(r.result,true);}catch(e){error(e.message);}finally{busy(false);}};
  $('fresh-form').addEventListener('input',()=>{if(current&&!running){$('progress').hidden=false;$('progress').classList.add('warning');$('progress').textContent='Inputs changed. The displayed result retains its original recorded inputs. Run again to update it.';}});
  api('/api/extension-config').then(c=>{config=c;$('candidate').innerHTML=c.candidates.map((x,i)=>`<option value="${x.bus}">Example ${String.fromCharCode(65+i)} — ${esc(x.name)} (${x.bus})</option>`).join('');$('candidate').value=String(c.default.candidate_bus);$('recording').innerHTML=c.saved_examples.map(x=>`<option value="${esc(x.id)}">${esc(x.label)}</option>`).join('');$('availability').textContent=c.available?'Fresh Irish calculation engine is available. A scenario may take around a minute; the twelve-interval pilot takes longer.':c.install_instructions;$('availability').classList.toggle('warning',!c.available);busy(false);const job=remembered();if(job){busy(true);$('progress').hidden=false;poll(job);}}).catch(e=>error(e.message));
  // Narrow public helpers for deterministic DOM verification, not additional UI actions.
  window.ActionLabExtension={render,integrateDisplay:profileRows};
})();
