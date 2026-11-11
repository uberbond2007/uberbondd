# V5 changelog, diffs and rollback

**Rollback:** `source_v4/MicroScan_Visible_Hardware_Prototype_V4.zip` is the untouched input
(SHA-256 `274eca7f…94898e35`) and `source_v4/extracted_unmodified/` is its exact extraction. Delete
everything else and V4 is back. No V4 file was modified in place, and no V4 receipt was removed.

## Carried over byte-identical

`host/microscan_usb_packet.py`, `host/tests/test_usb_packet.py`, `host/tests/test_live_serial.py`,
`bench/packet_emitter.cpp`. The V4 tests still pass against the V5 host tool.

## Modified (new files; unified diffs in `docs/diffs/`)

| V5 file | From | Change | Diff |
|---|---|---|---|
| `host/serial_capture.py` | V4 same name | + baud 230400/460800/921600; + `--wait-ready`; fast fail on firmware `ERROR` lines; HUPCL cleared; reports timing. Still one request, no retry. | `host_serial_capture_v4_to_v5.diff` |
| `firmware/microscan_hw818_candidate/src/main.cpp` | `firmware/VISIBLE_USB_CAMERA_DIAGNOSTIC.ino` | Gates kept at 0 and still hard-coded; RAII indicator scope + guarded frame grab; latch re-check before sending; RGB565 → software JPEG fallback for JPEG-less sensors; `INFO`, `LAMPTEST`; selectable baud; capture-locked bring-up mode; CRC and wire format unchanged. | `firmware_v4_ino_to_v5_main_cpp.diff` |
| `cad/build_hardware_v5.py` | `cad/build_hardware_v2.py` | Re-layout for the photographed HW-818 (see `docs/MECHANICAL_V5.md`). | `cad_v2_to_v5.diff` |
| `BOM.csv` | V4 `BOM.csv` | Re-priced from pages fetched 2026-11-11; line totals; evidence class per line. | `bom_v4_to_v5.diff` |

## New

`checks/validate_cad_v5.py`, `checks/audit_v2_against_hw818.py`, `checks/test_firmware_interlock.py`,
`checks/test_firmware_source.py`, `checks/test_firmware_build.py`, `checks/test_bom.py`,
`checks/optics_and_transfer_budget.py`, `host/tests/test_v5_adversarial.py`, firmware mock HAL,
`drawings/generate_drawings_v5.py`, `tools/run_verification_v5.py`, `tools/package_release_v5.py`,
all of `docs/`, `diagrams/`, `evidence/`, `PHYSICAL_BLOCKERS.md`.

## V4 statements corrected by evidence

| V4 statement | Now |
|---|---|
| Board footprint 40 × 27 × 12 mm (seller) | Not on the ME-31692 page; HW-818 is listed elsewhere as 27 × 48.5 × 4.5 mm and the photo agrees. |
| Full board "advertised with OV2640" | Product is now named "ESP32-CAM RHYX-M21-45 Camera (with micro usb)". |
| ~180 mA @ 5 V (seller) | Not on the ME-31692 page; that figure is on another shop's classic ESP32-CAM page. |
| Cable 45 EGP; standalone sensor 120 EGP | 49.50 and 99.00. |
| "Local 2.4 GHz Wi-Fi → browser" in the V4 block diagram | Removed. V5 firmware links no Wi-Fi code (checked in the ELF). |
| "Authoring environment has no ESP32 toolchain" | A pinned toolchain was installed and a real build run. |

## Failures met while building V5 (kept, not hidden)

1. First toolchain attempt (download of a standalone compiler manager) was refused by the sandbox
   policy; PlatformIO from PyPI was used instead.
2. First CAD validation run: 99/100 — the failing item was a sign error in the *check* (tail-gap
   formula), not the CAD. Fixed in the check.
3. First retainer geometry gave 3.5 mm nominal overlap, which would sit on the solder fillets;
   the retainer body was shifted so mid-slot gives 1.5 mm and the recommended setting is 1.0 mm.
4. First 3D preview was depth-sorted wrongly by the renderer; faces are now drawn in one collection.
5. New host tests failed twice on first run: a pseudo-terminal echo race and a blocking read in the
   *test fixture*. Fixed in the fixture; product code unchanged.
6. Firmware source tests failed three times on first run: the test banned the substring `BLE`
   (present in "VISIBLE"), a comment contained `upload_port`, and a status string contained `wifi`.
   Test and strings corrected.
7. Interlock test expectation was wrong once: `CAPTURE` followed by a control character is trimmed to
   `CAPTURE` (behaviour inherited from V4) and does trigger. The test now uses genuinely different
   commands.
8. Two retailer pages timed out through the fetch agent; fetched directly instead. Two forum pages
   (Arduino forum 429, esp32.com bot wall) were never read.
