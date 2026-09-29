'use strict';
// Layout regression only. Saved examples are displayed without new power flows.
const {withBrowser}=require('./browser_harness');
const path=require('node:path');
const project=path.resolve(__dirname,'..');
withBrowser({project,port:Number(process.env.QA_PORT||8886),output:path.join(project,'browser-qa-results/extension-layout'),run:async({browser,base,assert,result,output})=>{
 const page=await browser.newPage({viewport:{width:390,height:844}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/extension');await page.waitForFunction(()=>!document.querySelector('#example').disabled);
 for(const example of ['snapshot_example','pilot_fixed_demand','pilot_observed_demand']){
  await page.locator('#recording').selectOption(example);await page.locator('#example').click();await page.waitForFunction(()=>!document.querySelector('#example').disabled&&!document.querySelector('#result').hidden);
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:900});
   const dims=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
   assert.ok(dims.scroll<=dims.width+1,`${example}: page overflow ${dims.scroll} > ${dims.width}`);
   result.checks.push({name:`${example}: no page overflow at ${width}px`,passed:true});
  }
 }
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:path.join(output,'mobile-fixed.png'),fullPage:true});
 assert.deepEqual(errors,[]);result.checks.push({name:'No browser JavaScript exceptions',passed:true});
 result.new_power_flows_run=0;result.scope='Layout regression using saved examples after the real calculation acceptance run.';
 await page.close();
}}).then(r=>{console.log(JSON.stringify({passed:r.passed,checks:r.checks.length,errors:r.errors}));if(!r.passed)process.exitCode=1;});
