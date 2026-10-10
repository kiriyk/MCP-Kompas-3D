"""Integration check after direct API verification and MCP exposure."""
import json
from pathlib import Path
from client import Client

def run():
    out=Path(__file__).resolve().parents[1]/'artifacts';d=None
    with Client() as c:
        try:
            c.call('connect');d=c.call('create_drawing')['document_id']
            def call(tool,**args):return c.call(tool,document_id=d,**args)
            call('create_view',name='Сложные функции',scale=.1,x=100,y=200)
            call('create_layer',name='Зелёный',number=7,color=0x009000)
            p=call('polyline',points=[[0,0],[1000,0],[1000,1000]])
            closed=call('polyline',points=[[6000,0],[7000,0],[6500,1000]],closed=True)
            src=call('line',x1=100,y1=200,x2=400,y2=500)
            mirror=call('mirror_object',reference=src['reference'],x1=0,y1=0,x2=0,y2=1000)
            call('linear_array',reference=p['reference'],count=3,dx=1800,dy=0)
            circle=call('circle',x=3000,y=3000,radius=100)
            call('circular_array',reference=circle['reference'],count=4,x=2000,y=3000)
            call('mixed_contour',segments=[{'type':'line','x1':0,'y1':2000,'x2':1000,'y2':2000},{'type':'arc','x':1000,'y':2500,'radius':500,'start_angle':270,'end_angle':90}])
            call('bezier',nodes=[{'x':0,'y':4000,'angle':40,'right':900},{'x':2000,'y':4300,'angle':-40,'left':900}])
            call('hatch_polygon',points=[[4000,2500],[5000,2500],[4800,3500]])
            owner=call('list_objects')['items']
            assert next(o for o in owner if o['api_reference']==mirror['api_reference'])['points']==[[-100,200],[-400,500]]
            assert sum(o['type']=='polyline' for o in owner)==4
            assert next(o for o in owner if o['api_reference']==closed['api_reference'])['closed']
            assert sum(o['type']=='circle' for o in owner)==4
            assert any(o['type']=='bezier' and o['node_count']==2 for o in owner)
            alias=next(o for o in owner if o['api_reference']==src['api_reference'])['reference']
            call('mirror_object',reference=src['reference'],x1=0,y1=0,x2=1000,y2=0,copy=False)
            try:call('move_object',reference=alias,dx=1,dy=0)
            except RuntimeError:pass
            else:raise AssertionError('Old mirror source alias remains valid')
            sheet=call('list_objects',coordinate_space='sheet')['items']
            assert next(o for o in sheet if o['api_reference']==p['api_reference'])['points']==[[100,200],[200,200],[200,300]]
            call('export_png',path=str(out/'features-mcp.png'),color_mode='layer',dpi=60)
            print('FEATURES MCP PASS',len(c.records),'calls',flush=True)
        finally:
            if d:c.call('close_document',document_id=d)
            (out/'features-mcp-results.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':run()
