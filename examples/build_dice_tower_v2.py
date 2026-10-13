"""Portable staged V2.1 builder using only public MCP tools. Existing runs are preserved."""
import argparse,os,json,math,hashlib
from pathlib import Path
from client import Client
from tower_runs import RunStore

def build_native(ROOT,executable=None):
    models={};states={};placements=[];owned=[]
    with Client(timeout=120) as c:
     def call(t,**kw):return c.call(t,**kw)
     call('connect',launch=True,executable=executable or os.environ.get('KOMPAS_EXECUTABLE'))
     def new(k):
      d=call('create_part',name=k)['document_id'];owned.append(d);return d
     def sk(d,plane='XY',offset=0):return call('create_sketch',document_id=d,plane=plane,offset=offset)['sketch_reference']
     def circle(d,r,plane='XY',offset=0,x=0,y=0):
      s=sk(d,plane,offset);call('sketch_circle',document_id=d,sketch_reference=s,x=x,y=y,radius=r);return s
     def poly(d,pts,plane='XY',offset=0):
      s=sk(d,plane,offset);call('sketch_polygon',document_id=d,sketch_reference=s,points=pts);return s
     def extr(d,s,h,op='base',rev=False,name='Extrusion'):return call('extrude',document_id=d,sketch_reference=s,depth=h,operation=op,reverse=rev,name=name)
     def loft(d,sections,op='base'):return call('loft',document_id=d,sketch_references=sections,operation=op)
     def rect(x,y,w,h):return [[x,y],[x+w,y],[x+w,y+h],[x,y+h]]
     def xz(d,pts,h,op='base',off=0):return extr(d,poly(d,[[x,-z] for x,z in pts],'XZ',off),h,op)
     def seat(d,sign,height):
      xs=[-53,-30] if sign==1 else [30,53]
      start=-38*sign
      top=lambda x:height-(x-start)*sign*math.tan(math.pi/6)
      pts=[[xs[0],top(xs[0])],[xs[1],top(xs[1])],[xs[1],top(xs[1])-4],[xs[0],top(xs[0])-4]]
      for y in [-25,22]:xz(d,pts,3,'boss',y)
     def ellipse(rx,ry,n=40):return [[rx*math.cos(2*math.pi*i/n),ry*math.sin(2*math.pi*i/n)] for i in range(n)]
     def finish(d,k,col):
      call('set_model_material',document_id=d,name='PLA (design assumption)',density_g_cm3=1.24)
      state=call('rebuild_model',document_id=d);assert state['body_count']==1 and state['volume_mm3']>0
      col=((col&255)<<16)|(col&0xFF00)|((col>>16)&255)
      call('set_model_appearance',document_id=d,color=col,transparency_percent=60 if k=='02-curved-window' else 0);call('set_model_display',document_id=d,transparency_percent=60 if k=='02-curved-window' else 0)
      p=ROOT/(k+'.m3d');call('save_model',document_id=d,path=str(p));models[k]=str(p);states[k]=state
      call('close_model',document_id=d);owned.remove(d);print('BUILT',k,flush=True)
      reopened=call('open_model',path=str(p))['document_id'];owned.append(reopened);check=call('rebuild_model',document_id=reopened);assert abs(check['volume_mm3']-state['volume_mm3'])<.01;call('close_model',document_id=reopened);owned.remove(reopened)
      (ROOT/'tower-build-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
     def put(k,origin=(0,0,0),xa=(1,0,0),ya=(0,1,0)):placements.append((k,list(origin),list(xa),list(ya)))
     try:
      sections=[(35,53,0),(85,56,-3),(145,53,3),(205,54,-2),(260,51,0)]
      d=new('01-organic-body');loft(d,[circle(d,r,offset=z,y=y) for z,r,y in sections]);loft(d,[circle(d,r-3,offset=z,y=y) for z,r,y in sections],'cut')
      xz(d,rect(-18,60,56,175),60,'cut',-75);xz(d,rect(-28,34,56,48),60,'cut',-75)
      xz(d,rect(-34,65,68,180),60,'cut',25)
      for sign,z in [(-1,205),(1,145),(-1,85)]:seat(d,sign,z)
      for x in [-37,37]:
       for z in [80,235]:
        xz(d,rect(x-3,z-6,6,12),35,'boss',30)
        extr(d,circle(d,1.25,'XZ',53,x,-z),12,'cut')
      for sign,z in [(-1,145),(1,110)]:
       for dz in [0,44]:
        s=circle(d,13,'YZ',-sign*57,x=-(z+dz));call('sketch_circle',document_id=d,sketch_reference=s,x=-(z+dz),y=0,radius=10);extr(d,s,8,'boss',rev=sign<0)
        extr(d,circle(d,10,'YZ',-sign*70,x=-(z+dz)),25,'cut',rev=sign<0)
      for z in [211,126]:extr(d,circle(d,6,'XZ',-54,-48,-z),30,'boss')
      # Outlet plate rests on two integral ledges, outside the useful dice corridor.
      for sign in [-1,1]:
       ys=[-23,-20];zz=lambda y:15+(y+90)*math.tan(math.radians(8))
       pts=[[zz(ys[0]),ys[0]],[zz(ys[1]),ys[1]],[zz(ys[1])-4,ys[1]],[zz(ys[0])-4,ys[0]]]
       extr(d,poly(d,[[-z,-y] for z,y in pts],'YZ',-sign*52),29,'boss',rev=sign<0)
       xz(d,rect(27 if sign>0 else -52,zz(-23)-1,25,43-zz(-23)+1),3,'boss',-23)
      finish(d,'01-organic-body',0xDBC9B0);put('01-organic-body')
      d=new('02-curved-window');loft(d,[circle(d,r+1.8,offset=z,y=y) for z,r,y in sections]);loft(d,[circle(d,r+.3,offset=z,y=y) for z,r,y in sections],'cut')
      extr(d,poly(d,rect(-100,-100,200,200)),60,'cut');extr(d,poly(d,rect(-100,-100,200,200),offset=235),60,'cut')
      xz(d,rect(-100,0,200,300),100,'cut',0)
      extr(d,poly(d,rect(-300,-100,300,200),'YZ',19),100,'cut')
      extr(d,poly(d,rect(-300,-100,300,200),'YZ',-39),100,'cut',rev=True)
      finish(d,'02-curved-window',0x71BDA4);put('02-curved-window')
      d=new('03-ramp');extr(d,poly(d,rect(0,-25,38/math.cos(math.radians(30)),50)),2.5);finish(d,'03-ramp',0xE97027)
      for i,z in enumerate([265,205,145,85]):
       sign=1 if i%2==0 else -1;put('03-ramp',(-38*sign,0,z),(sign*math.cos(math.radians(30)),0,-math.sin(math.radians(30))),(0,sign,0))
      d=new('04-funnel');loft(d,[circle(d,r,offset=z,x=x) for z,r,x in [(0,49,0),(18,55,4),(42,65,12)]]);loft(d,[circle(d,r,offset=z,x=x) for z,r,x in [(0,46,0),(18,52,4),(42,62,12)]],'cut');seat(d,1,5);finish(d,'04-funnel',0xF59432);put('04-funnel',(0,0,260))
      d=new('05-tray');extr(d,circle(d,75),18)
      faces=call('list_model_topology',document_id=d,kind='face')['items'];top=[f for f in faces if f['planar'] and f['bounds_mm'] and abs(f['bounds_mm']['min'][2]-18)<.01];assert len(top)==1
      call('shell',document_id=d,face_references=[top[0]['reference']],thickness=3,inward=True);finish(d,'05-tray',0x8155CB);put('05-tray',(0,-122,0))
      d=new('06-tray-rim');s=circle(d,78);call('sketch_circle',document_id=d,sketch_reference=s,x=0,y=0,radius=75);extr(d,s,12);finish(d,'06-tray-rim',0xE98F28);put('06-tray-rim',(0,-122,3))
      d=new('07-portal');s=circle(d,46,'XZ',x=0,y=-50);call('sketch_circle',document_id=d,sketch_reference=s,x=0,y=-50,radius=41);extr(d,s,7)
      for x in [-35,29]:xz(d,rect(x,3,6,17),7,'boss')
      finish(d,'07-portal',0x49ED41);put('07-portal',(0,-70,0))
      for k,oy in [('08-front-support',-26),('08-rear-support',18)]:
       d=new(k);xz(d,[[-65,0],[-48,73],[-30,88],[30,88],[48,73],[65,0]],8)
       extr(d,circle(d,28,'XZ',x=0,y=-34),8,'cut');xz(d,rect(-28,4,56,30),8,'cut')
       loft(d,[circle(d,r+.4,offset=z,y=y-oy) for z,r,y in sections],'cut')
       if k=='08-front-support':
        for x in [-52.4,26.6]:xz(d,rect(x,19,25.8,25),8,'cut')
       finish(d,k,0x4753D2);put(k,(0,oy,0))
      d=new('09-hose');s=circle(d,6,'XZ');call('sketch_circle',document_id=d,sketch_reference=s,x=0,y=0,radius=3.5);path=sk(d);call('sketch_arc',document_id=d,sketch_reference=path,x=22,y=0,radius=22,start_angle=180,end_angle=0,clockwise=True);call('sweep',document_id=d,profile_reference=s,path_references=[path]);finish(d,'09-hose',0x393D47)
      for sign,z in [(-1,145),(1,110)]:put('09-hose',(sign*50,0,z),(0,0,1),(sign,0,0))
      d=new('10-collar');s=circle(d,13);call('sketch_circle',document_id=d,sketch_reference=s,x=0,y=0,radius=10);extr(d,s,2);finish(d,'10-collar',0xBE3AC6)
      for sign,z in [(-1,145),(1,110)]:
       for dz in [0,44]:put('10-collar',(sign*57,0,z+dz),(0,1,0),(0,0,sign))
      d=new('11-crystal');loft(d,[poly(d,ellipse(r,r,6),offset=z) for z,r in [(0,8),(20,6),(39,.7)]]);finish(d,'11-crystal',0x56D8E9)
      for x,y,z in [(-35,22,289),(0,36,290),(32,27,291)]:put('11-crystal',(x,y,z))
      # Layered Rick and Morty reliefs; all visible layers have real native solids.
      for who,z,base in [('rick',211,0xA7E6EF),('morty',126,0x68452A)]:
       d=new('12-'+who+'-back')
       if who=='rick':pts=[[x,-zz] for x,zz in [[-19,-17],[-24,-8],[-20,0],[-27,9],[-15,8],[-18,23],[-8,16],[-4,31],[3,20],[13,29],[14,16],[26,19],[21,7],[28,6],[19,-3],[17,-17]]]
       else:pts=ellipse(23,25)
       extr(d,poly(d,pts,'XZ'),3);finish(d,'12-'+who+'-back',base);put('12-'+who+'-back',(-48,-57,z))
       d=new('13-'+who+'-face');loft(d,[poly(d,ellipse(rx,rz),'XZ',off) for off,rx,rz in [(0,16,20),(-3,17,20),(-6,14,18)]]);xz(d,rect(-4,-25,8,7),3,'boss',-3)
       finish(d,'13-'+who+'-face',0xF3D5A0);put('13-'+who+'-face',(-48,-57,z))
      d=new('14-morty-eye');loft(d,[circle(d,r,'XZ',off) for off,r in [(0,6),(-2,6.5),(-4,4.5)]]);finish(d,'14-morty-eye',0xF5F5ED)
      d=new('14-rick-eye');loft(d,[poly(d,ellipse(rx,rz),'XZ',off) for off,rx,rz in [(0,6,3.5),(-2,6.2,3.5),(-4,4.5,2.8)]]);finish(d,'14-rick-eye',0xF5F5ED)
      d=new('15-pupil');extr(d,circle(d,1.6,'XZ'),1.2);finish(d,'15-pupil',0x252835)
      d=new('16-mouth');extr(d,poly(d,ellipse(6,2.8),'XZ'),1);finish(d,'16-mouth',0x542A36)
      d=new('18-rick-brow');xz(d,[[-13,10],[0,11],[13,10],[13,12],[0,13],[-13,12]],1.5);finish(d,'18-rick-brow',0xA7E6EF);put('18-rick-brow',(-48,-64.5,211))
      d=new('19-rick-nose');xz(d,[[-1,0],[2,0],[4,-5],[1,-7],[-2,-5]],3);finish(d,'19-rick-nose',0xF3D5A0);put('19-rick-nose',(-48,-66,211))
      d=new('20-teeth');xz(d,rect(-4,-11,8,1.4),1);finish(d,'20-teeth',0xEFEFE1);put('20-teeth',(-48,-65,211))
      for who,z,key,color in [('rick',211,'21-rick-coat',0xEFEFE8),('morty',126,'22-morty-shirt',0xEAD536)]:
       d=new(key);xz(d,[[-7,-25],[7,-25],[18,-42],[-18,-42]],1.5);finish(d,key,color);put(key,(-48,-58.5,z))
      for who,z in [('rick',211),('morty',126)]:
       for dx in [-7,7]:put('14-'+who+'-eye',(-48+dx,-63,z+4));put('15-pupil',(-48+dx,-68.2,z+4))
       put('16-mouth',(-48,-64,z-10))
      d=new('17-exit-chute');extr(d,poly(d,rect(0,0,50,130/math.cos(math.radians(8)))),2.5);finish(d,'17-exit-chute',0xE97027);put('17-exit-chute',(-25,-90,15),(1,0,0),(0,math.cos(math.radians(8)),math.sin(math.radians(8))))
      d=new('23-service-cover');xz(d,rect(-40,62,80,186),3)
      for x in [-37,37]:
       for z in [80,235]:extr(d,circle(d,1.7,'XZ',x=x,y=-z),3,'cut')
      finish(d,'23-service-cover',0x62C9CC);put('23-service-cover',(0,65,0))
      a=call('create_assembly',name='DT2.1 Portal reactor')['document_id'];owned.append(a)
      for i,(k,o,xa,ya) in enumerate(placements):
       call('upsert_component',document_id=a,path=models[k],name=f'{i+1:02d} {k}',origin=o,x_axis=xa,y_axis=ya)
      call('rebuild_model',document_id=a);call('set_model_display',document_id=a);ap=ROOT/'00-dice-tower.a3d';call('save_model',document_id=a,path=str(ap));call('close_model',document_id=a);owned.remove(a)
      a=call('open_model',path=str(ap))['document_id'];owned.append(a);states['assembly']=call('model_state',document_id=a);components=call('list_components',document_id=a);assert components['count']==len(placements)
      call('set_model_display',document_id=a);call('set_model_orientation',document_id=a,projection='front_isometric');call('export_model_png',document_id=a,path=str(ROOT/'tower-preview.png'))
      (ROOT/'tower-model-state.json').write_text(json.dumps({'models':models,'states':states,'components':components,'placements':placements},ensure_ascii=False,indent=2),encoding='utf-8')
      intersections=call('check_assembly_intersections',document_id=a);(ROOT/'assembly-intersections.json').write_text(json.dumps(intersections,ensure_ascii=False,indent=2),encoding='utf-8')
      for projection in ['front','left','front_isometric']:
       call('set_model_orientation',document_id=a,projection=projection);call('export_model_png',document_id=a,path=str(ROOT/('tower-'+projection+'.png')))
      print('ASSEMBLY',len(placements),'verified, interference pairs',intersections['interference_count'],flush=True)
     finally:
      (ROOT/'tower-build-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
      for d in reversed(owned):
       try:call('close_model',document_id=d)
       except Exception:pass

    return ROOT,{'native_verified':True,'component_count':len(placements),'interference_count':intersections['interference_count']}

def build(output,executable=None,force=False):
    store=RunStore(output);fingerprint=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    previous=None if force else store.reusable(fingerprint)
    if previous is not None:
        print('REUSED VERIFIED RUN',previous,flush=True);return previous
    run=store.begin();run,verification=build_native(run,executable)
    if verification['interference_count']:raise RuntimeError(f'Interferences require review; draft preserved at {run}')
    store.publish(run,fingerprint,verification);return run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);parser.add_argument('--executable');parser.add_argument('--force',action='store_true');args=parser.parse_args();print(build(args.output,args.executable,args.force))
