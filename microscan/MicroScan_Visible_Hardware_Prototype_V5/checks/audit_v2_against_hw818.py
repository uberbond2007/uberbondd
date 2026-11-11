"""Audit of the UNMODIFIED V2/V4 carrier against the board the retailer photographs (HW-818).

Imports the original V4 CAD source from source_v4/ and the V5 nominal board parameters, and
records why V2 cannot be released for this board. Findings are geometric arithmetic on CAD and
on UNVERIFIED nominal board numbers - they justify the redesign, they are not measurements.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source_v4' / 'extracted_unmodified' / 'cad'))
sys.path.insert(0, str(ROOT / 'cad'))
import build_hardware_v2 as v2   # original, unmodified
import build_hardware_v5 as v5

f = []


def finding(code, title, numbers, blocks_release=True):
    f.append({'id': code, 'title': title, 'numbers': numbers, 'blocks_v2_release': blocks_release})
    print(code, '|', title, '|', numbers)


pcb_under = v2.PLATE_Z + v2.PCB_LIFT
tip = pcb_under - v5.HDR_BODY_H - v5.HDR_PIN_BELOW_BODY
finding('V2-F1', 'Factory-soldered header pins cannot seat: V2 lifts the PCB only 3.5 mm',
        {'v2_pcb_underside_z': pcb_under, 'pin_tip_z': round(tip, 2), 'plate_bottom_z': 0.0,
         'pins_would_pass_through_plate_and_protrude_toward_skin_mm': round(-tip, 2)})
clear_between_pillars = 2 * v2.ANCHOR_X - 6.0
finding('V2-F2', 'Board length exceeds the gap between V2 pillars',
        {'gap_between_pillar_faces_mm': clear_between_pillars, 'hw818_length_mm_UNVERIFIED': v5.PCB_L,
         'v2_assumed_length_mm': v2.PCB_X, 'interference_mm': round(v5.PCB_L - clear_between_pillars, 2)})
finding('V2-F3', 'USB plug has nowhere to go: board long axis ends at an M3 pillar pair and a strap slot',
        {'v2_pillar_x': v2.ANCHOR_X, 'v2_strap_slot_x': 35, 'plate_half_length': v2.PLATE_X / 2,
         'needed_beyond_board_end_for_plug_mm': v5.USB_PLUG_L,
         'available_beyond_40mm_board_end_mm': v2.PLATE_X / 2 - v2.PCB_X / 2})
pads_y = [v2.BOARD_CENTER_Y - 10, v2.BOARD_CENTER_Y + 10]
rows_y = [v2.BOARD_CENTER_Y - v5.HDR_ROW_SPACING / 2, v2.BOARD_CENTER_Y + v5.HDR_ROW_SPACING / 2]
finding('V2-F4', 'V2 support pads sit under the header rows',
        {'pad_centres_y': pads_y, 'pad_half_width': 2.0, 'header_row_y': [round(y, 2) for y in rows_y],
         'overlap': all(abs(p - r) < 2.0 + 1.27 for p, r in zip(pads_y, rows_y))})
finding('V2-F5', 'Skin-side head pocket is shallower than an M3 pan head',
        {'v2_pocket_depth_mm': 1.8, 'iso7045_m3_pan_head_height_mm': 2.4, 'head_proud_of_skin_face_mm': round(2.4 - 1.8, 2)})
stack_v2 = (v2.PLATE_Z - 1.8) + v2.PILLAR_H + 2.8
finding('V2-F6', 'V2 M3x16 recommendation happened to be long enough (kept for the record)',
        {'grip_mm': round(stack_v2, 2), 'thread_past_2.4_nut_mm': round(16 - stack_v2 - 2.4, 2)}, blocks_release=False)
finding('V2-F7', 'validate_cad.py comment says the CAD module "exports on import"; it does not (export is under __main__)',
        {'effect': 'V4 CAD checks validated the in-memory solid plus the previously exported STL; harmless but inaccurate'}, False)
finding('V2-F8', 'V4 host tool sends CAPTURE immediately after opening the port',
        {'risk': 'if the HW-818 has the usual DTR/RTS auto-program circuit, opening the port resets the ESP32 and the request is lost',
         'v5_change': '--wait-ready option; evidence class for the reset circuit: UNKNOWN'}, False)
out = {'scope': 'CAD arithmetic against UNVERIFIED nominal HW-818 numbers', 'findings': f,
       'v2_releasable_for_photographed_board': not any(x['blocks_v2_release'] for x in f)}
(ROOT / 'checks' / 'V2_AUDIT_FINDINGS.json').write_text(json.dumps(out, indent=2) + '\n')
assert out['v2_releasable_for_photographed_board'] is False
print('V2 releasable for the photographed board:', out['v2_releasable_for_photographed_board'])
