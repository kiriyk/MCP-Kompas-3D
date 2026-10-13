import os,sys,json,math
from pathlib import Path
from client import Client
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--executable');args=p.parse_args();root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True);owned=[];results={}
with Client(timeout=120) as c:
 def call(t,**kw):return c.call(t,**kw)
 call('connect',launch=True,executable=args.executable or os.environ.get('KOMPAS_EXECUTABLE'));schemas=c.request('tools/list',{})['tools'];assert {'select_model_topology','measure_model_geometry','check_assembly_intersections','set_model_appearance','set_model_orientation','upsert_component','remove_component'}.issubset({t['name'] for t in schemas})
 try:
  d=call('create_part',name='v08 fixture')['document_id'];owned.append(d);s=call('create_sketch',document_id=d,plane='XY')['sketch_reference'];call('sketch_polygon',document_id=d,sketch_reference=s,points=[[0,0],[10,0],[10,10],[0,10]]);call('extrude',document_id=d,sketch_reference=s,depth=10)
  faces=call('list_model_topology',document_id=d);print('FACES',faces['count'],flush=True);assert faces['count']==6
  top=call('select_model_topology',document_id=d,planar=True,normal=[0,0,1],bounds_min=[-1,-1,9],bounds_max=[11,11,11])['items'];bottom=call('select_model_topology',document_id=d,planar=True,bounds_min=[-1,-1,-1],bounds_max=[11,11,1])['items'];assert len(top)==len(bottom)==1
  measurement=call('check_model_measurements',document_id=d,reference_pairs=[[top[0]['reference'],bottom[0]['reference']]],required_minimum=9,purpose='thickness');assert measurement['passed'] and abs(measurement['minimum_of_selected_pairs_mm']-10)<1e-6
  color=call('set_model_appearance',document_id=d,color=0x60C080);repeat=call('set_model_appearance',document_id=d,color=0x60C080);assert repeat['changed_targets']==0
  bodies=call('list_model_bodies',document_id=d);assert bodies['count']==1;call('set_model_appearance',document_id=d,color=0x60C080,scope='body',reference=bodies['items'][0]['body_reference'])
  call('set_model_appearance',document_id=d,color=0xF0F0F0,scope='face',reference=top[0]['reference'])
  for pr in ['front','top','left','isometric','front_isometric']:
   call('set_model_orientation',document_id=d,projection=pr);call('set_model_orientation',document_id=d,projection=pr)
  call('set_model_display',document_id=d);call('save_model',document_id=d,path=str(root/'box.m3d'));call('export_model_png',document_id=d,path=str(root/'box.png'));call('close_model',document_id=d);owned.remove(d)
  ass=call('create_assembly',name='v08 placement fixtures')['document_id'];owned.append(ass);refs=[]
  for x in [0,8,10,15,30]:
   args=dict(document_id=ass,path=str(root/'box.m3d'),name=f'Box {x}',origin=[x,0,0],x_axis=[1,0,0],y_axis=[0,1,0]);rr=call('upsert_component',**args);refs.append(rr['component_reference']);assert call('upsert_component',**args)['action']=='reused'
  assert call('list_components',document_id=ass)['count']==5
  report=call('check_assembly_intersections',document_id=ass);assert report['checked_pairs']==10
  for j,x in enumerate([8,10,15,30],1):
   rr=call('check_assembly_intersections',document_id=ass,component_references=[refs[0],refs[j]]);assert rr['interference_count']==(1 if x==8 else 0);assert rr['contact_count']==(1 if x==10 else 0)
  first=call('select_model_topology',document_id=ass,component_reference=refs[0],planar=True,bounds_min=[9,-1,-1],bounds_max=[11,11,11])['items'];second=call('select_model_topology',document_id=ass,component_reference=refs[3],planar=True,bounds_min=[14,-1,-1],bounds_max=[16,11,11])['items'];assert len(first)==len(second)==1
  gap=call('measure_model_geometry',document_id=ass,first_reference=first[0]['reference'],second_reference=second[0]['reference']);assert abs(gap['minimum_distance_mm']-5)<1e-6
  call('set_model_appearance',document_id=ass,color=0xD09050,scope='component',reference=refs[3]);call('remove_component',document_id=ass,component_reference=refs[-1]);assert call('list_components',document_id=ass)['count']==4
  call('save_model',document_id=ass,path=str(root/'assembly.a3d'));call('close_model',document_id=ass);owned.remove(ass);ass=call('open_model',path=str(root/'assembly.a3d'))['document_id'];owned.append(ass);assert call('list_components',document_id=ass)['count']==4
  results.update(tools=len(schemas),thickness=measurement,placement_distance=gap,intersections=report,repeat_upsert_count=5,reopened_component_count=4,appearance_repeat_noop=True,orientation_repeat_noop=True)
  print('PASS v08',flush=True)
 finally:
  (root/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8');(root/'stdio-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
  for d in reversed(owned):
   try:call('close_model',document_id=d)
   except Exception:pass
