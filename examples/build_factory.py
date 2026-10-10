"""Build the learning example exclusively through standard MCP tools/call."""
import json
from pathlib import Path
from client import Client

def build():
    out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
    with Client() as c:
        d=None;completed=False
        try:
            c.call('connect')
            previous=out/'Цех-40x24-А0.cdw'
            if previous.exists():
                previous_id=c.call('open_document',path=str(previous))['document_id']
                c.call('close_document',document_id=previous_id)
            d=c.call('create_drawing')['document_id']
            c.call('set_sheet',document_id=d,format='A0',landscape=True)
            view=c.call('create_view',document_id=d,name='План цеха 1:50',scale=.02,x=100,y=200)
            def call(tool,**args):return c.call(tool,document_id=d,**args)
            def line(x1,y1,x2,y2,style=1):return call('line',x1=x1,y1=y1,x2=x2,y2=y2,style=style)
            def rect(x,y,w,h,style=1):return call('rectangle',x=x,y=y,width=w,height=h,style=style)
            def txt(x,y,value,h=3.5,angle=0):return call('text',x=x,y=y,value=value,height=h,angle=angle)
            def copy(ref,dx,dy):return call('copy_object',reference=ref['reference'],dx=dx,dy=dy)
            def layer(n):call('set_active_layer',number=n)
            for n,name,color in [(1,'Стены и проёмы',0),(2,'Оборудование и мебель',0),(3,'Проезды и пешеходные пути',0),(4,'Размеры',0),(5,'Подписи',0),(6,'Штриховки',0)]:
                call('create_layer',name=name,number=n,color=color)

            # Wall segments leave real openings, including two loading gates.
            layer(1)
            walls=[(0,0,40000,300),(0,23700,40000,300),
                   (0,300,300,1200),(0,2700,300,6800),(0,13500,300,10200),
                   (39700,300,300,9200),(39700,13500,300,10200),
                   (300,9300,2200,200),(3700,9300,6700,200),(13600,9300,10200,200),(27000,9300,6300,200),(36500,9300,3200,200),
                   (300,15000,2200,200),(5700,15000,26100,200),(35000,15000,4700,200),
                   (7800,300,200,9000),(19000,300,200,9000),(32000,300,200,9000),
                   (19000,15200,200,8500),
                   (300,4300,2700,200),(4200,4300,3600,200)]
            for x,y,w,h in walls:rect(x,y,w,h)
            layer(6)
            for x,y,w,h in walls:call('hatch_rectangle',x=x,y=y,width=w,height=h,step=3.5)

            # Hinged pedestrian doors and sliding production gates.
            layer(1)
            for x,y,start,end in [(2500,9500,270,360),(3000,4300,0,90),(0,1500,0,90)]:
                call('arc',x=x,y=y,radius=1200,start_angle=start,end_angle=end,style=2)
            line(2500,9500,2500,8300,2);line(3000,4300,3000,5500,2);line(0,1500,1200,1500,2)
            for x1,x2,y in [(2500,5700,15000),(31800,35000,15000),(10400,13600,9500),(23800,27000,9500),(33300,36500,9500)]:
                line(x1,y,x2,y,4)
                line(x1,y+180,x1+1500,y+180,2);line(x2-1500,y+180,x2,y+180,2)

            # Process 1: preparation, mixing and intermediate storage.
            layer(2)
            vessel=call('circle',x=3500,y=21800,radius=750)
            copy(vessel,3000,0);copy(vessel,6000,0)
            rect(12500,20400,3000,2200);rect(15800,20400,2200,1800)
            rect(1000,16900,5000,900);rect(8000,16900,4000,900)
            layer(5)
            txt(1300,23200,'01  ПОДГОТОВКА ШОКОЛАДА',5)
            txt(1300,19100,'Плавление → смешивание → буферные ёмкости',3.5)
            for x,label in [(3100,'П1'),(6100,'П2'),(9100,'Б1')]:txt(x,21650,label,3)
            txt(12900,21300,'Смеситель',3);txt(16000,21100,'Меланжер',3)
            txt(1200,17150,'Дозирование сырья',3);txt(8400,17150,'Контроль качества',3)

            # Process 2: the previously specified real equipment dimensions.
            layer(2)
            call('circle',x=20735,y=22265,radius=635)
            rect(21670,22100,960,800);rect(22930,21900,1600,1000)
            rect(24830,22120,12500,780);rect(32000,17000,4800,1600)
            rect(21000,17000,3500,900);rect(26500,17000,3500,900)
            layer(5)
            txt(20300,23200,'02  ИЗГОТОВЛЕНИЕ И УПАКОВКА',5)
            txt(20400,22170,'Е1',2.5);txt(21720,22400,'Темпер',2)
            txt(23000,22300,'Глазировка',2)
            txt(26800,22370,'Охлаждающий тоннель 12 500×780',3)
            txt(32600,17600,'Флоупак 4 800×1 600',3)
            txt(21100,17300,'Формование',3);txt(26700,17300,'Стол контроля',3)
            txt(20000,20200,'Технологический проход',3)
            txt(25000,19400,'Е1 Ø1270 · темпер 960×800 · глазировка 1600×1000',2.8)

            # Staff facilities and stores; pallet rows use native copying.
            layer(2)
            table=rect(2300,1500,1600,800)
            copy(table,2800,0)
            chair=rect(2500,800,500,500)
            for dx,dy in [(900,0),(0,1700),(900,1700),(2800,0),(3700,0),(2800,1700),(3700,1700)]:copy(chair,dx,dy)
            rect(700,3200,2600,600)
            locker=rect(700,5700,500,600)
            for i in range(1,10):copy(locker,i*600,0)
            rect(2200,7300,3200,500)
            pallet=rect(9000,1300,1200,800)
            for i in range(5):
                for j in range(3):
                    if i or j:copy(pallet,i*1800,j*2400)
            pallet2=rect(21000,1300,1200,800)
            for i in range(5):
                for j in range(3):
                    if i or j:copy(pallet2,i*2000,j*2400)
            rack=rect(34000,1500,1000,2000)
            copy(rack,3000,0);copy(rack,0,4200);copy(rack,3000,4200)
            layer(5)
            txt(1200,3900,'03  КУХНЯ / КОМНАТА ОТДЫХА',4)
            txt(1200,8500,'04  РАЗДЕВАЛКА',4.5);txt(1400,6800,'10 шкафчиков · скамья',3)
            txt(8600,8500,'05  СКЛАД СЫРЬЯ',4.5)
            txt(20000,8500,'06  СКЛАД ГОТОВОЙ ПРОДУКЦИИ',4)
            txt(32700,8500,'07  УПАКОВКА',4);txt(32700,7900,'и расходные материалы',3)

            # 4 m vehicle lane + separate 1.5 m pedestrian strip, crossings at gates.
            layer(3)
            line(300,13500,39700,13500,4)
            for x in (4200,12000,25400,34600):
                for offset in range(0,2400,400):rect(x-1200+offset,9500,180,4000,2)
            def arrow(x,y,length=1800):
                line(x,y,x+length,y,2);line(x+length,y,x+length-400,y+220,2);line(x+length,y,x+length-400,y-220,2)
            for x in (6000,17000,28500):arrow(x,11100)
            for x in (7500,21000,34500):arrow(x,14300,1200)
            layer(5)
            txt(7600,12300,'08  ПРОЕЗД ЭЛЕКТРОКАРОВ — 4 000 мм',4)
            txt(15400,13800,'Пешеходный путь — 1 500 мм',3)
            txt(600,11200,'Въезд',3);txt(37800,11200,'Выезд',3)
            # Vehicle symbol shows copy/move/rotate and deletion of a temporary construction object.
            layer(2)
            car=rect(36500,10100,1800,1000)
            rect(38200,10300,600,120,2);rect(38200,10700,600,120,2)
            layer(5);txt(36700,10400,'ЭК',2.5)
            temp=line(35000,10000,35100,10000,2)
            call('move_object',reference=temp['reference'],dx=0,dy=100)
            call('rotate_object',reference=temp['reference'],x=35000,y=10100,angle=90)
            call('delete_object',reference=temp['reference'])

            layer(4)
            call('linear_dimension',x1=0,y1=0,x2=40000,y2=0,x3=0,y3=-1900)
            call('linear_dimension',x1=0,y1=0,x2=0,y2=24000,x3=-1900,y3=0,orientation='vertical')
            call('linear_dimension',x1=39700,y1=9500,x2=39700,y2=13500,x3=42000,y3=9500,orientation='vertical')
            call('linear_dimension',x1=39700,y1=13500,x2=39700,y2=15000,x3=43600,y3=13500,orientation='vertical')
            for x1,x2 in [(0,8000),(8000,19000),(19000,32000),(32000,40000)]:
                call('linear_dimension',x1=x1,y1=0,x2=x2,y2=0,x3=x1,y3=-950)

            # Sheet-level headings, legend and equipment schedule.
            call('set_active_view',view_number=0)
            txt(100,770,'ПЛАН ШОКОЛАДНОГО ЦЕХА',12)
            txt(100,748,'40×24 м  ·  А0  ·  Масштаб 1:50',6)
            txt(100,729,'Учебный пример работы с КОМПАС-3D API и локальным MCP',4.5)
            txt(940,680,'ЭКСПЛИКАЦИЯ',5)
            rows=['01  Подготовка шоколада','02  Изготовление и упаковка','03  Кухня / комната отдыха','04  Раздевалка','05  Склад сырья','06  Склад готовой продукции','07  Упаковочные материалы','08  Транспортный коридор']
            for i,value in enumerate(rows):txt(940,660-i*13,value,3.5)
            txt(940,530,'УСЛОВНЫЕ ОБОЗНАЧЕНИЯ',4)
            line(940,516,965,516,1);txt(970,514,'Стена / перегородка',3)
            line(940,503,965,503,4);txt(970,501,'Граница прохода',3)
            rect(940,478,24,12,2);txt(970,481,'Оборудование',3)
            txt(940,449,'Проезд: 4,0 м',3.5);txt(940,434,'Пешеходная полоса: 1,5 м',3.5)
            txt(940,405,'Размеры указаны в мм.',3)
            txt(940,391,'Планировка демонстрационная.',3)
            txt(940,377,'Габариты ЭК уточняются',3)
            txt(940,365,'для проверки маневрирования.',3)

            txt(100,153,'ОБОРУДОВАНИЕ УЧАСТКА 02',5)
            schedule=[('Е1','Буферная ёмкость','Ø1270'),('Т1','Темпер','960×800'),('Г1','Глазировка','1600×1000'),('Х1','Охлаждающий тоннель','12500×780; H=1530'),('У1','Флоупак','4800×1600')]
            rect(100,60,650,80,2)
            line(150,60,150,140,2);line(480,60,480,140,2)
            for y in (124,108,92,76):line(100,y,750,y,2)
            for i,(code,name,size) in enumerate(schedule):
                y=128-i*16;txt(110,y,code,3.5);txt(163,y,name,3.5);txt(494,y,size,3.5)
            txt(100,38,'Два производственных помещения разделены перегородкой и обслуживаются общим транспортным коридором.',3.5)
            txt(100,25,'Схема используется для испытания API; санитарные и строительные расчёты в этот пример не входят.',3)
            # A readable custom title above the default KOMPAS stamp.
            txt(990,86,'Шоколадный цех — план',4)
            txt(990,73,'Учебный пример API',3)

            state=call('document_state')
            assert state['sheet']['format']=='A0' and state['sheet']['width']==1189
            assert any(v['number']==view['number'] and v['scale']==.02 for v in state['views'])
            objects=call('list_objects')
            assert sum(o['type']=='linear_dimension' for o in objects['items'])==8
            assert sorted(o['nominal_value'] for o in objects['items'] if o['type']=='linear_dimension')==[1500,4000,8000,8000,11000,13000,24000,40000]
            assert all(o['layer_number']!=0 for o in objects['items'] if o['view']==view['number'])
            call('save_document',path=str(out/'Цех-40x24-А0.cdw'))
            call('export_png',path=str(out/'Цех-40x24-А0.png'),dpi=100)
            call('close_document')
            d=c.call('open_document',path=str(out/'Цех-40x24-А0.cdw'))['document_id']
            checked=c.call('document_state',document_id=d)
            assert checked['sheet']['width']==1189 and checked['sheet']['height']==841
            assert any(v['scale']==.02 for v in checked['views'])
            reloaded=c.call('list_objects',document_id=d)
            assert len(reloaded['items'])==len(objects['items'])
            assert any(o.get('value')=='04  РАЗДЕВАЛКА' for o in reloaded['items'])
            c.call('set_active_view',document_id=d,view_number=view['number'])
            (out/'factory-verification.json').write_text(json.dumps({'state':checked,'objects':len(reloaded['items']),'tools_used':sorted({r['tool'] for r in c.records}),'mcp_calls':len(c.records)},ensure_ascii=False,indent=2),encoding='utf-8')
            print('FACTORY PASS',len(reloaded['items']),'objects',len(c.records),'MCP calls',flush=True)
            completed=True
        finally:
            if d and not completed:
                try:c.call('close_document',document_id=d)
                except RuntimeError:pass
            (out/'factory-calls.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':build()
