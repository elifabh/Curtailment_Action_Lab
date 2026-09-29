'use strict';const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),root=path.resolve(__dirname,'..');const core=require('../web/decision-core.js'),d=JSON.parse(fs.readFileSync(path.join(root,'evaluation/decision_parity_fixtures.json'),'utf8'));
for(const c of d.cases){const actual=core.analyse(c.input,d.matrix);delete actual.elapsed_seconds;assert.deepEqual(actual,c.expected);}
console.log(JSON.stringify({passed:true,python_javascript_cases:d.cases.length}));
