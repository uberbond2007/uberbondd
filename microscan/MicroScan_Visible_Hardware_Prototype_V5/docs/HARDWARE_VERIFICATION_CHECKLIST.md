# Bench checklist once a board exists (≈30 minutes)

Nothing here has been done. Do the steps in order; stop at the first failure and record it.
Use a computer, never the OnePlus 15 or the Galaxy A51.

## A. Unpowered (5 min, calipers)

1. Silk reads HW-818? Camera flex reads RHYX M21-45? Photograph both faces.
2. Headers fitted, pins away from the camera face? If not → STOP (carrier does not apply).
3. Measure and write on drawing sheet 3: PCB length, width, thickness; header row spacing; first
   pin from the antenna end; pin length below the plastic; tallest part under the PCB; USB socket
   position; your cable's plug length × width × height.
4. Lay the board on the printed gauge. Edit `cad/build_hardware_v5.py` if anything differs by
   more than 0.5 mm, rebuild, re-run the CAD checks.

## B. Bring-up build — capture is locked (10 min)

5. `pio run -e hw818_bringup_capture_locked -t upload --upload-port <port>` from
   `firmware/microscan_hw818_candidate/` (hold FLASH while plugging in if upload does not start).
   *This is the first device modification and needs the owner's go-ahead.*
6. Open a serial monitor at 115200. Expect `MICROSCAN_BRINGUP capture LOCKED`.
   - `ERROR camera init 0x105` → pin map or flex seating is wrong → gate 1 stays 0.
7. Type `INFO`. Record `sensor_pid` (0x26 = OV2640, 0x2145 = GC2145), `format`, `psram`.
8. Type `LAMPTEST`. Is the white LED on the **camera face** clearly lit for 3 s, visible in room
   light from 2 m? If a different LED or nothing lights → gate 2 stays 0.
9. Type `CAPTURE`. Expect `ERROR capture locked`. (Confirms the lock.)
10. Touch-check the regulator and LED after 5 minutes powered; measure USB current if a meter is
    available. Hot to the touch → STOP.

## C. Only if 6–8 all passed

11. In `src/main.cpp` set the two gates to 1 **by hand**, build `hw818_capture_GATED`, upload.
12. With consent of anyone nearby and a printed test page:
    `python host/serial_capture.py --port <port> --output shot.jpg --wait-ready 8 --indicator-confirmed`
13. Watch the LED: it must come on before the picture and stay on until the host reports success.
14. If init fails on a 0x2145 sensor, rebuild with `-DMICROSCAN_RGB565_FRAMESIZE=FRAMESIZE_QVGA`.
15. Repeat at `-DMICROSCAN_BAUD=921600` / `--baud 921600`; ten frames, zero CRC failures required
    before adopting it.
16. Do the optics test in `docs/OPTICS_GATE.md`.

## D. Mechanical

17. Print, fit pins into the troughs without force, set retainers to 1.0 mm overlap, check no
    screw head or pin is proud of the skin face, fit the pad and strap, wear for 15 minutes powered.

Report results back into `reports/` as new files; do not edit existing receipts.
