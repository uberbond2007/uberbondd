# Optics gate — independent of everything else

**Status: OPEN. No photograph exists.** Megapixels are not sharpness, and nothing below is a
measurement. Numbers come from `checks/optics_and_transfer_budget.py`
(`reports/OPTICS_AND_TRANSFER_BUDGET.json`).

## What is known about the sensor–lens assembly

| Property | Value | Grade |
|---|---|---|
| Module | RHYX M21-45, 2 MP, 1600 × 1200 max | RETAILER CLAIM |
| Output | RGB565 / YCbCr422 / raw Bayer, **no hardware JPEG** | RETAILER CLAIM + THIRD-PARTY |
| Lens | integrated, fixed focus | RETAILER CLAIM |
| Focal length, field of view, aperture | — | UNKNOWN |
| Factory focus distance / minimum focus | — | UNKNOWN |
| Largest still the ESP32 can hold as RGB565 | SVGA comfortably; XGA possibly; UXGA no (3.84 MB) | CALCULATED |
| Resolution a seller reports as working | QVGA | THIRD-PARTY |

## What pixel count alone allows (upper bound)

Target used: capital letters ≥ 25 px tall (Tesseract's guidance is roughly 20–30 px), 10 pt text.

| Mode | Widest field that still meets the target | Whole A4 short side (210 mm) |
|---|---|---|
| UXGA 1600 px (hardware-JPEG sensors only) | 158 mm | 18.8 px caps — below target |
| XGA 1024 px | 101 mm | 12.0 px |
| SVGA 800 px (V5 default for this sensor) | 79 mm | 9.4 px |
| QVGA 320 px | 32 mm | 3.8 px |

So with the RHYX camera the realistic unit of capture is **a paragraph or a column about 8 cm wide,
not a page**, and only if the lens is actually sharp at the distance that gives that field. A Bayer
sensor converted to RGB565 and then JPEG delivers less real detail than its pixel count.

## Field width versus distance

Depends on a lens FOV nobody has published for this module. For an *assumed* horizontal FOV:

| Distance | 45° | 55° | 65° | 75° |
|---|---|---|---|---|
| 100 mm | 83 | 104 | 127 | 153 |
| 150 mm | 124 | 156 | 191 | 230 |
| 200 mm | 166 | 208 | 255 | 307 |
| 300 mm | 249 | 312 | 382 | 460 |

(mm). An 80 mm field would need roughly 60–100 mm working distance — close enough that a
fixed-focus lens set for room distances may be out of focus. That is the single biggest optical risk
and it cannot be resolved without a unit.

## Decision this informs

- **Keep ME-31692 (RHYX):** cheapest (499), matches the V5 carrier, but SVGA-class stills and a
  software encoder; legibility of small print is doubtful.
- **Switch to ME-11814 + ME-18384 (OV2640 + USB shield, 698):** hardware JPEG at UXGA (158 mm field
  at target), but a two-board stack the V5 carrier does not fit, and a different listing whose own
  sensor identity would again need checking on arrival.
- **Fit an OV2640 module to the HW-818:** no priced standalone OV2640 was found in Egypt today
  (the shop's "ov2640" URL is the RHYX part), so this is UNKNOWN.

## Closing the gate (physical)

One authorised, consented frame of a printed test page (6–12 pt lines plus a ruler) at three
measured distances, saved at original resolution with the firmware `INFO` line. Record the smallest
legible size by eye and by an OCR engine. Synthetic images are not accepted as evidence here.
