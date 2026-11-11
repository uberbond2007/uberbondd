"""Independent geometric checks of the V5 CAD: exported meshes + B-rep interference probes.

Everything here is DIGITAL. A pass means the CAD is self-consistent against the NOMINAL,
UNVERIFIED board envelope in cad/build_hardware_v5.py. It is not a physical fit result.
Run: python checks/validate_cad_v5.py   (after python cad/build_hardware_v5.py)
"""
import json
import sys
from pathlib import Path

import trimesh
import cadquery as cq

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'cad'))
import build_hardware_v5 as hw  # builds solids in memory; writes nothing

results = []


def check(name, ok, evidence=None):
    ok = bool(ok)
    results.append({'name': name, 'pass': ok, 'evidence': evidence})
    print(('PASS' if ok else 'FAIL') + ' | ' + name + ((' | ' + str(evidence)) if evidence is not None else ''))


def vol(a, b):
    return a.val().intersect(b.val()).Volume()


def cyl(r, h, x, y, z):
    return cq.Workplane('XY').circle(r).extrude(h).translate((x, y, z))


C = hw.carrier
EPS = 1e-3

# 1. exported files agree with the in-memory solids
for name, dims in {'Open_Camera_Carrier_V5': [hw.PLATE_X, hw.PLATE_Y, hw.PILLAR_TOP_Z],
                   'Adjustable_Edge_Retainer_V5': [hw.CLIP_L, hw.CLIP_W, hw.CLIP_T],
                   'HW818_Nominal_PCB_Gauge_DO_NOT_MOUNT': [hw.PCB_L, hw.PCB_W, hw.PCB_T]}.items():
    m = trimesh.load_mesh(str(BASE / 'cad' / f'{name}.stl'))
    check(f'{name} STL watertight', m.is_watertight)
    check(f'{name} STL winding consistent', m.is_winding_consistent)
    check(f'{name} STL extents mm', all(abs(a - b) < 0.1 for a, b in zip(m.extents, dims)), [round(float(v), 3) for v in m.extents])
    brep_v = hw.solids[name].val().Volume()
    check(f'{name} STL volume within 0.5% of B-rep', abs(m.volume - brep_v) / brep_v < 0.005,
          {'stl_mm3': round(float(m.volume), 1), 'brep_mm3': round(brep_v, 1)})
    step = BASE / 'cad' / f'{name}.step'
    check(f'{name} STEP re-imports as one solid', step.is_file() and cq.importers.importStep(str(step)).solids().size() == 1)
check('Carrier keeps the 84 x 58 mm footprint from V2', (hw.PLATE_X, hw.PLATE_Y) == (84.0, 58.0))

# 2. through features
for s in (-1, 1):
    probe = hw.box(hw.STRAP_SLOT_X - 0.6, hw.STRAP_SLOT_Y - 0.6, hw.PLATE_Z + 1, 0, s * hw.STRAP_SLOT_CY, -0.5)
    check(f'Strap slot y={s*hw.STRAP_SLOT_CY} open for a 20 mm strap', vol(C, probe) < EPS)
    margin = hw.PLATE_Y / 2 - (hw.STRAP_SLOT_CY + hw.STRAP_SLOT_Y / 2)
    check(f'Strap slot y={s*hw.STRAP_SLOT_CY} edge web >= 2.4 mm', margin >= 2.4, margin)
    probe = hw.box(hw.TIE_WIN_X - 0.4, hw.TIE_WIN_Y - 0.4, hw.PLATE_Z + 1, hw.SADDLE_X, s * hw.TIE_WIN_CY, -0.5)
    check(f'Cable-tie window y={s*hw.TIE_WIN_CY} open', vol(C, probe) < EPS)
probe = hw.box(hw.TIE_WIN_X - 0.4, 2 * hw.TIE_WIN_CY, hw.TIE_CHANNEL_DEPTH - 0.1, hw.SADDLE_X, 0, 0)
check('Skin-side tie channel lets the tie sit flush', vol(C, probe) < EPS)
for (x, y) in hw.pillar_xy():
    check(f'M3 clearance hole ({x},{y}) through', vol(C, cyl(1.5, hw.PILLAR_TOP_Z + 0.5, x, y, -0.25)) < EPS)
    check(f'Pan-head pocket ({x},{y}) admits dk6.0 x k2.4 head below skin face', vol(C, cyl(3.0, 2.4, x, y, 0)) < EPS)
    wall = (hw.STRAP_SLOT_CY - hw.STRAP_SLOT_Y / 2) - (abs(y) + hw.HEAD_POCKET_D / 2)
    check(f'Wall between pocket ({x},{y}) and strap slot >= 1.2 mm', wall >= 1.2, round(wall, 2))

# 3. skin-side insulation under the header pins
floor = hw.PLATE_Z - hw.TROUGH_INTO_PLATE
check('Solid floor under pin troughs >= 1.6 mm', floor >= 1.6, floor)
xs = hw.pin_xs()
for s in (-1, 1):
    y = s * hw.HDR_ROW_SPACING / 2
    slab = hw.box(xs[-1] - xs[0] + 6, 3.0, floor - 0.02, (xs[0] + xs[-1]) / 2, y, 0.01)
    full = slab.val().Volume()
    check(f'Plate is unbroken beneath pin row y={y:.2f}', abs(vol(C, slab) - full) / full < 1e-4, round(full, 2))
pin_tip_z = hw.PCB_UNDER_Z - hw.HDR_BODY_H - hw.HDR_PIN_BELOW_BODY
check('Nominal pin tips stay >= 0.5 mm above trough floor', pin_tip_z - floor >= 0.5, round(pin_tip_z - floor, 2))
ledge = (hw.HDR_BODY_H - hw.TROUGH_W) / 2
check('Header plastic bearing ledge each side >= 0.5 mm', ledge >= 0.5, round(ledge, 2))
check('Rail wall beside trough >= 1.2 mm (3 perimeters @0.4)', (hw.RAIL_W - hw.TROUGH_W) / 2 >= 1.2, (hw.RAIL_W - hw.TROUGH_W) / 2)
check('Row-spacing float available each side (mm)', (hw.TROUGH_W - hw.HDR_PIN_SQ) / 2 >= 0.4, (hw.TROUGH_W - hw.HDR_PIN_SQ) / 2)

# 4. interference against the NOMINAL board envelope
for part, solid in hw.envelope.items():
    v = vol(C, solid)
    check(f'Carrier does not intersect NOMINAL {part}', v < EPS, round(v, 5))
plug = hw.envelope['usb_plug'].val().BoundingBox()
check('USB plug underside clears plate top by >= 1.0 mm', plug.zmin - hw.PLATE_Z >= 1.0, round(plug.zmin - hw.PLATE_Z, 2))
check('>= 6 mm between nominal plug end and cable saddle for the boot', (hw.SADDLE_X - hw.SADDLE_LEN_X / 2) - plug.xmax >= 6.0,
      round((hw.SADDLE_X - hw.SADDLE_LEN_X / 2) - plug.xmax, 2))
check('Plug, boot and saddle stay inside the plate outline', hw.SADDLE_X + hw.SADDLE_LEN_X / 2 <= hw.PLATE_X / 2 - 2, hw.SADDLE_X + hw.SADDLE_LEN_X / 2)
check('Board outline inside plate with >= 1.5 mm margin', hw.ANT_END_X - (-hw.PLATE_X / 2) >= 1.5 and hw.PCB_W / 2 < hw.PLATE_Y / 2)
module_gap = (hw.PCB_UNDER_Z - hw.MODULE_H) - hw.PLATE_Z
check('Open air gap under module can >= 3 mm (convection, no skin contact)', module_gap >= 3.0, round(module_gap, 2))

# 5. retainers
nom = hw.placed_clips()
for i, c in enumerate(nom):
    check(f'Retainer {i+1} does not cut into carrier', vol(C, c) < EPS)
    for part, solid in hw.envelope.items():
        check(f'Retainer {i+1} clear of NOMINAL {part} at 1.0 mm overlap', vol(c, solid) < EPS)
check('Nominal retainer overlap on PCB edge is 1.0 mm', abs(hw.clip_overlap(hw.CLIP_NOMINAL_SHIFT) - 1.0) < 1e-9, hw.clip_overlap(hw.CLIP_NOMINAL_SHIFT))
travel = (hw.CLIP_SLOT_L - hw.CLIP_SLOT_W) / 2  # slot travel about the bolt axis
lo, hi = hw.clip_overlap(-travel), hw.clip_overlap(travel)
check('Slot travel lets a retainer fully release the board', lo <= -0.5, round(lo, 2))
check('Slot travel reaches >= 3 mm overlap for a narrower real board', hi >= 3.0, round(hi, 2))
tail_gap = (hw.PCB_W / 2 - 1.0) - (hw.HDR_ROW_SPACING / 2 + hw.HDR_PIN_SQ / 2)
check('At 1.0 mm overlap the retainer tip is >= 0.5 mm from pin tails', tail_gap >= 0.5, round(tail_gap, 2))
max_safe = hw.PCB_W / 2 - (hw.HDR_ROW_SPACING / 2 + hw.HDR_PIN_SQ / 2) - 0.6
check('Documented maximum overlap before fouling solder fillets (mm)', 0.8 <= max_safe <= 2.0, round(max_safe, 2))

# 6. fastener stack (pan head in skin-side pocket, nut on top)
stack = (hw.PILLAR_TOP_Z + hw.CLIP_T) - hw.HEAD_POCKET_DEPTH
NUT = 2.4
fasteners = {}
for L in (12, 15, 16, 20, 25):
    fasteners[f'M3x{L}'] = {'thread_past_nut_mm': round(L - stack - NUT, 2), 'full_nut_engagement': L - stack - NUT >= 0}
check('Grip length head-seat to retainer top (mm)', abs(stack - 13.14) < 1e-6, round(stack, 2))
check('M3x16 gives full nut engagement', fasteners['M3x16']['full_nut_engagement'], fasteners['M3x16'])
check('M3x20 gives full nut engagement', fasteners['M3x20']['full_nut_engagement'], fasteners['M3x20'])
check('M3x15 is correctly REJECTED (too short)', not fasteners['M3x15']['full_nut_engagement'], fasteners['M3x15'])
check('Fastener points away from skin (head recessed, excess thread upward)', hw.HEAD_POCKET_DEPTH >= 2.6)
check('Material left under pillar at pocket >= 0.5 mm', hw.PLATE_Z - hw.HEAD_POCKET_DEPTH >= 0.5, round(hw.PLATE_Z - hw.HEAD_POCKET_DEPTH, 2))

# 7. identification
for s in (-1, 1):
    pr = hw.box(26, 5.5, hw.LABEL_DEPTH - 0.05, hw.LABEL_CX, s * hw.LABEL_CY, hw.PLATE_Z - hw.LABEL_DEPTH + 0.02)
    removed = pr.val().Volume() - vol(C, pr)
    check(f'Engraved CAMERA label present at y={s*hw.LABEL_CY}', removed > 15.0, round(removed, 1))
check('Nothing in the carrier stands above the PCB top plane (lens and LED uncovered)',
      C.val().BoundingBox().zmax <= hw.PCB_TOP_Z + 1e-6, round(C.val().BoundingBox().zmax, 2))

# 8. derived figures for the drawings / BOM (reported, not asserted as physical)
PETG = 1.27e-3  # g/mm3
derived = {
    'carrier_volume_mm3': round(C.val().Volume(), 1),
    'carrier_mass_g_solid_PETG_upper_bound': round(C.val().Volume() * PETG, 1),
    'four_retainers_mass_g_solid_PETG': round(4 * hw.clip.val().Volume() * PETG, 2),
    'gauge_mass_g_solid_PETG': round(hw.gauge.val().Volume() * PETG, 2),
    'pcb_underside_z_mm': round(hw.PCB_UNDER_Z, 2),
    'pcb_top_z_mm': round(hw.PCB_TOP_Z, 2),
    'estimated_total_height_mm_UNVERIFIED': round(hw.PCB_TOP_Z + hw.CAMERA_STACK_ABOVE_PCB, 2),
    'usb_end_x_mm': hw.USB_END_X,
    'fasteners': fasteners,
    'retainer_overlap_range_mm': [round(lo, 2), round(hi, 2)],
}
summary = {'scope': 'V5 digital CAD self-consistency against a NOMINAL, UNVERIFIED HW-818 envelope',
           'tests': len(results), 'passed': sum(r['pass'] for r in results), 'failed': sum(not r['pass'] for r in results),
           'derived': derived, 'results': results,
           'physical_board_available': False, 'actual_board_fit_verified': False, 'printed': False}
(BASE / 'checks' / 'CAD_V5_TEST_RESULTS.json').write_text(json.dumps(summary, indent=2) + '\n')
print('TOTAL', summary['passed'], '/', summary['tests'])
print(json.dumps(derived, indent=1))
raise SystemExit(0 if summary['failed'] == 0 else 1)
