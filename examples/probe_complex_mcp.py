import sys,os,json,math
from pathlib import Path
from client import Client
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--executable');args=p.parse_args();root=Path(args.output).resolve()
root.mkdir(parents=True,exist_ok=True);owned=[];results={}
with Client(timeout=75) as client:
    def call(tool,**kw):return client.call(tool,**kw)
    call('connect',launch=True,executable=args.executable or os.environ.get('KOMPAS_EXECUTABLE'));schema=client.request('tools/list',{})['tools'];assert {'loft','sweep','shell','fillet','list_model_topology','export_model_png'}.issubset({t['name'] for t in schema})
    def new(name):
        d=call('create_part',name=name)['document_id'];owned.append(d);return d
    def circle(d,plane,z,r,x=0,y=0):
        s=call('create_sketch',document_id=d,plane=plane,offset=z)['sketch_reference']
        call('sketch_circle',document_id=d,sketch_reference=s,x=x,y=y,radius=r);return s
    def box(d):
        s=call('create_sketch',document_id=d,plane='XY')['sketch_reference']
        call('sketch_polygon',document_id=d,sketch_reference=s,points=[[0,0],[30,0],[30,20],[0,20]])
        call('extrude',document_id=d,sketch_reference=s,depth=40)
    def save(d,name):
        state=call('rebuild_model',document_id=d)
        assert state['body_count']==1 and state['volume_mm3']>0
        assert all(f['valid'] and not f['error'] for f in state['features'])
        call('set_model_color',document_id=d,color=0x4EC485)
        call('set_model_display',document_id=d)
        path=str(root/(name+'.m3d'));call('save_model',document_id=d,path=path)
        call('close_model',document_id=d);owned.remove(d)
        d=call('open_model',path=path)['document_id'];owned.append(d)
        after=call('model_state',document_id=d)
        assert abs(state['volume_mm3']-after['volume_mm3'])<.01
        assert all(f['valid'] and not f['error'] for f in after['features'])
        call('export_model_png',document_id=d,path=str(root/(name+'.png')))
        results[name]={'volume_mm3':state['volume_mm3'],'bounds_mm':state['bounds_mm'],'reopened':True}
        print(name,results[name],flush=True)
        call('close_model',document_id=d);owned.remove(d)
    try:
        d=new('MCP hollow loft')
        sections=[circle(d,'XY',z,r,x) for z,r,x in [(0,20,0),(30,14,8),(60,10,-4)]]
        call('loft',document_id=d,sketch_references=sections)
        inner=[circle(d,'XY',z,r,x) for z,r,x in [(0,17,0),(30,11,8),(60,7,-4)]]
        call('loft',document_id=d,sketch_references=inner,operation='cut')
        save(d,'hollow-loft')
        d=new('MCP annular swept tube')
        profile=circle(d,'XZ',0,4);call('sketch_circle',document_id=d,sketch_reference=profile,x=0,y=0,radius=2)
        path=call('create_sketch',document_id=d,plane='XY')['sketch_reference']
        call('sketch_arc',document_id=d,sketch_reference=path,x=25,y=0,radius=25,start_angle=180,end_angle=90,clockwise=True)
        call('sweep',document_id=d,profile_reference=profile,path_references=[path])
        assert abs(call('model_state',document_id=d)['volume_mm3']-math.pi*12*math.pi*25/2)<.01
        save(d,'annular-sweep')
        d=new('MCP fillet rollback');box(d)
        edges=call('list_model_topology',document_id=d,kind='edge')['items'];assert len(edges)==12
        before=call('model_state',document_id=d)['volume_mm3']
        try:call('fillet',document_id=d,edge_references=[e['reference'] for e in edges],radius=1000)
        except RuntimeError:pass
        else:raise AssertionError('Invalid fillet accepted')
        assert abs(call('rebuild_model',document_id=d)['volume_mm3']-before)<.01
        edges=call('list_model_topology',document_id=d,kind='edge')['items']
        call('fillet',document_id=d,edge_references=[e['reference'] for e in edges],radius=2)
        save(d,'fillet')
        for inward in (False,True):
            d=new('MCP shell');box(d)
            faces=call('list_model_topology',document_id=d,kind='face')['items']
            top=[f for f in faces if f['planar'] and f['bounds_mm'] and abs(f['bounds_mm']['min'][2]-40)<1e-6]
            assert len(top)==1,faces
            call('shell',document_id=d,face_references=[top[0]['reference']],thickness=2,inward=inward)
            save(d,'shell-inward' if inward else 'shell-outward')
    finally:
        (root/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        (root/'stdio-trace.json').write_text(json.dumps(client.records,ensure_ascii=False,indent=2),encoding='utf-8')
        for d in reversed(owned):
            try:call('close_model',document_id=d)
            except Exception:pass

