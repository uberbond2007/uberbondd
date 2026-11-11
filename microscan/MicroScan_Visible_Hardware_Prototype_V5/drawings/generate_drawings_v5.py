"""Generate the V5 1:1 dimensioned drawing set (PDF) and previews rendered from the real CAD.

Every number printed on the drawings is read from cad/build_hardware_v5.py, so the
drawings cannot drift from the model. 3D previews are flat-shaded renders of the
tessellated CAD solids (no illustration, no generative image).
Print the PDF at 100 % / actual size and check the 100 mm ruler before trusting it.
"""
import sys
from pathlib import Path

import numpy as np
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
sys.path.insert(0, str(ROOT / 'cad'))
import build_hardware_v5 as hw

PT = 72 / 25.4
pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuB', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
NAVY, TEAL, GOLD, GRAY, RED = (HexColor(c) for c in ('#102333', '#027E76', '#B46A19', '#6A7787', '#B3261E'))
PW, PH = A4
pdf_path = OUT / 'MicroScan_V5_Drawings_1to1.pdf'
c = canvas.Canvas(str(pdf_path), pagesize=A4, invariant=1)
c.setTitle('MicroScan V5 open camera carrier - 1:1 drawings')
c.setAuthor('MicroScan V5 generator')


def mm(v):
    return v * PT


def txt(s, x, y, size=8, color=NAVY, font='DejaVu', anchor='l'):
    c.setFont(font, size)
    c.setFillColor(color)
    {'l': c.drawString, 'c': c.drawCentredString, 'r': c.drawRightString}[anchor](x, y, s)


def header(title, sub):
    txt(title, mm(15), PH - mm(16), 13, NAVY, 'DejaVuB')
    txt(sub, mm(15), PH - mm(22), 7.5, GOLD)
    txt('BOARD DIMENSIONS ARE UNVERIFIED (seller datasheet + listing photo). NOT FABRICATED. NOT FIT-TESTED.',
        mm(15), PH - mm(27), 7.5, RED, 'DejaVuB')


def ruler(y):
    x0 = mm(55)
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.2)
    c.line(x0, y, x0 + mm(100), y)
    for i in range(101):
        h = 3 if i % 10 == 0 else (2 if i % 5 == 0 else 1)
        c.setLineWidth(0.8 if i % 10 == 0 else 0.3)
        c.line(x0 + mm(i), y, x0 + mm(i), y + mm(h))
    txt('0', x0, y - mm(3.5), 6, GRAY, anchor='c')
    txt('100 mm', x0 + mm(100), y - mm(3.5), 6, GRAY, anchor='c')
    txt('Scale check: this ruler must measure 100.0 mm. If not, reprint at 100 %.', x0, y + mm(5), 7, NAVY)


def dim_h(x1, x2, y, label, X, Y, off=0):
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.4)
    c.line(X(x1), Y(y), X(x2), Y(y))
    for x in (x1, x2):
        c.line(X(x), Y(y) - mm(1.2), X(x), Y(y) + mm(1.2))
    txt(label, (X(x1) + X(x2)) / 2, Y(y) + mm(1.0 + off), 6.5, GRAY, anchor='c')


def dim_v(y1, y2, x, label, X, Y):
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.4)
    c.line(X(x), Y(y1), X(x), Y(y2))
    for y in (y1, y2):
        c.line(X(x) - mm(1.2), Y(y), X(x) + mm(1.2), Y(y))
    c.saveState()
    c.translate(X(x) - mm(1.2), (Y(y1) + Y(y2)) / 2)
    c.rotate(90)
    txt(label, 0, 0, 6.5, GRAY, anchor='c')
    c.restoreState()


xs = hw.pin_xs()
row_cx = (xs[0] + xs[-1]) / 2
row_len = xs[-1] - xs[0]
rail_len = row_len + 2 * hw.RAIL_END_MARGIN
half_row = hw.HDR_ROW_SPACING / 2

# ------------------------------------------------------------------ page 1: plan 1:1
header('MicroScan V5 | Sheet 1 of 3 | Carrier plan view, scale 1:1',
       'Third-angle. Dimensions in mm. General printed tolerance +-0.3; holes modelled +0.4 on diameter for FDM.')
ox, oy = PW / 2, PH - mm(95)
X = lambda v: ox + mm(v)
Y = lambda v: oy + mm(v)
c.setStrokeColor(TEAL)
c.setLineWidth(1.4)
c.roundRect(X(-hw.PLATE_X / 2), Y(-hw.PLATE_Y / 2), mm(hw.PLATE_X), mm(hw.PLATE_Y), mm(hw.PLATE_FILLET))
c.setLineWidth(0.8)
c.setStrokeColor(NAVY)
for s in (-1, 1):
    c.rect(X(-hw.STRAP_SLOT_X / 2), Y(s * hw.STRAP_SLOT_CY - hw.STRAP_SLOT_Y / 2), mm(hw.STRAP_SLOT_X), mm(hw.STRAP_SLOT_Y))
    y = s * half_row
    c.rect(X(row_cx - rail_len / 2), Y(y - hw.RAIL_W / 2), mm(rail_len), mm(hw.RAIL_W))
    tl = row_len + hw.HDR_PIN_SQ + 2 * hw.TROUGH_END_CLEAR
    c.setFillColor(HexColor('#DDE7EA'))
    c.rect(X(row_cx - tl / 2), Y(y - hw.TROUGH_W / 2), mm(tl), mm(hw.TROUGH_W), fill=1)
    c.rect(X(hw.SADDLE_X - hw.TIE_WIN_X / 2), Y(s * hw.TIE_WIN_CY - hw.TIE_WIN_Y / 2), mm(hw.TIE_WIN_X), mm(hw.TIE_WIN_Y))
    txt(hw.LABEL, X(hw.LABEL_CX), Y(s * hw.LABEL_CY) - 5, 14.5, TEAL, 'DejaVuB', 'c')
for (x, y) in hw.pillar_xy():
    c.circle(X(x), Y(y), mm(hw.PILLAR_D / 2))
    c.circle(X(x), Y(y), mm(hw.BOLT_CLEAR_D / 2))
    c.setDash(1.5, 1.5)
    c.circle(X(x), Y(y), mm(hw.HEAD_POCKET_D / 2))
    c.setDash()
c.rect(X(hw.SADDLE_X - hw.SADDLE_LEN_X / 2), Y(-hw.SADDLE_W_Y / 2), mm(hw.SADDLE_LEN_X), mm(hw.SADDLE_W_Y))
# nominal board + plug, dashed gold
c.setStrokeColor(GOLD)
c.setDash(mm(1.6), mm(1.0))
c.setLineWidth(0.9)
c.rect(X(hw.ANT_END_X), Y(-hw.PCB_W / 2), mm(hw.PCB_L), mm(hw.PCB_W))
c.rect(X(hw.USB_END_X - 1.0), Y(-hw.USB_PLUG_W / 2), mm(hw.USB_PLUG_L), mm(hw.USB_PLUG_W))
c.setDash()
for x in xs:
    for s in (-1, 1):
        c.circle(X(x), Y(s * half_row), mm(0.45), stroke=1, fill=0)
txt('NOMINAL HW-818 OUTLINE (UNVERIFIED)', X(hw.BOARD_CX), Y(1.5), 6.5, GOLD, anchor='c')
txt('ANTENNA END', X(hw.ANT_END_X + 1), Y(-3), 5.5, GOLD)
txt('USB END  /  plug', X(hw.USB_END_X + 1), Y(-1), 5.5, GOLD)
# dimensions
dim_h(-hw.PLATE_X / 2, hw.PLATE_X / 2, -hw.PLATE_Y / 2 - 6, f'{hw.PLATE_X:.1f}', X, Y)
dim_v(-hw.PLATE_Y / 2, hw.PLATE_Y / 2, -hw.PLATE_X / 2 - 6, f'{hw.PLATE_Y:.1f}', X, Y)
dim_h(hw.ANT_END_X, hw.USB_END_X, -hw.PLATE_Y / 2 - 11, f'{hw.PCB_L:.1f} board (UNVERIFIED)', X, Y)
dim_h(-hw.PLATE_X / 2, hw.ANT_END_X, hw.PLATE_Y / 2 + 4, f'{hw.ANT_END_X + hw.PLATE_X / 2:.1f}', X, Y)
dim_h(hw.ANT_END_X, xs[0], hw.PLATE_Y / 2 + 4, f'{hw.HDR_PIN1_FROM_ANT_END:.1f} pin 1', X, Y)
dim_h(xs[0], xs[-1], hw.PLATE_Y / 2 + 4, f'{row_len:.2f} (7 x 2.54)', X, Y)
dim_h(-hw.STRAP_SLOT_X / 2, hw.STRAP_SLOT_X / 2, hw.PLATE_Y / 2 + 9, f'slot {hw.STRAP_SLOT_X:.0f} x {hw.STRAP_SLOT_Y:.0f}', X, Y)
dim_v(-half_row, half_row, hw.PLATE_X / 2 + 5, f'{hw.HDR_ROW_SPACING:.2f} rows (MEASURE)', X, Y)
dim_v(-hw.PILLAR_CY, hw.PILLAR_CY, hw.PLATE_X / 2 + 11, f'{2 * hw.PILLAR_CY:.1f} pillars', X, Y)
dim_v(-hw.STRAP_SLOT_CY, hw.STRAP_SLOT_CY, hw.PLATE_X / 2 + 17, f'{2 * hw.STRAP_SLOT_CY:.1f} slot centres', X, Y)
y0 = oy - mm(hw.PLATE_Y / 2 + 22)
rows = [
    f'Datum: plate centre (0,0). Board antenna-end edge at X = {hw.ANT_END_X:.1f}; USB-end edge at X = {hw.USB_END_X:.1f}.',
    'M3 pillars (X, Y): ' + ', '.join(f'({x:.1f}, {y:.1f})' for x, y in hw.pillar_xy()) +
    f'; dia {hw.PILLAR_D:.1f}, hole dia {hw.BOLT_CLEAR_D:.1f}.',
    f'Skin-side pan-head pockets (dashed): dia {hw.HEAD_POCKET_D:.1f} x {hw.HEAD_POCKET_DEPTH:.1f} deep. Head must sit below the face.',
    f'Pin troughs: {hw.TROUGH_W:.1f} wide, blind, floor {hw.PLATE_Z - hw.TROUGH_INTO_PLATE:.1f} solid toward skin. Never drill through.',
    f'Cable saddle at X = {hw.SADDLE_X:.1f}; tie windows {hw.TIE_WIN_X:.1f} x {hw.TIE_WIN_Y:.1f} at Y = +-{hw.TIE_WIN_CY:.1f}; tie lies in a {hw.TIE_CHANNEL_DEPTH:.1f} deep skin-side channel.',
    f'Engraved "{hw.LABEL}" x2, {hw.LABEL_DEPTH:.1f} deep. Fill with contrasting paint. Do not cover the lens, the label or the capture LED.',
    'One 20 mm hook-and-loop strap through the two long-edge slots. Cable stays outside clothing and fully visible.',
]
for i, r in enumerate(rows):
    txt('- ' + r, mm(15), y0 - mm(i * 4.6), 6.8, NAVY)
ruler(mm(22))
c.showPage()

# ------------------------------------------------------------------ page 2: section 2:1
header('MicroScan V5 | Sheet 2 of 3 | Section through a pin row, scale 1.5:1',
       'Section plane Y = +%.2f (pin row). Vertical datum Z = 0 is the skin-side face.' % half_row)
SC = 1.5
ox, oy = PW / 2 + mm(22), PH - mm(100)
X = lambda v: ox + mm(v * SC)
Z = lambda v: oy + mm(v * SC)
c.setLineWidth(0.9)
c.setStrokeColor(TEAL)
c.setFillColor(HexColor('#CFE6E4'))
c.rect(X(-hw.PLATE_X / 2), Z(0), mm(hw.PLATE_X * SC), mm(hw.PLATE_Z * SC), fill=1)
c.rect(X(row_cx - rail_len / 2), Z(hw.PLATE_Z), mm(rail_len * SC), mm(hw.RAIL_H * SC), fill=1)
tl = row_len + hw.HDR_PIN_SQ + 2 * hw.TROUGH_END_CLEAR
c.setFillColor(HexColor('#FFFFFF'))
c.rect(X(row_cx - tl / 2), Z(hw.PLATE_Z - hw.TROUGH_INTO_PLATE), mm(tl * SC), mm((hw.RAIL_H + hw.TROUGH_INTO_PLATE) * SC), fill=1)
c.setFillColor(HexColor('#CFE6E4'))
c.rect(X(hw.SADDLE_X - hw.SADDLE_LEN_X / 2), Z(hw.PLATE_Z), mm(hw.SADDLE_LEN_X * SC), mm((hw.SADDLE_TOP_Z - hw.PLATE_Z - hw.SADDLE_V_DEPTH) * SC), fill=1)
# nominal board
c.setStrokeColor(GOLD)
c.setDash(mm(1.4), mm(0.9))
c.rect(X(hw.ANT_END_X), Z(hw.PCB_UNDER_Z), mm(hw.PCB_L * SC), mm(hw.PCB_T * SC))
c.rect(X(xs[0] - 1.27), Z(hw.PCB_UNDER_Z - hw.HDR_BODY_H), mm(hw.HDR_PINS * hw.HDR_PITCH * SC), mm(hw.HDR_BODY_H * SC))
for x in xs:
    c.rect(X(x - hw.HDR_PIN_SQ / 2), Z(hw.PCB_UNDER_Z - hw.HDR_BODY_H - hw.HDR_PIN_BELOW_BODY), mm(hw.HDR_PIN_SQ * SC), mm(hw.HDR_PIN_BELOW_BODY * SC))
c.rect(X(hw.USB_END_X - 1.0), Z(hw.CABLE_CENTRE_Z - hw.USB_PLUG_H / 2), mm(hw.USB_PLUG_L * SC), mm(hw.USB_PLUG_H * SC))
c.rect(X(hw.ANT_END_X + 7), Z(hw.PCB_TOP_Z), mm(20 * SC), mm(hw.CAMERA_STACK_ABOVE_PCB * SC))
c.setDash()
txt('camera + SD stack (estimate)', X(hw.ANT_END_X + 8), Z(hw.PCB_TOP_Z + 2.4), 6, GOLD)
txt('Micro-B plug (worst case %g x %g)' % (hw.USB_PLUG_L, hw.USB_PLUG_H), X(hw.USB_END_X), Z(hw.CABLE_CENTRE_Z + hw.USB_PLUG_H / 2 + 0.8), 6, GOLD)
txt('saddle', X(hw.SADDLE_X), Z(hw.PLATE_Z + 0.6), 5.5, TEAL, anchor='c')
levels = [(0, 'Z 0.00 skin face'), (hw.PLATE_Z, f'Z {hw.PLATE_Z:.2f} plate top'),
          (hw.PLATE_Z + hw.RAIL_H, f'Z {hw.PLATE_Z + hw.RAIL_H:.2f} rail top = header seat'),
          (hw.PCB_UNDER_Z, f'Z {hw.PCB_UNDER_Z:.2f} PCB underside'), (hw.PCB_TOP_Z, f'Z {hw.PCB_TOP_Z:.2f} PCB top = pillar top'),
          (hw.PCB_TOP_Z + hw.CAMERA_STACK_ABOVE_PCB, f'Z {hw.PCB_TOP_Z + hw.CAMERA_STACK_ABOVE_PCB:.2f} est. lens top (UNVERIFIED)')]
for z, lab in levels:
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.3)
    c.line(X(-hw.PLATE_X / 2) - mm(4), Z(z), X(-hw.PLATE_X / 2) - mm(1), Z(z))
    txt(lab, X(-hw.PLATE_X / 2) - mm(5), Z(z) - 2, 5.6, GRAY, anchor='r')
stack = (hw.PILLAR_TOP_Z + hw.CLIP_T) - hw.HEAD_POCKET_DEPTH
y0 = oy - mm(16)
rows = [
    'HEIGHT STACK (nominal):  plate %.1f  +  rail %.1f  +  header plastic %.2f  +  PCB %.1f (ASSUMED)  =  %.2f to PCB top.' % (
        hw.PLATE_Z, hw.RAIL_H, hw.HDR_BODY_H, hw.PCB_T, hw.PCB_TOP_Z),
    'Pin tips end %.2f above the blind trough floor; %.1f mm of solid plate stays between pins and skin.' % (
        hw.PCB_UNDER_Z - hw.HDR_BODY_H - hw.HDR_PIN_BELOW_BODY - (hw.PLATE_Z - hw.TROUGH_INTO_PLATE), hw.PLATE_Z - hw.TROUGH_INTO_PLATE),
    'Open air gap under the ESP-32S can: %.2f mm. Under the Micro-B overmold: %.2f mm. Nothing encloses the board.' % (
        hw.PCB_UNDER_Z - hw.MODULE_H - hw.PLATE_Z, hw.CABLE_CENTRE_Z - hw.USB_PLUG_H / 2 - hw.PLATE_Z),
    'FASTENERS x4: M3 pan head, head in skin-side pocket, shank up through pillar and retainer slot, M3 nut on top.',
    '   Grip (head seat to retainer top) = %.2f mm. Nut 2.4.  M3x16: %.2f mm thread past nut.  M3x20: %.2f.  M3x15: TOO SHORT.' % (
        stack, 16 - stack - 2.4, 20 - stack - 2.4),
    '   Nylon (PA66) screws and nuts preferred. Steel only if the nut cannot reach a solder joint; excess thread points away from skin.',
    'IF THE REAL PCB IS THINNER THAN %.1f: add an M3 nylon washer or 0.5 mm shim under the retainer tip; never over-tighten.' % hw.PCB_T,
    'IF HEADERS ARE NOT FITTED, OR POINT TO THE CAMERA FACE: STOP. This carrier does not apply; re-measure and re-parametrise.',
    'PRINT: PETG, 0.2 mm layers, 0.4 nozzle, 4 perimeters, 5 top/bottom layers, >= 40 % infill, skin face on the bed, no supports',
    '   (pocket ceilings are 6.6 mm bridges). PLA softens near 55-60 C and is not recommended next to a 5 V regulator.',
]
for i, r in enumerate(rows):
    txt(r, mm(15), y0 - mm(i * 4.8), 6.8, NAVY)
ruler(mm(22))
c.showPage()

# ------------------------------------------------------------------ page 3: retainer + gauge
header('MicroScan V5 | Sheet 3 of 3 | Retainer 4:1 and 1:1, PCB gauge 1:1',
       'Cut out or print the gauge outline; lay the real board on it BEFORE printing the carrier.')
ox, oy = mm(60), PH - mm(62)
SC = 4.0
X = lambda v: ox + mm(v * SC)
Y = lambda v: oy + mm(v * SC)
bx0 = -hw.CLIP_L / 2 + hw.CLIP_BODY_SHIFT_OUT
c.setStrokeColor(TEAL)
c.setLineWidth(1.0)
c.roundRect(X(bx0), Y(-hw.CLIP_W / 2), mm(hw.CLIP_L * SC), mm(hw.CLIP_W * SC), mm(1.0 * SC))
c.roundRect(X(-hw.CLIP_SLOT_L / 2), Y(-hw.CLIP_SLOT_W / 2), mm(hw.CLIP_SLOT_L * SC), mm(hw.CLIP_SLOT_W * SC), mm(hw.CLIP_SLOT_W / 2 * SC))
dim_h(bx0, bx0 + hw.CLIP_L, -hw.CLIP_W / 2 - 1.6, f'{hw.CLIP_L:.1f}', X, Y)
dim_v(-hw.CLIP_W / 2, hw.CLIP_W / 2, bx0 + hw.CLIP_L + 1.4, f'{hw.CLIP_W:.1f}', X, Y)
dim_h(-hw.CLIP_SLOT_L / 2, hw.CLIP_SLOT_L / 2, hw.CLIP_W / 2 + 0.8, f'slot {hw.CLIP_SLOT_L:.1f} x {hw.CLIP_SLOT_W:.1f}', X, Y)
txt('<- this end over the PCB edge', X(bx0), Y(0) - 2, 6, GOLD)
txt(f'thickness {hw.CLIP_T:.1f}; fillet R1; print flat; qty 4', X(bx0), Y(-hw.CLIP_W / 2 - 4.2), 6.5, NAVY)
# 1:1 retainer
SC = 1.0
ox2, oy2 = mm(150), PH - mm(62)
c.roundRect(ox2 + mm(bx0), oy2 - mm(hw.CLIP_W / 2), mm(hw.CLIP_L), mm(hw.CLIP_W), mm(1.0))
c.roundRect(ox2 - mm(hw.CLIP_SLOT_L / 2), oy2 - mm(hw.CLIP_SLOT_W / 2), mm(hw.CLIP_SLOT_L), mm(hw.CLIP_SLOT_W), mm(hw.CLIP_SLOT_W / 2))
txt('1:1', ox2, oy2 - mm(8), 6.5, GRAY, anchor='c')
lo = hw.clip_overlap(-(hw.CLIP_SLOT_L - hw.CLIP_SLOT_W) / 2)
hi = hw.clip_overlap((hw.CLIP_SLOT_L - hw.CLIP_SLOT_W) / 2)
txt('Edge overlap adjustable %.2f ... %.2f mm about the bolt. SET 1.0 mm: more than ~1.15 mm reaches the header solder fillets.' % (lo, hi),
    mm(15), PH - mm(96), 7, NAVY)
# gauge 1:1
ox, oy = PW / 2, PH - mm(140)
X = lambda v: ox + mm(v - hw.BOARD_CX)
Y = lambda v: oy + mm(v)
c.setStrokeColor(GOLD)
c.setLineWidth(1.0)
c.rect(X(hw.ANT_END_X), Y(-hw.PCB_W / 2), mm(hw.PCB_L), mm(hw.PCB_W))
c.rect(X(hw.USB_END_X - 1.5), Y(-4), mm(1.5), mm(8))
for x in xs:
    for s in (-1, 1):
        c.circle(X(x), Y(s * half_row), mm(0.6))
txt('ANTENNA END', X(hw.ANT_END_X + 1.5), Y(-1), 6, GOLD)
txt('USB', X(hw.USB_END_X - 8), Y(-1), 6, GOLD)
txt('HW-818 NOMINAL GAUGE - DO NOT MOUNT', X(hw.BOARD_CX), Y(4), 6.5, GOLD, anchor='c')
dim_h(hw.ANT_END_X, hw.USB_END_X, -hw.PCB_W / 2 - 4, f'{hw.PCB_L:.1f} [seller datasheet, UNVERIFIED]', X, Y)
dim_v(-hw.PCB_W / 2, hw.PCB_W / 2, hw.ANT_END_X - 5, f'{hw.PCB_W:.1f}', X, Y)
dim_v(-half_row, half_row, hw.USB_END_X + 5, f'{hw.HDR_ROW_SPACING:.2f}', X, Y)
dim_h(hw.ANT_END_X, xs[0], hw.PCB_W / 2 + 3, f'{hw.HDR_PIN1_FROM_ANT_END:.1f} [photo +-1]', X, Y)
y0 = oy - mm(hw.PCB_W / 2 + 14)
rows = [
    'MEASURE ON THE REAL BOARD AND WRITE HERE BEFORE PRINTING (edit the same names in cad/build_hardware_v5.py):',
    '  PCB_L ______  PCB_W ______  PCB_T ______  HDR_ROW_SPACING ______  HDR_PIN1_FROM_ANT_END ______',
    '  HDR_PIN_BELOW_BODY ______   headers fitted, pins away from camera face?  YES / NO',
    '  USB receptacle on the module face at the end opposite the antenna?  YES / NO     plug overmold L x W x H ______',
    '  tallest part under the PCB ______ (must be < %.1f)   PCB silk says HW-818?  YES / NO' % (hw.PCB_UNDER_Z - hw.PLATE_Z),
    'Accept the carrier only if every pin drops into a trough without force and the board sits flat on both rails.',
]
for i, r in enumerate(rows):
    txt(r, mm(15), y0 - mm(i * 5.2), 7, NAVY)
ruler(mm(22))
c.save()

# ------------------------------------------------------------------ previews from the actual CAD
# Small orthographic z-buffer rasteriser (numpy only) so occlusion is exact; matplotlib's 3D
# painter sorting mis-orders large flat faces.
from PIL import Image, ImageDraw, ImageFont


def faces_of(wp, tol=0.08):
    verts, tris = wp.val().tessellate(tol, 0.2)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    return v[np.array(tris)]


def view_matrix(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    fwd = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])   # from scene toward the camera
    right = np.cross([0, 0, 1.0], fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    return np.vstack([right, up, fwd])


def render(path, title, parts, elev, azim, px_per_mm=13.0, size=(1500, 1000), ss=2):
    W, H = size[0] * ss, size[1] * ss
    R = view_matrix(elev, azim)
    light = R.T @ np.array([-0.35, 0.45, 0.82])
    light /= np.linalg.norm(light)
    zbuf = np.full((H, W), -1e9)
    img = np.full((H, W, 3), 255, dtype=np.uint8)
    sc = px_per_mm * ss
    for wp, rgb in parts:
        f = faces_of(wp)
        n = np.cross(f[:, 1] - f[:, 0], f[:, 2] - f[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ln[ln == 0] = 1
        n = n / ln[:, None]
        facing = n @ R[2]
        shade = 0.30 + 0.70 * np.abs(n @ light)
        cam = f @ R.T                                  # (T,3,3): x right, y up, z toward camera
        sx = W / 2 + cam[:, :, 0] * sc
        sy = H / 2 - (cam[:, :, 1] - 2.0) * sc
        sz = cam[:, :, 2]
        for t in np.nonzero(facing > 1e-6)[0]:
            x, y, z = sx[t], sy[t], sz[t]
            x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), W - 1))
            y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), H - 1))
            if x1 < x0 or y1 < y0:
                continue
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-12:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
            if not inside.any():
                continue
            depth = w0 * z[0] + w1 * z[1] + w2 * z[2]
            zb = zbuf[y0:y1 + 1, x0:x1 + 1]
            win = inside & (depth > zb)
            zb[win] = depth[win]
            img[y0:y1 + 1, x0:x1 + 1][win] = np.clip(np.array(rgb) * shade[t] * 255, 0, 255).astype(np.uint8)
    im = Image.fromarray(img).resize(size, Image.LANCZOS)
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    d.text((size[0] / 2, 34), title, fill=(16, 35, 51), font=big, anchor='mm')
    d.text((size[0] / 2, size[1] - 46), 'Rendered from the cad/build_hardware_v5.py solids (z-buffer raster of the tessellated B-rep).', fill=(90, 100, 115), font=small, anchor='mm')
    d.text((size[0] / 2, size[1] - 22), 'Any board shown is a NOMINAL, UNVERIFIED keep-out envelope. Nothing has been printed or assembled.', fill=(179, 38, 30), font=small, anchor='mm')
    im.save(path, optimize=True)


CARRIER = (0.62, 0.82, 0.86)
CLIPC = (0.0, 0.55, 0.50)
ENV = {'pcb': (0.13, 0.15, 0.14), 'header_bodies': (0.28, 0.28, 0.28), 'header_pins': (0.88, 0.72, 0.2),
       'solder_tails': (0.88, 0.72, 0.2), 'module': (0.75, 0.75, 0.75), 'usb_plug': (0.33, 0.33, 0.37),
       'camera_stack': (0.58, 0.58, 0.64)}
base_parts = [(hw.carrier, CARRIER)] + [(cl, CLIPC) for cl in hw.placed_clips()]
render(OUT / 'V5_Carrier_3D_Preview.png', 'MicroScan V5 open camera carrier + 4 retainers', base_parts, 34, -62)
render(OUT / 'V5_Nominal_Assembly_3D_Preview.png', 'MicroScan V5 with NOMINAL HW-818 envelope and Micro-B plug',
       base_parts + [(v, ENV[k]) for k, v in hw.envelope.items()], 30, -62)
render(OUT / 'V5_Underside_3D_Preview.png', 'MicroScan V5 skin-side face: recessed heads, flush tie channel, no pin break-through',
       [(hw.carrier, CARRIER)], -52, -62, px_per_mm=11.0)
print('WROTE', pdf_path.name, 'and 3 CAD-derived previews')
