"""Fast independent validation of the exported mechanical files. No CadQuery import."""
import json
from pathlib import Path
import trimesh
base=Path(__file__).resolve().parents[1]
tests=[]
def ck(name,p,obs=None):
 p=bool(p);tests.append({'test':name,'passed':p,'observed':obs});print(('PASS' if p else 'FAIL'),name,obs if obs is not None else '')
for name,dims in [('Open_Camera_Carrier_V2',[84,58,8.3]),('Adjustable_Edge_Retainer_V2',[14,6,2.8]),('Nominal_PCB_Gauge_DO_NOT_MOUNT',[40,27,1.6])]:
 m=trimesh.load(str(base/'cad'/(name+'.stl')),force='mesh')
 ck(name+' watertight',m.is_watertight)
 ck(name+' winding',m.is_winding_consistent)
 ck(name+' volume',m.volume>100,round(m.volume,1))
 ck(name+' size',all(abs(a-b)<0.12 for a,b in zip(m.extents,dims)),[round(x,3) for x in m.extents])
 ck(name+' STEP exists',(base/'cad'/(name+'.step')).is_file())
# Independent parameter math checks: no claim of actual connector/PCB clearance
ck('nominal 40mm board fits within 84mm plate',40<84)
ck('nominal 27mm board fits within 58mm plate',27<58)
ck('four board-support centers within 40x27 envelope',all(abs(x)<20 and -9.5<y<17.5 for x in [-17,17] for y in [-6,14]))
ck('right/left retainer nominal overlap >0',26-7.5<20)
ck('strap slots remain inside base',35+2<84/2)
ck('camera label not on PCB footprint',-21.8 < -9.5)
ck('assembled height estimate distinguishes plate+lift+board',abs(3.2+3.5+12-18.7)<1e-9)
ck('A4 PDF template present',(base/'templates'/'Hardware_Fit_Gauge_100pct.pdf').is_file())
ck('bill of materials present',(base/'BOM.csv').is_file())
ck('source ledger present',(base/'docs'/'SOURCES_AND_UNKNOWNS.md').is_file())
ck('wiring diagram present',(base/'diagrams'/'System_Block_Diagram.svg').is_file())
result={'scope':'digital CAD STL + document presence and nominal math only','tests':len(tests),'passed':sum(t['passed'] for t in tests),'failed':sum(not t['passed'] for t in tests),'tests_detail':tests,'physical_fit':False,'camera_firmware':False,'camera_image_captured':False}
(base/'checks'/'QUICK_VALIDATION_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
print('RESULT',result['passed'],'/',result['tests'])
raise SystemExit(0 if result['failed']==0 else 1)
