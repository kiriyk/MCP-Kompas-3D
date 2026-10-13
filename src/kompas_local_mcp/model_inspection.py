"""Native measurements with explicit entity scope; no inference of dice dynamics."""
import math
from typing import Literal
from .core import finite, positive

def vector(value, label='vector'):
    if not isinstance(value,(list,tuple)) or len(value)!=3:raise ValueError(f'{label} requires three finite coordinates')
    return [finite(x,label) for x in value]

def unit(value):
    value=vector(value);length=math.sqrt(sum(x*x for x in value))
    if length<1e-12:raise ValueError('Direction cannot be zero')
    return [x/length for x in value]

def cross(x,y):return [x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]]

def transform(v,placement,point=False):
    x=placement['x_axis'];y=placement['y_axis'];z=cross(x,y)
    return [sum(v[j]*[x,y,z][j][i] for j in range(3))+(placement['origin'][i] if point else 0) for i in range(3)]

class ModelInspection:
    def select_model_topology(self,document_id: str,kind: Literal['face','edge']='face',component_reference: str|None=None,planar: bool|None=None,straight: bool|None=None,radius: float|None=None,normal: list[float]|None=None,direction: list[float]|None=None,bounds_min: list[float]|None=None,bounds_max: list[float]|None=None,owner_name: str|None=None,adjacent_face_reference: str|None=None,tolerance: float=.01) -> dict:
        """AND-filter current topology by geometry in model/assembly coordinates; bounds must be contained. Directions parallel in either sense; tolerance in mm (direction dot tolerance capped at .001)."""
        tolerance=positive(tolerance,'tolerance')
        if radius is not None:radius=positive(radius,'radius')
        normal=unit(normal) if normal is not None else None
        direction=unit(direction) if direction is not None else None
        if (bounds_min is None)!=(bounds_max is None):raise ValueError('Both bounds required')
        if bounds_min is not None:
            bounds_min=vector(bounds_min);bounds_max=vector(bounds_max)
            if any(a>b for a,b in zip(bounds_min,bounds_max)):raise ValueError('Invalid bounds')
        adjacent=self._model_ref(document_id,adjacent_face_reference,'face') if adjacent_face_reference else None
        if adjacent is not None and kind!='edge':raise ValueError('Adjacency requires edge query')
        data=self.list_model_topology(document_id,kind,component_reference);items=[]
        for item in data['items']:
            if planar is not None and item.get('planar')!=planar:continue
            if straight is not None and item.get('straight')!=straight:continue
            if radius is not None and (item.get('radius_mm') is None or abs(item['radius_mm']-radius)>tolerance):continue
            if owner_name is not None and item.get('owner_name')!=owner_name:continue
            if any(want is not None and (item.get(key) is None or abs(sum(a*b for a,b in zip(want,item[key])))<1-min(tolerance,.001)) for key,want in [('normal',normal),('direction',direction)]):continue
            b=item.get('bounds_mm')
            if bounds_min is not None and (b is None or any(b['min'][i]<bounds_min[i]-tolerance or b['max'][i]>bounds_max[i]+tolerance for i in range(3))):continue
            if adjacent is not None:
                edge=self.api5.ksEdgeDefinition(self._model_ref(document_id,item['reference'],'edge').GetDefinition())
                neighbors=[edge.GetAdjacentFace(side) for side in (True,False)]
                if not any(f is not None and f.GetEntity()._oleobj_==adjacent._oleobj_ for f in neighbors):continue
            items.append(item)
        return {'kind':kind,'items':items,'count':len(items),'references_expire_on_rebuild':True,'selection':'geometry_conditions'}

    def measure_model_geometry(self,document_id: str,first_reference: str,second_reference: str) -> dict:
        """Native minimum distance between two selected bounded faces/edges, mm. Coverage is only these entities; not whole-model minimum wall thickness."""
        if first_reference==second_reference:raise ValueError('Two distinct geometry references required')
        self._model_doc(document_id)
        objects=[]
        for ref in (first_reference,second_reference):
            record=self.model_refs.get(ref)
            if record is None or record[0]!=document_id or record[1] not in ('face','edge'):raise ValueError('Current face/edge reference required')
            objects.append(record[2])
        m=self._part5(document_id).GetMeasurer();m.unit=1;m.extendObject1=False;m.extendObject2=False
        if not m.SetObject1(objects[0]) or not m.SetObject2(objects[1]) or not m.Calc():raise RuntimeError('Native distance measurement failed')
        distance=finite(m.MinDistance,'native_distance')
        p=m.GetMinPoint1();q=m.GetMinPoint2()
        if distance<0 or not p[0] or not q[0]:raise RuntimeError('Invalid native distance result')
        first=vector(p[1:]);second=vector(q[1:])
        if abs(math.dist(first,second)-distance)>max(.001,distance*1e-6):raise RuntimeError('Native distance/witness-point mismatch')
        return {'minimum_distance_mm':distance,'point1_mm':first,'point2_mm':second,'method':'KOMPAS_v21_ksMeasurer','coverage':'selected_bounded_entities','global_minimum_thickness_verified':False}

    def check_model_measurements(self,document_id: str,reference_pairs: list[list[str]],required_minimum: float,purpose: Literal['clearance','thickness']='clearance') -> dict:
        """Check specified face/edge pairs against a minimum, mm. Report selected-pair coverage; does not prove overall thickness, connectivity or dynamic dice motion."""
        required_minimum=positive(required_minimum,'required_minimum')
        if purpose not in ('clearance','thickness') or not isinstance(reference_pairs,list) or not 1<=len(reference_pairs)<=200 or any(not isinstance(p,list) or len(p)!=2 or any(not isinstance(r,str) or not r for r in p) or p[0]==p[1] for p in reference_pairs):raise ValueError('1..200 distinct-reference pairs required')
        for pair in reference_pairs:
            for ref in pair:
                record=self.model_refs.get(ref)
                if record is None or record[0]!=document_id or record[1] not in ('face','edge'):raise ValueError('Stale or cross-document geometry reference')
        results=[{'references':pair,**self.measure_model_geometry(document_id,*pair)} for pair in reference_pairs]
        for result in results:result['passed']=result['minimum_distance_mm']+1e-7>=required_minimum
        return {'purpose':purpose,'required_minimum_mm':required_minimum,'passed':all(r['passed'] for r in results),'minimum_of_selected_pairs_mm':min(r['minimum_distance_mm'] for r in results),'measurements':results,'coverage':'selected_pairs_only','global_minimum_verified':False,'dice_dynamics_verified':False}

    def check_assembly_intersections(self,document_id: str,component_references: list[str]|None=None,include_contacts: bool=True) -> dict:
        """Native body intersections in assembly placement coordinates. Distinguishes volumetric interference (type 4) from point/curve/surface contacts. Read-only; checks all selected pairs, no name-based exemptions."""
        self._model_doc(document_id,5)
        if component_references is None:component_references=[c['component_reference'] for c in self.list_components(document_id)['components']]
        if not isinstance(component_references,list) or not 2<=len(component_references)<=120 or len(set(component_references))!=len(component_references):raise ValueError('2..120 distinct components required')
        parts=[self._model_ref(document_id,r,'component') for r in component_references];bodies=[]
        for part in parts:
            c=part.BodyCollection()
            if not c.GetCount():raise RuntimeError(f'Component has no solid bodies: {part.name}')
            component_bodies=[c.GetByIndex(i) for i in range(c.GetCount())]
            if any(not b.IsSolid() for b in component_bodies):raise RuntimeError(f'Non-solid body in component: {part.name}')
            bodies.append(component_bodies)
        results=[];checked=0
        for i in range(len(parts)):
            for j in range(i+1,len(parts)):
                types=set();checked+=1
                for first in bodies[i]:
                    for second in bodies[j]:
                        raw=first.CheckIntersectionWithBody(second,include_contacts)
                        if raw is not None:
                            if raw.GetCount()<1:raise RuntimeError('Empty native intersection result')
                            types.update(raw.GetIntersectionType(k) for k in range(raw.GetCount()))
                if any(t not in (1,2,3,4) for t in types):raise RuntimeError('Unknown native intersection type')
                if types:results.append({'first_reference':component_references[i],'second_reference':component_references[j],'first_name':parts[i].name,'second_name':parts[j].name,'native_types':sorted(types),'volumetric_interference':4 in types,'contact_only':4 not in types})
        return {'method':'KOMPAS_v21_CheckIntersectionWithBody','coordinate_space':'assembly','component_count':len(parts),'checked_pairs':checked,'intersections':results,'interference_count':sum(r['volumetric_interference'] for r in results),'contact_count':sum(r['contact_only'] for r in results),'checked_contacts':include_contacts,'complete':True,'dice_dynamics_verified':False}
