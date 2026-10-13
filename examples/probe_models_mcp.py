"""Live native 3D regression through fresh stdio MCP; run one COM client at a time."""
import argparse,json,math
from pathlib import Path
from client import Client

def probe(output):
 root=Path(output).resolve();root.mkdir(parents=True,exist_ok=True);owned=[]
 with Client(timeout=75) as c:
  c.call('connect')
  def call(tool,**kw):return c.call(tool,**kw)
  def model():
   d=call('create_part',name='MCP verification block')['document_id'];owned.append(('model',d));return d
  try:
   schemas=c.request('tools/list',{})['tools'];assert len(schemas)==71
   # XZ mapping and offset; this box spans Y=10..50, Z=0..30.
   d=model();sk=call('create_sketch',document_id=d,plane='XZ',offset=10)['sketch_reference']
   call('sketch_polygon',document_id=d,sketch_reference=sk,points=[[0,0],[20,0],[20,-30],[0,-30]])
   e=call('extrude',document_id=d,sketch_reference=sk,depth=40)
   state=call('model_state',document_id=d);assert all(abs(a-b)<1e-6 for a,b in zip(state['bounds_mm']['min']+state['bounds_mm']['max'],[0.,10.,0.,20.,50.,30.]))
   assert abs(e['volume_mm3']-24000)<.01
   call('set_model_material',document_id=d,name='PLA test',density_g_cm3=1.24)
   call('set_model_color',document_id=d,color=0x55AA44)
   feature=e['feature_reference'];call('set_extrusion_depth',document_id=d,feature_reference=feature,depth=50)
   sk=call('create_sketch',document_id=d,plane='XZ',offset=10)['sketch_reference'];call('sketch_circle',document_id=d,sketch_reference=sk,x=10,y=-15,radius=3)
   cut=call('extrude',document_id=d,sketch_reference=sk,depth=50,operation='cut');assert abs(cut['volume_mm3']-(30000-math.pi*9*50))<.01
   part=str(root/'block.m3d');call('save_model',document_id=d,path=part);call('export_model',document_id=d,path=str(root/'block.stl'))
   drawing=call('create_drawing')['document_id'];owned.append(('drawing',drawing));call('set_sheet',document_id=drawing,format='A3',landscape=True)
   base=call('create_model_view',document_id=drawing,model_path=part,projection='front',name='Front',x=100,y=100)['view_number']
   call('create_section_view',document_id=drawing,base_view_number=base,points=[[10,-5],[10,35]],name='A',x=220,y=100)
   call('set_active_view',document_id=drawing,view_number=base)
   assert call('model_view_state',document_id=drawing)['views'][0]['scale']==1
   call('set_extrusion_depth',document_id=d,feature_reference=feature,depth=60);call('save_model',document_id=d,path=part)
   linked=call('update_model_views',document_id=drawing);assert linked['count']==2
   section=next(v for v in linked['views'] if v['section']);assert abs(section['projected_bounds_mm']['max'][0]-70)<1e-5 or abs(section['projected_bounds_mm']['min'][0]+70)<1e-5
   dp=str(root/'linked.cdw');call('save_document',document_id=drawing,path=dp);call('export_pdf',document_id=drawing,path=str(root/'linked.pdf'));call('export_png',document_id=drawing,path=str(root/'linked.png'))
   call('close_document',document_id=drawing);owned.remove(('drawing',drawing));drawing=call('open_document',path=dp)['document_id'];owned.append(('drawing',drawing));assert call('model_view_state',document_id=drawing)['count']==2
   assembly=call('create_assembly',name='Repeated rotated blocks')['document_id'];owned.append(('model',assembly))
   for i in range(2):
    ref=call('insert_component',document_id=assembly,path=part,name=f'Block {i}')['component_reference']
    call('set_component_placement',document_id=assembly,component_reference=ref,origin=[i*100,0,0],x_axis=[0,1,0],y_axis=[-1,0,0])
   ap=str(root/'assembly.a3d');call('save_model',document_id=assembly,path=ap);call('close_model',document_id=assembly);owned.remove(('model',assembly))
   assembly=call('open_model',path=ap)['document_id'];owned.append(('model',assembly));assert call('list_components',document_id=assembly)['count']==2
   assert call('model_state',document_id=assembly)['body_count']==2
   invalid=c.request('tools/call',{'name':'extrude','arguments':{'document_id':'invalid','sketch_reference':'expired','depth':0}});assert invalid['isError']
   print('PASS: 71 schemas, XZ mapping, material/color, depth/cut, STL, linked section rebuild, reopen, repeated rotated components and errors',flush=True)
  finally:
   for kind,doc in reversed(owned):
    try:call('close_model' if kind=='model' else 'close_document',document_id=doc)
    except Exception:pass
   (root/'trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);probe(parser.parse_args().output)

