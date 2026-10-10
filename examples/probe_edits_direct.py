"""Prove room and equipment edits directly through native API, then reopen."""
import json
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

def run():
 a=Adapter();d=None;out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
 try:
  a.connect();d=a.create_drawing()['document_id'];a.set_sheet(d,'A1',True);a.create_view(d,'Редактирование',.02,100,200)
  a.create_layer(d,'Room',1,0)
  walls=[a.rectangle(d,*v) for v in ((0,0,5000,200),(0,3800,5000,200),(0,200,200,3600),(4800,200,200,3600))]
  hatch=a.hatch_rectangle(d,0,0,5000,200,3.5)
  label=a.text(d,1000,2400,'Комната 5 × 4 м',4)
  dimension=a.linear_dimension(d,0,0,5000,0,0,-500)
  original=a.list_objects(d)['items']
  a.move_objects(d,[o['reference'] for o in original],3000,2000)
  moved=a.list_objects(d)['items'];assert len(moved)==len(original)
  byref={o['api_reference']:o for o in moved}
  for old in original:
   new=byref[old['api_reference']]
   if 'base' in old:assert new['base']==[old['base'][0]+3000,old['base'][1]+2000]
   if 'points' in old:assert new['points']==[[x+3000,y+2000] for x,y in old['points']]
  for wall in walls[:2]:a.resize_rectangle(d,wall['reference'],6000,200)
  a.move_object(d,walls[3]['reference'],1000,0)
  # Redraw the resized boundary's hatch as an actual native hatch.
  a.delete_object(d,hatch['reference']);a.hatch_rectangle(d,3000,2000,6000,200,3.5)
  a.edit_text(d,label['reference'],'Комната 6 × 4 м — после правки')
  native=a.api7.ISymbols2DContainer(a._views(d).ActiveView).LineDimensions
  obj=a.api7.ILineDimension(native.Item(0));obj.X2+=1000;assert obj.Update()
  native_text=a._find_native_object(d,label['reference'],'text')
  assert a.api7.ITextFont(a.api7.IText(native_text).TextLine(0).TextItem(0)).FontName=='Arial'
  a.save_document(d,str(out/'edit-room-direct.cdw'));a.close_document(d);d=a.open_document(str(out/'edit-room-direct.cdw'))['document_id']
  items=a.list_objects(d)['items'];assert any(o.get('nominal_value')==6000 for o in items)
  assert any(o.get('value')=='Комната 6 × 4 м — после правки' for o in items)
  assert sum(o['type']=='rectangle' and o['width']==6000 for o in items)==2
  a.export_png(d,str(out/'edit-room-direct.png'),100,'layer')
  result={'moved_module':len(original),'native_dimension_after_resize':6000,'redrawn_hatch':True,'text_replaced':True,'reopened':True,'object_count':len(items)}
  (out/'edit-room-direct-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  print('DIRECT EDIT PASS',json.dumps(result,ensure_ascii=False),flush=True)
 finally:
  if d:a.close_document(d)
  a.shutdown()
if __name__=='__main__':run()
