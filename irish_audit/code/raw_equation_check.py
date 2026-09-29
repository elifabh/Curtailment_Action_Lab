"""Separate direct-text RAW electrical check using winding-side voltages.

Does not use the legacy transformer's converted R/X/tap fields or PYPOWER Ybus.
Checks the electrical transformation, not the omitted PSS/E control dynamics.
"""
import json
from functools import lru_cache
import numpy as np
from source_audit import rows
from fixed_case import ROOT

@lru_cache(maxsize=1)
def _source_rows():
    # The audit fixes and checks the RAW SHA-256 before evaluating scenarios.
    # Cache text parsing, not converted network equations or numerical results.
    return rows(ROOT/'TYTFS2024_WP2024_V33.raw')[1]

def verify(out,meta,*,tap_changes=None,shunt_off=(),branch_off=(),wind_mw=0.,wind_bus=1341,extra_load=None):
    tap_changes=tap_changes or {}
    data=_source_rows()
    base=float(out['baseMVA']);ids=meta['source_ids']
    v=out['bus'][:,7]*np.exp(1j*np.deg2rad(out['bus'][:,8]))
    rawbus={int(r[0]):r for r in data['BUS']}
    def V(i):return v[ids[i]] if i in ids else float(rawbus[i][7])*np.exp(1j*np.deg2rad(float(rawbus[i][8])))
    powers=np.zeros(len(v),complex);flows={};source_ratings={};ties=0
    def add(i,z):
        if i in ids:powers[ids[i]]+=z
    def store(name,i,j,pf,pt,rate):
        flows[name]=(pf,pt);source_ratings[name]=rate;add(i,pf);add(j,pt)
    for r in data['BRANCH']:
        i,j,ckt=int(r[0]),abs(int(r[1])),r[2].strip();name=f'line:{i}:{j}:{ckt}'
        active=bool(int(r[13])) and name not in branch_off
        if not active:
            if name in meta['branch_names']:flows[name]=(0j,0j);source_ratings[name]=float(r[6])
            continue
        R,X,B=map(float,r[3:6]);yi=complex(float(r[9]),float(r[10]));yj=complex(float(r[11]),float(r[12]))
        add(i,base*abs(V(i))**2*np.conj(yi));add(j,base*abs(V(j))**2*np.conj(yj))
        if R==0 and abs(X)<=1.00001e-4:
            assert ids[i]==ids[j]
            add(i,-1j*base*B*abs(V(i))**2/2);add(j,-1j*base*B*abs(V(j))**2/2);ties+=1;continue
        I=(V(i)-V(j))/complex(R,X)
        pf=base*V(i)*np.conj(I+1j*B*V(i)/2)
        pt=base*V(j)*np.conj(-I+1j*B*V(j)/2)
        store(name,i,j,pf,pt,float(r[6]))
    tables={int(r[0]):[(float(r[k]),float(r[k+1])) for k in range(1,len(r)-1,2) if float(r[k+1])>0] for r in data['IMPEDANCE CORRECTION']}
    def factor(w):
        tab=int(w[13])
        if not tab:return 1.
        points=tables[tab];x=float(w[2]) if abs(int(w[6]))==3 else float(w[0])
        return float(np.interp(x,[p[0] for p in points],[p[1] for p in points]))
    pos=0;number=0;two=0;three=0
    while pos<len(data['TRANSFORMER']):
        p=data['TRANSFORMER'][pos];q=data['TRANSFORMER'][pos+1]
        i,j,k=int(p[0]),int(p[1]),int(p[2]);ckt=p[3].strip();status=int(p[11]);cz=int(p[5])
        windings=[list(data['TRANSFORMER'][pos+2]),list(data['TRANSFORMER'][pos+3])]
        if k:windings.append(list(data['TRANSFORMER'][pos+4]))
        pos+=5 if k else 4;number+=1
        if not status:continue
        assert int(p[4])==1 and int(p[6])==1 and cz in [1,2]
        add(i,base*abs(V(i))**2*np.conj(complex(float(p[7]),float(p[8]))))
        def z(off):return complex(float(q[off]),float(q[off+1]))*(1 if cz==1 else base/float(q[off+2]))
        if not k:
            name=f'trafo:{i}:{j}:{ckt}';w1,w2=windings
            w1[0]=tap_changes.get(name,float(w1[0]))
            e1=V(i)/float(w1[0])*np.exp(-1j*np.deg2rad(float(w1[2])))
            e2=V(j)/float(w2[0]);I=(e1-e2)/(z(0)*factor(w1))
            store(name,i,j,base*e1*np.conj(I),-base*e2*np.conj(I),float(w1[3]));two+=1
        else:
            z12,z23,z31=z(0),z(3),z(6)
            arms=[(z12+z31-z23)/2,(z12+z23-z31)/2,(z23+z31-z12)/2]
            star=1_000_000+number-1
            for n,(bus,w,Z) in enumerate(zip((i,j,k),windings,arms),1):
                name=f'trafo3:{i}:{j}:{k}:{ckt}:{n}'
                active=status==1 or status==2 and n!=2 or status==3 and n!=3 or status==4 and n!=1
                if not active:
                    flows[name]=(0j,0j);source_ratings[name]=float(w[3]);continue
                w[0]=tap_changes.get(name,float(w[0]))
                E=V(bus)/float(w[0])*np.exp(-1j*np.deg2rad(float(w[2])))
                E_star=v[ids[star]];I=(E-E_star)/(Z*factor(w))
                store(name,bus,star,base*E*np.conj(I),-base*E_star*np.conj(I),float(w[3]))
            three+=1
    for r in data['LOAD']:
        if int(r[2]) and int(r[0]) in ids:
            assert all(float(x)==0 for x in r[7:11]),'This check is for the supplied constant-power case only.'
            add(int(r[0]),complex(float(r[5]),float(r[6])))
    for r in data['FIXED SHUNT']:
        if int(r[2]):add(int(r[0]),complex(float(r[3]),-float(r[4]))*abs(V(int(r[0])))**2)
    for r in data['SWITCHED SHUNT']:
        bus=int(r[0])
        if int(r[3]) and bus not in shunt_off:add(bus,-1j*float(r[9])*abs(V(bus))**2)
    gen_rows=[r for r in data['GENERATOR'] if int(r[0]) in ids]
    gen_ids=[int(r[0]) for r in gen_rows]
    assert len(gen_ids)==len(out['gen'])
    for bus,g in zip(gen_ids,out['gen']):
        if g[7]>0:add(bus,-complex(g[1],g[2]))
    for h in meta['source_import']['hvdc_terminal_boundary_injections']:
        add(h['bus'],-complex(h['P_MW'],h['Q_Mvar']))
    add(wind_bus,-wind_mw)
    for bus,p in (extra_load or {}).items():add(int(bus),p)
    errs=[];rateerrs=[]
    for n,r in zip(meta['branch_names'],out['branch']):
        pf,pt=flows[n]
        errs.append(max(abs(pf-complex(r[13],r[14])),abs(pt-complex(r[15],r[16]))))
        rateerrs.append(abs(source_ratings[n]-r[5]))
    bound_errors=[]
    original_groups={}
    for bid,r in rawbus.items():
        if bid in ids:original_groups.setdefault(ids[bid],[]).append(r)
    for group,original in original_groups.items():
        if original:
            bound_errors.extend([abs(out['bus'][group,11]-min(float(r[9]) for r in original)),
                abs(out['bus'][group,12]-max(float(r[10]) for r in original))])
    for r,g in zip(gen_rows,out['gen']):
        bound_errors.extend(abs(float(r[a])-g[b]) for a,b in [(4,3),(5,4),(16,8),(17,9),(14,7)])
    live=out['bus'][:,1]!=4
    return {'method':__doc__,'direct_raw_branch_count':len(flows),'compared_branch_count':len(errs),
        'two_winding_transformers':two,'three_winding_transformers':three,'merged_ideal_ties':ties,
        'max_branch_flow_difference_MVA':float(max(errs)),'max_grouped_KCL_residual_MVA':float(max(abs(powers[live]))),
        'max_source_rating_difference':float(max(rateerrs)),
        'max_source_bus_generator_bound_or_status_difference':float(max(bound_errors)),
        'passed':bool(max(errs)<1e-6 and max(abs(powers[live]))<1e-4 and max(rateerrs)==0 and max(bound_errors)==0),
        'fixed_boundary_caveat':'HVDC injection is explicitly calibrated; this test does not independently validate that boundary or remote-control behavior.'}

def main():
    from fixed_case import build
    _,meta=build();out=dict(np.load(ROOT/'results/feasible_counterfactual.npz'))
    history=json.loads((ROOT/'results/expanded_tap_experiment.json').read_text())['history']
    taps={c['transformer']:c['new_w1'] for r in history for c in r['changes']}
    actions=json.loads((ROOT/'results/feasible_counterfactual_actions.json').read_text())
    report=verify(out,meta,tap_changes=taps,shunt_off=actions['disconnect_shunts'])
    (ROOT/'results/raw_equation_check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
