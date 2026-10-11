"""Pure validation for simple closed 2D sketch polygons."""
from .core import finite

def polygon(points):
    if not isinstance(points,(list,tuple)) or not 3<=len(points)<=1000:raise ValueError('Polygon needs 3..1000 vertices')
    out=[]
    for p in points:
        if not isinstance(p,(list,tuple)) or len(p)!=2:raise ValueError('Each vertex needs x,y')
        out.append([finite(p[0],'x'),finite(p[1],'y')])
    if out[0]==out[-1]:out.pop()
    if len(out)<3 or len({tuple(p) for p in out})!=len(out):raise ValueError('Duplicate or too few vertices')
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def intersects(a,b,c,d):
        c1,c2,c3,c4=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
        if c1*c2<0 and c3*c4<0:return True
        for u,v,w,z in ((a,b,c,c1),(a,b,d,c2),(c,d,a,c3),(c,d,b,c4)):
            if abs(z)<1e-9 and min(u[0],v[0])-1e-9<=w[0]<=max(u[0],v[0])+1e-9 and min(u[1],v[1])-1e-9<=w[1]<=max(u[1],v[1])+1e-9:return True
        return False
    n=len(out)
    for i in range(n):
        for j in range(i+1,n):
            if j==i+1 or (i==0 and j==n-1):continue
            if intersects(out[i],out[(i+1)%n],out[j],out[(j+1)%n]):raise ValueError('Self-intersecting polygon')
    area=sum(out[i][0]*out[(i+1)%n][1]-out[(i+1)%n][0]*out[i][1] for i in range(n))/2
    if abs(area)<1e-8:raise ValueError('Degenerate polygon')
    return out
