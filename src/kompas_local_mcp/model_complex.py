"""Native forming operations; no arbitrary script execution is exposed."""
from pathlib import Path
from typing import Literal
from .core import finite, positive, windows_path, verified_output
from .model_documents import model_name, solid_bounds

def references(values,minimum=1):
    if not isinstance(values,list) or len(values)<minimum or any(not isinstance(v,str) or not v for v in values) or len(set(values))!=len(values):
        raise ValueError(f'At least {minimum} distinct references required')
    return values

class ModelComplex:
    def _invalidate_topology(self,document_id):
        self.model_refs={k:v for k,v in self.model_refs.items() if not(v[0]==document_id and v[1] in ('edge','face','body'))}

    def _forming(self,document_id,entity,operation='modify'):
        before=self.model_state(document_id)
        try:
            if not entity.Create():raise RuntimeError('Native forming Create failed')
            state=self.rebuild_model(document_id)
            feature=self.api5.ksFeature(entity.GetFeature())
            if not feature.IsValid() or feature.objectError:raise RuntimeError(f'Native forming error {feature.objectError}')
            if state['body_count']<1 or state['volume_mm3']<=0:raise RuntimeError('No valid solid result')
            delta=state['volume_mm3']-before['volume_mm3']
            if operation=='cut' and delta>=-1e-7:raise RuntimeError('Cut did not remove volume')
            if operation in ('base','boss') and delta<=1e-7:raise RuntimeError('Forming did not add volume')
        except Exception as error:
            # Create can return False with an erroneous feature already inserted.
            if not self._model5(document_id).DeleteObject(entity):
                raise RuntimeError(f'Forming failed; rollback incomplete: {entity.name}') from error
            self._model5(document_id).RebuildDocument();self._invalidate_topology(document_id)
            restored=self.model_state(document_id)
            if restored['body_count']!=before['body_count'] or abs(restored['volume_mm3']-before['volume_mm3'])>.01:
                raise RuntimeError('Forming failed; rollback geometry mismatch') from error
            raise
        return {'feature_reference':self._model_token(document_id,'feature',entity),'name':entity.name,
                'volume_mm3':state['volume_mm3'],'body_count':state['body_count']}

    def sketch_arc(self,document_id: str,sketch_reference: str,x: float,y: float,radius: float,start_angle: float,end_angle: float,clockwise: bool=False) -> dict:
        """Circular arc in sketch-local mm/degrees, for swept paths; not a closed profile."""
        x=finite(x,'x');y=finite(y,'y');radius=positive(radius,'radius')
        start_angle=finite(start_angle,'start_angle');end_angle=finite(end_angle,'end_angle')
        if abs((end_angle-start_angle)%360)<1e-9:raise ValueError('Arc endpoints must differ')
        def writer(cad,created):
            ref=cad.ksArcByAngle(x,y,radius,start_angle,end_angle,-1 if clockwise else 1,1)
            if not ref:raise RuntimeError('Sketch arc failed')
            created.append(ref)
        return self._edit_sketch(document_id,sketch_reference,writer)

    def loft(self,document_id: str,sketch_references: list[str],operation: Literal['base','boss','cut']='base',name: str='Loft') -> dict:
        """Solid loft through ordered distinct closed sketch sections. Base/boss/cut; no guides."""
        references(sketch_references,2);name=model_name(name)
        if operation not in ('base','boss','cut'):raise ValueError('Expected base/boss/cut')
        self._model_doc(document_id,4)
        sketches=[self._model_ref(document_id,s,'sketch') for s in sketch_references]
        entity=self.api5.ksEntity(self._part5(document_id).NewEntity({'base':30,'boss':31,'cut':32}[operation]));entity.name=name
        cls={'base':self.api5.ksBaseLoftDefinition,'boss':self.api5.ksBossLoftDefinition,'cut':self.api5.ksCutLoftDefinition}[operation]
        definition=cls(entity.GetDefinition())
        if not definition.SetLoftParam(False,False,True):raise RuntimeError('Loft parameters failed')
        arr=self.api5.ksEntityCollection(definition.Sketchs())
        for sketch in sketches:
            if not arr.Add(sketch):raise RuntimeError('Loft sketch registration failed')
        return self._forming(document_id,entity,operation)

    def sweep(self,document_id: str,profile_reference: str,path_references: list[str],name: str='Sweep') -> dict:
        """Base solid sweep along ordered sketch paths, profile normal to starting tangent."""
        references(path_references);name=model_name(name)
        if profile_reference in path_references:raise ValueError('Profile cannot be its own path')
        self._model_doc(document_id,4)
        profile=self._model_ref(document_id,profile_reference,'sketch')
        paths=[self._model_ref(document_id,s,'sketch') for s in path_references]
        entity=self.api5.ksEntity(self._part5(document_id).NewEntity(45));entity.name=name
        definition=self.api5.ksBaseEvolutionDefinition(entity.GetDefinition());definition.sketchShiftType=1
        if not definition.SetSketch(profile):raise RuntimeError('Sweep profile failed')
        arr=self.api5.ksEntityCollection(definition.PathPartArray())
        for path in paths:
            if not arr.Add(path):raise RuntimeError('Sweep path registration failed')
        return self._forming(document_id,entity,'base')

    def fillet(self,document_id: str,edge_references: list[str],radius: float,name: str='Fillet') -> dict:
        """Fillet explicitly selected current edges; geometry references expire on rebuild."""
        radius=positive(radius,'radius');references(edge_references);name=model_name(name)
        self._model_doc(document_id,4)
        edges=[self._model_ref(document_id,r,'edge') for r in edge_references]
        entity=self.api5.ksEntity(self._part5(document_id).NewEntity(34));entity.name=name
        definition=self.api5.ksFilletDefinition(entity.GetDefinition());definition.radius=radius;definition.tangent=False
        arr=self.api5.ksEntityCollection(definition.array())
        for edge in edges:
            if not arr.Add(edge):raise RuntimeError('Fillet edge registration failed')
        return self._forming(document_id,entity)

    def shell(self,document_id: str,face_references: list[str],thickness: float,inward: bool=False,name: str='Shell') -> dict:
        """Constant wall shell removing explicitly selected faces; inward=False grows outward."""
        thickness=positive(thickness,'thickness');references(face_references);name=model_name(name)
        self._model_doc(document_id,4)
        faces=[self._model_ref(document_id,r,'face') for r in face_references]
        entity=self.api5.ksEntity(self._part5(document_id).NewEntity(43));entity.name=name
        definition=self.api5.ksShellDefinition(entity.GetDefinition());definition.thickness=thickness;definition.thinType=inward
        arr=self.api5.ksEntityCollection(definition.FaceArray())
        for face in faces:
            if not arr.Add(face):raise RuntimeError('Shell face registration failed')
        return self._forming(document_id,entity)

    def _edge_bounds(self,entity):
        definition=self.api5.ksEdgeDefinition(entity.GetDefinition())
        if definition.IsStraight():
            points=[]
            for start in (True,False):
                native=definition.GetVertex(start)
                if native is None:return None
                vertex=self.api5.ksVertexDefinition(native)
                raw=vertex.GetPoint()
                if not raw[0]:return None
                points.append(raw[1:])
            return solid_bounds((True,*[min(p[i] for p in points) for i in range(3)],*[max(p[i] for p in points) for i in range(3)]))
        return solid_bounds(self.api5.ksCurve3D(definition.GetCurve3D()).GetGabarit())

    def list_model_topology(self,document_id: str,kind: Literal['face','edge']='face',component_reference: str|None=None) -> dict:
        """List current topology with scoped references and geometry. Curved bounds cover underlying curve, may exceed trimmed edge. Never select by index after rebuild."""
        if kind not in ('face','edge'):raise ValueError('Expected face or edge')
        doc=self._model_doc(document_id)
        if doc.DocumentType==5 and component_reference is None:raise ValueError('Select a component for assembly topology')
        part=self._model_ref(document_id,component_reference,'component') if component_reference else self._part5(document_id)
        placement=self._placement_info(part) if component_reference else None
        bodies=self.api5.ksBodyCollection(part.BodyCollection());entities=[];items=[]
        for bi in range(int(bodies.GetCount())):
            body=self.api5.ksBody(bodies.GetByIndex(bi))
            faces=self.api5.ksFaceCollection(body.FaceCollection())
            for fi in range(int(faces.GetCount())):
                face=self.api5.ksEntity(faces.GetByIndex(fi).GetEntity())
                if kind=='face':entities.append(face);continue
                edges=self.api5.ksEdgeCollection(self.api5.ksFaceDefinition(face.GetDefinition()).EdgeCollection())
                for ei in range(int(edges.GetCount())):
                    edge=self.api5.ksEntity(edges.GetByIndex(ei).GetEntity())
                    if not any(edge._oleobj_==other._oleobj_ for other in entities):entities.append(edge)
        for entity in entities:
            bounds=None
            definition=(self.api5.ksFaceDefinition if kind=='face' else self.api5.ksEdgeDefinition)(entity.GetDefinition())
            if kind=='edge':
                if definition.sketchEdge:continue
                bounds=self._edge_bounds(entity)
                if bounds is None:continue
                properties={'straight':bool(definition.IsStraight()),'length_mm':definition.GetLength(1)}
            else:
                edges=self.api5.ksEdgeCollection(definition.EdgeCollection());boxes=[]
                for j in range(int(edges.GetCount())):
                    box=self._edge_bounds(self.api5.ksEntity(edges.GetByIndex(j).GetEntity()))
                    if box:boxes.append(box)
                if boxes:bounds=solid_bounds((True,*[min(b['min'][k] for b in boxes) for k in range(3)],*[max(b['max'][k] for b in boxes) for k in range(3)]))
                properties={'planar':bool(definition.IsPlanar()),'area_mm2':definition.GetArea(1)}
            properties.update(self._topology_properties(definition,kind,placement))
            if placement and bounds:
                import itertools
                from .model_inspection import transform
                pts=[transform(p,placement,True) for p in itertools.product(*zip(bounds['min'],bounds['max']))]
                bounds=solid_bounds((True,*[min(p[i] for p in pts) for i in range(3)],*[max(p[i] for p in pts) for i in range(3)]))
            items.append({'reference':self._model_token(document_id,kind,entity),'bounds_mm':bounds,'component_reference':component_reference,**properties})
        return {'kind':kind,'items':items,'count':len(items),'references_expire_on_rebuild':True,'coordinate_space':'assembly' if placement else 'part'}

    def _topology_properties(self,definition,kind,placement):
        from .model_inspection import unit,transform
        owner=definition.GetOwnerEntity();result={'owner_name':owner.name if owner is not None else None,'radius_mm':None,'normal':None,'direction':None}
        if kind=='face':
            if definition.IsPlanar():
                surface=self.api5.ksSurface(definition.GetSurface());p=self.api5.ksPlaneParam(surface.GetSurfaceParam()).GetPlacement();raw=p.GetVector(2)
                if raw[0]:result['normal']=unit(transform(raw[1:],placement) if placement else raw[1:])
            if definition.IsCylinder():
                raw=definition.GetCylinderParam()
                if raw[0]:result['radius_mm']=raw[2]
        else:
            curve=self.api5.ksCurve3D(definition.GetCurve3D())
            if curve.IsCircle() or curve.IsArc():
                cls=self.api5.ksCircle3dParam if curve.IsCircle() else self.api5.ksArc3dParam
                result['radius_mm']=positive(cls(curve.GetCurveParam()).radius,'native_radius')
            if definition.IsStraight():
                points=[definition.GetVertex(b).GetPoint() for b in (True,False)]
                direction=[points[1][i]-points[0][i] for i in range(1,4)];result['direction']=unit(transform(direction,placement) if placement else direction)
        return result

    def set_model_display(self,document_id: str,transparency_percent: float=0,hide_auxiliary: bool=True,wireframe: bool=False) -> dict:
        """Set shaded model display and top-part transparency in UI percent: 0 opaque, 100 invisible."""
        value=finite(transparency_percent,'transparency_percent')
        if not 0<=value<=100:raise ValueError('Transparency must be 0..100 percent')
        doc=self.api7.IKompasDocument3D(self._model_doc(document_id));part=doc.TopPart
        cls=self.api7.IColorParam7;params=cls(part._oleobj_.QueryInterface(cls.CLSID,self.com.IID_IDispatch))
        old=params.GetAdvancedColor()
        if not old[0]:raise RuntimeError('Cannot read display opacity')
        old_mode=(doc.DrawMode,doc.ShadedWireframe,doc.HideAllPlanes,doc.HideAllSketches,getattr(doc,'HideAllAxis',False),getattr(doc,'HideAllAuxiliaryGeom',False))
        try:
            if abs(old[6]-(1-value/100))>1e-8:
                if not params.SetAdvancedColor(*old[1:6],1-value/100,old[7]) or not part.Update():raise RuntimeError('Display update failed')
            actual=cls(doc.TopPart).GetAdvancedColor()[6]
            if abs(actual-(1-value/100))>1e-8:raise RuntimeError('Transparency readback failed')
            doc.DrawMode=3;doc.ShadedWireframe=wireframe;doc.HideAllPlanes=hide_auxiliary;doc.HideAllSketches=hide_auxiliary
            doc.HideAllAxis=hide_auxiliary;doc.HideAllAuxiliaryGeom=hide_auxiliary
        except Exception:
            params.SetAdvancedColor(*old[1:]);part.Update()
            doc.DrawMode,doc.ShadedWireframe,doc.HideAllPlanes,doc.HideAllSketches,doc.HideAllAxis,doc.HideAllAuxiliaryGeom=old_mode
            raise
        return {'transparency_percent':value,'shaded':True,'hide_auxiliary':hide_auxiliary}

    def export_model_png(self,document_id: str,path: str,dpi: int=120) -> dict:
        """Native colored 3D raster export in current orientation; no UI automation/screenshot."""
        path=windows_path(path)
        if Path(path).suffix.lower()!='.png':raise ValueError('Expected .png')
        if isinstance(dpi,bool) or not isinstance(dpi,int) or not 40<=dpi<=300:raise ValueError('DPI must be 40..300')
        Path(path).parent.mkdir(parents=True,exist_ok=True);doc=self._model5(document_id);doc.ZoomPrevNextOrAll(2)
        param=self.api5.ksRasterFormatParam(doc.RasterFormatParam());param.Init()
        param.format=3;param.colorBPP=24;param.greyScale=False;param.colorType=3;param.extResolution=dpi;param.extScale=1
        verified_output(path,lambda stage:doc.SaveAsToRasterFormat(stage,param),b'\x89PNG\r\n\x1a\n')
        return {'path':path,'bytes':Path(path).stat().st_size,'capture_mode':'native_colored_model'}



