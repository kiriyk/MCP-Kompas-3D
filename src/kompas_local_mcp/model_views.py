"""Native associative projections and straight section views from saved models."""
import math
from pathlib import Path
from typing import Literal
from .core import positive,finite,windows_path
from .model_documents import model_name

def projection_matrix(name):
    r=math.sqrt(.5);s=math.sqrt(1/6);t=math.sqrt(2/3);u=math.sqrt(1/3)
    rows={'front':([1,0,0],[0,0,1],[0,-1,0]),'top':([1,0,0],[0,1,0],[0,0,1]),'left':([0,1,0],[0,0,1],[1,0,0]),'isometric':([r,-r,0],[s,s,t],[-u,-u,u])}
    if name not in rows:raise ValueError('Expected front, top, left or isometric')
    return [float(x) for row in rows[name] for x in (*row,0)]+[0.,0.,0.,1.]

class ModelViews:
    def create_model_view(self,document_id: str,model_path: str,projection: Literal['front','top','left','isometric'],name: str,x: float,y: float,scale: float=1) -> dict:
        """Linked view: front=XZ, top=XY, left=YZ; position in sheet mm, scale coefficient."""
        scale=positive(scale,'scale');x=finite(x,'x');y=finite(y,'y');name=model_name(name);matrix=projection_matrix(projection)
        model_path=windows_path(model_path)
        if Path(model_path).suffix.lower() not in ('.m3d','.a3d') or not Path(model_path).is_file():raise ValueError('A saved native model is required')
        from win32com.client import VARIANT
        v=self._views(document_id).Add(2)
        try:
            av=self.api7.IAssociationView(v);av.SourceFileName=model_path
            av.ProjectionMatrix=VARIANT(self.com.VT_ARRAY|self.com.VT_R8,matrix)
            av.Name=name;av.X=x;av.Y=y;av.Scale=scale;av.VisibleLinesStyle=1;av.HiddenLinesVisible=False
            if not av.Update() or not av.ObjectCount:raise RuntimeError('Linked model view did not produce geometry')
            if windows_path(av.SourceFileName).casefold()!=model_path.casefold() or abs(av.Scale-scale)>1e-8:raise RuntimeError('Model view postcondition failed')
            self._a5(document_id).ksOpenView(v.Number)
            return {'view_number':v.Number,**self._view(v),'source_path':av.SourceFileName,'projection':projection,'matrix':list(av.ProjectionMatrix)}
        except Exception:
            v.Delete();raise

    def create_section_view(self,document_id: str,base_view_number: int,points: list[list[float]],name: str,x: float,y: float,scale: float=1) -> dict:
        """Linked straight section. Two points in base-view mm; section origin in sheet mm."""
        scale=positive(scale,'scale');x=finite(x,'x');y=finite(y,'y');name=model_name(name)
        if len(points)!=2 or any(len(p)!=2 for p in points):raise ValueError('A straight section requires two XY points')
        pts=[[finite(v,'point') for v in p] for p in points]
        if math.dist(*pts)<1e-8:raise ValueError('Section line must have nonzero length')
        views=self._views(document_id);base=views.ViewByNumber(base_view_number)
        if base is None or base.ViewType not in (2,3,4):raise ValueError('A linked base view is required')
        source=self.api7.IAssociationView(base).SourceFileName
        if not source:raise ValueError('Base view has no model link')
        from win32com.client import VARIANT
        cut=self.api7.ISymbols2DContainer(base).CutLines.Add();section=None
        try:
            cut.Points=VARIANT(self.com.VT_ARRAY|self.com.VT_R8,[v for p in pts for v in p]);cut.ArrowPos=True;cut.ArrowType=1
            cut.X1=pts[0][0];cut.Y1=pts[0][1]-8/scale;cut.X2=pts[1][0];cut.Y2=pts[1][1]+8/scale;cut.Text.Str=name
            if not cut.Update() or not cut.Reference:raise RuntimeError('Native section line failed')
            section=views.Add(7);av=self.api7.IAssociationView(section)
            av.SourceFileName=source;av.BaseView=base;av.BaseObject=cut;av.Section=True;av.UseOcclusion=False;av.Name=f'{name}-{name}';av.X=x;av.Y=y;av.Scale=scale
            if not av.Update() or not av.ObjectCount:raise RuntimeError('Section view produced no geometry')
            self._a5(document_id).ksOpenView(section.Number)
            return {'view_number':section.Number,**self._view(section),'source_path':av.SourceFileName,'base_view_number':base.Number,'section':True,'cut_points':list(cut.Points)}
        except Exception:
            if section is not None:section.Delete()
            cut.Delete();raise

    def model_view_state(self,document_id: str) -> dict:
        """Read persisted source links and projected line/circle bounds in view mm."""
        views=self._views(document_id);result=[]
        for i in range(views.Count):
            v=views.View(i)
            if v.ViewType not in (2,3,4,5,7):continue
            av=self.api7.IAssociationView(v);item={**self._view(v),'source_path':av.SourceFileName,'section':bool(av.Section),'view_type':v.ViewType}
            container=self.api7.IDrawingContainer(v);pts=[]
            for j in range(container.LineSegments.Count):
                line=self.api7.ILineSegment(container.LineSegments.Item(j));pts.extend([[line.X1,line.Y1],[line.X2,line.Y2]])
            for j in range(container.Circles.Count):
                c=self.api7.ICircle(container.Circles.Item(j));pts.extend([[c.X-c.Radius,c.Y-c.Radius],[c.X+c.Radius,c.Y+c.Radius]])
            item['projected_bounds_mm']=None if not pts else {'min':[min(p[k] for p in pts) for k in range(2)],'max':[max(p[k] for p in pts) for k in range(2)]}
            if v.ViewType==7:
                item['base_view_number']=av.BaseView.Number if av.BaseView else None
                if av.BaseObject:item['cut_points']=list(self.api7.ICutLine(av.BaseObject).Points)
            else:item['matrix']=list(av.ProjectionMatrix) if av.ProjectionMatrix else None
            result.append(item)
        return {'views':result,'count':len(result)}

    def update_model_views(self,document_id: str) -> dict:
        """Update linked base views before sections and read resulting source links/bounds."""
        self._a5(document_id).ksRebuildDocument()
        state=self.model_view_state(document_id)
        for v in state['views']:
            if not v['source_path'] or not Path(v['source_path']).is_file() or not v['object_count'] or v['scale']<=0:raise RuntimeError(f'View {v["number"]} rebuild postcondition failed')
        return state
