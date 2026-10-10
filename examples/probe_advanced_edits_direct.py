"""Direct SDK checks before exposing the new methods through stdio."""
import json
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

def run():
 a=Adapter();d=None;out=Path(__file__).resolve().parents[1]/'artifacts'
 try:
  a.connect();d=a.create_drawing()['document_id'];a.set_sheet(d,'A1',True);a.create_view(d,'Native properties',.02,100,200);a.create_layer(d,'Test',2,0)
  rect=a.rectangle(d,0,0,5000,4000,angle=2,style=1)
  p=a.set_object_properties(d,rect['reference'],angle=0,style=2);assert p['properties']=={'Angle':0.,'Style':2}
  line=a.line(d,0,5000,5000,5000);a.set_object_properties(d,line['reference'],style=4)
  dim=a.linear_dimension(d,0,0,5000,0,2500,-500)
  changed=a.edit_linear_dimension(d,dim['reference'],0,0,6000,0,3000,-800);assert changed['nominal_value']==6000 and changed['points'][2][1]==-800
  vertical=a.linear_dimension(d,0,0,0,4000,-500,2000,'vertical')
  assert a.edit_linear_dimension(d,vertical['reference'],0,0,0,2600,-700,1300)['nominal_value']==2600
  parallel=a.linear_dimension(d,0,6000,3000,10000,1000,8000,'parallel')
  assert a.edit_linear_dimension(d,parallel['reference'],0,6000,3000,10000,500,9500,'parallel')['nominal_value']==5000
  quarter=a.mixed_contour(d,[{'type':'arc','x':10000,'y':0,'radius':1000,'start_angle':0,'end_angle':90}])
  bounds=a.get_object_boundaries(d,quarter['reference']);print('ARC NATIVE',json.dumps(bounds),flush=True)
  b=bounds['bounds'];assert abs(b['left']-10000)<.001 and abs(b['bottom'])<.001 and abs(b['width']-1000)<.001 and abs(b['height']-1000)<.001
  for primitive in (a.circle(d,12000,3000,500),a.arc(d,12000,5000,500,0,90),a.polyline(d,[[12000,7000],[13000,7000],[13000,8000]])):
   assert a.set_object_properties(d,primitive['reference'],style=4)['properties']['Style']==4
  hatch=a.hatch_rectangle(d,7000,3000,2000,1000,3.5)
  hb=a.get_object_boundaries(d,hatch['reference']);assert hb['bounds']=={'left':7000.,'bottom':3000.,'right':9000.,'top':4000.,'width':2000.,'height':1000.}
  a.set_active_view(d,0);a.save_document(d,str(out/'advanced-edits-direct.cdw'));a.close_document(d);d=a.open_document(str(out/'advanced-edits-direct.cdw'))['document_id'];items=a.list_objects(d)['items']
  rect=next(o for o in items if o['type']=='rectangle');assert rect['angle']==0
  obj=a._find_native_object(d,rect['reference'],'rectangle');assert obj.Style==2 and obj.LayerNumber==2
  for o in items:
   if o['type'] in ('line','circle','arc','polyline'):assert a._find_native_object(d,o['reference'],o['type']).Style==4
  assert {2600,5000,6000}=={o['nominal_value'] for o in items if o['type']=='linear_dimension'}
  contour=next(o for o in items if o['type']=='contour');assert a.get_object_boundaries(d,contour['reference'])['bounds']==bounds['bounds']
  a.export_png(d,str(out/'advanced-edits-direct.png'),100,'layer')
  result={'reopened':True,'absolute_angle':0,'rectangle_style':2,'primitive_styles_persisted':True,'dimensions':[2600,5000,6000],'quarter_arc_bounds':bounds['bounds'],'hatch_bounds':hb['bounds'],'objects':len(items)}
  (out/'advanced-edits-direct-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('ADVANCED DIRECT PASS',json.dumps(result),flush=True)
 finally:
  if d:a.close_document(d)
  a.shutdown()
if __name__=='__main__':run()
