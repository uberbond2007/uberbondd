"""Release-level honesty and completeness checks."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4_ZIP = ROOT / 'source_v4' / 'MicroScan_Visible_Hardware_Prototype_V4.zip'
V4_SHA = '274eca7fa3e85b6563b47045f1934f04a302df59b2dd993af538b8e494898e35'


class Release(unittest.TestCase):
    def test_v4_archive_is_the_one_named_in_the_mission(self):
        self.assertEqual(hashlib.sha256(V4_ZIP.read_bytes()).hexdigest(), V4_SHA)
        handoff = json.loads((ROOT / 'source_v4' / 'MICROSCAN_FABLE52_HANDOFF_MANIFEST.json').read_text())
        self.assertEqual(handoff['source_sha256'], V4_SHA)

    def test_v4_extraction_is_byte_identical_and_complete(self):
        with zipfile.ZipFile(V4_ZIP) as z:
            self.assertIsNone(z.testzip())
            names = [n for n in z.namelist() if not n.endswith('/')]
            self.assertEqual(len(names), 43)
            for n in names:
                rel = n.split('/', 1)[1]
                self.assertEqual((ROOT / 'source_v4' / 'extracted_unmodified' / rel).read_bytes(), z.read(n), rel)
        on_disk = [p for p in (ROOT / 'source_v4' / 'extracted_unmodified').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        self.assertEqual(len(on_disk), 43)

    def test_v4_internal_manifest_still_matches(self):
        base = ROOT / 'source_v4' / 'extracted_unmodified'
        m = json.loads((base / 'RELEASE_MANIFEST.json').read_text())['entries']
        self.assertEqual(len(m), 42)
        for rel, digest in m.items():
            self.assertEqual(hashlib.sha256((base / rel).read_bytes()).hexdigest(), digest, rel)

    def test_required_deliverables_exist(self):
        for rel in ('README.md', 'PHYSICAL_BLOCKERS.md', 'BOM.csv', 'cad/build_hardware_v5.py',
                    'cad/Open_Camera_Carrier_V5.step', 'cad/Open_Camera_Carrier_V5.stl',
                    'cad/Adjustable_Edge_Retainer_V5.step', 'cad/Adjustable_Edge_Retainer_V5.stl',
                    'cad/HW818_Nominal_PCB_Gauge_DO_NOT_MOUNT.step', 'cad/HW818_Nominal_PCB_Gauge_DO_NOT_MOUNT.stl',
                    'drawings/MicroScan_V5_Drawings_1to1.pdf', 'drawings/V5_Carrier_3D_Preview.png',
                    'drawings/V5_Nominal_Assembly_3D_Preview.png', 'diagrams/Connection_Diagram_HW818.svg',
                    'firmware/microscan_hw818_candidate/src/main.cpp', 'firmware/microscan_hw818_candidate/platformio.ini',
                    'host/serial_capture.py', 'host/microscan_usb_packet.py', 'evidence/WEB_EVIDENCE_2026-11-11.json',
                    'docs/HARDWARE_IDENTITY.md', 'docs/OPTICS_GATE.md', 'docs/READINESS.md', 'docs/SOURCING_AND_DFM.md',
                    'docs/HARDWARE_VERIFICATION_CHECKLIST.md', 'docs/V5_CHANGELOG_AND_DIFF.md'):
            self.assertTrue((ROOT / rel).is_file() and (ROOT / rel).stat().st_size > 200, rel)

    def test_no_flashable_image_or_build_tree_is_shipped(self):
        bad = [p for p in ROOT.rglob('*') if p.is_file() and 'source_v4' not in p.parts
               and (p.suffix in ('.bin', '.elf', '.hex', '.uf2') or '.pio' in p.parts)]
        self.assertEqual(bad, [])

    def test_readiness_is_not_inflated(self):
        text = (ROOT / 'docs' / 'READINESS.md').read_text()
        for phrase in ('Not reached: PHYSICAL ASSEMBLY, LIVE IMAGING VALIDATED', 'Fabrication | **NOT DONE**', 'Flashing | **NOT DONE**',
                       'cannot take a picture'):
            self.assertIn(phrase, text)
        readme = (ROOT / 'README.md').read_text()
        self.assertIn('Not printed. Not assembled. Not flashed.', readme)
        for doc in ROOT.glob('**/*.md'):
            if 'source_v4' in doc.parts:
                continue
            low = doc.read_text().lower()
            for claim in ('100% complete', 'fully validated', 'production ready', 'production-ready', 'works on android'):
                self.assertNotIn(claim, low, f'{claim!r} in {doc.name}')

    def test_design_stays_overt(self):
        cad = (ROOT / 'cad' / 'build_hardware_v5.py').read_text()
        self.assertIn("LABEL = 'CAMERA'", cad)
        for doc in ('README.md', 'docs/MECHANICAL_V5.md'):
            low = (ROOT / doc).read_text().lower()
            for word in ('disguise', 'covert', 'hidden lens', 'undetect'):
                if word in low:
                    self.assertRegex(low, r'(no|not|never|must not)[^.]{0,80}' + word, f'{word} used affirmatively in {doc}')

    def test_blockers_are_at_most_three(self):
        text = (ROOT / 'PHYSICAL_BLOCKERS.md').read_text()
        self.assertEqual(len([l for l in text.splitlines() if l.startswith('## ')]), 3)


if __name__ == '__main__':
    unittest.main()
