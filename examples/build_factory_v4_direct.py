"""Factory revision through direct API only, before MCP integration."""
import json
import math
from pathlib import Path
from kompas_local_mcp.adapter import Adapter
from direct_features import DirectFeatures

class FactoryAPI(Adapter):pass

def build():
    out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
    target=out/'Цех-40x24-А0-v4.cdw'
    a=FactoryAPI();d=None;completed=False;calls=[];dimensions=[]
    try:
        a.connect()
        if target.exists():a.close_document(a.open_document(str(target))['document_id'])
        d=a.create_drawing()['document_id'];a.set_sheet(d,'A0',True)
        view=a.create_view(d,'План цеха 1:50',.02,100,200)
        def call(tool_name,**args):
            result=getattr(a,tool_name)(document_id=d,**args)
            calls.append({'api_function':tool_name,'arguments':args,'result':result})
            return result
        def layer(n):call('set_active_layer',number=n)
        def line(x1,y1,x2,y2,style=1):return call('line',x1=x1,y1=y1,x2=x2,y2=y2,style=style)
        def rect(x,y,w,h,style=1):return call('rectangle',x=x,y=y,width=w,height=h,style=style)
        def txt(x,y,value,h=3.5):return call('text',x=x,y=y,value=value,height=h)
        def circ(x,y,r):return call('circle',x=x,y=y,radius=r,style=2)
        def poly(points,style=1):return call('polyline',points=points,style=style)
        def arr(obj,n,dx,dy):return call('linear_array',reference=obj['reference'],count=n,dx=dx,dy=dy)
        def dim(x1,y1,x2,y2,x3,y3,vertical=False):
            call('linear_dimension',x1=x1,y1=y1,x2=x2,y2=y2,x3=x3,y3=y3,orientation='vertical' if vertical else 'horizontal')
            dimensions.append(abs(y2-y1) if vertical else abs(x2-x1))
        for n,name,color in [(1,'Стены и проёмы',0),(2,'Оборудование и сантехника',0),(3,'Проезды электрокаров',0xB06020),(4,'Нативные размеры',0),(5,'Подписи',0),(6,'Штриховка стен',0),(7,'Поток продукции',0x009000)]:
            call('create_layer',name=name,number=n,color=color)
        walls=[(0,0,40000,300),(0,23700,40000,300),
               (0,300,300,1200),(0,2700,300,6800),(0,9500,300,14200),
               (39700,300,300,23400),
               (300,9300,2200,200),(3700,9300,6700,200),(14400,9300,9400,200),(27800,9300,5500,200),(37300,9300,2400,200),
               (300,11000,10100,200),(14400,11000,9400,200),(27800,11000,5500,200),(37300,11000,2400,200),
               (7800,300,200,9000),(19000,300,200,9000),(32000,300,200,9000),
               (19000,11200,200,500),(19000,12900,200,8000),(19000,22400,200,1300),
               (300,4300,2700,200),(4200,4300,3600,200)]
        # Staff sanitary wing: two WC cubicles, two showers, vestibule.
        walls += [(5400,4500,100,3000),(5400,7500,700,100),(7000,7500,800,100),
                  (6550,4500,100,1500),(5400,6000,300,100),(6300,6000,1500,100)]
        # Production WC with a separate vestibule and self-closing doors.
        walls += [(300,11200,100,3000),(400,14200,800,100),(2200,14200,1800,100),
                  (3900,11200,100,3000),(400,12900,800,100),(2200,12900,1700,100),
                  (2150,11200,100,1700)]
        for w in walls:
            layer(1);rect(*w)
            layer(6);call('hatch_rectangle',x=w[0],y=w[1],width=w[2],height=w[3],step=3.5)

        def door(x,y,width=900,side=1,vertical=False):
            layer(1)
            line(x,y,x+width if vertical else x,y if vertical else y+width,2)
            call('arc',x=x,y=y,radius=width,start_angle=0 if side==1 else 90,end_angle=90 if side==1 else 180,style=2)
        door(2500,9300,1200);door(3000,4300,1200);door(0,1500,1200,vertical=True)
        door(6100,7500);door(5700,6000,600);door(6700,6000,600)
        door(1200,14200,1000);door(1200,12900,1000)
        for x1,x2,y in [(10400,14400,11000),(23800,27800,11000),(33300,37300,11000),(10400,14400,9500),(23800,27800,9500),(33300,37300,9500)]:
            layer(1);line(x1,y,x2,y,4);line(x1,y+150,x1+1800,y+150,2);line(x2-1800,y+150,x2,y+150,2)
        # Pipe penetrates production partition; door for personnel is separate.
        door(19000,11700,1200,vertical=True)
        layer(1);line(19000,20900,19000,22400,4)

        def toilet(x,y):
            layer(2);rect(x,y+450,480,160,2)
            # Rounded bowl is a native contour, not a rectangle.
            call('mixed_contour',segments=[{'type':'line','x1':x+40,'y1':y+450,'x2':x+40,'y2':y+230},
                {'type':'arc','x':x+240,'y':y+230,'radius':200,'start_angle':180,'end_angle':360},
                {'type':'line','x1':x+440,'y1':y+230,'x2':x+440,'y2':y+450},
                {'type':'line','x1':x+440,'y1':y+450,'x2':x+40,'y2':y+450}],style=2)
            call('arc',x=x+240,y=y+250,radius=125,start_angle=180,end_angle=360,style=2)
        def sink(x,y,w=600):
            layer(2);rect(x,y,w,450,2)
            call('mixed_contour',segments=[{'type':'line','x1':x+70,'y1':y+350,'x2':x+70,'y2':y+190},
                {'type':'arc','x':x+w/2,'y':y+190,'radius':w/2-70,'start_angle':180,'end_angle':360},
                {'type':'line','x1':x+w-70,'y1':y+190,'x2':x+w-70,'y2':y+350},
                {'type':'line','x1':x+w-70,'y1':y+350,'x2':x+70,'y2':y+350}],style=2)
            circ(x+w/2,y+240,30);line(x+w/2,y+450,x+w/2,y+340,2)
        def shower(x,y):
            layer(2);rect(x,y,900,900,2)
            line(x,y,x+900,y+900,2);line(x+900,y,x,y+900,2);circ(x+450,y+450,45)
            call('arc',x=x+450,y=y+830,radius=140,start_angle=180,end_angle=360,style=2)
        toilet(5650,5150);toilet(6900,5150)
        shower(5600,6500);shower(6750,6500)
        sink(7000,7950);sink(2700,13350)
        toilet(800,11800);toilet(2850,11800)
        # Kitchen double sink, cooktop and tables.
        layer(2);rect(600,3200,3500,600,2);sink(900,3250);sink(1550,3250)
        rect(2600,3250,1000,450,2)
        hotplate=circ(2820,3370,90)
        call('circular_array',reference=hotplate['reference'],count=4,x=3100,y=3475)
        table=rect(1800,1300,1800,900,2);call('copy_object',reference=table['reference'],dx=3000,dy=0)
        chair=rect(1900,650,500,500,2);arr(chair,3,650,0)
        chair2=call('mirror_object',reference=chair['reference'],x1=0,y1=1750,x2=7000,y2=1750)
        arr(chair2,3,650,0);call('copy_object',reference=chair['reference'],dx=3000,dy=0)
        layer(2);locker=rect(600,5100,450,550,2);arr(locker,7,600,0)
        rect(1400,7100,3000,500,2)

        # Purchased cocoa mass/butter + sugar: dosing, mixing, refining, conching.
        layer(2)
        rect(1000,20800,1600,1400,2);circ(1600,21500,350) # dosing hopper
        rect(3100,20800,2400,1700,2);circ(4300,21650,650) # premixer
        rect(6100,20700,2400,1800,2);circ(7300,21600,550) # ball mill
        rect(9100,20700,3300,1900,2) # conche
        for x in (10000,11400):circ(x,21650,600)
        circ(14400,21600,750);circ(17200,21600,750) # heated storage
        rect(4700,17200,3600,900,2);rect(4800,19100,2200,1000,2)
        equipment=[(900,22600,'Д1 Дозатор / весы'),(3100,22900,'С1 Смеситель'),(6100,23000,'М1 Шаровая мельница'),
                   (9100,23100,'К1 Конш-машина'),(13600,22800,'Б1 Буфер'),(16500,22800,'Б2 Буфер'),
                   (4900,17450,'Стол дозирования'),(4800,19500,'Фильтр / насос')]
        layer(5)
        for x,y,label in equipment:txt(x,y,label,3)
        txt(8000,23350,'01  ПРИГОТОВЛЕНИЕ ШОКОЛАДНОЙ МАССЫ',4.5)
        txt(4500,18450,'Исходное сырьё: какао-масса, масло, сахар',3)
        txt(11100,16900,'Подача сырья / ЭК',3)

        layer(2)
        circ(20735,22265,635)
        rect(21670,22100,960,800,2);rect(22930,21900,1600,1000,2)
        rect(24830,22120,12500,780,2)
        rect(26800,19000,4800,1600,2)
        rect(21100,18000,2800,1300,2);rect(24000,16400,3200,800,2)
        rect(28000,16400,2000,1000,2)
        layer(5)
        txt(22800,23350,'02  ФОРМОВАНИЕ / ГЛАЗИРОВАНИЕ И УПАКОВКА',4.5)
        txt(20400,22170,'Е1',2.5);txt(21720,22400,'Т1',2.2);txt(23000,22300,'Г1',2.5)
        txt(26700,22370,'Х1 Тоннель 12500 х 780',3)
        txt(27100,19600,'У1 Флоупак 4800 х 1600',3)
        txt(21300,18500,'Ф1 Формование',3);txt(24100,16650,'Контроль / металлоискатель',2.7)
        txt(28100,16700,'Укладка в короб',2.5)
        txt(23900,13100,'Выдача ГП / ЭК',3)
        txt(500,13750,'С/У ЦЕХА',2.8);txt(2450,13750,'Шлюз',2.8)

        # Stores: clear four-metre longitudinal aisles actually reach room gates.
        layer(2)
        def pallet(x,y,w=1200,h=800):
            # Plan symbol: perimeter, five deck boards and nine support blocks.
            rect(x,y,w,h,2)
            for j in range(5):rect(x,y+j*h/5,w,h*.15,2)
            for u in (0,w/2-75,w-150):
                for v in (0,h/2-75,h-150):rect(x+u,y+v,150,150,4)
        def rack_row(x,y,width):
            # Three longitudinal rows with open loading aisles between them.
            rect(x,y,width,900,2)
            n=int(width//1200);bay=width/n
            for j in range(n):pallet(x+j*bay+(bay-1200)/2,y+50)
            for j in range(n+1):
                px=x+j*bay-(80 if j==n else 0)
                rect(px,y,80,80,1);rect(px,y+820,80,80,1)
            line(x,y+40,x+width,y+40,2);line(x,y+860,x+width,y+860,2)
        for y in (300,4350,8400):
            for x,w in ((8000,2400),(14400,4600),(19200,4600),(27800,4200),(37300,2400)):
                rack_row(x,y,w)
        # Narrow side of packaging store: six individually accessible bays.
        rect(32250,350,900,8700,2)
        for j in range(6):
            yy=450+j*1400
            pallet(32300,yy,800,1200)
            for xx in (32250,33070):rect(xx,yy-50,80,80,1)
        line(32290,350,32290,9050,2);line(33110,350,33110,9050,2)
        layer(5)
        for x,y,label in [(800,3900,'03 КУХНЯ'),(800,8700,'04 РАЗДЕВАЛКА'),(5450,8400,'WC / ДУШ'),
                          (8300,7800,'05 СКЛАД СЫРЬЯ'),(19800,7800,'06 СКЛАД ГОТОВОЙ ПРОДУКЦИИ'),
                          (33400,8050,'07 УПАКОВОЧНЫЕ МАТЕРИАЛЫ')]:txt(x,y,label,4 if len(label)<30 else 3.4)

        txt(8100,2700,'Загрузка рядов: 3150 мм',2.5)
        txt(19400,2700,'Загрузка рядов: 3150 мм',2.5)
        txt(14450,8050,'Стеллажи: 2 уровня',2.5)
        txt(28000,8050,'Стеллажи: 2 уровня',2.5)
        def arrow_path(points,n=1,style=2):
            poly(points,style)
            for p,q in zip(points,points[1:]):
                if math.dist(p,q)<1500:continue
                x=(p[0]+q[0])/2;y=(p[1]+q[1])/2;ang=math.atan2(q[1]-p[1],q[0]-p[0])
                poly([[x-380*math.cos(ang)+220*math.sin(ang),y-380*math.sin(ang)-220*math.cos(ang)],
                      [x,y],[x-380*math.cos(ang)-220*math.sin(ang),y-380*math.sin(ang)+220*math.cos(ang)]],style)
        layer(3)
        line(300,10250,39700,10250,4)
        for x in (10400,23800,33300):
            stripe=rect(x,9500,180,1500,2);arr(stripe,10,400,0)
        for x in (10400,23800,33300):
            # Dashed aisle boundaries and entry to storage zones.
            line(x,3500,x,9300,4);line(x+4000,3500,x+4000,9300,4)
        line(10400,11200,10400,19300,4);line(14400,11200,14400,19300,4)
        line(23800,11200,23800,15100,4);line(27800,11200,27800,15100,4)
        line(33300,11200,33300,15200,4);line(37300,11200,37300,15200,4)
        arrow_path([[12400,4200],[12400,17400]])
        arrow_path([[25800,14700],[25800,4300]])
        arrow_path([[35300,4300],[35300,15200]])
        layer(5);txt(10400,15300,'ЭК: подача сырья',3)
        txt(23900,14000,'ЭК: выдача → склад ГП',3)
        txt(15400,10500,'Проход персонала 1500; поперечные пересечения у ворот',3)
        txt(32800,5800,'Подача тары',3)

        # Green product route; chocolate mass transfer and conveyor handling are distinct from cars.
        layer(7)
        arrow_path([[12400,7200],[12400,10250],[12400,19400],[1800,19400],[1800,21500]])
        arrow_path([[1800,20400],[4300,20400],[7300,20400],[10750,20400],[14400,20400],[17200,20400],[17200,21800],[19900,21800],[20735,21800]])
        arrow_path([[20735,21600],[22000,21600],[23500,21600],[28000,21600],[37330,21600],[38400,21600],[38400,20900],[31600,20900],[31600,19800],[26800,19800],[26800,18000],[25200,18000],[25200,16800],[29200,16800],[29200,14700],[25800,14700],[25800,7000]])
        # Formed products alternative joins the common cooling line.
        arrow_path([[22150,21800],[20200,21800],[20200,18650],[22500,18650],[24800,18650],[24800,21600],[25700,21600]])
        layer(5);txt(8300,19800,'Зелёный: технологический поток',3)
        txt(28000,21300,'Направление охлаждения →',3)

        # Native room dimensions: clear inside faces, including sanitary partitions.
        layer(4)
        dim(0,0,40000,0,0,-1900);dim(0,0,0,24000,-1900,0,True)
        for x1,x2 in [(0,8000),(8000,19000),(19000,32000),(32000,40000)]:dim(x1,0,x2,0,x1,-950)
        # Horizontal room widths in clear unobstructed bands.
        rooms=[('01',4000,19000,11200,23700),('02',19200,39700,11200,23700),
               ('03',300,7800,300,4300),('04',300,5400,4500,9300),
               ('05',8000,19000,300,9300),('06',19200,32000,300,9300),('07',32200,39700,300,9300)]
        for name,x1,x2,y1,y2 in rooms:
            dim(x1,y1,x2,y1,x1,2700 if name in ('05','06','07') else y1+700)
            dim(x1,y1,x1,y2,{'05':13700,'06':27100,'07':36400}.get(name,x1+700),y1,True)
        # Production 01 overall clear width extends above the sanitary wing.
        dim(300,23700,19000,23700,300,24450)
        dim(5400,4500,7800,4500,5400,4800);dim(7800,4500,7800,7500,7550,4500,True)
        dim(400,11200,3900,11200,400,11500);dim(3900,11200,3900,14200,3650,11200,True)
        dim(39700,9500,39700,11000,40700,9500,True)

        call('set_active_view',view_number=0)
        txt(100,770,'ПЛАН ШОКОЛАДНОГО ЦЕХА',12)
        txt(100,748,'40 х 24 м  ·  А0  ·  Масштаб 1:50',6)
        txt(100,729,'Прямые вызовы API v21: оборудование, санитарные приборы, маршруты и нативные размеры',4)
        txt(935,680,'ЭКСПЛИКАЦИЯ',5)
        labels=['01 Приготовление шоколадной массы','02 Формование / глазирование, упаковка','03 Кухня / отдых','04 Раздевалка; WC и душевые',
                '05 Склад сырья','06 Склад готовой продукции','07 Склад упаковочных материалов','08 Проход персонала 1.5 м; пересечения ЭК',
                '09 WC цеха; вход через шлюз']
        for i,label in enumerate(labels):txt(935,660-i*13,label,3.2)
        txt(935,520,'МАРШРУТЫ',4.5)
        # Colored legend belongs to its own layer in system view too.
        call('create_layer',name='Поток продукции / легенда',number=7,color=0x009000)
        line(935,501,970,501,1);layer(0);txt(975,499,'Продукция / шоколадная масса',3)
        call('create_layer',name='ЭК / легенда',number=3,color=0xB06020)
        line(935,485,970,485,2);layer(0);txt(975,483,'Маршрут электрокара',3)
        txt(935,462,'Склады соединены с цехами',3);txt(935,449,'через встречные ворота 4 м.',3)
        txt(935,429,'Зелёные линии между машинами:',3);txt(935,416,'трубопровод / конвейер / перегрузка.',3)
        txt(935,392,'Сырьё: готовые какао-продукты.',3)
        txt(935,379,'Измельчение и конширование — цех 01.',3)
        txt(935,360,'Размеры указаны в мм.',3)
        txt(935,347,'WC, душ, мойка — контуры с дугами,',3)
        txt(935,334,'сливами и обозначением прибора.',3)
        txt(100,154,'ОБОРУДОВАНИЕ: ПОСЛЕДОВАТЕЛЬНОСТЬ ПРОЦЕССА',4.5)
        txt(100,137,'Д1 Дозирование → С1 Смешивание → М1 Измельчение → К1 Конширование → Б1/Б2 Буфер',4)
        txt(100,120,'Е1 Ёмкость Ø1270 → Т1 Темпер 960 х 800 → Г1 Глазировка 1600 х 1000 → Х1 Тоннель 12500 х 780',3.7)
        txt(100,104,'Ф1 Формование — альтернативная подача; У1 Флоупак 4800 х 1600 → контроль → короб → склад ГП',3.7)
        txt(100,83,'Охлаждающий тоннель сохранён: 12500 х 780 мм, высота H=1530 мм.',3.2)
        txt(100,63,'Технология: Bühler (DoMiReCo / SmartChoc), SOLLICH (tempering, enrobing, cooling).',3.5)
        txt(100,44,'Габариты дополнительного оборудования — компоновочные допущения, без выбора конкретной модели.',3)
        txt(100,27,'Учебный пример API. Манёвры ЭК и нормативная планировка требуют отдельного проектного расчёта.',3)
        txt(990,86,'Шоколадный цех — план',4);txt(990,73,'Редакция 4 / API v21',3)
        objects=call('list_objects')['items']
        native=[o['nominal_value'] for o in objects if o['type']=='linear_dimension']
        assert all(abs(x-y)<1e-6 for x,y in zip(sorted(native),sorted(dimensions))) and len(native)==len(dimensions),(native,dimensions)
        assert sum(o['type']=='rectangle' and o.get('width')==12500 and o.get('height')==780 for o in objects)==1
        vehicle_aisles=[(10400,3500,14400,9300),(23800,3500,27800,9300),(33300,3500,37300,9300),
                        (10400,11200,14400,19300),(23800,11200,27800,15100),(33300,11200,37300,15200)]
        for x1,x2 in ((8000,10400),(14400,19000),(19200,23800),(27800,32000),(37300,39700)):
            vehicle_aisles.extend([(x1,1200,x2,4350),(x1,5250,x2,8400)])
        for obj in objects:
            if obj['view']!=view['number'] or obj['layer_number']!=2 or obj['type']!='rectangle':continue
            x,y=obj['base'];w=obj['width'];h=obj['height']
            for left,bottom,right,top in vehicle_aisles:
                assert not (x<right and x+w>left and y<top and y+h>bottom),('Equipment intersects aisle',obj)
        call('save_document',path=str(target))
        # Direct method call, without protocol; native export verified above.
        call('export_png',path=str(out/'Цех-40x24-А0-v4.png'),dpi=100,color_mode='layer')
        for paper in ('sheet','A4'):
            for color in (True,False):
                call('export_pdf',path=str(out/f'Цех-40x24-v4-{paper}-{"color" if color else "bw"}.pdf'),paper=paper,color=color)
        call('close_document');d=a.open_document(str(target))['document_id']
        state=a.document_state(d);loaded=a.list_objects(d)['items']
        after=sorted(o['nominal_value'] for o in loaded if o['type']=='linear_dimension')
        assert len(after)==len(dimensions) and all(abs(x-y)<1e-6 for x,y in zip(after,sorted(dimensions)))
        a.set_active_view(d,view['number'])
        summary={'transport':'direct API, no MCP','state':state,'native_dimensions':native,'dimension_count':len(native),
                 'listed_objects':len(loaded),'polyline_count':a._container(d).PolyLines2D.Count,
                 'contour_count':a._container(d).DrawingContours.Count,'vehicle_aisles_clear':True,'storage_cross_aisle_mm':3150,'central_passage_mm':1500,'cooling_tunnel_mm':[12500,780],'direct_calls':len(calls)}
        (out/'factory-v4-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print('FACTORY V4 DIRECT PASS',json.dumps(summary,ensure_ascii=False),flush=True)
        completed=True
    finally:
        if d and not completed:a.close_document(d)
        a.shutdown()
        (out/'factory-v4-api-calls.json').write_text(json.dumps(calls,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':build()
