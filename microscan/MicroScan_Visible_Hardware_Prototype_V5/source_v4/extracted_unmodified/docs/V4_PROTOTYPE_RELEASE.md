# MICROSCAN V4 DIGITAL PREFLIGHT: hardware status, facts, and limits

**Date:** 2026-11-10. **Scope:** an **open, conspicuous camera** on a laboratory/wrist-top fixture, not a disguised button camera. This deliverable is *not* a physical hardware prototype.

## Real work completed in V4

- Preserved V2 mechanical STEP/STL files and their dimensional checks. Nominal carrier **84×58 mm**, not a 12 mm imaging device; fit against any real PCB remains unmeasured.
- Added `host/serial_capture.py`: explicit foreground one-shot request over a **USB-serial** connection. Requires `--indicator-confirmed`, refuses automatic/repeated acquisition; uses raw POSIX serial and captures one CRC-checked JPEG. No networking or recording service.
- Added tests using Linux pseudo-terminals: actual local device-file I/O with fragmented frames, false headers, CRC corruption and timeouts. This tests OS serial handling, **not a camera**.
- Added portable C++ packet emitter using the same CRC and framing algorithm as the firmware source. It was compiled with GNU g++ and verified against Python's JPEG decoder. This is **not an ESP32 firmware build**.
- Introduced a reproducible release generator and auditable test receipts.

## Discovery that changes the buying decision

Most Electronics currently has **two distinct items** involving the RHYX-M21-45 name:

1. A full ESP32 S-CAM-CH340 USB board **advertised with OV2640** for 499 EGP, footprint 40×27×12 mm [full board listing](https://mostelectronic.com/shop/arduino-development-boards/esp32-cam-ov2640-ch340-camera-micro-usb/).
2. A **standalone RHYX-M21-45** camera sensor for 120 EGP; the seller explicitly says this sensor **is not OV2640** and may require different firmware settings [sensor listing](https://mostelectronic.com/shop/sensors/ov2640-camera-for-esp32-cam/).

The full board listing and RHYX label therefore do **not** establish which exact sensor and flash circuit will be delivered or whether it matches the provisional AI-Thinker Arduino camera pin map. This uncertainty is not a software bug. No purchase is approved.

## Explicit physical blockers

1. **Unverified specific board revision:** PCB/LED pinout and actual included sensor, port orientation, 5V input details and position measured on a real unit. The firmware's `#error` guards must remain active until this is established. Do not edit the source flags speculatively.
2. **Physical manufacturing and assembly:** no purchased board, actual printed chassis, fastening measurements, electrical inspection, skin/temperature tests, or safety-qualified power wiring.
3. **Real sensor image and Android:** no flashed firmware, no actual OV2640 JPEG, no verified phone USB-serial access, no real optical test.

No system here is 12 mm overall. This is not an instruction kit for concealing a camera or unauthorized exams.

## Serial transport limitations

- USB on an ESP32-CAM-CH340 board is ordinarily connected to its **USB-UART converter**, not a native USB Video Class webcam. The `MSJ1` framing used here is a custom serial protocol and cannot be assumed compatible with Camera2/UVC apps.
- At **115200 baud with 8N1**, peak payload throughput is 11,520 bytes/s before framing and USB overhead. A 250,000-byte JPEG needs **at least ~21.7 seconds**, and a 1 MB image at least 91 seconds. The host timeout defaults to 180 seconds; actual reliability is unknown.
- The POSIX terminal capture tool is for **Linux/macOS computer hosts** only, and has **not** been tested on Android/Termux.
- The frame parser uses CRC32 for accidental corruption detection, not cryptographic authentication. Bad packets are rejected; no retry capture is triggered.
- The visible indicator `GPIO4` and camera mapping are **provisional** and not verified for the target board. In V3 the firmware intentionally has compile-blocking guards. The firmware was *not* flashed or ESP32-compiled in V4 either.

## Re-run all digital checks

```sh
python tools/run_verification.py
python tools/package_release.py
```

Requirements: Python with Pillow, trimesh, CadQuery; GNU g++. The Python test suite also uses the POSIX `pty` and `termios` modules. No downloads or installers run automatically.

## Real readiness

**DIGITAL HARDWARE/PACKET PREFLIGHT VERIFIED (conditional). NOT PHYSICAL PROTOTYPE.**

Actual camera board, physical prototype and operator-authorized real camera testing remain separate external steps. User approval is required before costs or device modifications. No expenses or outreach were incurred.
