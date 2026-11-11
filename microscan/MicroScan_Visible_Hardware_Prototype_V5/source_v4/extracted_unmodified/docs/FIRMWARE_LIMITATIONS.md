# Bench firmware safety and build gate

The diagnostic sketch is intentionally limited to an **openly labelled, USB-tethered bench camera**. There is no wireless transfer, background stream or concealed trigger. It is not a production implementation.

The source uses a provisional AI-Thinker camera GPIO map from Espressif's reference example. There is NO confirmed schematic identifying the RHYX-equipped board's camera pins or built-in flash LED. A third-party RHYX report uses the same map; this is weaker than official documentation.

The two constants near the start of `VISIBLE_USB_CAMERA_DIAGNOSTIC.ino` are set to zero and intentionally make compilation fail. They can only be set after a legitimate physical review confirms (a) camera mapping, (b) indicator LED behavior. **No flashing or device modifications took place.**

The diagnostic wire packet is `MSJ1` + length (uint32 little endian) + width (uint16) + height (uint16) + CRC32 (uint32) + JPEG bytes. The host parser verifies the CRC and decodes the actual image. CRC32 detects accidental corruption, not malicious tampering.

The authoring environment has no installed Arduino ESP32 compiler toolchain, so a real firmware build could not be executed. Parsing the source or unit testing the packet protocol is NOT equivalent to compilation or real hardware functionality.

Reference: https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h
Third-party RHYX hypothesis: https://github.com/YigitMusstafa/rhyx-m21-45-esp32-cam-web-server-code
