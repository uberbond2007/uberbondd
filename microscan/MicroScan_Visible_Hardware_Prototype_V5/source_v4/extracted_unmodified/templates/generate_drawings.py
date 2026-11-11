"""Generate true 1:1 PDF and digital engineering previews.
Exact scale requires 100% printing with no fit-to-page adjustment.
"""
from pathlib import Path
import math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle,FancyBboxPatch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
ptmm=72/25.4
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
pdfmetrics.registerFont(TTFont('DejaVu',font))
page_w,page_h=A4
pdf=ROOT/'templates'/'Hardware_Fit_Gauge_100pct.pdf'
c=canvas.Canvas(str(pdf),pagesize=A4)
NAVY=HexColor('#102333');TEAL=HexColor('#027E76');GOLD=HexColor('#B46A19');GRAY=HexColor('#6A7787')

def mm(x):return x*ptmm

def txt(s,x,y,size=10,color=NAVY,font='DejaVu'):
    c.setFont(font,size);c.setFillColor(color);c.drawString(x,y,s)

def line(a,b,x1,y1,x2,y2):
    c.setStrokeColor(a);c.setLineWidth(b);c.line(x1,y1,x2,y2)

# A4 template 1:1 object units; origin device center.
c.setTitle('MicroScan Visible Camera - 1:1 Hardware Fit Gauge V2')
txt('MicroScan  |  Hardware Fit Gauge V2',mm(17),page_h-mm(20),17)
txt('PRINT 100% / ACTUAL SIZE. Turn OFF scaling. No physical board fit verified.',mm(17),page_h-mm(29),9,GOLD)
txt('Nominal board from retailer: 40 x 27 x 12 mm. Actual PCB revision unknown.',mm(17),page_h-mm(36),9,GRAY)
ox=page_w/2; oy=page_h-mm(90)
def X(x):return ox+mm(x)
def Y(y):return oy+mm(y)
# Outline is 84x58 mm
c.setStrokeColor(TEAL);c.setLineWidth(2)
c.roundRect(X(-42),Y(-29),mm(84),mm(58),mm(5),stroke=1,fill=0)
# strap slots
c.setStrokeColor(GRAY);c.setLineWidth(1)
for x in (-35,35):
    c.roundRect(X(x-2),Y(4-11),mm(4),mm(22),mm(0.6),stroke=1,fill=0)
# Board footprint
c.setDash(mm(1.6),mm(1.1));c.setStrokeColor(GOLD)
c.rect(X(-20),Y(4-13.5),mm(40),mm(27),stroke=1,fill=0);c.setDash()
# support pads
c.setStrokeColor(TEAL)
for x in (-17,17):
    for y in (-6,14):
        c.rect(X(x-2),Y(y-2),mm(4),mm(4),stroke=1,fill=0)
# M3 mounts
for x in (-26,26):
    for y in (-7,15):
        c.circle(X(x),Y(y),mm(3),stroke=1,fill=0)
        c.circle(X(x),Y(y),mm(1.65),stroke=1,fill=0)
# optional cable openings
for x in (-5.5,5.5):
    c.rect(X(x-1.35),Y(23-1.7),mm(2.7),mm(3.4),stroke=1,fill=0)
txt('BOARD (NOMINAL ONLY)',X(-18),Y(0),8,GOLD)
txt('CAMERA',X(-10),Y(-22.5),11,TEAL)
# dimension lines
line(GRAY,0.7,X(-42),Y(-35),X(42),Y(-35))
txt('84 mm',X(-7),Y(-39),9,GRAY)
line(GRAY,0.7,X(-48),Y(-29),X(-48),Y(29))
txt('58 mm',X(-60),Y(0),9,GRAY)
# 100mm ruler at 100% scale
ry=mm(44); start=mm(35)
line(NAVY,1.6,start,ry,start+mm(100),ry)
for i in range(11):
    x=start+mm(i*10)
    line(NAVY,1,x,ry-mm(3 if i%5==0 else 2),x,ry+mm(3 if i%5==0 else 2))
txt('100 mm printer calibration ruler (measure after printing)',start,ry+mm(8),8)
# secondary notes
note_y=mm(106)
notes=[
'Board outline is NOT a verified hole / component map.',
'All four retainers contact only a narrow edge region; check actual PCB first.',
'Do not route cables beneath skin. Camera must remain openly visible.',
'No purchase, printing, electrical connection or physical fitting has occurred.'
]
for ix,t in enumerate(notes):txt('• '+t,mm(17),note_y+mm((3-ix)*7),8.5,GRAY)
c.showPage()
# Page 2: z budget and parts
h=page_h
txt('MicroScan | Height and hardware stack (NOT to scale)',mm(17),h-mm(20),15)
txt('The V1 8.7mm number described printed geometry only, not total device thickness.',mm(17),h-mm(31),9,GOLD)
x0=mm(35); y0=mm(80); width=mm(100)
for label,z,height,color in [
    ('Printed base',0,3.2,HexColor('#BBCBD1')),
    ('Assumed underside clearance',3.2,3.5,HexColor('#CFE6E4')),
    ('Advertised assembled camera board height',6.7,12,HexColor('#E6D9B7'))
]:
    c.setFillColor(color);c.setStrokeColor(NAVY);c.setLineWidth(0.7)
    c.rect(x0,y0+mm(z),width,mm(height),stroke=1,fill=1)
    txt(f'{label}: {height:.1f} mm',x0+mm(4),y0+mm(z+height/2)-3,8)
txt('Estimated assembled thickness: 3.2 + 3.5 + 12 = 18.7 mm (NOT measured).',mm(17),mm(119),9,TEAL)
txt('Clamp height above base reaches 11.1 mm; camera board may be taller.',mm(17),mm(112),8.5,GRAY)
txt('M3 x 16 nylon screws/nuts are a provisional hardware size; verify before ordering.',mm(17),mm(105),8.5,GRAY)
txt('Power path:',mm(17),mm(89),12)
txt('Rated 5V USB supply -> visible USB cable -> built-in Micro-USB port -> ESP32/OV2640.',mm(17),mm(82),8.5)
txt('Local Wi-Fi transfer is firmware-dependent and NOT demonstrated on a board.',mm(17),mm(75),8.5,GRAY)
txt('Do not connect unknown camera wires, raw lithium cells, or new proprietary bus adapters.',mm(17),mm(68),8.2,GOLD)
c.save()

# PNG annotated plan (NOT necessarily printed to scale)
fig,ax=plt.subplots(figsize=(11,7.5));ax.set_aspect('equal')
ax.add_patch(FancyBboxPatch((-42,-29),84,58,boxstyle='round,pad=0,rounding_size=5',facecolor='#d7edf0',edgecolor='#027e76',lw=2.5))
for x in (-35,35):ax.add_patch(Rectangle((x-2,-7),4,22,fill=False,edgecolor='#567484',lw=1.4))
ax.add_patch(Rectangle((-20,-9.5),40,27,fill=False,edgecolor='#c27629',ls='--',lw=2))
for x in (-17,17):
 for y in (-6,14):ax.add_patch(Rectangle((x-2,y-2),4,4,facecolor='#74a6ab',edgecolor='#24566b'))
for x in (-26,26):
 for y in (-7,15):
  ax.add_patch(Circle((x,y),3,facecolor='white',edgecolor='#24475c',lw=1.5))
  ax.add_patch(Circle((x,y),1.65,facecolor='white',edgecolor='#24475c'))
for x in (-5.5,5.5):ax.add_patch(Rectangle((x-1.35,21.3),2.7,3.4,fill=False,edgecolor='#24475c'))
ax.text(0,-22,'CAMERA',ha='center',va='center',color='#027e76',fontsize=16,fontweight='bold')
ax.text(0,4,'40 x 27 mm BOARD ENVELOPE',ha='center',color='#bb6d1d',fontsize=9,fontweight='bold')
ax.annotate('',xy=(-42,-34),xytext=(42,-34),arrowprops={'arrowstyle':'<->','color':'#34495e'})
ax.text(0,-36.5,'84 mm',ha='center',color='#34495e')
ax.set_xlim(-48,48);ax.set_ylim(-41,40);ax.axis('off')
fig.suptitle('MicroScan V2 | Open Camera Carrier (illustrative CAD plan)',fontsize=16)
fig.text(.5,.06,'RETENTION + connector clearance require measurement on the physical board. No hidden camera.',ha='center',fontsize=10)
fig.savefig(ROOT/'diagrams'/'V2_Top_View.png',dpi=180,bbox_inches='tight',facecolor='white')
plt.close(fig)
print('WROTE',pdf)
