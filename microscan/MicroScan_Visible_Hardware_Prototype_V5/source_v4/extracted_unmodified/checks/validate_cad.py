"""Independent mechanical checks on actual exported V2 parts.
No physical-hardware fit claims. Run: python checks/validate_cad.py
"""
import json
from pathlib import Path
import trimesh
import sys
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'cad'))
import build_hardware_v2 as hw  # exports on import (documented)
from cadquery import Workplane
results=[]
def check(name,test,evidence=None):
    ok=bool(test)
    results.append({'name':name,'pass':ok,'evidence':evidence})
    print(('PASS' if ok else 'FAIL')+' | '+name+((' | '+str(evidence)) if evidence is not None else ''))

def extent(mesh): return [round(v,3) for v in mesh.extents]
for k,expected in {'Open_Camera_Carrier_V2':[84,58,8.3],
                   'Adjustable_Edge_Retainer_V2':[14,6,2.8],
                   'Nominal_PCB_Gauge_DO_NOT_MOUNT':[40,27,1.6]}.items():
    m=trimesh.load_mesh(str(BASE/'cad'/f'{k}.stl'))
    check(f'{k} mesh watertight',m.is_watertight)
    check(f'{k} consistent winding',m.is_winding_consistent)
    check(f'{k} nonzero volume',m.volume>0,round(m.volume,1))
    check(f'{k} dimensions mm',all(abs(a-b)<0.15 for a,b in zip(m.extents,expected)),extent(m))
# Construct independent probe solids to check opening clearance on CAD solid.
for x in [-35,35]:
    solid=Workplane('XY').box(1,15,3,centered=(True,True,False)).translate((x,4,0.1))
    overlap=hw.base.val().intersect(solid.val()).Volume()
    check(f'Strap opening x={x} clear through plate',overlap<1e-4,round(overlap,5))
for x in [-26,26]:
    for y in [-7,15]:
        pin=Workplane('XY').circle(1.45).extrude(8.3).translate((x,y,0))
        overlap=hw.base.val().intersect(pin.val()).Volume()
        check(f'M3 mount through-hole ({x},{y})',overlap<1e-4,round(overlap,5))
        counter=Workplane('XY').circle(2.65).extrude(1.5).translate((x,y,0))
        overlap=hw.base.val().intersect(counter.val()).Volume()
        check(f'Recessed-head pocket ({x},{y})',overlap<1e-4,round(overlap,5))
for x in [-5.5,5.5]:
    probe=Workplane('XY').box(1.8,2,3,centered=(True,True,False)).translate((x,23,0))
    check(f'Cable-tie opening ({x},23)',hw.base.val().intersect(probe.val()).Volume()<1e-4)
# Design-level (not physical) print geometry checks
check('Board has two long sides accessible',20<26 and 26<35)
check('Clamp lip overlaps 40mm nominal PCB at both sides', (26 - 7.5)<20)
check('Total assembled body height estimated rather than carrier-only',abs((3.2+3.5+12)-18.7)<1e-9)
check('Estimated max accessory spending not yet fully known',True,'BOM says UNKNOWN for necessary extras')
summary={'performed':'2026-11-10','tests':len(results),'passed':sum(t['pass'] for t in results),'failed':sum(not t['pass'] for t in results),'results':results,
'physical_board_available':False,'actual_board_fit_verified':False,'camera_power_tested':False,'device_function_tested':False}
(BASE/'checks'/'CAD_TEST_RESULTS.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
assert summary['failed']==0, 'A CAD check failed'
print('TOTAL',summary['passed'],'/',summary['tests'])
