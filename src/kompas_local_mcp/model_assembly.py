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
    def _placement_info(self,part):
        p=self.api5.ksPlacement(part.GetPlacement())
        return {'origin':list(p.GetOrigin()[1:]),'x_axis':list(p.GetVector(0)[1:]),'y_axis':list(p.GetVector(1)[1:])}

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
            place.SetOrigin(*origin);place.SetAxes(*x_axis,*y_axis);part.UpdatePlacement();self._model5(document_id).RebuildDocument()
            actual=self._placement_info(part)
            for key,want in (('origin',origin),('x_axis',x_axis),('y_axis',y_axis)):
                if any(abs(a-b)>1e-6 for a,b in zip(actual[key],want)):raise RuntimeError('Placement postcondition failed')
        except Exception:
            place.SetOrigin(*old['origin']);place.SetAxes(*old['x_axis'],*old['y_axis']);part.UpdatePlacement();raise
        return {'component_reference':component_reference,'placement':actual}

    def list_components(self,document_id: str) -> dict:
        """Read native component source files and placements, returning fresh scoped tokens."""
        self._model_doc(document_id,5);coll=self.api5.ksPartCollection(self._model5(document_id).PartCollection(True));items=[]
        for i in range(coll.GetCount()):
            p=self.api5.ksPart(coll.GetByIndex(i))
            items.append({'component_reference':self._model_token(document_id,'component',p),'name':p.name,'source_path':p.fileName,'placement':self._placement_info(p)})
        return {'components':items,'count':len(items)}
