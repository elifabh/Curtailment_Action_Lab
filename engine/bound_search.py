"""Reproduce bounded fixed-policy outage screen. Not a global optimum or safe plan."""
import json
from pathlib import Path
from scenario_screen import evaluate
ROOT=Path(__file__).parent
rows=[]
a=evaluate(100,True);rows.append(a)
b=evaluate(200,True);rows.append(b)
lo=100 if a['screen_pass'] else 0;hi=200
if b['screen_pass']:lo=200
else:
 while hi-lo>1:
  mid=(hi+lo)/2;r=evaluate(mid,True);rows.append(r)
  if r['screen_pass']:lo=mid
  else:hi=mid
(ROOT/'wind_limit_search.json').write_text(json.dumps({'hypothetical_available_wind_MW':200,'outage_feasible_lower_bound_MW':lo,'outage_infeasible_upper_bound_MW':hi,'search_scope':'Fixed redispatch rule and declared transmission screening predicate; collector issues remain unresolved. No global optimization claim.','rows':rows},indent=2))
