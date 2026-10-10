"""Native CAD operations verified by direct API experiments before MCP exposure."""
import math
from kompas_local_mcp.core import finite,positive

class NativeFeatures:
    def polyline(self,document_id: str,points: list[list[float]],closed: bool=False,style: int=1) -> dict:
        """Create one native polyline from owner-mm vertices."""
        pts=self._points(points,3 if closed else 2)
        obj=self._container(document_id).PolyLines2D.Add()
        try:
            for i,(x,y) in enumerate(pts):
                if not obj.AddPoint(i,x,y):raise RuntimeError('Polyline vertex failed')
        except Exception:
            obj.Delete();raise
        return self._update(document_id,obj,Closed=closed,Style=style)

    def mixed_contour(self,document_id: str,segments: list[dict],style: int=1) -> dict:
        """One native contour containing lines and circular arcs, in owner mm/degrees."""
        if not 1<=len(segments)<=1000:raise ValueError('1..1000 segments required')
        prepared=[]
        for s in segments:
            if s.get('type')=='line':
                prepared.append(('line',[finite(s[k],k) for k in ('x1','y1','x2','y2')]))
            elif s.get('type')=='arc':
                prepared.append(('arc',[finite(s[k],k) for k in ('x','y')]+[positive(s['radius'],'radius')]+[finite(s[k],k) for k in ('start_angle','end_angle')]))
            else:raise ValueError('Segment type must be line or arc')
        doc=self._a5(document_id)
        commands=[(lambda p=p:doc.ksLineSeg(*p,style)) if kind=='line' else (lambda p=p:doc.ksArcByAngle(*p,1,style)) for kind,p in prepared]
        ref=self._compose(doc,lambda:doc.ksContour(style),commands,check_returns=False)
        try:
            collection=self._container(document_id).DrawingContours
            obj=next(collection.Item(i) for i in range(collection.Count) if collection.Item(i).Reference==ref)
            contour=self.api7.IContour(obj._oleobj_.QueryInterface(self.api7.IContour.CLSID,self.com.IID_IDispatch))
            if contour.Count!=len(prepared):raise RuntimeError('Incomplete contour segments')
        except Exception:
            doc.ksDeleteObj(ref);raise
        return self._ref(document_id,ref)

    def bezier(self,document_id: str,nodes: list[dict],closed: bool=False,style: int=1) -> dict:
        """Native Bezier nodes: x,y,angle,left,right; handle lengths in owner mm."""
        if not 2<=len(nodes)<=500:raise ValueError('2..500 nodes required')
        prepared=[]
        for node in nodes:
            p={k:finite(node.get(k,0),k) for k in ('x','y','angle','left','right')}
            if p['left']<0 or p['right']<0:raise ValueError('Handle lengths must be nonnegative')
            prepared.append(p)
        doc=self._a5(document_id)
        def add(p):
            param=self.api5.ksBezierPointParam(self.app.GetParamStruct(17));param.Init()
            param.x=p['x'];param.y=p['y'];param.ang=p['angle'];param.left=p['left'];param.right=p['right']
            return doc.ksBezierPoint(param)
        ref=self._compose(doc,lambda:doc.ksBezier(int(closed),style),[lambda p=p:add(p) for p in prepared])
        return self._ref(document_id,ref)

    def mirror_object(self,document_id: str,reference: str,x1: float,y1: float,x2: float,y2: float,copy: bool=True) -> dict:
        """Mirror about an owner-space axis. copy=False replaces the source and invalidates its handles."""
        axis=[finite(v,k) for v,k in zip((x1,y1,x2,y2),('x1','y1','x2','y2'))]
        if axis[:2]==axis[2:]:raise ValueError('Mirror axis must have length')
        ref=self._checked_reference(document_id,reference)
        result=self._a5(document_id).ksSymmetryObj(ref,*axis,'1' if copy else '0')
        if not result:raise RuntimeError('Mirror failed')
        if not copy:self.refs.invalidate_reference(document_id,ref)
        return self._ref(document_id,result)

    def linear_array(self,document_id: str,reference: str,count: int,dx: float,dy: float) -> dict:
        """Native copies along a line; count includes the unchanged original. Not an associative array."""
        self._array_count(count);dx=finite(dx,'dx');dy=finite(dy,'dy')
        if dx==dy==0:raise ValueError('Array step must have length')
        ref=self._checked_reference(document_id,reference)
        return self._batch_copies(document_id,[(ref,0,0,finite(i*dx,'dx'),finite(i*dy,'dy'),1,0) for i in range(1,count)],count)

    def circular_array(self,document_id: str,reference: str,count: int,x: float,y: float,sweep: float=360) -> dict:
        """Native copies about owner x/y; count includes source. Full circle excludes duplicate endpoint."""
        self._array_count(count);x=finite(x,'x');y=finite(y,'y');sweep=finite(sweep,'sweep')
        if sweep==0 or abs(sweep)>360:raise ValueError('Sweep must be nonzero and at most 360 degrees')
        ref=self._checked_reference(document_id,reference)
        step=sweep/(count if abs(sweep)==360 else count-1)
        return self._batch_copies(document_id,[(ref,x,y,x,y,1,i*step) for i in range(1,count)],count)

    def hatch_polygon(self,document_id: str,points: list[list[float]],step: float=3.5,angle: float=45) -> dict:
        """Native hatch of a simple polygon; step is paper mm, vertices owner mm."""
        pts=self._points(points,3);step=positive(step,'step');angle=finite(angle,'angle')
        doc=self._a5(document_id)
        ref=self._compose(doc,lambda:doc.ksHatch(1,angle,step,0,*pts[0]),[lambda a=a,b=b:doc.ksLineSeg(*a,*b,0) for a,b in zip(pts,pts[1:]+pts[:1])],check_returns=False)
        try:
            collection=self._container(document_id).Hatches
            obj=next(collection.Item(i) for i in range(collection.Count) if collection.Item(i).Reference==ref)
            boundary=self.api7.IBoundariesObject(obj._oleobj_.QueryInterface(self.api7.IBoundariesObject.CLSID,self.com.IID_IDispatch)).Boundaries
            if len(boundary)!=1:raise RuntimeError('Unexpected hatch boundary count')
            contour=self.api7.IContour(boundary[0]._oleobj_.QueryInterface(self.api7.IContour.CLSID,self.com.IID_IDispatch))
            if contour.Count!=len(pts):raise RuntimeError('Incomplete hatch polygon')
        except Exception:
            doc.ksDeleteObj(ref);raise
        return self._ref(document_id,ref)

    def _batch_copies(self,document_id,parameters,count):
        doc=self._a5(document_id);created=[]
        try:
            for p in parameters:
                ref=doc.ksCopyObj(*p)
                if not ref:raise RuntimeError('Array copy failed')
                created.append(ref)
        except Exception as original:
            failed=[]
            for ref in created:
                try:
                    doc.ksDeleteObj(ref)
                    if doc.ksExistObj(ref):failed.append(ref)
                except Exception:failed.append(ref)
            if failed:raise RuntimeError(f'Array failed: {original}; rollback incomplete, remaining API references: {failed}') from original
            raise
        return {'copies':[self._ref(document_id,r) for r in created],'total_count':count}

    @staticmethod
    def _compose(doc,start,commands,check_returns=True):
        if not start():raise RuntimeError('Composite start failed')
        ended=False
        try:
            for command in commands:
                result=command()
                if check_returns and not result:raise RuntimeError('Composite member failed')
            ref=doc.ksEndObj();ended=True
            if not ref or not doc.ksExistObj(ref):raise RuntimeError('Composite end failed')
            return ref
        except Exception:
            if not ended:
                ref=doc.ksEndObj()
                if ref:doc.ksDeleteObj(ref)
            raise

    @staticmethod
    def _points(points,minimum):
        if not minimum<=len(points)<=1000:raise ValueError(f'{minimum}..1000 points required')
        pts=[]
        for point in points:
            if len(point)!=2:raise ValueError('Each point must contain x,y')
            pts.append([finite(point[0],'x'),finite(point[1],'y')])
        if any(a==b for a,b in zip(pts,pts[1:])):raise ValueError('Repeated adjacent vertices')
        return pts

    @staticmethod
    def _array_count(count):
        if isinstance(count,bool) or not isinstance(count,int) or not 2<=count<=500:raise ValueError('count must be an integer in 2..500')
