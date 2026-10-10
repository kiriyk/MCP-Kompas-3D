"""Live contract tests; changes ONLY documents created by this script."""
import json
from pathlib import Path
from client import Client

def run():
    out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
    with Client() as c:
        d=None;opened=None
        try:
            catalog=c.request('tools/list',{})
            assert len(catalog['tools'])>=10
            c.call('connect')
            d=c.call('create_drawing')['document_id']
            fmt=c.call('set_sheet',document_id=d,format='A0',landscape=True)
            assert fmt['width']==1189 and fmt['height']==841
            v=c.call('create_view',document_id=d,name='Probe',scale=.02,x=40,y=50,angle=90)
            assert abs(v['scale']-.02)<1e-9
            mapped=c.call('view_to_sheet',document_id=d,view_number=v['number'],x=10,y=20)
            assert abs(mapped['x']-39.6)<1e-6 and abs(mapped['y']-50.2)<1e-6
            c.call('set_active_view',document_id=d,view_number=0)
            c.call('set_active_view',document_id=d,view_number=v['number'])
            c.call('create_layer',document_id=d,name='Test',number=5,color=255)
            shapes=[
                c.call('line',document_id=d,x1=0,y1=0,x2=1000,y2=0),
                c.call('rectangle',document_id=d,x=0,y=0,width=1000,height=500),
                c.call('circle',document_id=d,x=300,y=200,radius=50),
                c.call('arc',document_id=d,x=100,y=100,radius=100,start_angle=0,end_angle=90),
                c.call('text',document_id=d,x=10,y=600,value='Проверка Ø1270',height=3.5),
                c.call('linear_dimension',document_id=d,x1=0,y1=0,x2=1000,y2=0,x3=0,y3=-200),
                c.call('hatch_rectangle',document_id=d,x=0,y=0,width=100,height=100,step=20),
                c.call('linear_dimension',document_id=d,x1=0,y1=0,x2=0,y2=500,x3=-200,y3=0,orientation='vertical'),
            ]
            ref=shapes[0]['reference']
            cp=c.call('copy_object',document_id=d,reference=ref,dx=0,dy=100)
            c.call('move_object',document_id=d,reference=cp['reference'],dx=50,dy=20)
            c.call('rotate_object',document_id=d,reference=cp['reference'],x=0,y=0,angle=90)
            moved=next(o for o in c.call('list_objects',document_id=d)['items'] if o['api_reference']==cp['api_reference'])
            assert abs(moved['points'][0][0]+120)<1e-6 and abs(moved['points'][0][1]-50)<1e-6
            c.call('delete_object',document_id=d,reference=cp['reference'])
            try:c.call('move_object',document_id=d,reference=moved['reference'],dx=1,dy=1)
            except RuntimeError:pass
            else:raise AssertionError('Deleted alias accepted')
            for name,args in [('rectangle',dict(x=0,y=0,width=-1,height=100)),('move_object',dict(reference='stale',dx=1,dy=1))]:
                try:c.call(name,document_id=d,**args)
                except RuntimeError:pass
                else:raise AssertionError('Invalid argument accepted: '+name)
            obj=c.call('list_objects',document_id=d,coordinate_space='owner')
            assert len(obj['items'])>=7
            assert next(o for o in obj['items'] if o['type']=='text')['value']=='Проверка Ø1270'
            assert all(o['layer_number']==5 for o in obj['items'])
            assert sorted(o['nominal_value'] for o in obj['items'] if o['type']=='linear_dimension')==[500,1000]
            sheet=c.call('list_objects',document_id=d,coordinate_space='sheet')
            circle=next(o for o in sheet['items'] if o['type']=='circle')
            assert abs(circle['center'][0]-36)<1e-6 and abs(circle['center'][1]-56)<1e-6 and circle['radius']==1
            c.call('set_active_layer',document_id=d,number=5)
            c.call('save_document',document_id=d,path=str(out/'probe.cdw').replace('\\','/'))
            c.call('export_png',document_id=d,path=str(out/'probe.png'),dpi=80)
            c.call('close_document',document_id=d)
            d=None
            opened=c.call('open_document',path=str(out/'probe.cdw'))['document_id']
            state=c.call('document_state',document_id=opened)
            assert state['sheet']['format']=='A0' and state['sheet']['landscape']
            assert any(abs(view['scale']-.02)<1e-9 for view in state['views'])
            assert len(c.call('list_objects',document_id=opened)['items'])>=7
            c.call('close_document',document_id=opened)
            opened=None
            print('LIVE PROBE PASS',len(c.records),'calls',flush=True)
        finally:
            for token in (opened,d):
                if token:
                    try:c.call('close_document',document_id=token)
                    except RuntimeError:pass
            (out/'probe-results.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':run()
