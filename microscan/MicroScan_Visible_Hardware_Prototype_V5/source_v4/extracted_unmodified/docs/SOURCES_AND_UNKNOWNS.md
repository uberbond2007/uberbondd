# Source ledger - 10 November 2026

## Verified external listing content (NOT physically inventoried)

1. [Most Electronics RHYX-M21-45 / OV2640 + Micro-USB](https://mostelectronic.com/shop/arduino-development-boards/esp32-cam-ov2640-ch340-camera-micro-usb/). Advertises **499 EGP**, nominal 40x27x12mm, OV2640 included, CH340 Micro-USB, an approximate 180mA @5V LED-off current. Vendor states dimension tolerance ±2%. Actual board mechanical drawing and revision UNKNOWN.
2. [Most Electronics USB-A to Micro USB 1m](https://mostelectronic.com/shop/wires-crocodiles/usb-a-to-micro-usb-data-cable-1m/). Advertises **45 EGP** on product page checked; other category listings show a different price, so checkout may differ. Not ordered.
3. [Makers Electronics ESP32-CAM with OV2640](https://makerselectronics.com/product/esp32-cam-esp32-s-wifibluetooth-with-ov2640-camera-module/). **495 EGP**, separate optional ESP32-CAM-MB programmer **75 EGP**; not a fit-compatible alternative for V2 without reworking board geometry.
4. [RAM Electronics M3x16 fasteners](https://www.ram-e-shop.com/shop/category/pcb-holders-121). **45 EGP / 100 pcs** advertised for an M3x16 item, material not confirmed nylon; nylons and nuts vary in stock status. **Do not record these as a validated compatible nylon fastening kit.**
5. [Espressif Arduino CameraWebServer example](https://github.com/espressif/arduino-esp32/tree/master/libraries/ESP32/examples/Camera/CameraWebServer), reference firmware; no RHYX-specific pin match verified.

## Engineering inferences (NOT manufacturer specifications)
- V2 plate size, support and clamp dimensions, head recesses and 3.5mm PCB lift are CAD design choices.
- Expected assembled board height ~18.7mm from the carrier underside (assuming a 12mm board including lens is placed atop 3.5mm posts), not measured.
- Clearance and total bill of materials remain OPEN.
- 3D printer fidelity and material tolerances must be evaluated independently.

## Missing facts that could invalidate this design
- Camera lens and Micro-USB connector locations and height; whether the FPC camera head can be mechanically exposed without stress.
- Component-free board corner edge zones for secure retention.
- PCB underside solder protrusion heights and mounting stability.
- Firmware pin mapping for the specific RHYX development-board revision.
- Ambient and skin-contact temperature during operation.
- Real optical focus, still-photo capture resolution, one-shot behavior and OCR accuracy.
- Availability of correct M3 nylon screws and nuts, physical printer, wrist strap and safe power supply; final priced BOM.

No direct retailer messages, checkout, purchases, manufacturing, hardware or phone tests occurred.
