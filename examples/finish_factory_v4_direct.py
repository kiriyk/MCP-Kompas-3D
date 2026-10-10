"""Direct native cleanup of labels/dimensions after storage layout changes."""
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

def run():
 out=Path(__file__).resolve().parents[1]/'artifacts';a=Adapter()
 try:
  a.connect();d=a.open_document(str(out/'Цех-40x24-А0-v4.cdw'))['document_id'];a.set_active_view(d,1)
  positions={'05 СКЛАД СЫРЬЯ':(8300,7800),'06 СКЛАД ГОТОВОЙ ПРОДУКЦИИ':(19800,7800),'07 УПАКОВОЧНЫЕ МАТЕРИАЛЫ':(33400,8050),'Выдача ГП / ЭК':(23900,13100)}
  texts=a._container(d).DrawingTexts;updated=[]
  for i in range(texts.Count):
   obj=a.api7.IDrawingText(texts.Item(i));value=a.api7.IText(obj).Str
   if value in positions:
    obj.X,obj.Y=positions[value];assert obj.Update();updated.append(value)
  assert len(updated)==4,updated
  dims=a.api7.ISymbols2DContainer(a._views(d).ActiveView).LineDimensions
  shifted=0
  for i in range(dims.Count):
   obj=a.api7.ILineDimension(dims.Item(i))
   if abs(obj.Y1-300)>1e-6:continue
   if obj.Orientation==1 and obj.X1 in (8000,19200,32200):obj.Y3=2700;assert obj.Update();shifted+=1
   if obj.Orientation==2 and obj.X1 in (8000,19200,32200):
    obj.X3={8000:13700,19200:27100,32200:36400}[obj.X1];assert obj.Update();shifted+=1
  assert shifted==6,shifted
  a.set_active_view(d,0);a.save_document(d,str(out/'Цех-40x24-А0-v4.cdw'))
  a.export_png(d,str(out/'Цех-40x24-А0-v4.png'),100,'layer')
  # Active view is UI state; export source is the saved sheet.
  for paper in ('sheet','A4'):
   for color in (True,False):a.export_pdf(d,str(out/f'Цех-40x24-v4-{paper}-{"color" if color else "bw"}.pdf'),paper=paper,color=color)
  print('FINAL LABELS/DIMENSIONS PASS',len(updated),shifted,flush=True)
 finally:a.shutdown()
if __name__=='__main__':run()
