"""Pure validation and coordinate helpers, independent of COM."""
import math
import ntpath
import uuid
import os
from pathlib import Path

def verified_output(path,writer,signature=None):
    """Publish only a newly produced file; an old target never proves success."""
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    stage=target.with_name(f'{target.stem}.{uuid.uuid4().hex}{target.suffix}')
    try:
        writer(str(stage))
        if not stage.is_file() or stage.stat().st_size==0:
            raise RuntimeError('Fresh output was not produced')
        if signature is not None:
            with stage.open('rb') as stream:
                if stream.read(len(signature))!=signature:raise RuntimeError('Invalid output signature')
        os.replace(stage,target)
    finally:
        if stage.exists():stage.unlink()
    return target.stat().st_size

def finite(value, name):
    value=float(value)
    if not math.isfinite(value):raise ValueError(f'{name} must be finite')
    return value

def positive(value,name):
    value=finite(value,name)
    if value<=0:raise ValueError(f'{name} must be positive')
    return value

def windows_path(path):
    if not path or '\x00' in path:raise ValueError('Invalid path')
    path=ntpath.normpath(path)
    drive,tail=ntpath.splitdrive(path)
    if not drive or not tail.startswith('\\'):raise ValueError('Absolute Windows path required')
    return path

def sheet_point(x,y,origin_x,origin_y,scale,angle_degrees):
    x=finite(x,'x');y=finite(y,'y');scale=positive(scale,'scale')
    angle=math.radians(finite(angle_degrees,'angle'))
    return (origin_x+scale*(x*math.cos(angle)-y*math.sin(angle)),
            origin_y+scale*(x*math.sin(angle)+y*math.cos(angle)))

class ReferenceStore:
    def __init__(self,session=None):
        self.session=session or uuid.uuid4().hex
        self.items={}
    def add(self,document,reference):
        token=f'{self.session}:{uuid.uuid4().hex}'
        self.items[token]=(document,reference)
        return token
    def get(self,token,document):
        item=self.items.get(token)
        if item is None or item[0]!=document:raise ValueError('Stale reference or wrong document')
        return item[1]
    def invalidate(self,document):
        self.items={k:v for k,v in self.items.items() if v[0]!=document}
    def invalidate_reference(self,document,reference):
        self.items={k:v for k,v in self.items.items() if v!=(document,reference)}
