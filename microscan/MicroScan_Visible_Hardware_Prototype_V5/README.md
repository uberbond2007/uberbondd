# MicroScan V5 — digital fabrication package for an open, visibly marked document camera

**Status: DIGITAL FABRICATION PACKAGE + FIRMWARE COMPILED (capture-locked bring-up image only).**
**Not printed. Not assembled. Not flashed. No photograph has ever been taken with this design.**

This is the successor of `MicroScan_Visible_Hardware_Prototype_V4.zip`
(SHA-256 `274eca7fa3e85b6563b47045f1934f04a302df59b2dd993af538b8e494898e35`), which is preserved
byte-for-byte in `source_v4/`. Nothing in V4 was edited in place; every change is a new file and is
listed with diffs in `docs/V5_CHANGELOG_AND_DIFF.md`.

The device is a plainly labelled wrist-top carrier for a bare ESP32 camera board on a visible USB
cable. It has no radio code, no storage, no background or repeated capture, and nothing covers the
lens, the engraved `CAMERA` labels or the capture light. It is not designed for, and must not be
adapted to, concealed or unauthorised capture.

## What changed and why (one paragraph)

Reading the retailer's own photographs for the 499 EGP item showed a single-PCB board marked
**HW-818** carrying a camera labelled **RHYX M21-45**, with header pins factory-soldered away from
the camera face and the Micro-USB socket on the opposite face. Three consequences: (1) the V2/V4
carrier cannot hold that board — the pins would pass through the plate toward the skin and there is
no room for a USB plug (`checks/V2_AUDIT_FINDINGS.json`); (2) the same shop states the RHYX M21-45
has **no hardware JPEG**, so the V4 firmware (JPEG, UXGA) would fail at camera init on it; (3) the
figures V4 used for this item (40×27×12 mm, 180 mA, OV2640) are no longer on that product page.
V5 therefore re-lays the carrier inside the same 84×58 mm footprint, adds an RGB565 → software-JPEG
path and a capture-indicator interlock to the firmware, and keeps both V4 safety gates closed.

## Start here

| Read | For |
|---|---|
| `PHYSICAL_BLOCKERS.md` | the three things only the owner can do |
| `docs/READINESS.md` | what is and is not established |
| `docs/HARDWARE_IDENTITY.md` | board / sensor / LED evidence, graded |
| `docs/HARDWARE_VERIFICATION_CHECKLIST.md` | the short bench procedure once a board exists |
| `drawings/MicroScan_V5_Drawings_1to1.pdf` | dimensioned 1:1 drawings (print at 100 %) |
| `reports/V5_EXECUTION_RECEIPT.json` | every command that was run, with exit codes and tool versions |

## Contents

- `cad/` — `build_hardware_v5.py` (editable parametric source), STEP + STL for the carrier, the
  retainer and a PCB comparison gauge, plus a reference-only nominal assembly STEP.
- `drawings/` — generator, 3-sheet 1:1 PDF, three previews rendered from the CAD solids.
- `firmware/microscan_hw818_candidate/` — PlatformIO project (pinned `espressif32@6.9.0`), mock HAL.
- `host/` — one-shot capture tool and packet parser, with tests. `bench/` — C++ packet emitter.
- `checks/` — CAD, firmware, BOM and audit checks. `tools/` — verification runner and packager.
- `docs/`, `diagrams/`, `evidence/`, `reports/`, `BOM.csv`, `MANIFEST.json`.

## Reproduce

```sh
python -m venv venv && . venv/bin/activate
pip install -r requirements-lock.txt        # cadquery 2.8.0, trimesh, pillow, numpy, reportlab, platformio
python tools/run_verification_v5.py        # all digital checks; writes reports/V5_EXECUTION_RECEIPT.json
python tools/package_release_v5.py         # MANIFEST.json + ZIP next to this folder
```

Needs GNU g++, the fonts DejaVu Sans and Liberation Sans, and (first firmware build only) network
access for PlatformIO to fetch the pinned toolchain. Without PlatformIO the build tests are skipped
and the receipt says so.

No purchase, message, order, print, flash or device change was made in producing this package.
