# MicroScan V3: execution and remaining blockers (10 November 2026)

## What is actually completed
- Reused and independently rechecked the existing visible, open-carrier V2 CAD: STEP, STL, printable gauge and fabrication drawings.
- Authored USB-tethered, **operator-initiated-only** ESP32-CAM diagnostic firmware source for a conspicuous camera. The operator must issue a serial `CAPTURE` command; there is no Wi-Fi, background streaming, or hidden button trigger.
- Firmware **deliberately refuses to compile** by default until the physical RHYX board pinout and capture-indicator GPIO have been confirmed. The AI-Thinker pins are provisional; vendor listing does not include a RHYX board wiring schematic.
- Implemented a host-side serial JPEG decoder with CRC32, dimension checks, strict JPEG decoding, and no network dependencies. The host-side decoder can be tested against generated image frames.
- Added release integrity and transport-frame tests. Software tests do not show real camera operation.

## Evidence level
- CAD export files: GENERATED and digitally checked (carry-over V2).
- USB serial frame parser: IMPLEMENTED and locally tested with synthetic JPEG.
- Diagnostic firmware source: WRITTEN, **NOT COMPILED**, **NOT FLASHED**, **NOT TESTED on hardware**.
- Printed plastic parts: **NOT BUILT**.
- Electrical assembly: **NOT BUILT**.
- Original camera photograph: **NOT TESTED**.
- OnePlus 15 direct serial support: UNKNOWN, NOT TESTED.
- Stable physical capture/thermal/cuff comfort: UNKNOWN, NOT TESTED.

## Remaining physical gates (not solvable in this runtime)
1. **Hardware acquisition, board revision, and actual dimensions:** source an actual camera board, check camera connector positions, safe retention contact zones, verify its camera GPIO mapping and indicator circuitry. User-approved spend required; no purchases authorized.
2. **Physical fabrication and assembly:** print STEP/STL design, fit nonconductive hardware, use a certified USB 5V power source and keep the circuit fully visible. Check mechanical/electrical safety.
3. **Real end-to-end evidence:** compile/flash on verified board, confirm visible capture indication, capture a genuine full-resolution JPEG and verify focus/optics/temperature and image transfer with the actual phone.

These gates are necessary because a simulated circuit and CAD geometry cannot prove a camera physical prototype works. Do not call this release a functional hardware device.

## Provenance caveats
- Most Electronics advertises ESP32 S-CAM-CH340 with OV2640 for 499 EGP, but RHYX-M21-45 sometimes names the *camera sensor module* rather than the entire microcontroller board.
- A third-party GitHub example reports AI-Thinker GPIO equivalence for RHYX M21-45, but it does NOT establish the precise board revision/LED pin map for the Most Electronics item.
- No seller has provided a mechanical or electrical drawing for the exact board revision.
- No additional expenditure was made.
