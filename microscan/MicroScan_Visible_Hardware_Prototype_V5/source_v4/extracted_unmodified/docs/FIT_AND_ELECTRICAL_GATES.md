# Fit, assembly and electrical gates (candidate design; physical work NOT performed)

## Geometry and reversible mounting
- Printed base footprint: 84 x 58 x 3.2 mm, with two through-strap slots 4 x 22 mm.
- Nominal PCB envelope from seller: 40 x 27 x 12 mm, subject to ±2% dimensions and unlisted physical revision changes. No official hole drawing has been obtained.
- Four small supports raise nominal PCB underside 3.5mm above carrier (a chosen CAD clearance, not an observed board need).
- Four outboard M3 mounting pillars carry independent **adjustable, open edge retainers**. They overlap the footprint by about 1.5mm each at nominal board dimensions; no camera or antenna cover is added.
- The retainer contact area must be on *bare board edge*, avoiding antenna, FPC, camera flex, components, pins and USB connection. Without actual PCB measurements, the design cannot guarantee four available contact locations. The parts must not be forced.
- Bottom mounting-head pockets are 6mm diameter by 1.8mm depth. Provisional M3x16mm nylon screw recommendation, with head/nut geometry still unverified; the selected bolt head must sit flush, and screw ends must not touch circuitry or skin.
- Two optional 2.7 x 3.4mm cable tie windows are provided. USB remains openly visible, and the cable is never routed secretly through a garment.
- Nylon / PETG are recommended non-conductive prototype materials, but neither material eliminates thermal/skin risks.
- V1 rail retainers have been **removed**; V2 introduces removable clips so unknown board revisions are not trapped by a non-adjustable slot.

## Critical 'must know' dimensions missing from public listing
1. USB connector orientation and protrusion relative to 40x27 outline.
2. Lens position, camera flex bend radius and PCB antenna zone.
3. Actual PCB thickness and underside tallest components.
4. Exposed safe contact zones on the two long PCB edges.
5. True case height, thermal rise, battery/power supply characteristics.

## Electrical block diagram (only existing documented interfaces)

```
[Certified, insulated 5V USB-A power / computer]
          |
          | ordinary exposed USB-A -> Micro-USB data cable
          v
[RHYX-M21-45 ESP32-CAM: CH340 + power inputs]
          |
          | factory-supplied camera FPC (no cutting / extension)
          v
[OV2640 sensor / visible optical module]
          |
          | optional manufacturer-compatible firmware path, NOT installed
          v
[Local 2.4GHz Wi-Fi -> overt local browser/photo reading]
```

- Seller advertises approximately 180mA at 5V with flash OFF and 310mA at 5V with flash at maximum; these are marketing specifications, **not observed maxima**. Budget power supply capacity conservatively, e.g. certified 5V >=1A USB source, but confirm real USB voltage/current during operation.
- **No raw phone camera wiring, no MIPI cable, no hand-built LiPo charge circuit, and no bare-wire USB power.** USB port already exists on the candidate board.
- CH340 is a USB serial programmer, not a USB Video Class camera interface. JPEG output requires compatible camera firmware, which hasn't been flashed or compiled for this PCB variant.
- Espressif's reference CameraWebServer has an `AI_THINKER` camera-model pin map. The seller's RHYX board has not been demonstrated pin-compatible with AI Thinker. Validate the specific board pins and boot mode before firmware flashing.
- The board's stock camera flash LED is NOT an assured capture-indicator LED. The camera remains clearly identified by printed text; a reliable capture-status indicator is a **separate unfinished requirement**.
- Avoid unrestricted internet exposure: if/when a real board exists, use a consent-based local network only, no public ports.

## Mechanical/electrical safety stop checks
- Any PCB component touches a clip/support: STOP, revise the CAD; don't force a board into place.
- Any fastener protrudes through underside toward skin: STOP, adjust bolt/insulation.
- Strain relief directly loads the Micro-USB connector or camera flex: STOP, reroute cable externally.
- Overheating, repeated resets, excessive current or exposed circuitry against skin: STOP and disconnect power.
- Lens cannot focus on printed documents: record an optical failure, not a software success.
- No visible capture activity assurance: do not call the product finished.

## Real-world acceptance criteria not yet satisfied
- PCB measured and fitting, with camera, connector and antenna unobstructed.
- Actual installed firmware and user-visible capture confirmation tested.
- Stable regulated supply and thermally comfortable skin-adjacent operation verified.
- At least one original-resolution, actually captured photograph and document legibility result.
- Completed BOM with pricing of straps, 3D printing, connectors, and fasteners.
