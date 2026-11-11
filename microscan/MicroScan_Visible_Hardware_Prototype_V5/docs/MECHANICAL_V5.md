# Mechanical package V5

Source: `cad/build_hardware_v5.py` (CadQuery 2.8.0). Outputs: STEP + STL for
`Open_Camera_Carrier_V5`, `Adjustable_Edge_Retainer_V5` (×4) and
`HW818_Nominal_PCB_Gauge_DO_NOT_MOUNT`, plus `MicroScan_V5_Nominal_Assembly_REFERENCE_ONLY.step`.
Checks: `checks/validate_cad_v5.py` → 100/100 (`checks/CAD_V5_TEST_RESULTS.json`).
All of it is digital. Nothing was printed.

## Why V2 could not be released

`checks/V2_AUDIT_FINDINGS.json`, computed from the unmodified V2 source:

| ID | Finding |
|---|---|
| V2-F1 | PCB sits 3.5 mm above the plate; soldered header pins need 8.64 mm. Pin tips would end 1.94 mm *below the skin-side face*. |
| V2-F2 | Gap between pillar faces 46.0 mm; HW-818 is 48.5 mm long. |
| V2-F3 | The board's long axis ends at an M3 pillar pair and a strap slot; 22 mm remain where a 19 mm plug plus cable bend is needed, and the pillars are in the way. |
| V2-F4 | Support pads lie under the header rows. |
| V2-F5 | Skin-side pocket 1.8 mm deep; an M3 pan head is 2.4 mm → 0.6 mm proud against the skin. |

## What V5 keeps and changes

Kept: 84 × 58 × 3.2 mm plate, one 20 mm strap, four adjustable slotted retainers on M3 pillars,
engraved identification, open frame, no enclosure.

Changed (all transparent, all parametric):

- Board runs along the 84 mm axis: antenna end at X = −40, USB end at X = +8.5, leaving 33.5 mm
  on-plate for the plug, its boot and a strain-relief saddle. Cable leaves toward the elbow.
- Strap slots moved to the two long edges (22 × 4 mm at Y = ±24.5) so the strap crosses the 58 mm axis.
- Two rails with **blind** pin troughs replace the pads. Header plastic rests on the rail tops; pins
  hang in 1.5 mm-wide troughs that stop 1.8 mm short of the skin face. The plate under the pins is
  unbroken (checked by intersecting a probe slab with the solid).
- PCB underside at Z = 11.14 mm → 4.74 mm of open air under the ESP-32S can and 2.59 mm under a
  worst-case 8 mm plug overmold.
- Pillars moved beside the header region, where the board edge carries only solder joints. Retainer
  overlap is adjustable −0.95 … +3.95 mm; set **1.0 mm** (more than ~1.15 mm reaches the solder fillets).
- Screw head now sits in a 6.6 × 2.6 mm pocket (0.2 mm below the skin face); nut on top; spare
  thread points away from the skin. M3×16 engages a 2.4 mm nut fully (+0.46 mm); M3×20 also works;
  M3×15 is rejected by the check.
- Cable saddle with a V-groove at X = 37 and two tie windows; the tie lies in a 1.2 mm channel so it
  is flush with the skin face.
- `CAMERA` engraved twice (5.2 mm letters, 0.8 mm deep) on the free area beside the cable.
- Nothing in the carrier rises above the PCB top plane: lens and LED are uncovered from every side.

## Clearance summary (nominal, UNVERIFIED board)

| Item | Value |
|---|---|
| Carrier bounding box | 84.0 × 58.0 × 12.74 mm |
| Estimated height to lens top | ≈ 19.2 mm (camera stack 6.5 mm is an estimate) |
| Solid floor between pin tips and skin | 1.8 mm PETG + 0.7 mm air above it |
| Header bearing ledge per side | 0.52 mm |
| Row-spacing float per side | 0.43 mm |
| First-pin position tolerance along the row | ±2.0 mm |
| Carrier mass, solid PETG upper bound | 21.0 g (+0.9 g retainers, +2.6 g gauge) |

## Airflow, insulation, washability

The board is open on five sides with an air gap beneath; there is no cover to trap heat. Nothing
conductive faces the skin: pins are blind, heads are recessed, the tie is recessed, and a foam pad
is listed as a second layer. The board lifts out after loosening four nuts, so the carrier and strap
can be washed; the board itself must never be washed or sealed.

## Printing (DFM)

PETG, 0.2 mm layers, 0.4 mm nozzle, 4 perimeters, 5 top/bottom layers, ≥ 40 % infill, skin face on the
bed, no supports. The only overhangs are the 6.6 mm pocket ceilings and the 3.6 mm tie channel
(short bridges). Smallest printed walls: 1.55 mm beside the troughs, 1.7 mm between pocket and strap
slot. Holes are modelled +0.4 mm on diameter. General tolerance to expect from a desktop FDM
machine: ±0.3 mm; the trough float (±0.43) and end clearance (±2.0) were sized for that. PLA is not
recommended next to a linear regulator.

## Before printing the carrier

Print or cut the gauge on sheet 3 of the drawings, lay the real board on it, fill in the measurement
form, edit the same names at the top of `cad/build_hardware_v5.py`, re-run
`python cad/build_hardware_v5.py && python checks/validate_cad_v5.py`, then print. If the board has no
headers, or they point toward the camera face, **stop** — this layout does not apply.

## Known mechanical limits

- Every board number is from a seller datasheet, a catalogue photo or a generic part standard.
- Retainers assume a 1.6 mm PCB; a thinner board needs a 0.5 mm shim under the retainer tip.
- A single screw per retainer relies on friction against rotation; it is not a rated fastening.
- One central strap on an 84 mm plate may rock with a stiff cable; comfort is untested.
- Plug overmolds longer than ~25 mm will reach the saddle; boot shape varies by cable.
