"""Registered native model documents. COM objects never leave the STA worker."""
import math
import uuid
from pathlib import Path
from .core import windows_path

def solid_bounds(raw):
    if not raw[0] or any(not math.isfinite(x) or abs(x)>1e100 for x in raw[1:]):return None
    lo=list(map(float,raw[1:4]));hi=list(map(float,raw[4:7]))
    if any(b<a for a,b in zip(lo,hi)):return None
    return {'min':lo,'max':hi,'size':[b-a for a,b in zip(lo,hi)]}

def model_name(value):
    if not isinstance(value,str) or not value.strip():raise ValueError('A nonempty name is required')
    return value.strip()

class ModelDocuments:
    def _model_doc(self,document_id,kind=None):
        self._ready();doc=self.docs.get(document_id)
        if doc is None:raise ValueError('Unknown or closed document_id')
        if doc.DocumentType not in (4,5):raise ValueError('A 3D model is required')
        if kind is not None and doc.DocumentType!=kind:raise ValueError('Wrong model document type')
        doc.Active=True
        return doc

    def _model5(self,document_id):
        doc=self._model_doc(document_id)
        return self.api5.ksDocument3D(self.app.ksGetDocumentByReference(doc.Reference))

    def _part5(self,document_id):return self.api5.ksPart(self._model5(document_id).GetPart(-1))

    def _model_token(self,document_id,kind,obj):
        token=f'{self.refs.session}:3d:{uuid.uuid4().hex}'
        self.model_refs[token]=(document_id,kind,obj)
        return token

    def _model_ref(self,document_id,reference,kind):
        record=self.model_refs.get(reference)
        if record is None or record[0]!=document_id or record[1]!=kind:raise ValueError('Stale model reference, wrong document or wrong reference kind')
        return record[2]

    def _create_model(self,name,kind):
        name=model_name(name);self._ready()
        doc=self.app7.Documents.AddWithDefaultSettings(kind,True)
        result=self._register(doc)
        try:
            part=self._part5(result['document_id']);part.name=name;part.Update()
        except Exception:
            doc.Close(0);self.docs.pop(result['document_id']);raise
        result.update(type='part' if kind==4 else 'assembly',name=name)
        return result

    def create_part(self,name: str='Part') -> dict:
        """Create a separate native 3D part in the current server session."""
        return self._create_model(name,4)

    def create_assembly(self,name: str='Assembly') -> dict:
        """Create a separate native assembly. Placement is explicit, without mates."""
        return self._create_model(name,5)

    def open_model(self,path: str) -> dict:
        """Open a saved M3D/A3D and issue session-scoped model references."""
        path=windows_path(path)
        if Path(path).suffix.lower() not in ('.m3d','.a3d'):raise ValueError('Expected .m3d or .a3d')
        self._ready()
        if not Path(path).is_file():raise ValueError('Model file not found')
        for token,doc in self.docs.items():
            if doc.PathName and windows_path(doc.PathName).casefold()==path.casefold():
                self._model_doc(token);return {'document_id':token,'path':doc.PathName,'reused':True}
        doc=self.app7.Documents.Open(path,True,False)
        if doc is None or doc.DocumentType not in (4,5):raise RuntimeError('Model did not open')
        return self._register(doc)

    def save_model(self,document_id: str,path: str) -> dict:
        """Save a registered model, verifying fresh files and native path; mm units."""
        path=windows_path(path);doc=self._model_doc(document_id)
        expected='.m3d' if doc.DocumentType==4 else '.a3d'
        if Path(path).suffix.lower()!=expected:raise ValueError(f'Expected {expected}')
        target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
        stage=target.with_name(f'{target.stem}.{uuid.uuid4().hex}{expected}')
        self._model5(document_id).RebuildDocument()
        doc.SaveAs(str(stage))
        if not stage.is_file() or not stage.stat().st_size or windows_path(doc.PathName).casefold()!=str(stage).casefold():raise RuntimeError('Fresh model save failed')
        before=target.stat().st_mtime_ns if target.exists() else None
        doc.SaveAs(path)
        if not target.is_file() or not target.stat().st_size or target.stat().st_mtime_ns==before or windows_path(doc.PathName).casefold()!=path.casefold():raise RuntimeError(f'Save failed; recovery file: {stage}')
        stage.unlink()
        return {'saved':True,'path':path,'bytes':target.stat().st_size}

    def close_model(self,document_id: str) -> dict:
        """Close a registered model WITHOUT saving; invalidate all its model tokens."""
        doc=self._model_doc(document_id)
        if not doc.Close(0):raise RuntimeError('Model did not close')
        self.docs.pop(document_id);self.refs.invalidate(document_id)
        self.model_refs={k:v for k,v in self.model_refs.items() if v[0]!=document_id}
        return {'closed':True}

    def model_state(self,document_id: str) -> dict:
        """Read native solid bounds/volume and feature errors, excluding auxiliary planes."""
        doc=self._model_doc(document_id);part=self._part5(document_id)
        bodies=self.api5.ksBodyCollection(part.BodyCollection());count=bodies.GetCount()
        bounds=solid_bounds(part.GetGabarit(False,False)) if count else None
        volume=float(self.api5.ksMassInertiaParam(part.CalcMassInertiaProperties(1)).v) if count else 0.
        features=[]
        for typ,kind in ((5,'sketch'),(14,'offset_plane'),(24,'base'),(25,'boss'),(26,'cut')):
            coll=self.api5.ksEntityCollection(part.EntityCollection(typ))
            for i in range(coll.GetCount()):
                entity=self.api5.ksEntity(coll.GetByIndex(i));feature=self.api5.ksFeature(entity.GetFeature())
                item={'name':entity.name,'kind':kind,'valid':bool(feature.IsValid()),'error':feature.objectError}
                if typ in (24,25,26):
                    item['reference']=self._model_token(document_id,'feature',entity)
                    definition=self._extrusion_definition(entity)
                    side=definition.directionType!=1
                    item['depth_mm']=definition.GetSideParam(side)[2]
                elif typ==5:item['reference']=self._model_token(document_id,'sketch',entity)
                features.append(item)
        return {'document_id':document_id,'type':'part' if doc.DocumentType==4 else 'assembly','name':part.name,'path':doc.PathName,'changed':bool(doc.Changed),'body_count':count,'bounds_mm':bounds,'volume_mm3':volume,'features':features}

    def rebuild_model(self,document_id: str) -> dict:
        """Rebuild a model and read feature validity/errors, not only its COM bool."""
        self._model5(document_id).RebuildDocument()
        state=self.model_state(document_id)
        errors=[f for f in state['features'] if f['error'] or not f['valid']]
        if errors:raise RuntimeError(f'Model rebuild errors: {errors}')
        return state
