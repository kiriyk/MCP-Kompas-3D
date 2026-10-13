"""Build the Rick-and-Morty teaching tower exclusively with public MCP tools.

Run: python examples/build_dice_tower.py --output <absolute directory>
KOMPAS_EXECUTABLE must point to the installed v21 executable.
"""
import argparse,json,math
from pathlib import Path
from client import Client
from dice_tower_parameters import tower_parameters,validate_dice_clearances

def build(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    p=tower_parameters();facts=validate_dice_clearances(p);models={};states={};owned=[]
    (output/'tower-parameters.json').write_text(json.dumps({'parameters':p,'clearances':facts},indent=2),encoding='utf-8')
    with Client(timeout=75) as c:
        c.call('connect')
        def call(tool,**kwargs):return c.call(tool,**kwargs)
        def new(key,label):
            doc=call('create_part',name=label)['document_id'];owned.append(doc);return doc
        def profile(doc,plane,pts,depth,operation='base',offset=0,reverse=False,name='Extrusion'):
            sk=call('create_sketch',document_id=doc,plane=plane,name=name+' profile',offset=offset)['sketch_reference']
            call('sketch_polygon',document_id=doc,sketch_reference=sk,points=pts)
            return call('extrude',document_id=doc,sketch_reference=sk,depth=depth,operation=operation,reverse=reverse,name=name)
        def rect(x,y,w,h):return [[x,y],[x+w,y],[x+w,y+h],[x,y+h]]
        def xz(doc,pts,depth,operation='boss',offset=0,reverse=False,name='Front detail'):
            return profile(doc,'XZ',[[x,-z] for x,z in pts],depth,operation,offset,reverse,name)
        def circle(doc,x,z,radius,depth,offset=0):
            sk=call('create_sketch',document_id=doc,plane='XZ',offset=offset)['sketch_reference']
            call('sketch_circle',document_id=doc,sketch_reference=sk,x=x,y=-z,radius=radius)
            return call('extrude',document_id=doc,sketch_reference=sk,depth=depth,operation='cut',name='Hole')
        def finish(doc,key,color):
            call('set_model_color',document_id=doc,color=color)
            call('set_model_material',document_id=doc,name='PLA (учебный проект)',density_g_cm3=1.24)
            path=output/(key+'.m3d');call('save_model',document_id=doc,path=str(path))
            call('export_model',document_id=doc,path=str(output/(key+'.stl')))
            states[key]=call('model_state',document_id=doc);models[key]=str(path)
            call('close_model',document_id=doc);owned.remove(doc)
            (output/'tower-build-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
            print('BUILT',key,'volume',round(states[key]['volume_mm3'],2),'bounds',states[key]['bounds_mm']['size'],flush=True)
        try:
            body=new('body','DT-001 Корпус лаборатории')
            profile(body,'XY',rect(0,0,90,90),220,name='Outer shell')
            profile(body,'XY',rect(3,3,84,84),217,'cut',offset=3,name='Open chamber')
            profile(body,'XY',rect(3,87,84,3),214,'cut',offset=3,name='Service panel opening')
            xz(body,rect(16,3,58,52),3,'cut',name='Dice outlet')
            # Integrated ledges support removable plates; their top follows the ramp.
            for i,high in enumerate(p['baffle_heights']):
                start=3 if i%2==0 else 87;end=start+(41 if i%2==0 else -41);low=high-41*math.tan(math.radians(35))
                yz=[[start,high],[end,low],[end,low-3],[start,high-3]]
                for xpos in (0,85):
                    profile(body,'YZ',[[-z,-y] for y,z in yz],5,'boss',offset=-xpos,reverse=True,name=f'Ramp {i+1} ledge')
            # Exit chute ledges.
            high=3.3+83.4*math.tan(math.radians(15));yz=[[3.3,3.3],[86.7,high],[86.7,high-3],[3.3,.3]]
            for xpos in (0,85):profile(body,'YZ',[[-z,-y] for y,z in yz],5,'boss',offset=-xpos,reverse=True,name='Exit chute ledge')
            # Rear service cover fastens to four integral corner tabs.
            for x in (9,81):
                for z in (12,208):
                    xz(body,rect(x-6,z-5,12,10),3,'boss',offset=84,name='Cover mounting tab')
                    circle(body,x,z,1.4,3,offset=84)
            # Front laboratory panel strips sit above the character silhouettes.
            for x,w in ((8,26),(39,43)):
                xz(body,rect(x,195,w,8),.8,'boss',reverse=True,name='Laboratory panel')
            finish(body,'01-body',0xCEC4B7)

            cover=new('cover','DT-002 Сервисная стенка')
            xz(cover,rect(3.3,3.3,83.4,213.4),2.4,'base',name='Removable cover')
            for x in (9,81):
                for z in (12,208):circle(cover,x,z,1.7,2.4)
            finish(cover,'02-cover',0xC5B6A4)

            baffle=new('baffle','DT-003 Перегородка, 3 шт.')
            profile(baffle,'XY',rect(0,0,facts['plate_width_mm'],facts['baffle_length_mm']),2.5,name='Deflector plate')
            finish(baffle,'03-baffle',0x9B8C72)

            chute=new('chute','DT-004 Выходной скат')
            length=83.4/math.cos(math.radians(15))
            profile(chute,'XY',rect(0,0,83.4,length),2.5,name='Outlet ramp')
            finish(chute,'04-chute',0x9B8C72)

            tray=new('tray','DT-005 Лоток')
            profile(tray,'XY',rect(-10,-110,110,110),18,name='Tray blank')
            profile(tray,'XY',rect(-7,-107,104,107),15,'cut',offset=3,name='Open rolling tray')
            finish(tray,'05-tray',0x4B4540)

            portal=new('portal','DT-006 Портал')
            pts=[]
            for i in range(40):
                t=2*math.pi*i/40;r=1+.035*math.sin(5*t)+.018*math.cos(9*t)
                pts.append([45+40*r*math.cos(t),35+32*r*math.sin(t)])
            xz(portal,pts,4,'base',name='Portal halo')
            xz(portal,rect(16,3,58,52),4,'cut',name='Portal mouth')
            finish(portal,'06-portal',0x33FF6B)

            rick=new('rick','DT-007 Силуэт Рика')
            outline=[[11,153],[8,163],[17,162],[12,174],[22,170],[23,183],[29,174],[39,181],[38,169],[47,170],[40,158],[38,147],[36,132],[22,130],[17,143]]
            xz(rick,outline,1.8,'base',name='Rick silhouette')
            for x in (25,33):circle(rick,x,151,1.7,1.8)
            xz(rick,rect(24,139,10,1.5),1.8,'cut',name='Rick mouth')
            finish(rick,'07-rick',0xF7E79F)

            morty=new('morty','DT-008 Силуэт Морти')
            outline=[[59,137],[53,141],[51,148],[53,155],[58,160],[65,162],[72,159],[77,153],[78,147],[75,140],[70,136],[70,131],[78,128],[80,111],[50,111],[52,128],[59,131]]
            xz(morty,outline,1.8,'base',name='Morty silhouette')
            for x in (60,69):circle(morty,x,150,1.8,1.8)
            xz(morty,rect(61,141,7,1.5),1.8,'cut',name='Morty mouth')
            finish(morty,'08-morty',0x65DCFF)

            assembly=call('create_assembly',name='DT-000 Портальная лаборатория Рика')['document_id'];owned.append(assembly)
            def insert(key,label,origin=(0,0,0),xa=(1,0,0),ya=(0,1,0)):
                ref=call('insert_component',document_id=assembly,path=models[key],name=label)['component_reference']
                call('set_component_placement',document_id=assembly,component_reference=ref,origin=list(origin),x_axis=list(xa),y_axis=list(ya))
            insert('01-body','01 Корпус');insert('02-cover','02 Стенка',(0,87.3,0));insert('05-tray','05 Лоток');insert('06-portal','06 Портал',(0,-4,0));insert('07-rick','07 Рик',(0,-1.8,0));insert('08-morty','08 Морти',(0,-1.8,0))
            angle=math.radians(35)
            for i,z in enumerate(p['baffle_heights']):
                sign=1 if i%2==0 else -1
                insert('03-baffle',f'03 Перегородка {i+1}',(3.3 if sign==1 else 86.7,3 if sign==1 else 87,z),(sign,0,0),(0,sign*math.cos(angle),-math.sin(angle)))
            angle=math.radians(15);insert('04-chute','04 Скат',(3.3,3.3,3.3),(1,0,0),(0,math.cos(angle),math.sin(angle)))
            ap=output/'00-dice-tower.a3d';call('save_model',document_id=assembly,path=str(ap));call('close_model',document_id=assembly);owned.remove(assembly)
            assembly=call('open_model',path=str(ap))['document_id'];owned.append(assembly)
            components=call('list_components',document_id=assembly);assert components['count']==10
            states['assembly']=call('model_state',document_id=assembly)
            assert all(abs(a-b)<1e-6 for a,b in zip(states['assembly']['bounds_mm']['size'],[110,200,220]))
            assert states['assembly']['volume_mm3']>300000
            (output/'tower-model-state.json').write_text(json.dumps({'models':models,'states':states,'components':components},ensure_ascii=False,indent=2),encoding='utf-8')
            call('close_model',document_id=assembly);owned.remove(assembly)
            print('ASSEMBLY verified after reopening: 10 components',flush=True)
        finally:
            (output/'tower-build-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
            for doc in reversed(owned):
                try:call('close_model',document_id=doc)
                except Exception:pass
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();build(args.output)
