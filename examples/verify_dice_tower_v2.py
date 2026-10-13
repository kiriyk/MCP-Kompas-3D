"""Verify selected native thicknesses and the complete tower assembly."""
import argparse,json,os,math
from pathlib import Path
from client import Client
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--executable');a=p.parse_args()
root=Path(a.output).resolve()
if (root/'current.json').exists():root=root/json.loads((root/'current.json').read_text())['run']
checks={};owned=[]
with Client(timeout=120) as c:
 def call(t,**k):return c.call(t,**k)
 call('connect',launch=True,executable=a.executable or os.environ.get('KOMPAS_EXECUTABLE'))
 try:
  modeldata=json.loads((root/'tower-model-state.json').read_text(encoding='utf-8'))
  for key,path in modeldata['models'].items():
   d=call('open_model',path=path)['document_id'];owned.append(d)
   call('set_model_material',document_id=d,name='PLA (design assumption)',density_g_cm3=1.24)
   call('save_model',document_id=d,path=path);call('close_model',document_id=d);owned.remove(d)
  for key,minimum in [('03-ramp',2.49),('23-service-cover',2.99)]:
   d=call('open_model',path=str(root/(key+'.m3d')))['document_id'];owned.append(d)
   faces=call('select_model_topology',document_id=d,planar=True)['items']
   large=sorted(faces,key=lambda f:f['area_mm2'],reverse=True)[:2]
   assert len(large)==2
   r=call('check_model_measurements',document_id=d,reference_pairs=[[large[0]['reference'],large[1]['reference']]],required_minimum=minimum,purpose='thickness');assert r['passed'];checks[key]=r
   call('close_model',document_id=d);owned.remove(d)
  d=call('open_model',path=str(root/'07-portal.m3d'))['document_id'];owned.append(d)
  edges=call('select_model_topology',document_id=d,kind='edge',radius=41)['items'];assert edges
  checks['portal_opening']={'native_radius_mm':edges[0]['radius_mm'],'diameter_mm':2*edges[0]['radius_mm'],'scope':'selected circular edges'}
  call('close_model',document_id=d);owned.remove(d)
  d=call('open_model',path=str(root/'00-dice-tower.a3d'))['document_id']
  parts=call('list_components',document_id=d);assert parts['count']==42
  clash=call('check_assembly_intersections',document_id=d);assert clash['checked_pairs']==861 and clash['interference_count']==0
  checks['assembly']=clash
  call('set_model_display',document_id=d);call('set_model_orientation',document_id=d,projection='front_isometric');call('save_model',document_id=d,path=str(root/'00-dice-tower.a3d'))
  checks['limits']={'overall_minimum_wall_thickness_verified':False,'physical_dice_motion_verified':False,'mounting_tolerances_require_prototype':True}
 finally:
  (root/'geometry-verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
  (root/'geometry-verification-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
  for d in owned:
   try:call('close_model',document_id=d)
   except Exception:pass
print('VERIFIED selected thicknesses, portal opening and 861 assembly pairs; assembly left open')
