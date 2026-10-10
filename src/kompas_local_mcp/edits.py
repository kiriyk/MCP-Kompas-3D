"""Native edits preserve object identity, layers and unrelated geometry."""
from .core import positive,finite

def checked_resize(width,height):return {'Width':positive(width,'width'),'Height':positive(height,'height')}

def apply_properties(obj,values,verify_names=None,postcheck=None):
    before={name:getattr(obj,name) for name in values}
    try:
        for name,value in values.items():setattr(obj,name,value)
        if not obj.Update():raise RuntimeError('Update failed')
        for name,value in values.items():
            if verify_names is not None and name not in verify_names:continue
            actual=getattr(obj,name)
            if isinstance(value,(int,float)):
                if abs(actual-value)>1e-6:raise RuntimeError(f'{name} postcondition failed')
            elif actual!=value:raise RuntimeError(f'{name} postcondition failed')
        if postcheck:postcheck()
    except Exception as error:
        failed=[]
        for name,value in before.items():
            try:setattr(obj,name,value)
            except Exception:failed.append(name)
        try:
            if not obj.Update():failed.append('Update')
        except Exception:failed.append('Update')
        if failed:raise RuntimeError(f'{error}; rollback failed for {failed}; inspect before retrying') from error
        raise

class NativeEdits:
    def _find_native_object(self,document_id,reference,kind=None):
        ref=self._checked_reference(document_id,reference)
        views=self._views(document_id)
        mapping={'rectangle':('Rectangles','IRectangle'),'text':('DrawingTexts','IDrawingText'),'line':('LineSegments','ILineSegment'),'circle':('Circles','ICircle'),'arc':('Arcs','IArc'),'polyline':('PolyLines2D','IPolyLine2D'),'contour':('DrawingContours','IDrawingContour'),'bezier':('Beziers','IBezier'),'hatch':('Hatches','IHatch')}
        for i in range(views.Count):
            view=views.View(i);container=self.api7.IDrawingContainer(view)
            for name,(collection,interface) in mapping.items():
                if kind and kind!=name:continue
                objects=getattr(container,collection)
                for j in range(objects.Count):
                    raw=objects.Item(j)
                    if raw.Reference==ref:return getattr(self.api7,interface)(raw)
        raise ValueError(f'Object is not a supported {kind or "edit"} type')

    def resize_rectangle(self,document_id: str,reference: str,width: float,height: float) -> dict:
        """Change an existing rectangle in place; retain its origin, angle, layer and reference."""
        values=checked_resize(width,height);obj=self._find_native_object(document_id,reference,'rectangle')
        apply_properties(obj,values)
        return {'updated':True,'api_reference':obj.Reference,'width':obj.Width,'height':obj.Height}

    def edit_text(self,document_id: str,reference: str,value: str) -> dict:
        """Replace native text in place, keeping position and font. Use nonempty single-line text."""
        if not value or '\n' in value or '\r' in value:raise ValueError('Nonempty single-line text required')
        obj=self._find_native_object(document_id,reference,'text');text=self.api7.IText(obj)
        if text.Count!=1 or text.TextLine(0).Count!=1:raise ValueError('Only one plain text run is supported; complex source formatting is retained unchanged')
        before=text.Str
        font_names=('FontName','Height','WidthFactor','Color','Bold','Italic','Underline','TextLineStep')
        item=text.TextLine(0).TextItem(0)
        font=self.api7.ITextFont(item._oleobj_.QueryInterface(self.api7.ITextFont.CLSID,self.com.IID_IDispatch))
        saved={name:getattr(font,name) for name in font_names}
        def replace(string):
            # Replace retains the existing run; assigning Str resets persistent font/style.
            if not text.Replace(text.Str,string,True,False,True) or not obj.Update():raise RuntimeError('Text Replace/Update failed')
            current=text.TextLine(0).TextItem(0)
            fmt=self.api7.ITextFont(current._oleobj_.QueryInterface(self.api7.ITextFont.CLSID,self.com.IID_IDispatch))
            if text.Str!=string or any(getattr(fmt,k)!=v for k,v in saved.items()):raise RuntimeError('Text/font postcondition failed')
        try:replace(value)
        except Exception as error:
            try:replace(before)
            except Exception as rollback:raise RuntimeError(f'{error}; text rollback failed: {rollback}') from error
            raise
        return {'updated':True,'api_reference':obj.Reference,'value':text.Str}

    def move_objects(self,document_id: str,references: list[str],dx: float,dy: float) -> dict:
        """Move a room/module: walls, hatches, equipment, labels and dimensions together in one view. No persistent grouping."""
        dx=finite(dx,'dx');dy=finite(dy,'dy')
        if not references:raise ValueError('No objects to move')
        refs=list(dict.fromkeys(self._checked_reference(document_id,t) for t in references))
        listed=self.list_objects(document_id,limit=10000)
        if listed['truncated']:raise ValueError('Move lookup exceeds 10000 objects')
        chosen=[o for o in listed['items'] if o['api_reference'] in refs]
        if len(chosen)!=len(refs) or len({o['view'] for o in chosen})!=1:raise ValueError('Move requires supported objects in one view')
        self.set_active_view(document_id,chosen[0]['view']);native=self._a5(document_id);group=native.ksNewGroup(1)
        if not group:raise RuntimeError('Could not create move group')
        try:
            try:
                for ref in refs:
                    if not native.ksAddObjGroup(group,ref):raise RuntimeError('Could not add move member')
            finally:native.ksEndGroup()
            if not native.ksMoveObj(group,dx,dy):raise RuntimeError(f'Group move failed; inspect API references {refs} before retrying')
            if not all(native.ksExistObj(ref) for ref in refs):raise RuntimeError('Move member disappeared')
            return {'moved':len(refs),'api_references':refs,'dx':dx,'dy':dy}
        finally:
            if not native.ksClearGroup(group,True):raise RuntimeError(f'Temporary move group {group} cleanup failed; inspect before retrying')
