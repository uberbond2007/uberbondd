# MicroScan V3 visible hardware preflight release

**Start:** `docs/V3_COMPLETION_REPORT.md`

The V2 mechanical files are retained intact and can be opened in any STEP-compatible CAD system or STL slicer. V3 adds a restricted open-bench diagnostic firmware source, verified host-side JPEG packet decoding and test scaffolding.

Run local Python tests (Pillow required):

```bash
python -m unittest discover -s host/tests -v
python -m unittest discover -s checks -p test_release_integrity.py -v
python checks/validate_cad.py
python checks/validate_exported_meshes.py
```

**This does not manufacture hardware.** Firmware has compile-time guards and hasn't been compiled, flashed or tested. The user still must authorize any expenditure and physical fabrication. No autonomous physical manufacturer exists in this environment.
