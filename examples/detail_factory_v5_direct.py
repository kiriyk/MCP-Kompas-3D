from pathlib import Path
from kompas_local_mcp.adapter import Adapter
import json
a=Adapter();out=Path(r'C:\Users\user\DevProjects\MCP-Kompas-3D\artifacts')
try:
 a.connect();d=a.open_document(str(out/'Цех-40x24-А0-v5.cdw'))['document_id'];a.set_active_view(d,1);a.create_layer(d,'Детали машин и конвейеров',8,0)
 def line(x,y,xx,yy):return a.line(d,x,y,xx,yy,2)
 def rect(x,y,w,h):return a.rectangle(d,x,y,w,h,style=2)
 def circle(x,y,r):return a.circle(d,x,y,r,2)
 details=0
 for offset in (0,-5000):
  x=24830;y=22120+offset
  line(x+100,y+240,x+12400,y+240);line(x+100,y+540,x+12400,y+540);details+=2
  for j in range(1,10):line(x+j*1250,y+50,x+j*1250,y+730);details+=1
  # Tempering vessel, enrober mesh conveyor and removable casing outline.
  circle(22150,22500+offset,250);circle(22000,22500+offset,60);details+=2
  x=22930;y=21900+offset
  line(x+100,y+250,x+1500,y+250);line(x+100,y+750,x+1500,y+750)
  for j in range(6):line(x+180+j*230,y+250,x+180+j*230,y+750)
  details+=8
 for y in (19400,14300):
  x=31300
  rect(x+1450,y+180,1900,1240)
  circle(x+2000,y+800,240);circle(x+2850,y+800,240)
  for start in (x+80,x+3500):
   line(start,y+300,start+1100,y+300);line(start,y+1300,start+1100,y+1300)
   for j in range(5):line(start+120+j*220,y+300,start+120+j*220,y+1300)
  details+=17
  # Metal detector aperture and short conveyor, below/above the corresponding row.
 for x,y in ((27000,19600),(27000,14600)):
  rect(x+950,y+100,600,600);line(x+50,y+220,x+3150,y+220);line(x+50,y+580,x+3150,y+580);details+=3
 texts=a._container(d).DrawingTexts
 positions={'У1 Флоупак 4800 х 1600':(31300,21250),'У2 Флоупак 4800 × 1600':(31300,16050),'Х1 Тоннель 12500 х 780':(26500,23100),'Х2 Тоннель 12500 × 780':(26500,18100)}
 for i in range(texts.Count):
  obj=a.api7.IDrawingText(texts.Item(i));value=a.api7.IText(obj).Str
  if value in positions:obj.X,obj.Y=positions[value];assert obj.Update()
 a.set_active_view(d,0);a.save_document(d,str(out/'Цех-40x24-А0-v5.cdw'));a.export_png(d,str(out/'Цех-40x24-А0-v5.png'),100,'layer')
 for paper in ('sheet','A4'):
  for color in (True,False):a.export_pdf(d,str(out/f'Цех-40x24-v5-{paper}-{"color" if color else "bw"}.pdf'),paper=paper,color=color)
 report={'detail_layer':8,'native_detail_objects':details,'machine_details':'conveyor sections, roller beds, temper vessel, film mechanism, detector aperture'}
 (out/'factory-v5-details.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print('MACHINE DETAILS PASS',details,flush=True)
finally:a.shutdown()
