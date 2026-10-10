"""Correct the v6 rectangle argument error in place; preserve its layout."""
import json
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

def run():
 out=Path(__file__).resolve().parents[1]/'artifacts';a=Adapter()
 try:
  a.connect();d=a.open_document(str(out/'Цех-40x24-А0-v6.cdw'))['document_id']
  a.save_document(d,str(out/'Цех-40x24-А0-v7.cdw'));a.set_active_view(d,1)
  rects=a._container(d).Rectangles;changed=[]
  for i in range(rects.Count):
   obj=a.api7.IRectangle(rects.Item(i))
   if obj.Angle:
    if obj.Angle not in (1.,2.):raise RuntimeError('Unexpected angle: inspect before mutation')
    original=(obj.X,obj.Y,obj.Width,obj.Height,obj.LayerNumber);angle=obj.Angle
    obj.Angle=0;obj.Style=1 if obj.LayerNumber==1 else 2
    assert obj.Update() and obj.Angle==0
    assert original==(obj.X,obj.Y,obj.Width,obj.Height,obj.LayerNumber)
    changed.append({'reference':obj.Reference,'from_angle':angle,'base':[obj.X,obj.Y]})
  items=a.list_objects(d)['items'];removed=[]
  for o in items:
   if o['view']==1 and o['type']=='rectangle' and o['layer_number']==2 and abs(o['width'])==500 and abs(o['height'])==500 and o['base'][0]<7000 and o['base'][1]<3000:
    a.delete_object(d,o['reference']);removed.append(o['api_reference'])
  assert len(changed)==37 and len(removed)==3,(len(changed),len(removed))
  a.set_active_view(d,0)
  footer=next(o for o in items if o.get('value')=='Редакция 6 / 2 подготовки + 2 линии')
  a.edit_text(d,footer['reference'],'Редакция 7 / 2 подготовки + 2 линии')
  a.save_document(d,str(out/'Цех-40x24-А0-v7.cdw'));a.export_png(d,str(out/'Цех-40x24-А0-v7.png'),100,'layer')
  for paper in ('sheet','A4'):
   for color in (True,False):a.export_pdf(d,str(out/f'Цех-40x24-v7-{paper}-{"color" if color else "bw"}.pdf'),paper=paper,color=color)
  a.close_document(d);d=a.open_document(str(out/'Цех-40x24-А0-v7.cdw'))['document_id'];items=a.list_objects(d)['items']
  assert all(o.get('angle',0)==0 for o in items if o['type']=='rectangle')
  assert sum(o['view']==1 and o['type']=='rectangle' and o['width']==900 and o['height']==900 for o in items)==2
  assert sum(o['view']==1 and o['type']=='rectangle' and o['width']==480 and o['height']==160 for o in items)==4
  assert sum(o['view']==1 and o['type']=='rectangle' and o['width']==420 and o['height']==75 for o in items)==12
  report={'reopened':True,'rectangles_corrected':len(changed),'obsolete_chairs_removed':len(removed),'all_rectangle_angles_zero':True,'showers':2,'toilets':4,'chair_backs':12,'objects':len(items),'changes':changed}
  (out/'factory-v7-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('V7 ANGLES PASS',len(changed),len(removed),len(items),flush=True)
 finally:a.shutdown()
if __name__=='__main__':run()
