"""Open, identifiable MicroScan document-camera hardware carrier V2.

No button disguise. No hidden wiring. Hardware has NOT been measured or assembled.
Only intended as a reversible mechanical CAD prototype for a visible camera board.
Requires cadquery 2.x.
"""
from pathlib import Path
import cadquery as cq

OUT=Path(__file__).resolve().parent
PCB_X=40.0; PCB_Y=27.0; PCB_THICKNESS_ASSUMED=1.6
BOARD_CENTER_Y=4.0
PLATE_X=84.0; PLATE_Y=58.0; PLATE_Z=3.2
PCB_LIFT=3.5  # assumed clearance to underside components
PILLAR_H=PCB_LIFT+PCB_THICKNESS_ASSUMED
ANCHOR_X=26.0
ANCHOR_YS=(-7.0,15.0)
HOLE_DIAM=3.3
STRAP_SLOT_X=4.0; STRAP_SLOT_Y=22.0

# Board carrier (open, fully visible, clearly identified as CAMERA)
base=cq.Workplane('XY').rect(PLATE_X,PLATE_Y).extrude(PLATE_Z).edges('|Z').fillet(5.0)
for x in (-35,35):
    base=base.cut(cq.Workplane('XY').box(STRAP_SLOT_X,STRAP_SLOT_Y,PLATE_Z+2,centered=(True,True,False)).translate((x,4,-1)))

# Spaced support pads: footprints MUST be verified against actual PCB solder/component side.
for x in (-17,17):
    for y in (BOARD_CENTER_Y-10,BOARD_CENTER_Y+10):
        base=base.union(cq.Workplane('XY').box(4.0,4.0,PCB_LIFT,centered=(True,True,False)).translate((x,y,PLATE_Z)))

# Four collar mounts for separate non-conductive clips, not PCB hole assumptions.
for x in (-ANCHOR_X,ANCHOR_X):
    for y in ANCHOR_YS:
        pillar=cq.Workplane('XY').circle(3.0).extrude(PILLAR_H).translate((x,y,PLATE_Z))
        base=base.union(pillar)
        base=base.cut(cq.Workplane('XY').circle(HOLE_DIAM/2).extrude(PLATE_Z+PILLAR_H+1).translate((x,y,-0.5)))
        # Recess for a low-profile nylon M3 bolt head on skin-facing underside.
        # Actual head diameter and height must be verified before choosing hardware.
        base=base.cut(cq.Workplane('XY').circle(3.0).extrude(1.8).translate((x,y,0)))

# Two optional cable tie openings near top edge: cable itself stays fully exposed.
for x in (-5.5,5.5):
    base=base.cut(cq.Workplane('XY').box(2.7,3.4,PLATE_Z+2,centered=(True,True,False)).translate((x,23,-1)))

# Label leaves no doubt this is an imaging accessory.
letter=cq.Workplane('XY').text('CAMERA',7.2,0.8,font='Liberation Sans',kind='bold',combine=True).translate((0,-21.8,PLATE_Z-0.79))
base=base.cut(letter)

# Symmetrical side retaining pads: top-only board-edge contact, no case over optics.
# The user selects two or four clips AFTER physical inspection of the PCB edges.
# Slot allows a few mm of location adjustment around printed pillar; clip is not a rated fastener.
clip=cq.Workplane('XY').box(14.0,6.0,2.8,centered=(True,True,False)).translate((-0.5,0,0))
clip=clip.edges('|Z').fillet(1.0)
# Longitudinal mounting slot: 5.0mm center-to-center + 3.3mm diameter => 8.3mm overall.
slot=cq.Workplane('XY').slot2D(8.3,3.3,angle=0).extrude(5).translate((0,0,-1))
clip=clip.cut(slot)
# Tiny outward-facing CAMERA label remains on the main carrier, not the clip.

# A dimensional gauge representing nominal PCB rectangle, not a real PCB physical model.
gauge=cq.Workplane('XY').box(PCB_X,PCB_Y,PCB_THICKNESS_ASSUMED,centered=(True,True,False)).translate((0,BOARD_CENTER_Y,0))

solids={'Open_Camera_Carrier_V2':base,'Adjustable_Edge_Retainer_V2':clip,'Nominal_PCB_Gauge_DO_NOT_MOUNT':gauge}
if __name__=='__main__':
    for name,obj in solids.items():
        cq.exporters.export(obj,str(OUT/(name+'.step')))
        cq.exporters.export(obj,str(OUT/(name+'.stl')),tolerance=0.08,angularTolerance=0.1)
    print('EXPORTED', ', '.join(solids), flush=True)
    for name,obj in solids.items():
        bb=obj.val().BoundingBox()
        print(name,'bounds mm',(round(bb.xlen,2),round(bb.ylen,2),round(bb.zlen,2)),'volume mm3',round(obj.val().Volume(),2))
