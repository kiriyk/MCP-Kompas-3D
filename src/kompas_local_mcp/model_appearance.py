"""Native model appearance and camera controls, with persisted readback."""
import math
from typing import Literal
from .core import finite
from .model_views import projection_matrix

def color_value(color):
    if isinstance(color,bool) or not isinstance(color,int) or not 0<=color<=0xffffff:raise ValueError('Expected COLORREF integer 0..0xffffff')
    return color

def same_appearance(actual,desired):
    return actual[0]==desired[0] and all(abs(a-b)<1e-7 for a,b in zip(actual[1:],desired[1:]))

class ModelAppearance:
    def _color7(self,obj):
        cls=self.api7.IColorParam7
        return cls(obj._oleobj_.QueryInterface(cls.CLSID,self.com.IID_IDispatch))

    def list_model_bodies(self,document_id: str) -> dict:
        """List current top-part bodies and native appearance references. References expire on rebuild; use component topology for assembly geometry."""
        top=self.api7.IKompasDocument3D(self._model_doc(document_id)).TopPart
        raw=self.api7.IFeature7(top).ResultBodies
        objects=[] if raw is None else list(raw) if isinstance(raw,(tuple,list)) else [raw]
        items=[]
        for i,obj in enumerate(objects):
            body=self.api7.IBody7(obj);p=self._color7(body);c=p.GetAdvancedColor()
            items.append({'body_reference':self._model_token(document_id,'body',body),'body_index':i,'color':c[1],'transparency_percent':100*(1-c[6]),'use_color':p.UseColor})
        return {'items':items,'count':len(items),'references_expire_on_rebuild':True}

    def set_model_appearance(self,document_id: str,color: int,transparency_percent: float=0,scope: Literal['document','body','face','component']='document',reference: str|None=None,cascade: bool=True) -> dict:
        """Set COLORREF and UI transparency (0 opaque) on document/body/face/component. Document cascade explicitly colors result bodies and solid faces; no render-filter coloring. Rollback on failure."""
        color=color_value(color);transparency_percent=finite(transparency_percent,'transparency_percent')
        if not 0<=transparency_percent<=100:raise ValueError('Transparency must be 0..100')
        if scope not in ('document','body','face','component'):raise ValueError('Invalid appearance scope')
        if (scope=='document')!=(reference is None):raise ValueError('Reference required only for non-document scopes')
        self._model_doc(document_id);opacity=1-transparency_percent/100;targets=[]
        if scope=='document':
            part=self.api7.IKompasDocument3D(self._model_doc(document_id)).TopPart
            targets.append((part,self._color7(part),True))
            if cascade:
                # Forming features can carry independent colors overriding TopPart.
                if self._model_doc(document_id).DocumentType==4:
                    p5=self._part5(document_id)
                    for kind in (24,25,26,30,31,32,34,43,45,46,47):
                        features=p5.EntityCollection(kind)
                        for i in range(features.GetCount()):
                            feature=features.GetByIndex(i);targets.append((feature,feature,False))
                for item in self.list_model_bodies(document_id)['items']:
                    body=self._model_ref(document_id,item['body_reference'],'body');targets.append((body,self._color7(body),True))
                if self._model_doc(document_id).DocumentType==4:
                    for item in self.list_model_topology(document_id,'face')['items']:
                        face=self._model_ref(document_id,item['reference'],'face');targets.append((face,face,False))
        else:
            obj=self._model_ref(document_id,reference,scope)
            targets.append((obj,self._color7(obj) if scope=='body' else obj,scope=='body'))
        snapshots=[];changed=[]
        try:
            for index,(obj,param,api7) in enumerate(targets):
                old=param.GetAdvancedColor()
                if not old[0]:raise RuntimeError('Appearance read failed')
                # TopPart UseColor can read -1 even after setting 0; it has no parent.
                use=None if scope=='document' and index==0 else param.UseColor if api7 else getattr(param,'useColor',None)
                snapshots.append((obj,param,api7,old,use))
                desired=(color,.55,.9,.1,.25,opacity,0)
                if not same_appearance(old[1:],desired) or use not in (None,0):
                    changed.append(snapshots[-1])
                    if api7 and use is not None:param.UseColor=0
                    elif use is not None:param.useColor=0
                    if not param.SetAdvancedColor(*desired):raise RuntimeError('Appearance setter failed')
                    if not obj.Update():raise RuntimeError('Appearance update failed')
                actual=param.GetAdvancedColor()
                if not actual[0] or actual[1]!=color or abs(actual[6]-opacity)>1e-8:raise RuntimeError('Appearance readback failed')
            # TopPart is independently reacquired to avoid reading only a transient setter proxy.
            if scope=='document':
                actual=self._color7(self.api7.IKompasDocument3D(self._model_doc(document_id)).TopPart).GetAdvancedColor()
                if actual[1]!=color or abs(actual[6]-opacity)>1e-8:raise RuntimeError('Independent appearance readback failed')
        except Exception as error:
            rollback=[]
            for obj,param,api7,old,use in reversed(changed):
                try:
                    if use is not None:
                        if api7:param.UseColor=use
                        else:param.useColor=use
                    if not param.SetAdvancedColor(*old[1:]):raise RuntimeError('Rollback setter failed')
                    if not obj.Update():raise RuntimeError('Rollback update failed')
                    restored=param.GetAdvancedColor()
                    if not same_appearance(restored[1:],old[1:]):raise RuntimeError('Rollback readback mismatch')
                except Exception as failure:rollback.append(str(failure))
            if rollback:raise RuntimeError(f'Appearance failed; rollback incomplete: {rollback}') from error
            raise
        return {'scope':scope,'color':color,'color_format':'COLORREF 0x00BBGGRR','transparency_percent':transparency_percent,'targets_verified':len(targets),'changed_targets':len(changed)}

    def set_model_orientation(self,document_id: str,projection: Literal['front','top','left','isometric','front_isometric']='front_isometric') -> dict:
        """Select a reusable native camera projection; no computer use. front_isometric shows the negative-Y front of the model. Does not transform model geometry."""
        if projection=='front_isometric':
            r=math.sqrt(.5);s=math.sqrt(1/6);t=math.sqrt(2/3);u=math.sqrt(1/3)
            matrix=[r,r,0.,0.,-s,s,t,0.,u,-u,u,0.,0.,0.,0.,1.]
        else:matrix=projection_matrix(projection)
        from win32com.client import VARIANT
        doc=self._model5(document_id);coll=doc.GetViewProjectionCollection();name='MCP '+projection
        old=next((coll.GetByIndex(i) for i in range(coll.GetCount()) if coll.GetByIndex(i).IsCurrent()),None)
        view=coll.GetByName(name)
        if view is None:
            view=coll.NewViewProjection();view.name=name
            if not view.SetMatrix3D(VARIANT(self.com.VT_ARRAY|self.com.VT_R8,matrix)):raise RuntimeError('Native orientation matrix failed')
            if not coll.Add(view):raise RuntimeError('Native orientation registration failed')
        try:
            if not view.IsCurrent() and not view.SetCurrent():raise RuntimeError('Native orientation activation failed')
            if not view.IsCurrent():raise RuntimeError('Native orientation readback failed')
            doc.ZoomPrevNextOrAll(2)
        except Exception:
            if old is not None:old.SetCurrent()
            raise
        return {'projection':projection,'native_name':view.name,'matrix':matrix,'geometry_transformed':False}
