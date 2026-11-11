# Physical blockers — owner-only

Everything that software and public research can settle has been settled. These three remain and
none of them can be done from here. Spend authority is 0 EGP; nothing below has been initiated.

## 1. Approve and obtain one board (decision + ~499–654 EGP)

*Evidence:* the only candidate with photographs matching this design is Most Electronics
SKU ME-31692, 499.00 EGP, flagged in stock on 2026-11-11 (`evidence/` E1–E3). Its camera has no
hardware JPEG (E4, E14, E15).
*Decision for the owner:* buy this board knowing the optics/OCR risk in `docs/OPTICS_GATE.md`, **or**
choose the 599 + 99 EGP OV2640 pair (E6, E7) and accept that the V5 carrier must be re-parametrised
for a two-board stack. Do not buy both to "be safe" before reading the optics gate.
*Default if no decision:* nothing is bought; package stays at DIGITAL FABRICATION PACKAGE.

## 2. Measure the real board and run bring-up (≈30 min, calipers + a computer)

Follow `docs/HARDWARE_VERIFICATION_CHECKLIST.md`. It yields the seven numbers the CAD needs
(length, width, thickness, header row spacing, first-pin offset, pin length, plug size), the sensor
PID and PSRAM state from the capture-locked bring-up build, and a visual confirmation of which LED
the indicator output drives. Only after that may the two `#define … 0` gates in
`firmware/microscan_hw818_candidate/src/main.cpp` be changed by hand.
*Why owner-only:* flashing is a device modification; the gates require a person looking at a board.

## 3. Get a print quote and one authorised test photograph

The PETG rate and the minimum order are not published (E9), so the print cost is unknown until the
STLs are uploaded to a bureau's calculator or sent for a quote — that is an external message and
needs approval. After assembly, one consented photograph of printed text at a measured distance is
the only thing that can close the optics gate. Until then no claim about legibility is made.

---

Not blockers (already resolved digitally): toolchain, compile, protocol, parser robustness, CAD
self-consistency, drawings, cost arithmetic, packaging.
