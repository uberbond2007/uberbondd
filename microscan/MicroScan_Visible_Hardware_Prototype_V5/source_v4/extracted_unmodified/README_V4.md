# MicroScan V4: verified digital hardware preflight

Start at `docs/V4_PROTOTYPE_RELEASE.md`. V4 preserves the V2 CAD and V3 source and adds POSIX one-shot USB-serial host capture and integration tests. There is no wireless service, background recording, or camera-hiding design.

The V3 `firmware/VISIBLE_USB_CAMERA_DIAGNOSTIC.ino` is unchanged and **intentionally unbuildable** until an actual board and status LED are verified. The compiled `bench/packet_emitter.cpp` is a desktop C++ protocol test, not ESP32 firmware.

For digital testing in a compatible Linux environment, run `python tools/run_verification.py`. `python tools/package_release.py` regenerates the deterministic ZIP and manifest. No hardware was purchased, fabricated or connected.
