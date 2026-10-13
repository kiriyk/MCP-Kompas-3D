"""Native model exports with structural verification of fresh outputs."""
import math
import re
import struct
from pathlib import Path
from typing import Literal
from .core import windows_path,verified_output

def inspect_stl(path):
    data=Path(path).read_bytes();vertices=[]
    if len(data)>=84 and len(data)==84+50*struct.unpack_from('<I',data,80)[0]:
        count=struct.unpack_from('<I',data,80)[0]
        for i in range(count):
            values=struct.unpack_from('<12fH',data,84+50*i)
            vertices.extend([values[3:6],values[6:9],values[9:12]])
    elif data.lstrip().startswith(b'solid') and b'endsolid' in data:
        for match in re.finditer(rb'vertex\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)',data):vertices.append(tuple(float(x) for x in match.groups()))
        if len(vertices)%3:raise ValueError('Malformed ASCII STL')
        count=len(vertices)//3
    else:raise ValueError('Malformed or truncated STL')
    if not vertices or any(not math.isfinite(x) for v in vertices for x in v):raise ValueError('Empty/nonfinite STL')
    lo=[min(v[i] for v in vertices) for i in range(3)];hi=[max(v[i] for v in vertices) for i in range(3)]
    if any(b-a<1e-8 for a,b in zip(lo,hi)):raise ValueError('Degenerate STL')
    return {'triangles':count,'bounds_mm':{'min':lo,'max':hi,'size':[b-a for a,b in zip(lo,hi)]}}

class ModelIO:
    def export_model(self,document_id: str,path: str,format: Literal['stl','step']='stl') -> dict:
        """Export saved unchanged model to verified native STL in mm; STEP is rejected."""
        if format not in ('stl','step'):raise ValueError('Expected stl or step')
        path=windows_path(path)
        if Path(path).suffix.lower() not in ({'.stl'} if format=='stl' else {'.step','.stp'}):raise ValueError('Export extension does not match format')
        doc=self._model_doc(document_id)
        if not doc.PathName or doc.Changed:raise ValueError('Save the model before export')
        if format=='step':raise ValueError('STEP converter has not been verified for this installation')
        facts={}
        expected=self.model_state(document_id)['bounds_mm']
        def writer(stage):
            self._model5(document_id).SaveAsEx(stage,6)
            facts.update(inspect_stl(stage))
            if expected and any(abs(a-b)>0.05 for a,b in zip(expected['size'],facts['bounds_mm']['size'])):raise RuntimeError('STL/model bounds mismatch')
        size=verified_output(path,writer)
        return {'path':path,'bytes':size,'format':format,'units':'mm (STL has no unit metadata)',**facts}
