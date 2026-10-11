"""Probed API5 sketches/extrusions with explicit lifecycle and validation."""
from typing import Literal
from .core import finite,positive
from .model_documents import model_name
from .profile_validation import polygon

class ModelFeatures:
    def create_sketch(self,document_id: str,plane: Literal['XY','XZ','YZ'],name: str='Sketch',offset: float=0) -> dict:
        """Sketch on a standard/offset plane. Local XY coordinates; offset follows plane normal."""
        if plane not in ('XY','XZ','YZ'):raise ValueError('Expected XY, XZ or YZ')
        offset=finite(offset,'offset');name=model_name(name)
        self._model_doc(document_id,4);part=self._part5(document_id);doc=self._model5(document_id)
        base=part.GetDefaultEntity({'XY':1,'XZ':2,'YZ':3}[plane]);created=[]
        try:
            if offset:
                entity=self.api5.ksEntity(part.NewEntity(14));definition=self.api5.ksPlaneOffsetDefinition(entity.GetDefinition())
                definition.SetPlane(base);definition.offset=abs(offset);definition.direction=offset>=0
                if not entity.Create():raise RuntimeError('Offset plane creation failed')
                created.append(entity);base=entity
            sketch=self.api5.ksEntity(part.NewEntity(5));sketch.name=name
            definition=self.api5.ksSketchDefinition(sketch.GetDefinition());definition.SetPlane(base)
            if not sketch.Create():raise RuntimeError('Sketch creation failed')
            created.append(sketch)
            return {'sketch_reference':self._model_token(document_id,'sketch',sketch),'name':sketch.name,'plane':plane,'offset_mm':offset}
        except Exception:
            remaining=[]
            for item in reversed(created):
                try:
                    if not doc.DeleteObject(item):remaining.append(item.name)
                except Exception:remaining.append(item.name)
            if remaining:raise RuntimeError(f'Sketch rollback incomplete: {remaining}')
            raise

    def _edit_sketch(self,document_id,reference,writer):
        self._model_doc(document_id,4);sketch=self._model_ref(document_id,reference,'sketch')
        definition=self.api5.ksSketchDefinition(sketch.GetDefinition())
        cad=self.api5.ksDocument2D(definition.BeginEdit());created=[]
        try:writer(cad,created)
        except Exception:
            for ref in reversed(created):cad.ksDeleteObj(ref)
            raise
        finally:
            if not definition.EndEdit():raise RuntimeError('EndEdit failed; inspect model edit mode before continuing')
        return {'sketch_reference':reference,'created_count':len(created)}

    def sketch_polygon(self,document_id: str,sketch_reference: str,points: list[list[float]]) -> dict:
        """Add a validated simple closed polygon in sketch-local mm."""
        pts=polygon(points)
        def writer(cad,created):
            for p,q in zip(pts,pts[1:]+pts[:1]):
                ref=cad.ksLineSeg(*p,*q,1)
                if not ref:raise RuntimeError('Sketch line failed')
                created.append(ref)
        return self._edit_sketch(document_id,sketch_reference,writer)

    def sketch_circle(self,document_id: str,sketch_reference: str,x: float,y: float,radius: float) -> dict:
        """Add a circle in sketch-local mm; radius must be positive."""
        x=finite(x,'x');y=finite(y,'y');radius=positive(radius,'radius')
        def writer(cad,created):
            ref=cad.ksCircle(x,y,radius,1)
            if not ref:raise RuntimeError('Sketch circle failed')
            created.append(ref)
        return self._edit_sketch(document_id,sketch_reference,writer)

    def _extrusion_definition(self,entity):
        cls={24:self.api5.ksBaseExtrusionDefinition,25:self.api5.ksBossExtrusionDefinition,26:self.api5.ksCutExtrusionDefinition}.get(entity.type)
        if cls is None:raise ValueError('An extrusion feature is required')
        return cls(entity.GetDefinition())

    def extrude(self,document_id: str,sketch_reference: str,depth: float,operation: Literal['base','boss','cut']='base',reverse: bool=False,name: str='Extrusion') -> dict:
        """Extrude along sketch normal (+ by default), for base/boss/cut; native finite depth."""
        depth=positive(depth,'depth');name=model_name(name)
        if operation not in ('base','boss','cut'):raise ValueError('Expected base, boss or cut')
        self._model_doc(document_id,4);sketch=self._model_ref(document_id,sketch_reference,'sketch');part=self._part5(document_id)
        before=self.model_state(document_id)['volume_mm3']
        entity=self.api5.ksEntity(part.NewEntity({'base':24,'boss':25,'cut':26}[operation]));entity.name=name
        definition=self._extrusion_definition(entity)
        # API5 cuts invert their direction relative to base/boss extrusions.
        side=(not reverse) if operation!='cut' else reverse
        definition.directionType=0 if side else 1
        definition.SetSketch(sketch);definition.SetSideParam(side,0,depth,0,False)
        created=False
        try:
            created=bool(entity.Create())
            if not created:raise RuntimeError('Extrusion creation failed')
            state=self.rebuild_model(document_id)
            after=state['volume_mm3']
            if (operation=='cut' and after>=before-1e-7) or (operation!='cut' and after<=before+1e-7):raise RuntimeError('Extrusion produced no expected solid volume change')
        except Exception:
            if created:
                if not self._model5(document_id).DeleteObject(entity):raise RuntimeError('Extrusion failed; rollback incomplete, inspect model')
                self._model5(document_id).RebuildDocument()
            raise
        return {'feature_reference':self._model_token(document_id,'feature',entity),'name':entity.name,'operation':operation,'depth_mm':definition.GetSideParam(side)[2],'reverse':reverse,'volume_mm3':after}

    def set_extrusion_depth(self,document_id: str,feature_reference: str,depth: float) -> dict:
        """Change finite extrusion depth, rebuild and restore old depth if validation fails."""
        depth=positive(depth,'depth');self._model_doc(document_id,4)
        entity=self._model_ref(document_id,feature_reference,'feature');definition=self._extrusion_definition(entity)
        side=definition.directionType!=1;old=definition.GetSideParam(side)
        try:
            definition.SetSideParam(side,0,depth,old[3],old[4]);entity.Update()
            state=self.rebuild_model(document_id)
            actual=self._extrusion_definition(entity).GetSideParam(side)[2]
            if abs(actual-depth)>1e-7:raise RuntimeError('Depth postcondition failed')
        except Exception:
            definition.SetSideParam(side,old[1],old[2],old[3],old[4]);entity.Update();self._model5(document_id).RebuildDocument();raise
        return {'feature_reference':feature_reference,'depth_mm':actual,'volume_mm3':state['volume_mm3']}
