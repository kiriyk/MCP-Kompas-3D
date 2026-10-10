"""Direct COM experiment. Intentionally no MCP client or protocol."""
import json
from pathlib import Path
from kompas_local_mcp.adapter import Adapter
from direct_features import DirectFeatures

class ExperimentalAdapter(Adapter):pass

def run():
    out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
    a=ExperimentalAdapter();d=None;results={}
    try:
        a.connect();d=a.create_drawing()['document_id'];a.set_sheet(d,'A0',True)
        a.create_view(d,'Прямые проверки API',.1,100,200)
        a.create_layer(d,'Зелёный маршрут',7,0x00A000)
        p=a.polyline(d,[[0,0],[1000,0],[1000,1000]])
        container=a._container(d);poly=a.api7.IPolyLine2D(container.PolyLines2D.Item(0))
        assert poly.PointsCount==3
        results['polyline']={'reference':p['api_reference'],'points':poly.Points}
        a.polyline(d,[[6000,0],[7000,0],[6500,1000]],closed=True)
        closed=a.api7.IPolyLine2D(container.PolyLines2D.Item(1))
        assert closed.Closed,'Closed polyline flag was not applied'
        src=a.line(d,100,200,400,500)
        mir=a.mirror_object(d,src['reference'],0,0,0,1000)
        obj=next(o for o in a.list_objects(d)['items'] if o['api_reference']==mir['api_reference'])
        assert obj['points']==[[-100,200],[-400,500]],obj
        results['mirror']=obj['points']
        ar=a.linear_array(d,src['reference'],4,1000,0)
        assert len(ar['copies'])==3
        circle=a.circle(d,3000,0,100)
        ring=a.circular_array(d,circle['reference'],4,2000,0)
        centers=[o['center'] for o in a.list_objects(d)['items'] if o['type']=='circle']
        assert all(any(abs(p[0]-q[0])<1e-6 and abs(p[1]-q[1])<1e-6 for p in centers) for q in [(3000,0),(2000,1000),(1000,0),(2000,-1000)])
        results['arrays']={'linear':len(ar['copies'])+1,'circular_centers':centers}
        ct=a.mixed_contour(d,[{'type':'line','x1':0,'y1':2000,'x2':1000,'y2':2000},{'type':'arc','x':1000,'y':2500,'radius':500,'start_angle':270,'end_angle':90}])
        assert container.DrawingContours.Count==1
        contour=a.api7.IContour(container.DrawingContours.Item(0)._oleobj_.QueryInterface(a.api7.IContour.CLSID,a.com.IID_IDispatch))
        assert contour.Count==2,contour.Count
        bz=a.bezier(d,[{'x':0,'y':4000,'angle':40,'right':800},{'x':2000,'y':4300,'angle':-40,'left':800}])
        assert container.Beziers.Count==1
        a.hatch_polygon(d,[[4000,0],[5000,0],[4800,1000],[4200,800]])
        assert container.Hatches.Count==1
        boundary=a.api7.IBoundariesObject(container.Hatches.Item(0)._oleobj_.QueryInterface(a.api7.IBoundariesObject.CLSID,a.com.IID_IDispatch))
        results['hatch_boundaries']=str(boundary.Boundaries)
        results.update(contour=ct['api_reference'],bezier=bz['api_reference'],polygon_hatch=True)
        # Raster color by layer, tested independently of the server facade.
        doc=a._a5(d);param=a.api5.ksRasterFormatParam(doc.RasterFormatParam());param.Init()
        param.format=3;param.colorBPP=24;param.extResolution=60;param.extScale=1;param.colorType=2;param.pages='1';param.rangeIndex=0
        doc.SaveAsToRasterFormat(str(out/'direct-api.png'),param)
        results['color_export']='direct-api.png; raster colorType=2 (by layer)'
        a.save_document(d,str(out/'direct-api.cdw'))
        (out/'direct-api-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print('DIRECT API PASS',json.dumps(results,ensure_ascii=False),flush=True)
    finally:
        if d:a.close_document(d)
        a.shutdown()

if __name__=='__main__':run()
