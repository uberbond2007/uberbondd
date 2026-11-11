# Egypt sourcing ledger — 11 November 2026

Spend authority: **0 EGP**. Nothing was ordered, reserved or enquired about. Prices are what the
public pages returned on 2026-11-11 (`evidence/WEB_EVIDENCE_2026-11-11.json`); a web "InStock" flag
is not a physical stock check, and checkout totals may differ.

## Known lines (`BOM.csv`)

| Line | EGP |
|---|---|
| HW-818 board with RHYX camera, ME-31692 | 499.00 |
| USB-A → Micro-USB data cable 1 m, ME-22356 | 49.50 |
| 4 × M3×20 screw @ 1.73 | 6.92 |
| 4 × M3 lock nut @ 0.65 | 2.60 |
| Delivery inside Cairo, "starts from" (0 if collected in Abbasia) | 95.00 |
| **Known subtotal** | **653.02** |

## Unknown lines — deliberately not priced

| Item | Why unknown |
|---|---|
| 3D printing in PETG | Service lists PLA+ 3, ABS+ 4, e-TPU 6 EGP/g; PETG is offered but has no published rate, and the minimum-order amount is not shown. Solid-volume upper bound is 24.5 g → 73.5 EGP at the PLA+ rate, 98 EGP at the ABS+ rate. This is a bracket, not a quote. |
| 20 mm hook-and-loop strap | no priced Egyptian listing found this session |
| Backing pad | not found |
| Cable tie | not found |
| Nylon M3 screws/nuts | not found in Egypt; steel M3×20 priced instead |

## Budget statement

Target ≤ 1,500 EGP all-in. Known lines total **653.02**, leaving **846.98** for four unknown lines of
which the largest plausible one is the print. A complete build under 1,500 EGP therefore looks
likely but is **NOT PROVEN** until a print quote and the three small items have real prices.

## Price movements since V4 (one day earlier)

Cable 45 → 49.50; standalone RHYX module 120 → 99.00; board unchanged at 499.00. The board page no
longer shows the 40×27×12 mm / 180 mA / OV2640 text V4 quoted.

## Options compared

| Option | Known cost | Fits V5 carrier | Sensor | Comment |
|---|---|---|---|---|
| A. ME-31692 HW-818 + RHYX | 499.00 | yes (nominal) | no hardware JPEG | cheapest, one PCB, biggest optics risk |
| B. ME-11814 ESP32-CAM (OV2640) + ME-18384 USB shield | 698.00 | no — two-board stack | OV2640 claimed | better stills if the claim holds; carrier must be redone |
| C. ME-33563 board without camera | 400.00 | n/a | none | only useful with a camera in hand |
| D. Makers ESP32-CAM OV2640 | 495.00 + programmer (75 per V4, not re-checked) | no | OV2640 claimed | same geometry problem as B |

Reduced-component alternative: none is cheaper than A, and A already has the fewest parts (one PCB,
one cable, one print, four screws).

## Manufacturing route

No fabrication service is connected to this session. If one is approved later the steps are:
upload the three STLs to the bureau's calculator (that reveals the PETG price and minimum) →
owner approves the figure → order. Each of those is an external action and needs explicit approval.
