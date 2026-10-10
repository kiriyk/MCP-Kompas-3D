"""Typed SDK adapter. This instance belongs exclusively to the STA worker."""
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from typing import Literal
from .core import ReferenceStore, finite, positive, windows_path, sheet_point, verified_output
from .features import NativeFeatures

from .io_features import NativeIO

class Adapter(NativeFeatures, NativeIO):
    def __init__(self):
        import pythoncom
        self.com=pythoncom;pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        self.app=None;self.docs={};self.refs=ReferenceStore()

    def shutdown(self):
        self.docs.clear();self.app=None
        self.com.CoUninitialize()

    def connect(self, executable: str | None = None, launch: bool = False) -> dict:
        """Connect to KOMPAS v21 using installed SDK. Set KOMPAS_EXECUTABLE or pass executable."""
        if self.app is not None:return {'connected':True,'session':self.refs.session}
        import win32com,win32com.client,win32com.gen_py
        from win32com.client import gencache
        executable=executable or os.environ.get('KOMPAS_EXECUTABLE')
        sdk=os.environ.get('KOMPAS_SDK')
        if executable:
            executable=windows_path(executable)
            if not Path(executable).is_file():raise ValueError('KOMPAS executable not found')
            sdk=sdk or str(Path(executable).parent.parent/'SDK')
        if not sdk:raise ValueError('Set KOMPAS_EXECUTABLE or KOMPAS_SDK for your v21 installation')
        lib=Path(sdk)/'lib'
        if not all((lib/f).is_file() for f in ('kAPI5.tlb','kAPI7.tlb')):raise ValueError('SDK type libraries not found')
        cache=Path(os.environ.get('KOMPAS_MCP_CACHE',str(Path(tempfile.gettempdir())/'kompas-local-mcp-cache')))
        cache.mkdir(parents=True,exist_ok=True)
        win32com.__gen_path__=str(cache);win32com.gen_py.__path__=[str(cache)]
        try:ole=self.com.GetActiveObject('Kompas.Application.5').QueryInterface(self.com.IID_IDispatch)
        except self.com.com_error:
            if not launch or not executable:raise RuntimeError('KOMPAS is not running. Call connect(launch=True, executable=...)')
            subprocess.Popen([executable],cwd=str(Path(executable).parent))
            deadline=time.monotonic()+30
            while True:
                try:ole=self.com.GetActiveObject('Kompas.Application.5').QueryInterface(self.com.IID_IDispatch);break
                except self.com.com_error:
                    if time.monotonic()>deadline:raise RuntimeError('KOMPAS launch timed out')
                    time.sleep(.25)
        self.api5=gencache.EnsureModuleForTypelibInterface(self.com.LoadTypeLib(str(lib/'kAPI5.tlb')))
        self.api7=gencache.EnsureModuleForTypelibInterface(self.com.LoadTypeLib(str(lib/'kAPI7.tlb')))
        self.executable=executable;self.sdk=sdk
        self.app=self.api5.KompasObject(ole)
        self.app7=self.api7.IApplication(self.app.ksGetApplication7())
        return {'connected':True,'session':self.refs.session,'sdk':str(lib),'document_count':self.app7.Documents.Count}

    def _ready(self):
        if self.app is None:raise RuntimeError('Call connect first')

    def _register(self,document):
        token=uuid.uuid4().hex;self.docs[token]=document
        return {'document_id':token,'name':document.Name,'path':document.PathName}

    def _doc(self,document_id):
        self._ready();doc=self.docs.get(document_id)
        if doc is None:raise ValueError('Unknown or closed document_id')
        if doc.DocumentType!=1:raise ValueError('A 2D drawing is required')
        doc.Active=True
        return doc

    def _views(self,document_id):
        return self.api7.IKompasDocument2D(self._doc(document_id)).ViewsAndLayersManager.Views

    def _a5(self,document_id):
        self._doc(document_id)
        return self.api5.ksDocument2D(self.app.ActiveDocument2D())

    def _container(self,document_id):
        return self.api7.IDrawingContainer(self._views(document_id).ActiveView)

    def _ref(self,document_id,ref):
        if not ref:raise RuntimeError('API did not create an object')
        return {'reference':self.refs.add(document_id,int(ref)),'api_reference':int(ref)}

    def _update(self,document_id,obj,**properties):
        try:
            layers=self._views(document_id).ActiveView.Layers;target_layer=0
            for i in range(layers.Count):
                layer=layers.Layer(i)
                if layer.Current:target_layer=layer.LayerNumber
            for name,value in properties.items():setattr(obj,name,value)
            if not obj.Update():raise RuntimeError('Object Update failed')
            self._a5(document_id).ksChangeObjectLayer(obj.Reference,target_layer)
            if obj.LayerNumber!=target_layer:raise RuntimeError(f'Object layer postcondition failed: expected {target_layer}, got {obj.LayerNumber}')
            return self._ref(document_id,obj.Reference)
        except Exception:
            obj.Delete();raise

    def create_drawing(self) -> dict:
        """Create a separate visible drawing, never reuse the active user document."""
        self._ready();return self._register(self.app7.Documents.AddWithDefaultSettings(1,True))

    def open_document(self,path: str) -> dict:
        """Open or reuse a saved drawing and issue fresh session references."""
        self._ready();path=windows_path(path)
        if not Path(path).is_file():raise ValueError('File not found')
        for token,doc in self.docs.items():
            if doc.PathName and windows_path(doc.PathName).casefold()==path.casefold():return {'document_id':token,'path':doc.PathName,'reused':True}
        return self._register(self.app7.Documents.Open(path,True,False))

    def close_document(self,document_id: str) -> dict:
        """Close a registered document WITHOUT saving. Save explicitly first."""
        doc=self._doc(document_id)
        doc.Close(0);self.docs.pop(document_id);self.refs.invalidate(document_id)
        return {'closed':True}

    def save_document(self,document_id: str,path: str) -> dict:
        """Save with a normalized absolute Windows path and verify file/path postconditions."""
        doc=self._doc(document_id);path=windows_path(path)
        if Path(path).suffix.lower()!='.cdw':raise ValueError('Expected .cdw extension')
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        stage=Path(path).with_name(f'{Path(path).stem}.{uuid.uuid4().hex}.cdw')
        doc.SaveAs(str(stage))
        if not stage.is_file() or stage.stat().st_size==0 or windows_path(doc.PathName).casefold()!=str(stage).casefold():
            raise RuntimeError('Fresh saved document was not produced')
        target=Path(path)
        before=target.stat().st_mtime_ns if target.exists() else None
        doc.SaveAs(path)
        if not target.is_file() or target.stat().st_size==0 or target.stat().st_mtime_ns==before or windows_path(doc.PathName).casefold()!=path.casefold():
            raise RuntimeError(f'Save postcondition failed; recovery copy: {stage}')
        stage.unlink()
        return {'saved':True,'path':path,'bytes':Path(path).stat().st_size}

    def set_sheet(self,document_id: str,format: Literal['A0','A1','A2','A3','A4']='A0',landscape: bool=True) -> dict:
        """Set standard sheet format and verify actual dimensions (Update may return false)."""
        doc=self._doc(document_id);sheet=doc.LayoutSheets.Item(0);fmt=sheet.Format
        code={'A0':0,'A1':1,'A2':2,'A3':3,'A4':4}[format]
        fmt.Format=code;fmt.FormatMultiplicity=1;fmt.VerticalOrientation=not landscape
        raw=sheet.Update()
        result=self._sheet(doc);result['update_return']=bool(raw)
        if fmt.Format!=code or bool(fmt.VerticalOrientation)==landscape:raise RuntimeError('Sheet postcondition failed')
        return result

    def _sheet(self,doc):
        fmt=doc.LayoutSheets.Item(0).Format
        return {'format':{0:'A0',1:'A1',2:'A2',3:'A3',4:'A4'}.get(fmt.Format,str(fmt.Format)),
                'landscape':not bool(fmt.VerticalOrientation),'width':fmt.FormatWidth,'height':fmt.FormatHeight}

    def _view(self,v):
        return {'number':v.Number,'name':v.Name,'scale':v.Scale,'x':v.X,'y':v.Y,'angle':v.Angle,'active':bool(v.Current),'object_count':v.ObjectCount}

    def document_state(self,document_id: str) -> dict:
        """Read actual sheet and view settings, not cached request arguments."""
        doc=self._doc(document_id);views=self._views(document_id)
        return {'document_id':document_id,'name':doc.Name,'path':doc.PathName,'sheet':self._sheet(doc),
                'views':[self._view(views.View(i)) for i in range(views.Count)]}

    def create_view(self,document_id: str,name: str,scale: float=1,x: float=0,y: float=0,angle: float=0) -> dict:
        """Create and activate a view. Model coordinates are mm; scale is 0.02 for 1:50; angle in degrees."""
        scale=positive(scale,'scale');x=finite(x,'x');y=finite(y,'y');angle=finite(angle,'angle')
        v=self._views(document_id).Add(1)
        v.Name=name;v.X=x;v.Y=y;v.Scale=scale;v.Angle=angle;v.Current=True
        if not v.Update() or abs(v.Scale-scale)>1e-9:raise RuntimeError('View postcondition failed')
        return self._view(v)

    def set_active_view(self,document_id: str,view_number: int) -> dict:
        """Activate a view through API7 and verify the current number."""
        views=self._views(document_id);v=views.ViewByNumber(view_number)
        if v is None:raise ValueError('View not found')
        v.Current=True;v.Update()
        if views.ActiveView.Number!=view_number:self._a5(document_id).ksOpenView(view_number)
        if views.ActiveView.Number!=view_number:raise RuntimeError('Active view postcondition failed')
        return self._view(views.ActiveView)

    def view_to_sheet(self,document_id: str,view_number: int,x: float,y: float) -> dict:
        """Convert owner-view coordinates to sheet mm, including rotation and scale."""
        v=self._views(document_id).ViewByNumber(view_number)
        if v is None:raise ValueError('View not found')
        a,b=sheet_point(x,y,v.X,v.Y,v.Scale,v.Angle)
        return {'coordinate_space':'sheet','x':a,'y':b}

    def create_layer(self,document_id: str,name: str,number: int,color: int=0) -> dict:
        """Create and activate a layer in the current view. Color is Windows COLORREF."""
        layers=self._views(document_id).ActiveView.Layers
        if number<1:raise ValueError('Use a positive custom layer number')
        layer=layers.Add();layer.Name=name;layer.LayerNumber=number;layer.Color=color;layer.Current=True
        if not layer.Update():raise RuntimeError('Layer Update failed')
        return {'number':layer.LayerNumber,'name':layer.Name,'color':layer.Color,'current':bool(layer.Current)}

    def set_active_layer(self,document_id: str,number: int) -> dict:
        """Activate an existing layer in the current view."""
        layers=self._views(document_id).ActiveView.Layers;layer=layers.LayerByNumber(number)
        if layer is None:raise ValueError('Layer not found')
        layer.Current=True;layer.Update()
        return {'number':layer.LayerNumber,'current':bool(layer.Current)}

    def line(self,document_id: str,x1: float,y1: float,x2: float,y2: float,style: int=1) -> dict:
        """Draw a finite line segment in the active view (mm)."""
        values=[finite(v,n) for v,n in zip((x1,y1,x2,y2),('x1','y1','x2','y2'))]
        if values[:2]==values[2:]:raise ValueError('Zero length line')
        return self._ref(document_id,self._a5(document_id).ksLineSeg(*values,style))

    def rectangle(self,document_id: str,x: float,y: float,width: float,height: float,angle: float=0,style: int=1) -> dict:
        """Draw a rectangle, angle in degrees, dimensions in real mm."""
        properties=dict(X=finite(x,'x'),Y=finite(y,'y'),Width=positive(width,'width'),Height=positive(height,'height'),Angle=finite(angle,'angle'),Style=style)
        return self._update(document_id,self._container(document_id).Rectangles.Add(),**properties)

    def circle(self,document_id: str,x: float,y: float,radius: float,style: int=1) -> dict:
        """Draw a circle in real mm."""
        x=finite(x,'x');y=finite(y,'y');radius=positive(radius,'radius')
        return self._ref(document_id,self._a5(document_id).ksCircle(x,y,radius,style))

    def arc(self,document_id: str,x: float,y: float,radius: float,start_angle: float,end_angle: float,style: int=1) -> dict:
        """Draw a counterclockwise arc with degree angles, e.g. a door swing."""
        properties=dict(Xc=finite(x,'x'),Yc=finite(y,'y'),Radius=positive(radius,'radius'),Angle1=finite(start_angle,'start_angle'),Angle2=finite(end_angle,'end_angle'),Direction=False,Style=style)
        return self._update(document_id,self._container(document_id).Arcs.Add(),**properties)

    def text(self,document_id: str,x: float,y: float,value: str,height: float=3.5,angle: float=0,font: str='Arial') -> dict:
        """Create native text. Height is paper text height in mm; x/y are model coordinates."""
        x=finite(x,'x');y=finite(y,'y');height=positive(height,'height');angle=finite(angle,'angle')
        if not value:raise ValueError('Empty text')
        if not font:raise ValueError('Empty font name')
        raw=self._a5(document_id).ksText(x,y,angle,height,1,0,value)
        if not raw:raise RuntimeError('Text creation failed')
        try:
            collection=self._container(document_id).DrawingTexts
            obj=next(collection.Item(i) for i in range(collection.Count) if collection.Item(i).Reference==raw)
            text=self.api7.IText(obj._oleobj_.QueryInterface(self.api7.IText.CLSID,self.com.IID_IDispatch))
            item=text.TextLine(0).TextItem(0)
            fmt=self.api7.ITextFont(item._oleobj_.QueryInterface(self.api7.ITextFont.CLSID,self.com.IID_IDispatch))
            fmt.FontName=font;fmt.Italic=False
            if not item.Update() or not obj.Update():raise RuntimeError('Font Update failed')
            if fmt.FontName.casefold()!=font.casefold():raise RuntimeError('Font postcondition failed')
            return self._ref(document_id,raw)
        except Exception:
            self._a5(document_id).ksDeleteObj(raw);raise

    def linear_dimension(self,document_id: str,x1: float,y1: float,x2: float,y2: float,x3: float,y3: float,orientation: Literal['horizontal','vertical','parallel']='horizontal') -> dict:
        """Create a native linear dimension, not separate lines/text."""
        p={k:finite(v,k) for k,v in dict(X1=x1,Y1=y1,X2=x2,Y2=y2,X3=x3,Y3=y3).items()}
        obj=self.api7.ISymbols2DContainer(self._views(document_id).ActiveView).LineDimensions.Add()
        p['Orientation']={'horizontal':1,'vertical':2,'parallel':0}[orientation]
        return self._update(document_id,obj,**p)

    def hatch_rectangle(self,document_id: str,x: float,y: float,width: float,height: float,step: float=100,angle: float=45) -> dict:
        """Native rectangular hatch. Boundary in owner mm, hatch step in paper mm; angle degrees."""
        x=finite(x,'x');y=finite(y,'y');width=positive(width,'width');height=positive(height,'height');step=positive(step,'step');angle=finite(angle,'angle')
        doc=self._a5(document_id)
        if not doc.ksHatch(1,angle,step,0,x,y):raise RuntimeError('Could not start hatch')
        try:
            for a,b,c,d in [(x,y,x+width,y),(x+width,y,x+width,y+height),(x+width,y+height,x,y+height),(x,y+height,x,y)]:doc.ksLineSeg(a,b,c,d,0)
            ref=doc.ksEndObj()
        except Exception:
            doc.ksEndObj();raise
        if not ref or not doc.ksExistObj(ref):raise RuntimeError('Hatch postcondition failed')
        return self._ref(document_id,ref)

    def copy_object(self,document_id: str,reference: str,dx: float,dy: float) -> dict:
        """Copy a session-scoped object by a translation in owner mm."""
        ref=self._checked_reference(document_id,reference);dx=finite(dx,'dx');dy=finite(dy,'dy')
        return self._ref(document_id,self._a5(document_id).ksCopyObj(ref,0,0,dx,dy,1,0))

    def move_object(self,document_id: str,reference: str,dx: float,dy: float) -> dict:
        """Move an object by owner mm; stale or cross-document references are rejected."""
        ref=self._checked_reference(document_id,reference);dx=finite(dx,'dx');dy=finite(dy,'dy')
        if not self._a5(document_id).ksMoveObj(ref,dx,dy):raise RuntimeError('Move failed')
        return {'moved':True}

    def rotate_object(self,document_id: str,reference: str,x: float,y: float,angle: float) -> dict:
        """Rotate an object around owner x/y by angle in degrees."""
        ref=self._checked_reference(document_id,reference);x=finite(x,'x');y=finite(y,'y');angle=finite(angle,'angle')
        if not self._a5(document_id).ksRotateObj(ref,x,y,angle):raise RuntimeError('Rotate failed')
        return {'rotated':True}

    def delete_object(self,document_id: str,reference: str) -> dict:
        """Delete a session-scoped object and invalidate its token."""
        ref=self._checked_reference(document_id,reference);doc=self._a5(document_id)
        doc.ksDeleteObj(ref)
        if doc.ksExistObj(ref):raise RuntimeError('Delete postcondition failed')
        self.refs.invalidate_reference(document_id,ref)
        return {'deleted':True}

    def _checked_reference(self,document_id,reference):
        ref=self.refs.get(reference,document_id)
        if not self._a5(document_id).ksExistObj(ref):
            self.refs.invalidate_reference(document_id,ref)
            raise ValueError('Object no longer exists')
        return ref

    def list_objects(self,document_id: str,coordinate_space: Literal['owner','sheet']='owner',limit: int=5000) -> dict:
        """List supported native 2D objects with fresh references; point coordinates respect the requested space."""
        if not 1<=limit<=10000:raise ValueError('limit must be 1..10000')
        views=self._views(document_id);items=[]
        def point(v,x,y):return list(sheet_point(x,y,v.X,v.Y,v.Scale,v.Angle)) if coordinate_space=='sheet' else [x,y]
        for i in range(views.Count):
            v=views.View(i);container=self.api7.IDrawingContainer(v)
            collections=[('line',container.LineSegments),('rectangle',container.Rectangles),('circle',container.Circles),('arc',container.Arcs),('text',container.DrawingTexts),('hatch',container.Hatches),('polyline',container.PolyLines2D),('contour',container.DrawingContours),('bezier',container.Beziers),('linear_dimension',self.api7.ISymbols2DContainer(v).LineDimensions)]
            for kind,collection in collections:
                for j in range(collection.Count):
                    if len(items)>=limit:return {'coordinate_space':coordinate_space,'items':items,'truncated':True}
                    base=collection.Item(j)
                    cls={'line':'ILineSegment','rectangle':'IRectangle','circle':'ICircle','arc':'IArc','text':'IDrawingText','hatch':'IHatch','polyline':'IPolyLine2D','contour':'IDrawingContour','bezier':'IBezier','linear_dimension':'ILineDimension'}[kind]
                    obj=getattr(self.api7,cls)(base)
                    item={'type':kind,'view':v.Number,'layer_number':obj.LayerNumber,**self._ref(document_id,obj.Reference)}
                    if kind=='line':item['points']=[point(v,obj.X1,obj.Y1),point(v,obj.X2,obj.Y2)]
                    elif kind=='rectangle':
                        item['base']=point(v,obj.X,obj.Y);item['width']=obj.Width;item['height']=obj.Height;item['angle']=obj.Angle
                        a=math.radians(obj.Angle);w=obj.Width;h=obj.Height
                        item['corners']=[point(v,obj.X+dx*math.cos(a)-dy*math.sin(a),obj.Y+dx*math.sin(a)+dy*math.cos(a)) for dx,dy in [(0,0),(w,0),(w,h),(0,h)]]
                        if coordinate_space=='sheet':item['width']*=v.Scale;item['height']*=v.Scale;item['angle']+=v.Angle
                    elif kind in ('circle','arc'):
                        item['center']=point(v,obj.Xc,obj.Yc);item['radius']=obj.Radius*(v.Scale if coordinate_space=='sheet' else 1)
                        if kind=='arc':item['angles']=[obj.Angle1+(v.Angle if coordinate_space=='sheet' else 0),obj.Angle2+(v.Angle if coordinate_space=='sheet' else 0)]
                    elif kind=='text':
                        item['base']=point(v,obj.X,obj.Y);item['value']=self.api7.IText(obj).Str;item['height']=obj.Height;item['angle']=obj.Angle
                    elif kind=='linear_dimension':
                        item['points']=[point(v,obj.X1,obj.Y1),point(v,obj.X2,obj.Y2),point(v,obj.X3,obj.Y3)]
                        item['nominal_value']=self.api7.IDimensionText(obj).NominalValue
                    elif kind=='polyline':
                        flat=obj.Points
                        item['points']=[point(v,flat[k],flat[k+1]) for k in range(0,len(flat),2)]
                        item['closed']=bool(obj.Closed)
                    elif kind=='bezier':item['node_count']=obj.PointsCount;item['closed']=bool(obj.Closed)
                    items.append(item)
        return {'coordinate_space':coordinate_space,'items':items,'truncated':False}

    def export_png(self,document_id: str,path: str,dpi: int=100,color_mode: Literal['black','layer']='black') -> dict:
        """Export the native full drawing sheet to PNG; no screen capture fallback."""
        if not 40<=dpi<=300:raise ValueError('dpi must be 40..300')
        path=windows_path(path)
        if Path(path).suffix.lower()!='.png':raise ValueError('Expected .png extension')
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        doc=self._a5(document_id)
        param=self.api5.ksRasterFormatParam(doc.RasterFormatParam());param.Init()
        param.format=3;param.colorBPP=24;param.greyScale=False;param.extResolution=dpi;param.extScale=1;param.colorType={'black':1,'layer':2}[color_mode];param.onlyThinLine=False;param.pages='1';param.rangeIndex=0;param.saveWorkArea=False
        verified_output(path,lambda stage:doc.SaveAsToRasterFormat(stage,param),b'\x89PNG\r\n\x1a\n')
        return {'path':path,'bytes':Path(path).stat().st_size,'capture_mode':'native_sheet'}

PUBLIC_TOOLS=('connect','create_drawing','open_document','close_document','save_document','set_sheet','document_state','create_view','set_active_view','view_to_sheet','create_layer','set_active_layer','line','rectangle','circle','arc','text','linear_dimension','hatch_rectangle','copy_object','move_object','rotate_object','delete_object','list_objects','export_png','polyline','mixed_contour','bezier','mirror_object','linear_array','circular_array','hatch_polygon','export_pdf','get_selected_objects','copy_objects_to_document')
