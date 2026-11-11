# FABLE 5.2 / DEEP RESEARCH · MICROSCAN HARDWARE RESCUE
## Execution brief | 11 November 2026

You are given an existing engineering archive. Your mission is to **recover, inspect, correct, build/test in software where possible, and deliver the next verifiable hardware release** for a plainly identifiable, consent-based, wearable document-reading camera. Do not restart the project with a generic concept sketch. Do not turn this into a covert/disguised camera or unauthorized examination capture system.

## Inputs and provenance

Attached unchanged source archive: `MicroScan_Visible_Hardware_Prototype_V4.zip`.
SHA-256: `274eca7fa3e85b6563b47045f1934f04a302df59b2dd993af538b8e494898e35`.
Archive files: 43; ZIP integrity checked by the sender. Open and independently verify before using.

Existing V4 status, based on reading the actual files:
- CAD V2: openly identifiable wrist-top carrier about 84 × 58 mm; STEP/STL and editable generator present; geometric tests exist. Fit against a physical PCB has **never** been verified.
- Electronics candidate: RHYX-M21-45 / ESP32-CAM-CH340 USB, retailer-advertised at 499 EGP with claimed footprint 40 × 27 × 12 mm. The actual sensor/PCB revision, pin map and LED identity remain unverified. A similarly named standalone sensor is reported as **not OV2640**. Do not combine them.
- Firmware file `firmware/VISIBLE_USB_CAMERA_DIAGNOSTIC.ino` has two intentional `#error` gates. It is not compiled or flashed. The camera pins and visible capture-indicator GPIO are provisional.
- USB transport is a custom `MSJ1` serial JPEG protocol, not USB Video Class. V4 tested Linux pseudo-terminal and C++ emitter-to-Python parser, *not* a physical camera or Android.
- V4 source document `docs/V4_PROTOTYPE_RELEASE.md` sets strict limitations. V4's reports are execution receipts for **digital** checks only.
- BOM has unpriced printed parts, fasteners, strap, power supply and shipping. 499 EGP plus an optional 45 EGP cable are listing-level evidence, not a complete system price.
- No PCB ordered, no 3D print fabricated, no firmware flashed, no optical test, no OnePlus integration.

## Explicit objective

Produce a **genuinely manufacturable and testable hardware prototype package** for an **openly identifiable, visibly marked** assistive document camera. Favor a simple removable USB-powered board and a standard camera system. Keep the existing visible 84×58 mm wrist-top architecture unless actual constraints require transparent revision. Do not optimize a hidden button, covert recording, invisible lens, covert trigger, silent transmission, secret audio relay or unauthorized exams. A physical recording indicator must be visible and functionally tied to capture, not merely a printed label.

Budget: no spending authority; research a possible complete BOM <= 1,500 EGP, including print, straps, cables, fasteners and labor, but never invent price quotes. No purchases, external messages, orders, deployments, device alteration, or paid APIs without separate owner approval. Existing OnePlus 15 and Galaxy A51 must remain untouched.

## Engineering execution order (do this work, don't just describe it)

1. **Recover and audit.** Verify the exact archive hash and inventory. Inspect drawings, CAD source, scripts, firmware, tests and past constraints. Re-run the released tests in a clean workspace when possible. Distinguish reproduced from reported results and preserve failures.
2. **Resolve hardware identity.** Search manufacturer documentation, Espressif pin-map examples, and the Egyptian vendor's *exact full-board* listing. Find actual schematic, compatible board variant, camera flex/sensor, voltage, CH340 wiring, flash/status LED signals, mounting holes and USB position. Do not substitute a generic AI-Thinker pin map as certain. Record VERIFIED / RETAILER CLAIM / THIRD-PARTY / UNKNOWN.
3. **Electrical engineering.** Use the real documented board only. Define a safe, USB-powered, foreground, user-triggered single-JPEG diagnostic with a conspicuous active-capture indication; no hidden/background/network capture. Identify if the current serial speed causes unreasonable transfer times. Suggest only documented, reversible improvements and calculate transfer times with protocol overhead. Do not bypass V4's safety compile gates without board-specific evidence.
4. **Mechanical manufacturing package.** Import existing editable CAD and STEP/STL. Verify actual carrier dimensions, strap slots, fastener engagement, board collision envelope, USB cable bend clearance, sensor FPC clearance, airflow, insulation, and washability/removability. Produce revised source CAD + STEP/STL and dimensioned 1:1 drawings with realistic printer tolerances. Mark dimensions derived only from advertisements as UNVERIFIED.
5. **Firmware and host integration.** Where actual hardware documentation is sufficient, create a board-specific *candidate* firmware and prove a real compile with pinned compiler/toolchain. If the actual pin map is unavailable, leave hardware release blocked, but implement verified host-side transport tests, deterministic firmware source checks and an explicit short hardware verification list. Do not claim hardware validation from mocks.
6. **Optics as an independent gate.** Evaluate whether the actual sensor-lens assembly can photograph authorized text at intended distances. Report verified minimum focus versus unknown, genuine still output, document field coverage and OCR constraints. Do not assume megapixels equal sharpness, nor substitute software OCR synthetic tests for camera samples.
7. **Egypt sourcing and DFM.** Locate exact in-stock listings and full prices for actual known parts, including print and assembly quotes only when publicly stated. If unknown, keep UNKNOWN. Compare reduced-component options with keeping the current board. Respect 0 EGP spend authority.
8. **Adversarial validation.** Test released CAD, firmware build if supported, custom serial frame/parser including corrupted and fragmented data, packaging manifest, cost arithmetic, configuration errors and honest runtime gates. Preserve command lines, logs, tool versions and failures. Check that compiled code cannot silently disable the indicator interlock.
9. **Deliver the release.** Produce a single ZIP with editable CAD, STEP/STL, dimensioned drawings, schematics/connection diagram from real pinout, firmware *if buildable*, host files, test fixtures, source ledger, BOM, README, MANIFEST with SHA-256 for every file, test logs, and a PHYSICAL_BLOCKERS.md listing the smallest owner-only requirements. Include 3D preview derived from actual CAD, not a generative illustration substituted for CAD.

## Mandatory stop and truth gates

- A manufactured physical prototype requires a real physical board, fabrication, assembly and on-device testing. If no physical workshop is connected, deliver the most complete verified digital package and label fabrication **NOT DONE**.
- Never claim optical performance, USB-C/Android support, pin compatibility, thermals, stock or power draw from placeholder numbers.
- Do not rewrite working source or erase failure receipts without a diff and rollback path.
- Do not output a merely decorative schematic or '100% complete' claim.
- Do not ask for permission to do public research or sandbox code execution. Escalate at most 3 **real** owner-only blockers, with exact evidence.

## Required response

Start with **MICROSCAN FABLE 5.2 HARDWARE EXECUTION RECEIPT**. Report: archive hash verification; source inventory; actual code/CAD modifications; models and manufacturers actually checked; exact board/indicator evidence; real build/test commands and outcomes; file hashes and direct durable artifact; full-cost known/unknown ledger; what remains physical; approved/nonapproved actions; and readiness (RESEARCH / DIGITAL FABRICATION PACKAGE / FIRMWARE COMPILED / PHYSICAL ASSEMBLY / LIVE IMAGING VALIDATED). Do not inflate readiness.

If you have a tool-connected, authorized manufacturing service, identify the exact steps, cost and approval requirement before initiating any order. Fable engineering is not a substitute for a fabrication receipt.
