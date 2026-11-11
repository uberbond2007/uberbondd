# Electrical design, capture indicator and serial link

Diagram: `diagrams/Connection_Diagram_HW818.svg`. There is **no added wiring**: one USB cable, the
board's own socket, the factory camera flex. No battery, no charger, no solder, no extension of the
camera flex, no connection to any phone.

## Power

5 V from a computer USB port or a certified power bank through the board's Micro-USB socket and its
on-board regulator. The listing asks for a stable 5 V 2 A source (RETAILER CLAIM). Actual current,
regulator temperature and LED current are UNKNOWN and are on the bench checklist. Stop conditions
from V4 (`source_v4/.../docs/FIT_AND_ELECTRICAL_GATES.md`) still apply unchanged.

## Capture indicator — what the firmware enforces

The indicator is the white LED on the camera face (provisionally GPIO4). In `src/main.cpp`:

1. `IndicatorScope` switches the output HIGH on construction and LOW on destruction; it is the only
   code that switches it off apart from `setup()`.
2. `guarded_fb_get()` is the only place the camera frame API is called. It needs a live scope and
   re-reads the output latch; if the latch is not HIGH it returns nothing.
3. `capture_explicit()` holds the scope for the whole operation: 300 ms pre-roll, discard of one
   stale frame, the exposure, optional software JPEG encoding, and the entire UART transmission. It
   re-checks the latch before sending and discards the frame if it dropped.
4. There is one call site, reached only by the exact line `CAPTURE` on the wired serial port.
   `loop()` contains no timer, delay or pin read, so nothing can fire on its own.
5. `LAMPTEST` lights the same output for 3 s without touching the camera so a person can see which
   LED it is. `INFO` prints sensor PID, PSRAM and gate state.

**Tested:** `checks/test_firmware_interlock.py` runs this exact source on a desktop mock and checks the
event order in 16 scenarios, including a stuck-low latch, a latch that drops mid-capture, camera
failure, encoder failure and a mutation test that removes the latch check and confirms the suite
notices. `checks/test_firmware_source.py` pins the structure in the source text.
`checks/test_firmware_build.py` shows a real ESP32 build refuses to compile a capture-capable image,
including when the gates are forced with `-D` flags.

**Not established:** that GPIO4 is that LED on an HW-818; that the LED is bright enough to be
conspicuous in daylight; that reading the latch implies light (a failed LED reads HIGH). Those are
physical checks, and the host tool still demands `--indicator-confirmed` from the operator.

**Known trade-off:** the light stays on during transmission (the image is leaving the device). At
115200 baud that can exceed 20 s for a large frame; LED heating over that time is unmeasured. A
higher baud rate shortens it — see below.

## Sensor handling

`camera_bring_up()` first asks for hardware JPEG. If the driver answers `ESP_ERR_NOT_SUPPORTED`
(0x106 — the documented behaviour of the RHYX/GC2145 class) it re-initialises once as RGB565 at
`MICROSCAN_RGB565_FRAMESIZE` (default SVGA, 0.96 MB in PSRAM) and encodes JPEG in software into a
PSRAM buffer. Without PSRAM it refuses. Risk: a seller guide reports only QVGA as working with this
camera for streaming (E14); a single still at SVGA is plausible but unproven — if init or capture
fails on the bench, rebuild with `-DMICROSCAN_RGB565_FRAMESIZE=FRAMESIZE_QVGA` first to establish
life, then step up. UXGA as RGB565 needs 3.84 MB and will not fit beside the encoder buffer.

## Serial link

Framing is unchanged from V4: `MSJ1`, length u32, width u16, height u16, CRC32 u32, JPEG — 16 bytes
of overhead, 10 line bits per byte. It is a custom protocol on a USB-UART bridge, **not** a USB
Video Class camera; no phone camera app will see it.

| Frame | 115200 | 230400 | 460800 | 921600 |
|---|---|---|---|---|
| 60 kB | 5.2 s | 2.6 s | 1.3 s | 0.7 s |
| 120 kB | 10.4 s | 5.2 s | 2.6 s | 1.3 s |
| 250 kB | 21.7 s | 10.9 s | 5.4 s | 2.7 s |
| 400 kB | 34.7 s | 17.4 s | 8.7 s | 4.3 s |
| 1 MB | 86.8 s | 43.4 s | 21.7 s | 10.9 s |

(lower bounds from `checks/optics_and_transfer_budget.py`; V4's 21.7 s figure is reproduced.)
115200 is unreasonable above ~120 kB. The documented, reversible improvement is a build flag
`-DMICROSCAN_BAUD=921600` with the host's `--baud 921600`; both ends refuse other values. Whether
this board's bridge and cable are error-free at that rate is a bench item — the CRC will reject bad
frames rather than deliver them, and the host never auto-retries a capture.

Host behaviour added in V5: optional `--wait-ready` (opening the port may reset the board), fast
failure on a firmware `ERROR …` line, extra baud rates. The host still sends exactly one request.
