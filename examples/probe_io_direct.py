"""Direct SDK check for fonts, quarter arcs, native PDF and selected transfer."""
import json
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

def run():
 a=Adapter();docs=[];out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
 try:
  a.connect();s=a.create_drawing()['document_id'];docs.append(s);a.set_sheet(s,'A1',True);a.create_view(s,'Source',.1,50,60)
  a.create_layer(s,'Green',7,0x009000)
  rect=a.rectangle(s,1000,2000,1200,800);a.circle(s,500,600,120)
  a.text(s,500,3500,'Arial: — → × Ø / Кириллица',8)
  a.arc(s,4000,3000,500,0,90)
  src=a._doc(s);ext=a.api7.IKompasDocument2D1(src._oleobj_.QueryInterface(a.api7.IKompasDocument2D1.CLSID,a.com.IID_IDispatch))
  container=a._container(s)
  ext.SelectionManager.Select((container.Rectangles.Item(0),container.Circles.Item(0)))
  assert len(a.get_selected_objects(s)['items'])==2
  t=a.create_drawing()['document_id'];docs.append(t);a.create_view(t,'Target',.02,100,200)
  copied=a.copy_objects_to_document(s,t,selected=True,dx=200,dy=300)
  assert copied['copied']==2
  rectangle=next(o for o in copied['items'] if o['type']=='rectangle')
  assert rectangle['base']==[1200,2300],rectangle
  assert len(a.list_objects(s)['items'])==4
  arc=a.api7.IArc(container.Arcs.Item(0));assert arc.Direction is False and arc.Angle2-arc.Angle1==90
  font=a.api7.ITextFont(a.api7.IText(container.DrawingTexts.Item(0)).TextLine(0).TextItem(0));assert font.FontName=='Arial'
  a.save_document(s,str(out/'io-direct.cdw'))
  exports=[a.export_pdf(s,str(out/f'io-{paper}-{color}.pdf'),paper=paper,color=color) for paper in ('sheet','A4') for color in (True,False)]
  a.export_png(s,str(out/'io-direct.png'),dpi=100,color_mode='layer')
  assert a.document_state(s)['sheet']['format']=='A1'
  result={'transfer':copied,'exports':exports,'font':font.FontName,'arc_ccw_90':True}
  (out/'io-direct-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  print('DIRECT IO PASS',json.dumps(result,ensure_ascii=False),flush=True)
 finally:
  for d in reversed(docs):a.close_document(d)
  a.shutdown()
if __name__=='__main__':run()
