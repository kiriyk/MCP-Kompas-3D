"""Generate native linked drawings from the saved teaching tower models."""
import argparse,json,math,itertools
from pathlib import Path
from client import Client

def build_drawings(output):
    output=Path(output).resolve();out=output/'drawings';out.mkdir(parents=True,exist_ok=True)
    data=json.loads((output/'tower-model-state.json').read_text(encoding='utf-8'));models=data['models'];states=data['states'];owned=[]
    with Client(timeout=75) as c:
        c.call('connect')
        def call(tool,**kw):return c.call(tool,**kw)
        def text(d,x,y,value,size=3.5):
            call('set_active_view',document_id=d,view_number=0);call('text',document_id=d,x=x,y=y,value=value,height=size)
        def view(d,model,projection,name,left,bottom,scale):
            return call('create_model_view',document_id=d,model_path=model,projection=projection,name=name,x=left,y=bottom,scale=scale)['view_number']
        def iso(d,model,lo,hi,left,bottom,scale):
            # Model origins need not coincide with the part bounding box.
            corners=list(itertools.product(*zip(lo,hi)))
            r=math.sqrt(.5);a=math.sqrt(1/6);b=math.sqrt(2/3)
            xmin=min(r*(x-y) for x,y,z in corners);ymin=min(a*(x+y)+b*z for x,y,z in corners)
            return view(d,model,'isometric','Изометрия',left-scale*xmin,bottom-scale*ymin,scale)
        def dim(d,v,p1,p2,p3,orientation):
            call('set_active_view',document_id=d,view_number=v)
            call('linear_dimension',document_id=d,x1=p1[0],y1=p1[1],x2=p2[0],y2=p2[1],x3=p3[0],y3=p3[1],orientation=orientation)
        def save(d,key):
            target=out/(key+'.cdw');call('save_document',document_id=d,path=str(target))
            call('export_pdf',document_id=d,path=str(target.with_suffix('.pdf')),color=False)
            call('export_png',document_id=d,path=str(target.with_suffix('.png')),dpi=120)
            expected=call('model_view_state',document_id=d)
            call('close_document',document_id=d);owned.remove(d)
            new=call('open_document',path=str(target))['document_id'];owned.append(new)
            actual=call('model_view_state',document_id=new)
            assert actual['count']==expected['count'] and all(v['source_path'] for v in actual['views'])
            assert all(v['scale']>0 for v in actual['views'])
            call('close_document',document_id=new);owned.remove(new)
            print('DRAWING',key,actual['count'],'linked views verified',flush=True)
        try:
            d=call('create_drawing')['document_id'];owned.append(d);call('set_sheet',document_id=d,format='A2',landscape=True)
            ap=str(output/'00-dice-tower.a3d')
            front=view(d,ap,'front','Общий вид',65,130,1)
            view(d,ap,'top','План',350,52.5,.25)
            view(d,ap,'isometric','Изометрия',515,185,.4)
            section=call('create_section_view',document_id=d,base_view_number=front,points=[[45,-5],[45,225]],name='A',x=325,y=130,scale=1)['view_number']
            dim(d,front,[-10,0],[100,0],[45,-22],'horizontal')
            dim(d,front,[-10,0],[-10,220],[-30,110],'vertical')
            # Section shows the complete 200 mm depth including rolling tray.
            dim(d,section,[-90,0],[110,0],[10,-22],'horizontal')
            text(d,100,397,'DT-000  ПОРТАЛЬНАЯ ЛАБОРАТОРИЯ РИКА',6)
            text(d,100,386,'Учебная модель MCP | башня для кубиков до 22 мм | все размеры в мм',3.5)
            # Native designations label the front and section views.
            text(d,345,15,'Вид сверху, 1:4',3.5);text(d,454,166,'Изометрия, 1:2,5',3.5)
            rows=['Состав сборки (10 компонентов)','01  Корпус лаборатории — 1','02  Сервисная стенка — 1','03  Перегородка — 3','04  Выходной скат — 1','05  Лоток — 1','06  Портал — 1','07  Силуэт Рика — 1','08  Силуэт Морти — 1']
            for i,row in enumerate(rows):text(d,439,135-i*7,row,3 if i else 3.5)
            notes=['1. Три перегородки: наклон 35°, отметки опор 200 / 145 / 90.',
                   '2. Выходной скат: 15°. Расчётный проход в торце ≥ 41,57 мм.',
                   '3. Зазор съёмных деталей 0,3 мм на сторону.',
                   '4. Стенка: 4 самореза Ø3 × 8 (покупные, в 3D не показаны).',
                   '5. Материал деталей — PLA. Физическая проверка после печати.']
            for i,n in enumerate(notes):text(d,25,78-i*7,n,3)
            save(d,'00-assembly')

            labels={'01-body':'Корпус лаборатории','02-cover':'Сервисная стенка','03-baffle':'Перегородка (3 шт.)','04-chute':'Выходной скат','05-tray':'Лоток','06-portal':'Портал','07-rick':'Силуэт Рика','08-morty':'Силуэт Морти'}
            for key,model in models.items():
                bounds=states[key]['bounds_mm'];lo=bounds['min'];hi=bounds['max'];size=bounds['size']
                d=call('create_drawing')['document_id'];owned.append(d);tall=size[2]>100;flat=size[2]<5
                call('set_sheet',document_id=d,format='A2' if tall else 'A3',landscape=True)
                sc=1. if tall or flat or size[0]>=60 else 2.
                bottom=130 if tall else (145 if flat else 115)
                front=view(d,model,'front','Главный вид',55-sc*lo[0],bottom-sc*lo[2],sc)
                top_sc=1. if tall or flat else (.5 if size[1]>100 else 1.)
                top_bottom=(10 if key=='01-body' else 25) if tall else (90 if flat else 100)
                top=view(d,model,'top','Вид сверху',(260 if tall else 175)-top_sc*lo[0],top_bottom-top_sc*lo[1],top_sc)
                iso(d,model,lo,hi,450 if tall else 280,160 if tall else 175,.5 if tall or size[1]>100 else 1.)
                dim(d,front,[lo[0],lo[2]],[hi[0],lo[2]],[(lo[0]+hi[0])/2,lo[2]-14/sc],'horizontal')
                if size[2]>8:dim(d,front,[lo[0],lo[2]],[lo[0],hi[2]],[lo[0]-14/sc,(lo[2]+hi[2])/2],'vertical')
                dim(d,top,[hi[0],lo[1]],[hi[0],hi[1]],[hi[0]+14/top_sc,(lo[1]+hi[1])/2],'vertical')
                if key=='01-body':
                    call('create_section_view',document_id=d,base_view_number=front,points=[[45,-5],[45,225]],name='B',x=325,y=130,scale=1.)
                    dim(d,front,[16,3],[74,3],[45,80],'horizontal')
                    dim(d,front,[74,3],[74,55],[103,29],'vertical')
                text(d,100,397 if tall else 277,f'DT-{int(key[:2]):03d}  {labels[key]}',5)
                text(d,100,386 if tall else 266,'Модель КОМПАС-3D | ассоциативные виды | размеры в мм',3.2)
                notes=['Материал: PLA (учебный проект).','Острые кромки притупить; посадки проверить на пробном образце.']
                if key=='01-body':notes+=['Стенка и дно 3 мм. Выход: X=16…74; Z=3…55.','Опоры 35°: Z=200/145/90; проекция 41 мм.','Резьбовые пилоты Ø2,8: X=9/81; Z=12/208.']
                elif key=='02-cover':notes+=['Толщина 2,4. Посадочный зазор 0,3 на сторону.','4 отв. Ø3,4: центры X=9/81; Z=12/208.']
                elif key in ('03-baffle','04-chute'):notes+=['Толщина 2,5 мм. Печатать плоской стороной на столе.','Установка: 35°.' if key=='03-baffle' else 'Установка: 15°.']
                elif key=='05-tray':notes+=['Дно и борта 3 мм. Высота борта 18 мм.','Внутренняя зона 104 × 107 мм; задняя сторона открыта.']
                elif key=='06-portal':notes+=['Толщина 4 мм. Вырез: X=16…74; Z=3…55.','Декоративный контур воспроизводить по нативной модели/STL.']
                else:notes+=['Толщина рельефа 1,8 мм.','Контур и отверстия декора воспроизводить по модели/STL.']
                for i,n in enumerate(notes):text(d,25,78-i*7,n,2.8)
                save(d,key)
        finally:
            (output/'tower-drawings-trace.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
            for d in reversed(owned):
                try:call('close_document',document_id=d)
                except Exception:pass
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();build_drawings(args.output)

