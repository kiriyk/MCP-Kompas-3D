"""Isolated SDK v21 forming probes. Never closes documents it did not create."""
import argparse, json, math, uuid
from pathlib import Path
from kompas_local_mcp.adapter import Adapter

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True)
parser.add_argument('--executable',required=True)
args=parser.parse_args()
root=Path(args.output)
if not root.is_absolute():raise ValueError('Use an absolute output folder')
root=root/('run-'+uuid.uuid4().hex[:10])
root.mkdir(parents=True,exist_ok=True)
a=Adapter();owned=[];results={}
def part(name):
    d=a.create_part(name)['document_id'];owned.append(d);return d
def circle(d,plane,offset,x,y,r):
    s=a.create_sketch(d,plane,offset=offset)['sketch_reference']
    a.sketch_circle(d,s,x,y,r);return a._model_ref(d,s,'sketch')
def validate(d,e,name,expected=None):
    a._model5(d).RebuildDocument()
    f=a.api5.ksFeature(e.GetFeature())
    state=a.model_state(d)
    assert f.IsValid() and not f.objectError, (name,f.objectError)
    assert state['body_count']==1 and state['volume_mm3']>0,state
    known={
        'loft':(40543.7561730608,[-20,-20,0,22.93032081001903,20,60]),
        'sweep':(math.pi*16*math.pi*25/2,[-4,0,-4,25,29,4]),
        'fillet':(23701.687229558316,[0,0,0,30,20,40]),
        'shell':(10272,[-2,-2,-2,32,22,40]),
    }
    volume,bounds=known[name]
    assert abs(state['volume_mm3']-volume)<.01
    assert all(abs(x-y)<1e-5 for x,y in zip(state['bounds_mm']['min']+state['bounds_mm']['max'],bounds))
    if expected:assert abs(state['volume_mm3']-expected)<.1,(state['volume_mm3'],expected)
    a.save_model(d,str(root/(name+'.m3d')))
    results[name]={'type':e.type,'valid':True,'error':f.objectError,'volume_mm3':state['volume_mm3'],'bounds_mm':state['bounds_mm']}
    try:
        a.export_model(d,str(root/(name+'.stl')));results[name]['stl']='passed'
    except RuntimeError as ex:results[name]['stl']=str(ex)
    reopened=a.open_model(str(root/(name+'.m3d')))['document_id']
    assert reopened==d  # Native path registered; separate reopen test below after close.
    print(name,json.dumps(results[name]),flush=True)
try:
    print(a.connect(executable=args.executable),flush=True)
    print('Output:',root,flush=True)
    d=part('SDK loft proof')
    sketches=[circle(d,'XY',z,x,0,r) for z,x,r in [(0,0,20),(30,8,14),(60,-4,10)]]
    e=a.api5.ksEntity(a._part5(d).NewEntity(30));e.name='Curved varying sections'
    definition=a.api5.ksBaseLoftDefinition(e.GetDefinition())
    assert definition.SetLoftParam(False,False,True)
    arr=a.api5.ksEntityCollection(definition.Sketchs())
    for s in sketches:assert arr.Add(s)
    assert e.Create(),'Loft Create failed'
    validate(d,e,'loft')
    d=part('SDK sweep proof')
    profile=circle(d,'XZ',0,0,0,4)
    pathref=a.create_sketch(d,'XY')['sketch_reference'];path=a._model_ref(d,pathref,'sketch')
    definition=a.api5.ksSketchDefinition(path.GetDefinition());cad=None
    try:
        cad=a.api5.ksDocument2D(definition.BeginEdit())
        # Arc from origin, tangent +Y, centre at (25,0): 180 to 90 clockwise.
        assert cad.ksArcByAngle(25,0,25,180,90,-1,1)
    finally:assert definition.EndEdit()
    e=a.api5.ksEntity(a._part5(d).NewEntity(45));e.name='Quarter bend R25'
    definition=a.api5.ksBaseEvolutionDefinition(e.GetDefinition());definition.sketchShiftType=1
    assert definition.SetSketch(profile)
    arr=a.api5.ksEntityCollection(definition.PathPartArray());assert arr.Add(path)
    assert e.Create(),'Sweep Create failed'
    validate(d,e,'sweep',math.pi*16*math.pi*25/2)
    d=part('SDK fillet proof')
    s=a.create_sketch(d,'XY')['sketch_reference'];a.sketch_polygon(d,s,[[0,0],[30,0],[30,20],[0,20]])
    a.extrude(d,s,40)
    edges=a.api5.ksEntityCollection(a._part5(d).EntityCollection(7))
    e=a.api5.ksEntity(a._part5(d).NewEntity(34));e.name='All edges R2'
    definition=a.api5.ksFilletDefinition(e.GetDefinition());definition.radius=2;definition.tangent=False
    arr=a.api5.ksEntityCollection(definition.array())
    for i in range(edges.GetCount()):assert arr.Add(edges.GetByIndex(i))
    assert e.Create(),'Fillet Create failed'
    validate(d,e,'fillet')
    d=part('SDK shell proof')
    s=a.create_sketch(d,'XY')['sketch_reference'];a.sketch_polygon(d,s,[[0,0],[30,0],[30,20],[0,20]])
    a.extrude(d,s,40)
    e=a.api5.ksEntity(a._part5(d).NewEntity(43));e.name='Open outward shell thickness 2'
    definition=a.api5.ksShellDefinition(e.GetDefinition());definition.thickness=2;definition.thinType=False
    faces=a.api5.ksEntityCollection(a._part5(d).EntityCollection(6))
    assert faces.GetCount()==6
    arr=a.api5.ksEntityCollection(definition.FaceArray());assert arr.Add(faces.GetByIndex(0))
    assert e.Create(),'Shell Create failed'
    validate(d,e,'shell')
    # Verify saved files after fully closing and reopening, without session tokens.
    for d in list(owned):a.close_model(d);owned.remove(d)
    for name,result in results.items():
        d=a.open_model(str(root/(name+'.m3d')))['document_id'];owned.append(d)
        state=a.model_state(d)
        assert abs(state['volume_mm3']-result['volume_mm3'])<.01
        assert state['body_count']==1
        assert all(abs(x-y)<1e-5 for x,y in zip(state['bounds_mm']['min']+state['bounds_mm']['max'],result['bounds_mm']['min']+result['bounds_mm']['max']))
        found=[]
        for typ in (30,31,34,43,45,46):
            coll=a.api5.ksEntityCollection(a._part5(d).EntityCollection(typ))
            for i in range(coll.GetCount()):
                f=a.api5.ksFeature(a.api5.ksEntity(coll.GetByIndex(i)).GetFeature())
                assert f.IsValid() and not f.objectError
                found.append(typ)
        assert found,'Saved advanced operation missing'
        result['reopened_feature_types']=found
        result['reopened']=True
finally:
    (root/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    for d in reversed(owned):
        try:a.close_model(d)
        except Exception as ex:print('Owned document close failed',ex,flush=True)
    a.shutdown()
