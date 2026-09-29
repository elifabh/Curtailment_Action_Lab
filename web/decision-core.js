/* Same finite decision rules as decision_service.py; usable without a server. */
(function(root){'use strict';
const num=(v,name,lo,hi)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<lo||v>hi)throw Error(`${name} must be a finite number from ${lo} to ${hi}.`);return v;};
function validate(p,d){
 const keys=['budget_EUR','duration_hours','wind_value_EUR_MWh','minimum_gain_MW','require_nonnegative_surplus','required_scenarios','offers'];
 if(!p||typeof p!=='object'||Array.isArray(p)||Object.keys(p).sort().join()!==keys.sort().join())throw Error('Supply exactly the documented decision fields.');
 const x=JSON.parse(JSON.stringify(p));
 for(const[k,lo,hi]of[['budget_EUR',0,1e6],['duration_hours',.01,24],['wind_value_EUR_MWh',-1000,10000],['minimum_gain_MW',.5,200]])x[k]=num(p[k],k,lo,hi);
 if(typeof p.require_nonnegative_surplus!=='boolean')throw Error('The surplus condition must be boolean.');
 const ids=d.scenarios.map(s=>s.id),r=p.required_scenarios;
 if(!Array.isArray(r)||!r.length||r.some(s=>typeof s!=='string'||!ids.includes(s))||new Set(r).size!==r.length||!r.includes('nominal'))throw Error('Required conditions must be distinct declared scenario IDs and include nominal.');
 if(!Array.isArray(p.offers)||p.offers.length!==d.candidates.length)throw Error('Supply one offer for each declared candidate.');
 const seen=new Set();
 for(const o of p.offers){if(!o||Object.keys(o).sort().join()!==['bus','premium_EUR_MWh','available','energy_MWh'].sort().join())throw Error('An offer requires bus, premium_EUR_MWh, available and energy_MWh.');
 if(!Number.isInteger(o.bus)||!d.candidates.some(c=>c.bus===o.bus)||seen.has(o.bus)||typeof o.available!=='boolean')throw Error('Offer IDs must be unique declared buses and availability must be boolean.');
 seen.add(o.bus);num(o.premium_EUR_MWh,'premium',0,10000);num(o.energy_MWh,'energy_MWh',0,1e5);}
 return x;
}
function evaluateCell(p,bus,sid,d){
 const o=p.offers.find(x=>x.bus===bus),c=d.cells.find(x=>x.bus===bus&&x.scenario_id===sid),s=d.scenarios.find(x=>x.id===sid),cost=20*p.duration_hours*o.premium_EUR_MWh,reasons=[];
 if(!o.available)reasons.push('offer_unavailable');if(o.energy_MWh+1e-9<20*p.duration_hours)reasons.push('insufficient_offered_energy');if(cost>p.budget_EUR+1e-9)reasons.push('over_budget');
 const gain=c.comparable?c.additional_wind_MW:null,energy=gain===null?null:gain*p.duration_hours,surplus=energy===null?null:energy*p.wind_value_EUR_MWh-cost;
 if(!c.comparable)reasons.push(c.block_reason);else{if(gain+1e-9<p.minimum_gain_MW)reasons.push('below_requested_wind_gain');if(p.require_nonnegative_surplus&&surplus< -1e-9)reasons.push('negative_assumed_surplus');}
 return{bus,scenario_id:sid,scenario_name:s.name,dimension:s.dimension,passes:!reasons.length,reasons,additional_wind_MW:gain,assumed_extra_wind_MWh:energy,reserved_flex_MWh:20*p.duration_hours,scenario_delivered_flex_MWh:s.flex_MW*p.duration_hours,assumed_offer_cost_EUR:cost,assumed_surplus_EUR:surplus,physical_record:c,new_power_flows_run:0};
}
const fields={wind:['Local wind availability and forecast','Confirm the wind conditions during the proposed event.'],delivery:['Metered flexibility and reserve obligations','Confirm delivered power and energy, deadlines and protected reserve before booking flexibility.'],demand:['Reviewed demand and generation dispatch','Confirm the operating point and redispatch/control scope. A failed fixed-control baseline needs model review.'],network:['Operator-confirmed network state','Confirm the line status, usable ratings and permitted controls.']};
function analyse(input,d){const started=performance.now(),p=validate(input,d),allrows=p.offers.flatMap(o=>d.scenarios.map(s=>evaluateCell(p,o.bus,s.id,d)));
 const nominal=allrows.filter(x=>x.scenario_id==='nominal'&&x.passes).sort((a,b)=>b.additional_wind_MW-a.additional_wind_MW||a.assumed_offer_cost_EUR-b.assumed_offer_cost_EUR||a.bus-b.bus),n=nominal[0]||null,choices=[];
 for(const o of p.offers){const needed=allrows.filter(x=>x.bus===o.bus&&p.required_scenarios.includes(x.scenario_id));if(needed.every(x=>x.passes))choices.push({bus:o.bus,minimum_tested_gain_MW:Math.min(...needed.map(x=>x.additional_wind_MW)),minimum_assumed_surplus_EUR:Math.min(...needed.map(x=>x.assumed_surplus_EUR)),assumed_offer_cost_EUR:needed[0].assumed_offer_cost_EUR,required_records:needed.map(x=>x.physical_record.id)});}
 choices.sort((a,b)=>b.minimum_tested_gain_MW-a.minimum_tested_gain_MW||a.assumed_offer_cost_EUR-b.assumed_offer_cost_EUR||a.bus-b.bus);const g=choices[0]||null,status=!n?'no_nominal_offer':!g?'withdraw':n.bus===g.bus?'retain':'switch';
 const audit=allrows.filter(x=>n&&x.bus===n.bus),priorities=[];
 for(const[dim,[field,action]]of Object.entries(fields)){const bad=audit.filter(x=>x.dimension===dim&&!x.passes);if(bad.length)priorities.push({dimension:dim,requested_data:field,action,affected_required_conditions:bad.filter(x=>p.required_scenarios.includes(x.scenario_id)).length,counterexample_records:bad.map(x=>x.physical_record.id),failed_tested_conditions:bad.length});}
 priorities.sort((a,b)=>b.affected_required_conditions-a.affected_required_conditions||b.failed_tested_conditions-a.failed_tested_conditions||a.dimension.localeCompare(b.dimension));
 return{status,inputs:p,nominal:n,guarded:g,eligible_guarded_choices:choices,nominal_offer_audit:audit,all_offer_results:allrows,data_priorities:priorities,contract_conditions:{reserved_power_MW:20,assumed_duration_hours:p.duration_hours,required_scenarios:p.required_scenarios,operating_permission:false,execution:'Advisory only. No contract, bid or device command is sent.'},scope:'Conditional selection among eight hypothetical 20 MW offers using checked planning-model records.',limitations:[...d.limitations,'Passing all selected tests is not a guarantee outside the finite tested set.','Reservation cost uses all quoted 20 MW even in lower-delivery stress cases.','Priority means observed decision sensitivity, not a measured monetary value of information.'],source_sha256:d.source_sha256,protocol_sha256:d.protocol_sha256,record_reads:allrows.length,new_power_flows_run:0,elapsed_seconds:(performance.now()-started)/1000,field_savings:false,customer_profit_established:false};
}
const api={validate,evaluateCell,analyse};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ActionLabDecision=api;
})(typeof window!=='undefined'?window:globalThis);
