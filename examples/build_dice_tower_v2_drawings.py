"""Generate associated drawings for a verified V2.1 run. Paths are CLI arguments."""
import argparse,os,sys,json,math,itertools,hashlib
from pathlib import Path
from client import Client

def build_drawings(output,executable=None,assembly_only=False):
 root=Path(output).resolve()
 if (root/'current.json').exists():
  manifest=json.loads((root/'current.json').read_text(encoding='utf-8'))
  run=(root/manifest['run']).resolve()
  if not run.is_relative_to(root/'runs'):raise ValueError('Manifest escapes output runs')
  root=run
 out=root/'drawings';out.mkdir(exist_ok=True)
 native_hashes=b''.join(hashlib.sha256(p.read_bytes()).digest() for p in sorted(root.iterdir()) if p.suffix in ('.m3d','.a3d'))
 fingerprint=hashlib.sha256(Path(__file__).read_bytes()+(root/'tower-model-state.json').read_bytes()+native_hashes).hexdigest()
 stamp=out/'verified-drawings.json'
 if stamp.exists():
  prior=json.loads(stamp.read_text(encoding='utf-8'))
  if prior['fingerprint']==fingerprint and all((out/k).is_file() and hashlib.sha256((out/k).read_bytes()).hexdigest()==v for k,v in prior['files'].items()):
   print('REUSED DRAWINGS',out);return out
 elif any(out.glob('*.cdw')):raise ValueError('Existing unverified drawings are preserved; choose a new model run')
 data=json.loads((root/'tower-model-state.json').read_text(encoding='utf-8'));owned=[]
 with Client(timeout=150) as c:
  def call(t,**kw):return c.call(t,**kw)
  call('connect',launch=True,executable=executable or os.environ.get('KOMPAS_EXECUTABLE'))
  def text(d,x,y,s,h=3):call('set_active_view',document_id=d,view_number=0);call('text',document_id=d,x=x,y=y,value=s,height=h)
  def view(d,p,pr,name,x,y,s):return call('create_model_view',document_id=d,model_path=p,projection=pr,name=name,x=x,y=y,scale=s)['view_number']
  def dim(d,v,p,q,r,ori):
   call('set_active_view',document_id=d,view_number=v);call('linear_dimension',document_id=d,x1=p[0],y1=p[1],x2=q[0],y2=q[1],x3=r[0],y3=r[1],orientation=ori)
  def save(d,k):
   p=out/(k+'.cdw');call('save_document',document_id=d,path=str(p));call('export_pdf',document_id=d,path=str(p.with_suffix('.pdf')),color=False);call('export_png',document_id=d,path=str(p.with_suffix('.png')),dpi=100)
   count=call('model_view_state',document_id=d)['count'];call('close_document',document_id=d);owned.remove(d)
   d=call('open_document',path=str(p))['document_id'];owned.append(d);vs=call('model_view_state',document_id=d);assert vs['count']==count and all(v['source_path'] for v in vs['views']);call('close_document',document_id=d);owned.remove(d);print('DRAWING',k,flush=True)
  try:
   d=call('create_drawing')['document_id'];owned.append(d);call('set_sheet',document_id=d,format='A2',landscape=True);p=str(root/'00-dice-tower.a3d')
   f=view(d,p,'front','Общий вид',105,75,.8);view(d,p,'top','План',255,117,.5)
   left=view(d,p,'left','Боковой вид',300,188,.3)
   call('create_section_view',document_id=d,base_view_number=left,points=[[0,-10],[0,345]],name='A',x=440,y=100,scale=.65)
   dim(d,f,[-78,0],[78,0],[0,-14],'horizontal');dim(d,f,[-78,0],[-78,330],[-95,165],'vertical')
   text(d,45,393,'DT2 — ПОРТАЛЬНЫЙ РЕАКТОР РИКА',6);text(d,45,381,'Вариант 2 | учебная модель MCP | размеры в мм',3.5)
   notes=['42 компонента; 27 деталей. Скаты: 265 / 205 / 145 / 85 мм.', 'Скаты: 30°, горизонтальная проекция 38 мм, толщина 2,5 мм.', 'Корпус: loft по пяти сечениям, радиусы 53 / 56 / 53 / 54 / 51 мм.', 'Полость: радиусы сечений уменьшены на 3 мм; это не shell постоянной толщины.', 'Кубики до 20 мм: геометрический ориентир диагонали 34,64 мм.', 'Выходной скат: 8°. Полки корпуса и воронки — клеевые посадки.', 'Крышка: 4 винта M3x8; отверстия 3,4 мм; пилоты 2,5 мм.']
   for i,n in enumerate(notes):text(d,25,50-i*6,n,2.8)
   save(d,'00-assembly')
   for k,p in ([] if assembly_only else data['models'].items()):
    b=data['states'][k]['bounds_mm'];lo=b['min'];hi=b['max'];sz=b['size'];d=call('create_drawing')['document_id'];owned.append(d);call('set_sheet',document_id=d,format='A3',landscape=True)
    sc=min(1.5,155/max(sz[0],sz[2],1));f=view(d,p,'front','Главный вид',55-sc*lo[0],95-sc*lo[2],sc)
    ts=min(1,90/max(sz[0],sz[1],1));top=view(d,p,'top','План',230-ts*lo[0],75-ts*lo[1],ts)
    corners=list(itertools.product(*zip(lo,hi)));r=math.sqrt(.5);s=math.sqrt(1/6);t=math.sqrt(2/3);iscl=min(.7,90/max(sz));ix=min(r*(x-y) for x,y,z in corners);iy=min(s*(x+y)+t*z for x,y,z in corners);view(d,p,'isometric','Изометрия',260-iscl*ix,185-iscl*iy,iscl)
    dim(d,f,[lo[0],lo[2]],[hi[0],lo[2]],[(lo[0]+hi[0])/2,lo[2]-12/sc],'horizontal')
    dim(d,f,[lo[0],lo[2]],[lo[0],hi[2]],[lo[0]-12/sc,(lo[2]+hi[2])/2],'vertical')
    dim(d,top,[hi[0],lo[1]],[hi[0],hi[1]],[hi[0]+12/ts,(lo[1]+hi[1])/2],'vertical')
    text(d,45,278,'DT2  '+k,5);text(d,45,268,'Ассоциативные виды исходной детали | размеры в мм',3)
    text(d,25,38,'Учебный проект. Контур воспроизводить по нативной модели.',2.8);text(d,25,31,'Клеевые контакты; допуски и ход кубика проверить на прототипе.',2.8)
    save(d,k)
  finally:
   (root/'tower-drawings-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
   for d in reversed(owned):
    try:call('close_document',document_id=d)
    except Exception:pass
 
 stamp.write_text(json.dumps({'fingerprint':fingerprint,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in ('.cdw','.pdf','.png')}},indent=2),encoding='utf-8')
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--executable');p.add_argument('--assembly-only',action='store_true');a=p.parse_args();print(build_drawings(a.output,a.executable,a.assembly_only))
