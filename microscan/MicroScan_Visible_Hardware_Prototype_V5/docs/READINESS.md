# Readiness — strict

Scale: RESEARCH → DIGITAL FABRICATION PACKAGE → FIRMWARE COMPILED → PHYSICAL ASSEMBLY → LIVE IMAGING VALIDATED.

**Reached: DIGITAL FABRICATION PACKAGE, and FIRMWARE COMPILED in the narrow sense below.**
**Not reached: PHYSICAL ASSEMBLY, LIVE IMAGING VALIDATED.**

| Subsystem | Status | Evidence | Missing |
|---|---|---|---|
| V4 archive integrity | VERIFIED | SHA-256 match; 42/42 manifest entries; 43 members | — |
| V4 digital checks | REPRODUCED 5/5 | `reports/V4_REPRODUCTION_RECEIPT.json` | — |
| Board identity | PHOTO + LISTING level | `docs/HARDWARE_IDENTITY.md` | a physical unit, a schematic |
| Sensor | RHYX M21-45, no hardware JPEG (claim) | E4, E14, E15 | PID read from a real unit |
| Carrier CAD V5 | DIGITAL, 100/100 self-consistency | `checks/CAD_V5_TEST_RESULTS.json` | measured board, a print, fit |
| 1:1 drawings | PRODUCED from CAD | `drawings/` | printed scale check |
| Firmware source | CANDIDATE, gates closed | `firmware/…/src/main.cpp` | physical verification of pins + LED |
| Firmware compile | **Capture-locked bring-up image compiles and links for ESP32** with a pinned toolchain; capture-capable image is refused by the compiler | `reports/FIRMWARE_BUILD_RECEIPT.json` | a capture-capable build (needs gates = 1) |
| Indicator interlock | Logic tested on a desktop mock (16 scenarios + mutation) | `checks/test_firmware_interlock.py` | LED identity, visibility, behaviour on hardware |
| Host transport | 36 tests incl. corruption, fragmentation, resync | `host/tests/` | a real serial device |
| Optics | CALCULATED bounds only | `docs/OPTICS_GATE.md` | any real frame |
| Android / phone use | NOT SUPPORTED, NOT TESTED | — | out of scope; phones untouched |
| Power, temperature | UNKNOWN | — | bench measurement |
| Cost | 653.02 EGP known; 4 lines unknown | `BOM.csv` | print quote, strap, pad, tie |
| Fabrication | **NOT DONE** | — | owner approval, a bureau |
| Flashing | **NOT DONE** | — | owner approval, a board |

"Firmware compiled" here means: this source cross-compiles and links against the Espressif camera
driver. The resulting image cannot take a picture, was not shipped, and was never run.
