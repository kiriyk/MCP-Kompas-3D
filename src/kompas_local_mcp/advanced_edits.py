"""Additional native edits and exact bounds for line/circular-arc boundaries."""
import math
from typing import Literal
from .core import finite
from .edits import apply_properties

def arc_points(x,y,r,start,end,clockwise):
    start%=360;end%=360
    sweep=(start-end)%360 if clockwise else (end-start)%360
    if sweep==0:raise ValueError('Ambiguous zero/full-circle arc boundary')
    angles=[start,end]
    for angle in (0,90,180,270):
        distance=(start-angle)%360 if clockwise else (angle-start)%360
        if distance<=sweep+1e-8:angles.append(angle)
    return [[x+r*math.cos(math.radians(t)),y+r*math.sin(math.radians(t))] for t in angles]

class AdvancedEdits:
    def set_object_properties(self,document_id: str,reference: str,angle: float | None=None,style: int | None=None) -> dict:
        """Set absolute angle for a rectangle and/or standard line style 1..9 for geometric primitives. Text, contours, Beziers, hatches and dimensions are excluded. Retains origin/reference; rollback on failure."""
        values={}
        if angle is not None:values['Angle']=finite(angle,'angle')%360
        if style is not None:
            if isinstance(style,bool) or not isinstance(style,int) or not 1<=style<=9:raise ValueError('Standard style must be an integer 1..9')
            values['Style']=style
        if not values:raise ValueError('Provide angle and/or style')
        allowed=('rectangle',) if angle is not None else ('rectangle','line','circle','arc','polyline')
        obj=None
        for kind in allowed:
            try:obj=self._find_native_object(document_id,reference,kind);break
            except ValueError:continue
        if obj is None:raise ValueError('Unsupported property/object combination')
        apply_properties(obj,values)
        return {'updated':True,'api_reference':obj.Reference,'properties':{k:getattr(obj,k) for k in values}}

    def _find_dimension(self,document_id,reference):
        ref=self._checked_reference(document_id,reference);views=self._views(document_id)
        for i in range(views.Count):
            coll=self.api7.ISymbols2DContainer(views.View(i)).LineDimensions
            for j in range(coll.Count):
                obj=coll.Item(j)
                if obj.Reference==ref:return self.api7.ILineDimension(obj)
        raise ValueError('Reference is not a native linear dimension')

    def edit_linear_dimension(self,document_id: str,reference: str,x1: float,y1: float,x2: float,y2: float,x3: float,y3: float,orientation: Literal['horizontal','vertical','parallel'] | None=None) -> dict:
        """Update existing native linear dimension endpoints and offset in owner-mm. Orientation None retains it. KOMPAS may reposition text along the dimension line. Does not resize geometry."""
        values={k:finite(v,k) for k,v in dict(X1=x1,Y1=y1,X2=x2,Y2=y2,X3=x3,Y3=y3).items()}
        if orientation is not None:
            if orientation not in ('horizontal','vertical','parallel'):raise ValueError('Invalid dimension orientation')
            values['Orientation']={'horizontal':1,'vertical':2,'parallel':0}[orientation]
        obj=self._find_dimension(document_id,reference);orient=values.get('Orientation',obj.Orientation)
        if (x1==x2 and y1==y2) or (orient==1 and x1==x2) or (orient==2 and y1==y2):raise ValueError('Zero dimension measurement')
        verify={'X1','Y1','X2','Y2','Orientation'}
        if orient==1:verify.add('Y3')
        elif orient==2:verify.add('X3')
        def check_offset():
            if orient!=0:return
            dx=x2-x1;dy=y2-y1;length=math.hypot(dx,dy)
            requested=(dx*(y3-y1)-dy*(x3-x1))/length
            actual=(dx*(obj.Y3-y1)-dy*(obj.X3-x1))/length
            if abs(actual-requested)>1e-6:raise RuntimeError('Dimension offset postcondition failed')
        apply_properties(obj,values,verify,check_offset)
        dim=self.api7.IDimensionText(obj._oleobj_.QueryInterface(self.api7.IDimensionText.CLSID,self.com.IID_IDispatch))
        return {'updated':True,'api_reference':obj.Reference,'orientation':obj.Orientation,'points':[[obj.X1,obj.Y1],[obj.X2,obj.Y2],[obj.X3,obj.Y3]],'nominal_value':dim.NominalValue}

    def get_object_boundaries(self,document_id: str,reference: str) -> dict:
        """Read native contour or hatch boundaries and exact union bounds in owner-mm (no stroke width). Supports lines and circular arcs; rejects other segment types. No CAD mutation."""
        obj=None
        for kind in ('contour','hatch'):
            try:obj=self._find_native_object(document_id,reference,kind);break
            except ValueError:continue
        if obj is None:raise ValueError('Reference must be a contour or hatch')
        if kind=='hatch':
            raw=self.api7.IBoundariesObject(obj._oleobj_.QueryInterface(self.api7.IBoundariesObject.CLSID,self.com.IID_IDispatch)).Boundaries
        else:raw=[obj]
        loops=[];pts=[];total=0
        for boundary in raw:
            contour=self.api7.IContour(boundary._oleobj_.QueryInterface(self.api7.IContour.CLSID,self.com.IID_IDispatch))
            total+=contour.Count
            if total>10000:raise ValueError('Boundary exceeds 10000 segments')
            segments=[]
            for i in range(contour.Count):
                seg=contour.Segment(i)
                try:
                    line=self.api7.IContourLineSegment(seg._oleobj_.QueryInterface(self.api7.IContourLineSegment.CLSID,self.com.IID_IDispatch))
                except self.com.com_error:
                    try:arc=self.api7.IContourArc(seg._oleobj_.QueryInterface(self.api7.IContourArc.CLSID,self.com.IID_IDispatch))
                    except self.com.com_error as error:raise ValueError('Unsupported boundary segment') from error
                    record={'type':'arc','center':[arc.Xc,arc.Yc],'radius':arc.Radius,'angles':[arc.Angle1,arc.Angle2],'clockwise':bool(arc.Direction)}
                    pts.extend(arc_points(arc.Xc,arc.Yc,arc.Radius,arc.Angle1,arc.Angle2,arc.Direction))
                else:
                    record={'type':'line','points':[[line.X1,line.Y1],[line.X2,line.Y2]]};pts.extend(record['points'])
                segments.append(record)
            loops.append({'closed':bool(contour.Closed),'segments':segments})
        if not pts:raise ValueError('Empty boundary')
        left=min(p[0] for p in pts);bottom=min(p[1] for p in pts);right=max(p[0] for p in pts);top=max(p[1] for p in pts)
        return {'api_reference':obj.Reference,'type':kind,'boundaries':loops,'bounds':{'left':left,'bottom':bottom,'right':right,'top':top,'width':right-left,'height':top-bottom}}
