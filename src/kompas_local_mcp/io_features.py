"""Native KOMPAS PDF conversion and object transfer. No clipboard or PDF writer."""
from pathlib import Path
from typing import Literal
from .core import positive, finite, windows_path, verified_output

PAPERS={'A0':(1189,841),'A1':(841,594),'A2':(594,420),'A3':(420,297),'A4':(297,210)}

def pdf_layout(width,height,paper,landscape):
    width=positive(width,'sheet width');height=positive(height,'sheet height')
    if paper=='sheet':return width,height,1.0
    if paper not in PAPERS:raise ValueError('Unsupported paper')
    w,h=PAPERS[paper]
    if not landscape:w,h=h,w
    return w,h,min(w/width,h/height)

class NativeIO:
    def export_pdf(self,document_id: str,path: str,paper: Literal['sheet','A0','A1','A2','A3','A4']='sheet',landscape: bool=True,color: bool=True) -> dict:
        """Export a saved, unchanged single-sheet CDW via KOMPAS Pdf2d.dll. Fit paper without changing the drawing format."""
        doc=self._doc(document_id);path=windows_path(path)
        if Path(path).suffix.lower()!='.pdf':raise ValueError('Expected .pdf extension')
        if not doc.PathName or doc.Changed:raise ValueError('Save the document before PDF export')
        if doc.LayoutSheets.Count!=1:raise ValueError('PDF fit currently supports a single sheet')
        sheet=self._sheet(doc);w,h,scale=pdf_layout(sheet['width'],sheet['height'],paper,landscape)
        from win32com.client import gencache
        folder=Path(self.executable).parent if self.executable else Path(self.sdk).parent/'Bin'
        if not all((folder/name).is_file() for name in ('Pdf2d.tlb','Pdf2d.dll')):raise RuntimeError('KOMPAS PDF converter not installed')
        module=gencache.EnsureModuleForTypelibInterface(self.com.LoadTypeLib(str(folder/'Pdf2d.tlb')))
        converter=self.app7.Converter(str(folder/'Pdf2d.dll'))
        raw=converter.ConverterParameters(0)
        params=module.IPdf2dParam(raw._oleobj_.QueryInterface(module.IPdf2dParam.CLSID,self.com.IID_IDispatch))
        values=dict(EmbedFonts=True,GrayScale=False,ColorType=2 if color else 1,MultiPageOutput=True,
                    PageRange=0,FilterDisable=True,UserFormat=paper!='sheet',HorizontOrientation=w>h,
                    ISOid=4,MultipleFormat=1,WidthUserSheet=w,HeightUserSheet=h,Scale=scale,CutByFormat=True)
        saved={key:getattr(params,key) for key in values}
        try:
            for key,value in values.items():setattr(params,key,value)
            def write(stage):
                if converter.Convert(doc.PathName,stage,0,False)!=1:raise RuntimeError('KOMPAS PDF converter failed')
            size=verified_output(path,write,b'%PDF-')
        finally:
            for key,value in saved.items():setattr(params,key,value)
        if self._sheet(doc)!=sheet:raise RuntimeError('Source sheet changed during export')
        return {'path':path,'bytes':size,'converter':'KOMPAS Pdf2d.dll','paper':paper,'width_mm':w,'height_mm':h,'scale':scale,'color':color}

    def get_selected_objects(self,document_id: str) -> dict:
        """Read native selection in a registered drawing; return supported objects with session references."""
        doc=self._doc(document_id)
        ext=self.api7.IKompasDocument2D1(doc._oleobj_.QueryInterface(self.api7.IKompasDocument2D1.CLSID,self.com.IID_IDispatch))
        selected=ext.SelectionManager.SelectedObjects
        if selected is None:return {'items':[]}
        if not isinstance(selected,(tuple,list)):selected=(selected,)
        refs={int(obj.Reference) for obj in selected}
        objects=self.list_objects(document_id,limit=10000)
        if objects['truncated']:raise ValueError('Selection lookup exceeds 10000 objects')
        items=[obj for obj in objects['items'] if obj['api_reference'] in refs]
        if len(items)!=len(refs):raise ValueError('Selection contains unsupported object types')
        return {'items':items}

    def copy_objects_to_document(self,source_id: str,target_id: str,references: list[str] | None=None,selected: bool=False,dx: float=0,dy: float=0) -> dict:
        """Copy explicit or selected native objects between registered documents, in target active-view model coordinates. Source is retained."""
        if source_id==target_id:raise ValueError('Use copy_object within one document')
        dx=finite(dx,'dx');dy=finite(dy,'dy')
        self._doc(source_id);self._doc(target_id)
        if selected:
            if references:raise ValueError('Choose references OR native selection')
            references=[item['reference'] for item in self.get_selected_objects(source_id)['items']]
        if not references:raise ValueError('No objects to copy')
        refs=list(dict.fromkeys(self._checked_reference(source_id,ref) for ref in references))
        before=self.list_objects(target_id,limit=10000)
        source=self.list_objects(source_id,limit=10000)
        if before['truncated'] or source['truncated']:raise ValueError('Transfer lookup exceeds 10000 objects')
        if not set(refs)<=set(obj['api_reference'] for obj in source['items']):raise ValueError('Unsupported transfer object')
        old={obj['api_reference'] for obj in before['items']}
        native=self._a5(source_id);group=native.ksNewGroup(1);copied=0;inserted=False
        if not group:raise RuntimeError('Could not start source group')
        try:
            try:
                for ref in refs:
                    if not native.ksAddObjGroup(group,ref):raise RuntimeError('Could not group source object')
            finally:native.ksEndGroup()
            target=self._a5(target_id)
            copied=target.ksCopyGroupToDocument(group,native.reference)
            if not copied:raise RuntimeError('Cross-document copy failed')
            if (dx or dy) and not target.ksMoveObj(copied,dx,dy):
                raise RuntimeError('Copied group translation failed')
            if not target.ksStoreTmpGroup(copied):raise RuntimeError('Could not insert copied group')
            inserted=True
            after=self.list_objects(target_id,limit=10000)
            items=[obj for obj in after['items'] if obj['api_reference'] not in old]
            if after['truncated'] or len(items)!=len(refs):
                raise RuntimeError('Transfer verification failed; inspect target before retrying')
            return {'copied':len(items),'items':items,'source_retained':True}
        except Exception as error:
            if copied:
                target=self._a5(target_id)
                if not inserted:
                    try:
                        if not target.ksClearGroup(copied,True):raise RuntimeError('Cleanup returned zero')
                    except Exception as cleanup:
                        raise RuntimeError(f'{error}; temporary target group {copied} cleanup failed: {cleanup}') from error
                else:
                    # Inserted entities are no longer a temporary group. Report the
                    # actual additions rather than deleting unidentified UI edits.
                    try:
                        rest=self.list_objects(target_id,limit=10000)
                        refs=[o['api_reference'] for o in rest['items'] if o['api_reference'] not in old]
                    except Exception:refs=['unknown']
                    raise RuntimeError(f'{error}; inserted target API references: {refs}; inspect before retrying') from error
            raise
        finally:
            self._a5(source_id).ksClearGroup(group,True)
