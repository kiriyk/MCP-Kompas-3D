"""Native revision 6: kitchen furniture and second chocolate preparation train."""
import json, math
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

def run():
 out=Path(__file__).resolve().parents[1]/'artifacts';a=Adapter()
 try:
  a.connect();d=a.open_document(str(out/'Цех-40x24-А0-v5.cdw'))['document_id']
  a.save_document(d,str(out/'Цех-40x24-А0-v6.cdw'));a.set_active_view(d,1)
  old=a.list_objects(d)['items']
  def layer(n):a.set_active_layer(d,n)
  def rect(x,y,w,h,style=2):return a.rectangle(d,x,y,w,h,style)
  def line(x,y,xx,yy,style=2):return a.line(d,x,y,xx,yy,style)
  def text(x,y,s,h=2.6):
   layer(5);return a.text(d,x,y,s,h)
  def exact(x,y,w,h):return next(o for o in old if o['view']==1 and o['type']=='rectangle' and o['base']==[x,y] and o['width']==w and o['height']==h)
  def label(s):return next(o for o in old if o['view']==1 and o.get('value')==s)
  # Read real contour/hatch boundaries before replacing the two sanitary blocks.
  container=a._container(d)
  native={}
  for name in ('DrawingContours','Hatches'):
   coll=getattr(container,name)
   native.update({coll.Item(i).Reference:coll.Item(i) for i in range(coll.Count)})
  def contour_points(raw):
   contour=a.api7.IContour(raw._oleobj_.QueryInterface(a.api7.IContour.CLSID,a.com.IID_IDispatch));pts=[]
   for j in range(contour.Count):
    seg=contour.Segment(j)
    try:
     l=a.api7.IContourLineSegment(seg._oleobj_.QueryInterface(a.api7.IContourLineSegment.CLSID,a.com.IID_IDispatch));pts.extend([[l.X1,l.Y1],[l.X2,l.Y2]])
    except a.com.com_error:
     arc=a.api7.IContourArc(seg._oleobj_.QueryInterface(a.api7.IContourArc.CLSID,a.com.IID_IDispatch));pts.extend([[arc.Xc-arc.Radius,arc.Yc-arc.Radius],[arc.Xc+arc.Radius,arc.Yc+arc.Radius]])
   return pts
  def uncached_points(o):
   if 'corners' in o:return o['corners']
   if 'points' in o:return o['points']
   if 'base' in o:return [o['base']]
   if 'center' in o:return [o['center']]
   if o['type']=='contour':return contour_points(native[o['api_reference']])
   if o['type']=='hatch':
    raw=native[o['api_reference']];bound=a.api7.IBoundariesObject(raw._oleobj_.QueryInterface(a.api7.IBoundariesObject.CLSID,a.com.IID_IDispatch)).Boundaries
    return [p for c in bound for p in contour_points(c)]
   return []
  bounds_cache={}
  def points(o):
   ref=o['api_reference']
   if ref not in bounds_cache:bounds_cache[ref]=uncached_points(o)
   return bounds_cache[ref]
  removed=0
  for o in old:
   if o['view']!=1 or o['layer_number'] not in (1,2,5,6):continue
   pts=points(o)
   if pts and (all(5400<=x<=7800 and 4500<=y<=9300 for x,y in pts) or all(300<=x<=4000 and 11200<=y<=15200 for x,y in pts)):
    a.delete_object(d,o['reference']);removed+=1
  def wall(x,y,w,h):
   layer(1);rect(x,y,w,h,1);layer(6);a.hatch_rectangle(d,x,y,w,h,3.5)
  def door(x,y,w,start,end):
   layer(1);a.arc(d,x,y,w,start,end,2)
   # Leaf is shown at the open end of the quarter-circle.
   angle=math.radians(end);line(x,y,x+w*math.cos(angle),y+w*math.sin(angle))
  def toilet(x,y):
   layer(2);rect(x,y,480,160)
   a.mixed_contour(d,[{'type':'line','x1':x+40,'y1':y+160,'x2':x+40,'y2':y+380},{'type':'arc','x':x+240,'y':y+380,'radius':200,'start_angle':0,'end_angle':180},{'type':'line','x1':x+440,'y1':y+380,'x2':x+440,'y2':y+160},{'type':'line','x1':x+440,'y1':y+160,'x2':x+40,'y2':y+160}],2)
   a.arc(d,x+240,y+360,125,0,180,2)
  def sink(x,y):
   layer(2);rect(x,y,600,450);rounded(x+70,y+60,460,290,100);a.circle(d,x+300,y+220,25,2);line(x+300,y+450,x+300,y+340)
  # WC and showers each have their own entrance from the changing room.
  for v in ((5400,4500,100,1600),(5400,6900,100,800),(5400,8500,100,800),(5500,7100,2300,100),(6600,4500,100,1400),(5500,5900,150,100),(6350,5900,550,100),(7600,5900,200,100)):wall(*v)
  door(5500,6900,800,270,360);door(5500,8500,800,270,360)
  door(6350,5900,700,180,270);door(7600,5900,700,180,270)
  toilet(5800,4500);toilet(6950,4500)
  # Shower trays against the external side wall; curtains separate the stalls.
  layer(2)
  for y in (7250,8350):
   rect(6800,y,900,900);line(6800,y,7700,y+900);line(7700,y,6800,y+900);a.circle(d,7250,y+450,45,2);a.arc(d,7670,y+450,140,90,270,2);line(6700,y+80,6700,y+820,4)
  wall(6650,8250,1150,100)
  # Production WC: vestibule plus TWO independently accessible cubicles.
  for v in ((300,11200,100,3000),(3900,11200,100,3000),(400,14200,800,100),(2200,14200,1800,100),(2150,11200,100,1700),(400,12900,800,100),(1900,12900,900,100),(3500,12900,400,100)):wall(*v)
  door(1200,14200,1000,270,360);door(1900,12900,700,180,270);door(3500,12900,700,180,270)
  toilet(800,11200);toilet(2850,11200)
  # Replace the two kitchen tables and seven crude seats, preserving sinks and appliances.
  for o in old:
   if o['view']==1 and o['type']=='rectangle' and o['layer_number']==2 and (o['base'] in ([1800,1300],[4800,1300]) and (o['width'],o['height'])==(1800,900) or (o['width'],o['height'])==(500,500) and o['base'][0]<7000 and o['base'][1]<3000):a.delete_object(d,o['reference'])
  kitchen=[o['reference'] for o in old if o['view']==1 and o['layer_number']==2 and points(o) and all(600<=x<=4100 and 3200<=y<=3800 for x,y in points(o))]
  a.move_objects(d,kitchen,0,500)  # Counter with both sinks and hob now touches the kitchen wall.
  layer(2)
  def rounded(x,y,w,h,r=65):
   line(x+r,y,x+w-r,y);line(x+w,y+r,x+w,y+h-r);line(x+w-r,y+h,x+r,y+h);line(x,y+h-r,x,y+r)
   for cx,cy,start,end in ((x+w-r,y+r,270,360),(x+w-r,y+h-r,0,90),(x+r,y+h-r,90,180),(x+r,y+r,180,270)):a.arc(d,cx,cy,r,start,end,2)
  sink(7050,6650);sink(2700,13750)
  text(5600,6950,'WC',2.5);text(5550,9000,'ДУШЕВАЯ',2.5)
  text(500,13800,'WC ЦЕХА',2.5);text(2450,13150,'Шлюз',2.5);layer(2)
  for x in (1800,4800):
   rounded(x,1300,1800,900,80)
   for xx in (x+140,x+1660):
    for yy in (1440,2060):a.circle(d,xx,yy,45,4)
   for xx in (x+50,x+650,x+1250):
    for yy,back in ((650,True),(2350,False)):
     rounded(xx,yy,500,500,40);rect(xx+40,yy+35 if back else yy+390,420,75)
   text(x+190,1680,'Стол 1800 × 900',2.5);layer(2)
  # Reuse native equipment bodies, their internals and labels for a parallel preparation train.
  originals=[o for o in old if o['view']==1 and o['layer_number']==2 and ((o['type']=='rectangle' and o['base'][1]>=20700 and 1000<=o['base'][0]<=12400) or (o['type']=='circle' and 1000<=o['center'][0]<=18000 and o['center'][1]>=20700))]
  assert len(originals)==11,len(originals)
  for o in originals:a.copy_object(d,o['reference'],0,-5000)
  replacements={'Д1 Дозатор / весы':'Д2 Дозатор / весы','С1 Смеситель':'С2 Смеситель','М1 Шаровая мельница':'М2 Шаровая мельница','К1 Конш-машина':'К2 Конш-машина','Б1 Буфер':'Б3 Буфер','Б2 Буфер':'Б4 Буфер'}
  for source,new in replacements.items():
   copied=a.copy_object(d,label(source)['reference'],0,-5000);a.edit_text(d,copied['reference'],new)
  for geom,s,dx,dy in (((4700,17200,3600,900),'Стол дозирования',0,-4200),((4800,19100,2200,1000),'Фильтр / насос',0,-4600)):
   a.move_objects(d,[exact(*geom)['reference'],label(s)['reference']],dx,dy)
  a.move_object(d,label('Исходное сырьё: какао-масса, масло, сахар')['reference'],0,-6300)
  a.move_object(d,label('Подача сырья / ЭК')['reference'],0,-2300)
  for o in old:
   if o['view']!=1:continue
   if o['type']=='line' and o['layer_number']==3 and o.get('points') in ([[10400,11200],[10400,19300]],[[14400,11200],[14400,19300]]):
    a.delete_object(d,o['reference']);layer(3);x=o['points'][0][0];line(x,11200,x,15100,4)
   if o['type']=='polyline' and ((o['layer_number']==7 and min(p[0] for p in o['points'])<19000) or (o['layer_number']==7 and o['points']==[[19900,21800],[19900,17265],[20735,17265]]) or (o['layer_number']==3 and all(abs(p[0]-12400)<400 for p in o['points']))):a.delete_object(d,o['reference'])
  def route(points):
   a.polyline(d,points,style=2)
   for p,q in zip(points,points[1:]):
    if math.dist(p,q)<1300:continue
    x=(p[0]+q[0])/2;y=(p[1]+q[1])/2;t=math.atan2(q[1]-p[1],q[0]-p[0])
    a.polyline(d,[[x-250*math.cos(t)+140*math.sin(t),y-250*math.sin(t)-140*math.cos(t)],[x,y],[x-250*math.cos(t)-140*math.sin(t),y-250*math.sin(t)+140*math.cos(t)]],style=2)
  layer(3);route([[12400,4200],[12400,14900]])
  layer(7)
  route([[12400,7200],[12400,14900],[1800,14900],[1800,15800]])
  route([[1800,14900],[500,14900],[500,20350],[1800,20350],[1800,20800]])
  route([[1800,20400],[4300,20400],[7300,20400],[10750,20400],[14400,20400],[17200,20400],[17200,21800],[20735,21800]])
  route([[1800,15400],[4300,15400],[7300,15400],[10750,15400],[14400,15400],[17200,15400],[17200,16800],[20735,16800],[20735,17265]])
  text(4500,19800,'Подготовка 1',2.5);text(4500,18250,'Подготовка 2',2.5)
  dimensions=a.api7.ISymbols2DContainer(a._views(d).ActiveView).LineDimensions
  for i in range(dimensions.Count):
   dim=a.api7.ILineDimension(dimensions.Item(i))
   if dim.X1==7800 and dim.Y1==4500 and dim.Y2==7500:dim.Y2=7100;assert dim.Update()
  a.set_active_view(d,0)
  footer=next(o for o in old if o.get('value')=='Редакция 5 / 2 линии');a.edit_text(d,footer['reference'],'Редакция 6 / 2 подготовки + 2 линии')
  a.save_document(d,str(out/'Цех-40x24-А0-v6.cdw'));a.export_png(d,str(out/'Цех-40x24-А0-v6.png'),100,'layer')
  for paper in ('sheet','A4'):
   for color in (True,False):a.export_pdf(d,str(out/f'Цех-40x24-v6-{paper}-{"color" if color else "bw"}.pdf'),paper=paper,color=color)
  a.close_document(d);d=a.open_document(str(out/'Цех-40x24-А0-v6.cdw'))['document_id'];items=a.list_objects(d)['items']
  assert all(any(o.get('value')==v for o in items) for v in replacements.values())
  assert sum(o['view']==1 and o['type']=='rectangle' and o['width']==3300 and o['height']==1900 for o in items)==2
  assert sum(o['view']==1 and o['type']=='rectangle' and o['width']==12500 and o['height']==780 for o in items)==2
  # No main preparation machine crosses the incoming forklift lane.
  for o in items:
   if o['view']==1 and o['layer_number']==2 and o['type']=='rectangle' and o['base'][0]<19000:
    x,y=o['base'];w,h=o['width'],o['height'];assert not(x<14400 and x+w>10400 and y<15100 and y+h>11200),o
  views=a._views(d);fonts=0
  for k in range(views.Count):
   texts=a.api7.IDrawingContainer(views.View(k)).DrawingTexts
   for i in range(texts.Count):
    item=a.api7.IText(texts.Item(i)).TextLine(0).TextItem(0);f=a.api7.ITextFont(item._oleobj_.QueryInterface(a.api7.ITextFont.CLSID,a.com.IID_IDispatch));assert f.FontName=='Arial';fonts+=1
  assert all(any(o['type']=='arc' and o.get('center')==c and o['radius']==r and abs((o['angles'][1]-o['angles'][0])%360-90)<.001 for o in items) for c,r in (([5500,6900],800),([5500,8500],800),([6350,5900],700),([7600,5900],700),([1900,12900],700),([3500,12900],700)))
  report={'reopened':True,'preparation_trains':2,'production_lines':2,'kitchen_tables':2,'kitchen_chairs':12,'separate_wc_shower_entries':True,'wc_cubicle_doors':4,'wall_mounted_sinks':2,'sanitary_objects_replaced':removed,'forklift_entry_clear':True,'all_drawing_texts_arial':fonts,'objects':len(items),'sheet':a.document_state(d)['sheet']}
  (out/'factory-v6-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False),flush=True)
 finally:a.shutdown()
if __name__=='__main__':run()
