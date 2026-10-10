"""Verify all advanced edits over stdio, including save/reopen and rejection cases."""
import json
from pathlib import Path
from client import Client

def run():
 out=Path(__file__).resolve().parents[1]/'artifacts';d=None
 with Client() as c:
  try:
   schema=c.request('tools/list',{});names={t['name'] for t in schema['tools']}
   assert len(names)==41 and {'set_object_properties','edit_linear_dimension','get_object_boundaries'}<=names
   c.call('connect');d=c.call('create_drawing')['document_id']
   def call(tool_name,**args):return c.call(tool_name,document_id=d,**args)
   call('set_sheet',format='A1',landscape=True)
   call('create_view',name='Advanced MCP',scale=.02,x=100,y=200)
   call('create_layer',name='Shapes',number=2,color=0)
   r=call('rectangle',x=0,y=0,width=5000,height=4000,angle=2,style=1)
   assert call('set_object_properties',reference=r['reference'],angle=0,style=2)['properties']=={'Angle':0.,'Style':2}
   dimension=call('linear_dimension',x1=0,y1=0,x2=5000,y2=0,x3=2500,y3=-500)
   assert call('edit_linear_dimension',reference=dimension['reference'],x1=0,y1=0,x2=6000,y2=0,x3=3000,y3=-800)['nominal_value']==6000
   parallel=call('linear_dimension',x1=0,y1=6000,x2=3000,y2=10000,x3=1000,y3=8000,orientation='parallel')
   assert call('edit_linear_dimension',reference=parallel['reference'],x1=0,y1=6000,x2=3000,y2=10000,x3=500,y3=9500,orientation='parallel')['nominal_value']==5000
   h=call('hatch_rectangle',x=7000,y=0,width=2000,height=1000,step=3.5)
   assert call('get_object_boundaries',reference=h['reference'])['bounds']['width']==2000
   contour=call('mixed_contour',segments=[{'type':'arc','x':10000,'y':0,'radius':1000,'start_angle':0,'end_angle':90}])
   b=call('get_object_boundaries',reference=contour['reference'])['bounds'];assert b['width']==b['height']==1000
   for tool,args in [('set_object_properties',{'reference':contour['reference'],'style':2}),('set_object_properties',{'reference':r['reference'],'style':0}),('get_object_boundaries',{'reference':r['reference']}),('edit_linear_dimension',{'reference':dimension['reference'],'x1':0,'y1':0,'x2':0,'y2':500,'x3':100,'y3':200})]:
    try:call(tool,**args)
    except RuntimeError:pass
    else:raise AssertionError('Expected rejection')
   before=call('list_objects')['items'];assert next(o for o in before if o['api_reference']==dimension['api_reference'])['nominal_value']==6000
   call('save_document',path=str(out/'advanced-edits-mcp.cdw'));call('close_document');d=None
   d=c.call('open_document',path=str(out/'advanced-edits-mcp.cdw'))['document_id']
   items=call('list_objects')['items'];r=next(o for o in items if o['type']=='rectangle');assert r['angle']==0
   assert {5000,6000}=={o['nominal_value'] for o in items if o['type']=='linear_dimension'}
   contour=next(o for o in items if o['type']=='contour');assert call('get_object_boundaries',reference=contour['reference'])['bounds']==b
   call('export_png',path=str(out/'advanced-edits-mcp.png'),dpi=100,color_mode='layer')
   print('ADVANCED MCP PASS',len(c.records),'calls, 41 tools',flush=True)
  finally:
   if d:c.call('close_document',document_id=d)
   (out/'advanced-edits-mcp-results.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':run()
