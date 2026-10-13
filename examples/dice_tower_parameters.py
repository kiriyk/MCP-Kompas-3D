"""Teaching model dimensions and conservative geometric cube-clearance checks."""
import math

def tower_parameters():
    return {'height':220.,'width':90.,'wall':3.,'dice':22.,'clearance':2.,'baffle_projection':41.,'baffle_angle':35.,'baffle_thickness':2.5,'baffle_heights':[200.,145.,90.],'side_clearance':.3,'exit_angle':15.}

def validate_dice_clearances(p):
    for k in ('height','width','wall','dice','clearance','baffle_projection','baffle_thickness'):
        if not math.isfinite(p[k]) or p[k]<=0:raise ValueError(f'{k} must be finite and positive')
    if not 5<=p['baffle_angle']<=60 or not 5<=p['exit_angle']<=30:raise ValueError('Unsupported ramp angle')
    inner=p['width']-2*p['wall'];angle=math.radians(p['baffle_angle']);needed=p['dice']*math.sqrt(3)+p['clearance']
    end_gap=inner-p['baffle_projection']-p['baffle_thickness']*math.sin(angle)
    tip=p['baffle_heights'][-1]-p['baffle_projection']*math.tan(angle)
    exit_at_tip=p['wall']+.3+p['baffle_projection']*math.tan(math.radians(p['exit_angle']))+p['baffle_thickness']*math.cos(math.radians(p['exit_angle']))
    headroom=tip-exit_at_tip
    separation=min(a-b for a,b in zip(p['baffle_heights'],p['baffle_heights'][1:]))-p['baffle_thickness']*math.cos(angle)
    if min(end_gap,headroom,separation)<needed:raise ValueError('Baffle arrangement cannot clear the cube diagonal with the requested allowance')
    return {'required_mm':needed,'end_gap_mm':end_gap,'exit_headroom_mm':headroom,'baffle_separation_mm':separation,'baffle_length_mm':p['baffle_projection']/math.cos(angle),'plate_width_mm':inner-2*p['side_clearance']}
