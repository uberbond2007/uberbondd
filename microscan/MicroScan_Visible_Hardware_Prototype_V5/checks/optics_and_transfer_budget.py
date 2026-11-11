"""Arithmetic budgets for the optics gate and the serial link. CALCULATIONS ONLY - no image was taken.

Nothing here says the camera is sharp. It states what pixel count alone permits (an upper bound on
legibility) and how long one frame takes on the UART (a lower bound on time).
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER_BYTES = 16

# --- pixel density --------------------------------------------------------------------------
# Tesseract's documentation asks for capital letters of roughly 20-30 px or more. Take 10 pt body text:
# cap height ~ 0.7 em = 2.47 mm, x-height ~ 0.5 em = 1.76 mm.
CAP_MM_10PT = 10 * 0.3528 * 0.70
TARGET_CAP_PX = 25
need_px_per_mm = TARGET_CAP_PX / CAP_MM_10PT
modes = {'UXGA 1600x1200 (JPEG sensors only; 3.84 MB as RGB565 - does not fit 4 MB PSRAM)': 1600,
         'XGA 1024x768 (RGB565 1.57 MB; driver support on this sensor UNVERIFIED)': 1024,
         'SVGA 800x600 (RGB565 0.96 MB; V5 default for JPEG-less sensors)': 800,
         'QVGA 320x240 (the only mode the seller guide for RHYX M21-45 says works)': 320}
targets = {'A4 long side 297 mm': 297, 'A4 short side 210 mm': 210, 'A5 short side 148 mm': 148, 'A6 short side 105 mm': 105,
           'text column 80 mm': 80}
density = {}
for mname, px in modes.items():
    row = {'max_field_width_mm_for_10pt_text': round(px / need_px_per_mm, 1)}
    for tname, mm in targets.items():
        ppm = px / mm
        row[tname] = {'px_per_mm': round(ppm, 2), 'dpi': round(ppm * 25.4), 'cap_height_px_10pt': round(ppm * CAP_MM_10PT, 1),
                      'meets_25px_cap_target': ppm >= need_px_per_mm}
    density[mname] = row

# --- field of view: lens data for the RHYX module is UNKNOWN, so give the geometry for a range -----
fov = {}
for hfov in (45, 55, 65, 75):
    fov[f'HFOV {hfov} deg (ASSUMPTION)'] = {f'{d} mm': round(2 * d * math.tan(math.radians(hfov / 2)), 1) for d in (100, 150, 200, 300, 400)}

# --- UART time ----------------------------------------------------------------------------------
bauds = (115200, 230400, 460800, 921600)
sizes = {'60 kB (SVGA soft-JPEG, text page, estimate)': 60_000, '120 kB': 120_000, '250 kB (V4 example)': 250_000,
         '400 kB (UXGA hardware JPEG, detailed page)': 400_000, '1 MB (V4 example)': 1_000_000}
uart = {name: {str(b): round((n + HEADER_BYTES) * 10 / b, 2) for b in bauds} for name, n in sizes.items()}
overhead = {'header_bytes': HEADER_BYTES, 'line_bits_per_byte_8N1': 10,
            'header_share_of_250kB_frame_percent': round(100 * HEADER_BYTES / (250_000 + HEADER_BYTES), 4),
            'fixed_firmware_delay_s': 0.3, 'note': 'plus two sensor frame times and, for JPEG-less sensors, software encoding (unmeasured)'}
v4_claim_ok = abs((250_000) * 10 / 115200 - 21.70) < 0.01
out = {'status': 'CALCULATED - NOT MEASURED', 'assumptions': {'cap_height_10pt_mm': round(CAP_MM_10PT, 3), 'target_cap_px': TARGET_CAP_PX,
       'needed_px_per_mm': round(need_px_per_mm, 2), 'needed_dpi': round(need_px_per_mm * 25.4)},
       'pixel_density': density, 'field_width_mm_vs_distance': fov, 'uart_seconds_lower_bound': uart, 'protocol_overhead': overhead,
       'v4_stated_21.7s_for_250kB_at_115200_reproduced': v4_claim_ok,
       'verdict': ['Whole-A4 capture of 10 pt text is below the 25 px cap-height target in every mode (UXGA gives ~13 px).',
                   'With the RHYX/GC2145-class sensor limited to SVGA, the usable field for 10 pt text is about 79 mm wide: a paragraph, not a page.',
                   'Focus distance, lens FOV, real sharpness and OCR accuracy are UNKNOWN until a physical frame exists.',
                   '115200 baud is tolerable for <=120 kB frames (<=10.4 s); 921600 brings a 400 kB frame to 4.3 s but must be bench-verified.']}
(ROOT / 'reports' / 'OPTICS_AND_TRANSFER_BUDGET.json').write_text(json.dumps(out, indent=2) + '\n')
assert v4_claim_ok
print(json.dumps({k: v['max_field_width_mm_for_10pt_text'] for k, v in density.items()}, indent=1))
print(json.dumps(uart, indent=1))
