"""File-linked native assembly components with verified rigid placement."""
from pathlib import Path
from .core import finite,windows_path
from .model_documents import model_name

def placement_vectors(origin,x_axis,y_axis):
    result=[]
    for label,v in (('origin',origin),('x_axis',x_axis),('y_axis',y_axis)):
        if len(v)!=3:raise ValueError(f'{label} requires three coordinates')
        result.append([finite(n,label) for n in v])
    o,x,y=result
    if abs(sum(n*n for n in x)-1)>1e-7 or abs(sum(n*n for n in y)-1)>1e-7 or abs(sum(a*b for a,b in zip(x,y)))>1e-7:raise ValueError('Placement axes must be orthonormal')
    return o,x,y

class ModelAssembly:
    def upsert_component(self,document_id: str,path: str,name: str,origin: list[float],x_axis: list[float],y_axis: list[float]) -> dict:
        """Insert or reposition one component by unique exact name, without duplicates. Existing source must match; ambiguous names/source changes fail before mutation."""
        path=windows_path(path);name=model_name(name);placement_vectors(origin,x_axis,y_axis)
        if Path(path).suffix.lower()!='.m3d' or not Path(path).is_file():raise ValueError('Saved M3D required')
        self._model_doc(document_id,5)
        matches=[c for c in self.list_components(document_id)['components'] if c['name']==name]
        if len(matches)>1:raise ValueError('Ambiguous component name')
        inserted=False
        if matches:
            result=matches[0]
            if windows_path(result['source_path']).casefold()!=path.casefold():raise ValueError('Existing component source differs; remove explicitly before replacement')
        else:
            result=self.insert_component(document_id,path,name);inserted=True
        try:
            placement=self.set_component_placement(document_id,result['component_reference'],origin,x_axis,y_axis)
        except Exception:
            if inserted:self.remove_component(document_id,result['component_reference'])
            raise
        return {**result,**placement,'action':'inserted' if inserted else 'reused'}

    def remove_component(self,document_id: str,component_reference: str) -> dict:
        """Remove one explicitly referenced component from this assembly; preserve its source M3D. Invalidate component/geometry references and verify count."""
        self._model_doc(document_id,5);part=self._model_ref(document_id,component_reference,'component')
        doc=self._model5(document_id);before=doc.PartCollection(True).GetCount();name=part.name
        aliases=[k for k,v in self.model_refs.items() if v[0]==document_id and v[1]=='component' and v[2]._oleobj_==part._oleobj_]
        if not doc.DeleteObject(part):raise RuntimeError('Component deletion failed')
        for ref in aliases:self.model_refs.pop(ref,None)
        self._invalidate_topology(document_id);doc.RebuildDocument()
        after=doc.PartCollection(True).GetCount()
        if after!=before-1:raise RuntimeError('Component removal count mismatch')
        return {'removed':True,'name':name,'component_count':after,'source_deleted':False}

    def _placement_info(self,part):
        p=self.api5.ksPlacement(part.GetPlacement())
        values=[p.GetOrigin(),p.GetVector(0),p.GetVector(1)]
        if any(len(v)!=4 or not v[0] for v in values):raise RuntimeError('Native placement read failed')
        try:o,x,y=placement_vectors(*[list(v[1:]) for v in values])
        except ValueError as error:raise RuntimeError('Invalid native placement') from error
        return {'origin':o,'x_axis':x,'y_axis':y}

    def insert_component(self,document_id: str,path: str,name: str='Component') -> dict:
        """Insert a saved native part into an assembly with an external source link."""
        path=windows_path(path);name=model_name(name)
        if Path(path).suffix.lower()!='.m3d' or not Path(path).is_file():raise ValueError('A saved .m3d component is required')
        self._model_doc(document_id,5);doc=self._model5(document_id)
        before=self.api5.ksPartCollection(doc.PartCollection(True)).GetCount()
        part=self.api5.ksPart(doc.GetPart(-3))
        try:
            if not doc.SetPartFromFile(path,part,True):raise RuntimeError('Component insertion failed')
            part.name=name;part.Update();doc.RebuildDocument()
            count=self.api5.ksPartCollection(doc.PartCollection(True)).GetCount()
            if count!=before+1:raise RuntimeError('Component count postcondition failed')
        except Exception:
            if not doc.DeleteObject(part):raise RuntimeError('Insertion failed and component rollback incomplete')
            raise
        return {'component_reference':self._model_token(document_id,'component',part),'name':part.name,'source_path':part.fileName,'placement':self._placement_info(part)}

    def set_component_placement(self,document_id: str,component_reference: str,origin: list[float],x_axis: list[float],y_axis: list[float]) -> dict:
        """Set a right-handed rigid placement; vectors must be orthonormal; origin in mm."""
        origin,x_axis,y_axis=placement_vectors(origin,x_axis,y_axis)
        self._model_doc(document_id,5);part=self._model_ref(document_id,component_reference,'component');old=self._placement_info(part)
        place=self.api5.ksPlacement(part.GetPlacement())
        try:
            if not place.SetOrigin(*origin) or not place.SetAxes(*x_axis,*y_axis) or not part.UpdatePlacement() or not self._model5(document_id).RebuildDocument():raise RuntimeError('Native placement update failed')
            actual=self._placement_info(part)
            self._invalidate_topology(document_id)
            for key,want in (('origin',origin),('x_axis',x_axis),('y_axis',y_axis)):
                if any(abs(a-b)>1e-6 for a,b in zip(actual[key],want)):raise RuntimeError('Placement postcondition failed')
        except Exception as error:
            self._invalidate_topology(document_id)
            try:
                if not place.SetOrigin(*old['origin']) or not place.SetAxes(*old['x_axis'],*old['y_axis']) or not part.UpdatePlacement() or not self._model5(document_id).RebuildDocument():raise RuntimeError('Rollback placement update failed')
                restored=self._placement_info(part)
                if any(abs(a-b)>1e-6 for key in old for a,b in zip(restored[key],old[key])):raise RuntimeError('Rollback placement mismatch')
            except Exception as failure:raise RuntimeError(f'Placement failed; rollback incomplete: {failure}') from error
            raise
        return {'component_reference':component_reference,'placement':actual}

    def list_components(self,document_id: str) -> dict:
        """Read native component source files and placements, returning fresh scoped tokens."""
        self._model_doc(document_id,5);coll=self.api5.ksPartCollection(self._model5(document_id).PartCollection(True));items=[]
        for i in range(coll.GetCount()):
            p=self.api5.ksPart(coll.GetByIndex(i))
            items.append({'component_reference':self._model_token(document_id,'component',p),'name':p.name,'source_path':p.fileName,'placement':self._placement_info(p)})
        return {'components':items,'count':len(items)}
