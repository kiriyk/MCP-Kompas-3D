"""Edit saved factory v4 in place with native API; publish revision 5."""
import json,math
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

def run():
 out=Path(__file__).resolve().parents[1]/'artifacts';a=Adapter();calls=[]
 try:
  a.connect();d=a.open_document(str(out/'Цех-40x24-А0-v4.cdw'))['document_id']
  a.save_document(d,str(out/'Цех-40x24-А0-v5.cdw'));a.set_active_view(d,1)
  old=a.list_objects(d)['items'];assert len(old)==1215,'Unexpected source contents; inspect before editing'
  def call(name,**kwargs):
   result=getattr(a,name)(document_id=d,**kwargs);calls.append({'method':name,'args':kwargs,'result':result});return result
  def layer(n):call('set_active_layer',number=n)
  def rect(x,y,w,h,style=2):return call('rectangle',x=x,y=y,width=w,height=h,style=style)
  def line(x,y,xx,yy,style=2):return call('line',x1=x,y1=y,x2=xx,y2=yy,style=style)
  def txt(x,y,value,h=2.5):
   layer(5);return call('text',x=x,y=y,value=value,height=h)
  def select_rect(x,y,w,h):return next(o for o in old if o['view']==1 and o['type']=='rectangle' and o['base']==[x,y] and o['width']==w and o['height']==h)
  def text_obj(value):return next(o for o in old if o['view']==1 and o.get('value')==value)
  def move_item(obj,dx,dy):return call('move_object',reference=obj['reference'],dx=dx,dy=dy)
  # Redraw the actual locker furniture, keeping enclosing walls and sanitary wing.
  for o in old:
   if o['view']==1 and o['type']=='rectangle' and ((o['width'],o['height'])==(450,550) and 500<=o['base'][0]<=5000 and o['base'][1]==5100 or o['base']==[1400,7100] and o['width']==3000):call('delete_object',reference=o['reference'])
  lockers=[]
  banks=[(300,4600,7),(4200,4600,3),(600,6450,6),(3900,6450,4),(600,6950,6),(3900,6950,4),(600,8500,6),(3900,8500,4)]
  for x,y,n in banks:
   for j in range(n):
    xx=x+j*300;layer(2);r=rect(xx,y,300,500);line(xx+35,y+70,xx+265,y+70);line(xx+245,y+160,xx+245,y+250)
    lockers.append((xx,y,300,500));txt(xx+65,y+290,f'{len(lockers):02d}',1.8)
  assert len(lockers)==40
  layer(2);rect(350,5400,300,800);rect(5000,5400,300,800)
  txt(750,8150,'40 шкафчиков 300 × 500',2.6)
  # Shift existing machines AND their existing labels; references are retained.
  for geom,label,dx,dy in [((26800,19000,4800,1600),'У1 Флоупак 4800 х 1600',4500,400),((21100,18000,2800,1300),'Ф1 Формование',0,1700),((24000,16400,3200,800),'Контроль / металлоискатель',3000,3200),((28000,16400,2000,1000),'Укладка в короб',-3600,3200)]:
   call('move_objects',references=[select_rect(*geom)['reference'],text_obj(label)['reference']],dx=dx,dy=dy)
  # Second parallel process line, copied from native originals in the upper row.
  layer(2)
  top=next(o for o in old if o['type']=='circle' and o['view']==1 and o['center']==[20735,22265])
  call('copy_object',reference=top['reference'],dx=0,dy=-5000)
  for geom in ((21670,22100,960,800),(22930,21900,1600,1000),(24830,22120,12500,780)):
   call('copy_object',reference=select_rect(*geom)['reference'],dx=0,dy=-5000)
  for value,new in [('Е1','Е2'),('Т1','Т2'),('Г1','Г2'),('Х1 Тоннель 12500 х 780','Х2 Тоннель 12500 × 780')]:
   copied=call('copy_object',reference=text_obj(value)['reference'],dx=0,dy=-5000)
   call('edit_text',reference=copied['reference'],value=new)
  layer(2);rect(31300,14300,4800,1600);rect(21100,14500,2800,1300);rect(27000,14600,3200,800);rect(24400,14600,2000,1000)
  for x,y,v in [(31500,14950,'У2 Флоупак 4800 × 1600'),(21300,14950,'Ф2 Формование'),(27100,14900,'Контроль / металлоискатель 2'),(24500,15000,'Укладка в короб 2')]:txt(x,y,v,2.5)
  txt(37400,23000,'ЛИНИЯ 1',2.6);txt(37400,18000,'ЛИНИЯ 2',2.6)
  # Revise transport markings to terminate below the second line's boxing zone.
  for o in old:
   if o['view']==1 and o['type']=='polyline' and o['layer_number'] in (3,7):call('delete_object',reference=o['reference'])
   if o['view']==1 and o['type']=='line' and o['layer_number']==3 and o.get('points') in ([[23800,11200],[23800,15100]],[[27800,11200],[27800,15100]],[[33300,11200],[33300,15200]],[[37300,11200],[37300,15200]]):call('delete_object',reference=o['reference'])
  layer(3)
  for x in (23800,27800,33300,37300):line(x,11200,x,13600,4)
  def arrows(points,style=2):
   call('polyline',points=points,style=style)
   for p,q in zip(points,points[1:]):
    if math.dist(p,q)<1200:continue
    x=(p[0]+q[0])/2;y=(p[1]+q[1])/2;ang=math.atan2(q[1]-p[1],q[0]-p[0])
    call('polyline',points=[[x-300*math.cos(ang)+180*math.sin(ang),y-300*math.sin(ang)-180*math.cos(ang)],[x,y],[x-300*math.cos(ang)-180*math.sin(ang),y-300*math.sin(ang)+180*math.cos(ang)]],style=style)
  arrows([[12400,4200],[12400,17400]]);arrows([[25800,13300],[25800,4300]]);arrows([[35300,4300],[35300,13300]])
  layer(7)
  arrows([[12400,7200],[12400,19400],[1800,19400],[1800,21500]])
  arrows([[1800,20400],[4300,20400],[7300,20400],[10750,20400],[14400,20400],[17200,20400],[17200,21800],[20735,21800]])
  arrows([[20735,21600],[23500,21600],[37330,21600],[38400,21600],[38400,21300],[36100,21300],[36100,20200],[31300,20200],[28600,20200],[25400,20200],[19900,20200],[19900,13700],[25800,13700],[25800,7000]])
  arrows([[19900,21800],[19900,17265],[20735,17265]])
  arrows([[20735,16600],[23500,16600],[37330,16600],[38400,16600],[38400,16050],[36100,16050],[36100,15100],[31300,15100],[28600,15100],[25400,15100],[25800,13700]])
  arrows([[22150,21800],[20200,21800],[20200,20350],[22500,20350],[24600,20350],[24600,21600]])
  arrows([[22150,16800],[20200,16800],[20200,15150],[22500,15150],[24600,15150],[24600,16600]])
  # Draw actual unit loads on all 45 native floor pallet footprints.
  pallets=[o for o in old if o['view']==1 and o['type']=='rectangle' and o['layer_number']==2 and (o['width'],o['height']) in ((1200,800),(800,1200)) and o['base'][0]>=7800 and o['base'][1]<9300]
  assert len(pallets)==45,len(pallets)
  for n,o in enumerate(pallets,1):
   x,y=o['base'];w=o['width'];h=o['height'];layer(2)
   # Three strapped packages, within the pallet perimeter.
   for j in range(3):rect(x+80+j*(w-160)/3,y+100,(w-160)/3-25,h-200,4)
   txt(x+200,y+h/2,f'P{n:02d}',1.7)
  txt(14500,7450,'15 мест × 2 уровня = 30 паллет',2.5)
  txt(28000,7450,'18 мест × 2 уровня = 36 паллет',2.5)
  txt(33400,7450,'12 мест × 2 уровня = 24 паллет',2.5)
  # Native elevation view: three bays and two storage levels, with loaded pallets.
  a.set_active_view(d,0);a.text(d,935,305,'Стеллаж: 3 секции, 2 уровня',3.5)
  elevation=a.create_view(d,'Стеллаж: фасад 1:25',.04,935,175)
  a.create_layer(d,'Стеллажи и грузы',2,0)
  for x in (0,1400,2800,4200):rect(x,0,80,2500)
  for y in (100,1250):
   rect(0,y,4280,100)
   for j in range(3):
    x=140+j*1400;rect(x,y+100,1200,140)
    for k in range(3):rect(x+k*390,y+240,360,750)
  call('linear_dimension',x1=0,y1=0,x2=4280,y2=0,x3=0,y3=-250)
  # Keep locker room title/dimension out of the new furniture.
  a.set_active_view(d,1)
  move_item(text_obj('04 РАЗДЕВАЛКА'),-50,-900)
  move_item(text_obj('Подача тары'),600,0)
  dimensions=a.api7.ISymbols2DContainer(a._views(d).ActiveView).LineDimensions
  for i in range(dimensions.Count):
   obj=a.api7.ILineDimension(dimensions.Item(i))
   if obj.Orientation==2 and obj.X1==300 and obj.Y1==4500:obj.X3=2700;assert obj.Update()
  # Final labels now describe both complete production lines.
  a.set_active_view(d,0)
  texts=a._container(d).DrawingTexts
  for i in range(texts.Count):
   obj=a.api7.IDrawingText(texts.Item(i));value=a.api7.IText(obj).Str
   if value=='Редакция 4 / API v21':call('edit_text',reference=a._ref(d,obj.Reference)['reference'],value='Редакция 5 / 2 линии')
   if value.startswith('Ф1 Формование — альтернативная'):call('edit_text',reference=a._ref(d,obj.Reference)['reference'],value='Две параллельные линии: глазирование / формование → охлаждение → флоупак → контроль → склад ГП')
  a.save_document(d,str(out/'Цех-40x24-А0-v5.cdw'))
  a.export_png(d,str(out/'Цех-40x24-А0-v5.png'),100,'layer')
  for paper in ('sheet','A4'):
   for color in (True,False):a.export_pdf(d,str(out/f'Цех-40x24-v5-{paper}-{"color" if color else "bw"}.pdf'),paper=paper,color=color)
  a.close_document(d);d=a.open_document(str(out/'Цех-40x24-А0-v5.cdw'))['document_id']
  objects=a.list_objects(d)['items'];tunnels=[o for o in objects if o['view']==1 and o['type']=='rectangle' and o['width']==12500 and o['height']==780]
  assert len(tunnels)==2
  assert sum(o['view']==1 and o['type']=='rectangle' and o['width']==300 and o['height']==500 and o['base'][0]<5400 for o in objects)==40
  assert sum(o['view']==1 and o['type']=='rectangle' and o['width']==4800 and o['height']==1600 for o in objects)==2
  # Positive clearance between main line equipment footprints.
  equipment=[o for o in objects if o['view']==1 and o['type']=='rectangle' and o['layer_number']==2 and o['base'][0]>=19000 and o['base'][1]>=14000]
  for i,o in enumerate(equipment):
   x,y=o['base'];w,h=o['width'],o['height']
   for p in equipment[i+1:]:
    xx,yy=p['base'];ww,hh=p['width'],p['height']
    assert not (x<xx+ww and x+w>xx and y<yy+hh and y+h>yy),('Machine overlap',o,p)
  report={'edited_from':'v4 saved CDW','sheet':a.document_state(d)['sheet'],'lockers':40,'floor_pallet_positions':45,'loaded_pallet_capacity_two_levels':90,'production_lines':2,'cooling_tunnels':len(tunnels),'no_machine_overlaps':True,'native_edit_calls':len(calls),'objects':len(objects),'reopened':True}
  (out/'factory-v5-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  print('FACTORY V5 EDIT PASS',json.dumps(report,ensure_ascii=False),flush=True)
 finally:
  a.shutdown();(out/'factory-v5-api-calls.json').write_text(json.dumps(calls,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':run()
