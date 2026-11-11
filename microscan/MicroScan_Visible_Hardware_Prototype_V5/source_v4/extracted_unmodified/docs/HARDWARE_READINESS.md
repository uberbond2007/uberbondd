# V2 hardware readiness matrix (strict status definitions)

| Subsystem | Status | Evidence | Missing gate |
|---|---|---|---|
| Camera board selection | RETAILER-ADVERTISED | Most RHYX listing | Exact board revision and fit |
| Carrier + edge retainers | **DIGITAL CAD VERIFIED** | STEP/STL + `checks/CAD_TEST_RESULTS.json` | Print, fastener fit, wrist comfort |
| 1:1 shop drawing | **PDF PRODUCED/RENDERED** | `templates/Hardware_Fit_Gauge_100pct.pdf` | Printer scale verification |
| USB power path | DESIGN ONLY | Existing board Micro-USB interface + retailer currents | Real voltage, temperature and supply |
| Camera cable/FPC | SUPPLIED WITH BOARD (retailer claim) | Most listing | FPC handling and mechanical fit |
| Camera firmware | NOT COMPILED/FLASHED | Espressif reference available | RHYX pin map and board behavior |
| Photo capture | NOT TESTED | none | Powered camera + actual JPEG |
| Android OnePlus connection | NOT TESTED | none | Phone/board Wi-Fi and firmware |
| Optical quality/OCR | NOT TESTED ON THIS CAMERA | none | Genuine photograph and transcription |
| Active capture indicator | NOT IMPLEMENTED | prominent passive label only | User-visible indicator confirmation |
| Egyptian complete price | **INCOMPLETE** | 499 EGP camera + optional advertised 45 EGP cable | Printed parts, straps, fasteners, power, delivery |
| Physical working prototype | **NOT BUILT** | no physical receipts | Fabrication + assembly + testing |

A 3D-printable STL is a geometric object, not a verified product assembly. Digital tests do not prove camera/electrical fit.
