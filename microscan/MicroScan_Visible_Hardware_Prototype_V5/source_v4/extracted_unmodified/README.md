# MicroScan V2 - VISIBLE CAMERA hardware engineering release

**Purpose:** A reusable, externally identifiable small document-camera accessory prototype. This kit is intentionally **NOT** a disguised shirt-button camera. No clandestine image capture, hidden triggers, or covert wiring are designed.

## What is finished
- Editable CadQuery source plus physical STEP and print-ready STL geometry: carrier, four adjustable retainer *copies from one part*, and a nominal PCB fit gauge.
- A two-page **1:1 print gauge PDF**, top-view drawing, documented geometry constraints and a simple documented power/data architecture.
- Real CAD mesh/boolean checks and a release manifest with checksums.
- A supplier-linked preliminary bill of materials for an integrated ESP32 camera board with native Micro-USB connector.

## What is NOT finished or verified
No board purchased, 3D printed, electrically powered, firmware flashed, Wi-Fi connected, mechanically fitted or optically tested. The manufacturer footprint is a retailer claim, not a measured board drawing. Actual camera lens placement, connector side, PCB thickness, PCB underside components and board-edge clearances are UNKNOWN. A complete working device cannot be honestly claimed from CAD alone.

## Start here
1. **Open** `templates/Hardware_Fit_Gauge_100pct.pdf`. If printed, use **Actual Size / 100%** and verify its 100 mm scale before comparison.
2. **Open** `cad/Open_Camera_Carrier_V2.step` in CAD, or `cad/Open_Camera_Carrier_V2.stl` in slicer. `cad/Adjustable_Edge_Retainer_V2.stl` is the separate printable clamp (quantity 4), subject to real-board fit. Do not print `Nominal_PCB_Gauge_DO_NOT_MOUNT` for use as electronics.
3. **Read** `docs/FIT_AND_ELECTRICAL_GATES.md` before hardware assembly or purchase; the four clamp contact zones and USB orientation are unvalidated.
4. **Rebuild** with `bash REBUILD.sh` (CadQuery 2.x, trimesh, ReportLab, matplotlib; installed in the authoring environment). It verifies solid geometry and generates a test report.

## Vendor facts
Most Electronics advertises RHYX-M21-45 ESP32-CAM CH340 camera with micro USB, board **40x27x12 mm**, **499 EGP**. The supplier says the included module is an OV2640 2MP camera. Stock displayed in a listing is not a physical store check. Source and limits in `docs/SOURCES_AND_UNKNOWNS.md`.

## Key dimension correction relative to V1
Carrier print-only envelope: **84 x 58 x 8.3 mm**. Assumed assembled height: **~18.7 mm** (3.2mm plate + 3.5mm unsupported under-board clearance + seller-advertised 12mm board height). The **18.7mm** is **NOT a measured product thickness**, and may be inaccurate depending on PCB construction and actual board revisions.

## Mechanical limitation
This is a digital fabrication candidate. The adjustable clips are not independently rated or physically load-tested. Print scale, clearances, cable reach, radio/thermal behavior, security and OCR performance all remain outstanding. **Do not position the powered prototype against skin until insulation/temperature and secure mounting have been physically verified.**

No purchases, downloads to the user's phone, third-party outreach, or production changes were made.
