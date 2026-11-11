# Hardware identity — evidence graded

Grades: **VERIFIED** (manufacturer software/docs read directly) · **RETAILER CLAIM** (listing text) ·
**RETAILER PHOTO** (catalogue image, not the delivered unit) · **THIRD-PARTY** · **UNKNOWN**.
Record IDs refer to `evidence/WEB_EVIDENCE_2026-11-11.json`. No physical board was available.

| Question | Finding | Grade | Evidence |
|---|---|---|---|
| What is sold at 499 EGP? | "ESP32-CAM RHYX-M21-45 Camera (with micro usb)", SKU ME-31692, in-stock flag | RETAILER CLAIM | E1 |
| Board model | Silk **HW-818**; one PCB; ESP-32S module; Micro-USB, RST and FLASH on the module face | RETAILER PHOTO | E2 |
| Is it a two-board ESP32-CAM + MB stack? | Text says "micro USB base"; the photos show one integrated PCB. Conflict → treat as HW-818 until a unit is seen | RETAILER CLAIM vs PHOTO | E1, E2 |
| Outline | 27 × 48.5 × 4.5 mm for model HW-818; photo aspect 1.81 agrees; 40 × 27 does not | THIRD-PARTY + PHOTO | E13, E2 |
| Where did "40×27×12 mm, 180/310 mA" come from? | Those figures are on a different shop's classic ESP32-CAM page; they are not on the ME-31692 page today | RETAILER CLAIM (other product) | E12, E1 |
| Camera module | Flex label **RHYX M21-45** | RETAILER PHOTO + CLAIM | E2, E3, E1 |
| Sensor chip | Reported as GalaxyCore GC2145 (driver PID 0x2145) | THIRD-PARTY | E14, E15 |
| Hardware JPEG | **Not supported**; RGB565 / YCbCr422 / raw Bayer | RETAILER CLAIM + THIRD-PARTY | E4, E14, E15 |
| Contradiction | One hobby repo says JPEG at VGA works; no evidence shown | THIRD-PARTY (weak) | E16 |
| Working resolution on ESP32-CAM | Seller guide: QVGA; says SVGA/UXGA RGB565 crashes a *stream* | THIRD-PARTY | E14 |
| Lens | Fixed focus; focal length, FOV and focus distance not stated anywhere | RETAILER CLAIM / UNKNOWN | E4 |
| Camera pin map | Seller guide and hobby repo use Espressif `CAMERA_MODEL_AI_THINKER` for this camera on "ESP32-CAM" boards | THIRD-PARTY | E14, E16 |
| HW-818 schematic | Not obtained; a forum thread that may link one could not be read | UNKNOWN | E18 |
| Header pinout | 5V GND IO12 IO13 IO15 IO14 IO2 IO4 / 3V3 IO16 IO0 GND VCC U0R U0T GND — same order as AI-Thinker | RETAILER PHOTO | E2 |
| Headers fitted, direction | Fitted; pins away from camera face | RETAILER PHOTO | E3 |
| USB bridge chip | Listing never names it; URL slug says ch340; an 8-pin IC sits by the USB socket in the photo | UNKNOWN (likely CH340-class) | E1, E2 |
| Auto-reset on DTR/RTS | Other seller describes holding FLASH while plugging in → may be absent | THIRD-PARTY / UNKNOWN | E13 |
| White LED on camera face | Present, corner nearest the USB end | RETAILER PHOTO | E2, E3 |
| Net driving that LED | GPIO4 on AI-Thinker-compatible boards; not confirmed for HW-818 | UNKNOWN | — |
| Second LED ("LED1") | On the module face (faces the plate when mounted) → not usable as a visible indicator | RETAILER PHOTO | E2 |
| PSRAM | Not stated for ME-31692 | UNKNOWN | E1 |
| Supply | "Use a stable 5V 2A supply" | RETAILER CLAIM | E1 |
| Driver support in the pinned toolchain | `GC2145_PID = 0x2145`, `CONFIG_GC2145_SUPPORT=y`, software JPEG encoder available | VERIFIED | E17 |

## What this permits

- Designing the carrier around the HW-818 photo layout, with every board dimension flagged UNVERIFIED
  and a gauge + measurement form to correct it.
- Writing firmware that handles both sensor classes and compiling it.

## What it does not permit

- Setting `MICROSCAN_BOARD_PINS_VERIFIED` or `MICROSCAN_VISIBLE_INDICATOR_VERIFIED` to 1.
  A pin map inferred from sellers and a LED net inferred from a look-alike board are not verification.
- Any statement about image quality, current draw, temperature, or Android use.
