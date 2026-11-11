"""Run the REAL firmware source on a desktop mock HAL and check the capture-indicator interlock.

This proves control-flow ordering in src/main.cpp. It does NOT prove that an LED emits light,
that GPIO4 is the LED on a physical HW-818, or that any camera works.
"""
import io
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / 'firmware' / 'microscan_hw818_candidate'
sys.path.insert(0, str(ROOT / 'host'))
from microscan_usb_packet import FrameError, decode_packet


def make_jpeg(w, h):
    rnd = random.Random(w * 31 + h)
    im = Image.new('RGB', (w, h), 'white')
    px = im.load()
    for _ in range(4000):
        px[rnd.randrange(w), rnd.randrange(h)] = (rnd.randrange(256),) * 3
    b = io.BytesIO()
    im.save(b, format='JPEG', quality=80)
    return b.getvalue()


class Interlock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name) / 'harness'
        cmd = ['g++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror', '-I', str(FW / 'mock'),
               str(FW / 'mock' / 'harness.cpp'), '-o', str(cls.exe)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        cls.jpegs = {}
        for (w, h) in ((1600, 1200), (800, 600)):
            data = make_jpeg(w, h)
            path = Path(cls.tmp.name) / f'{w}x{h}.jpg'
            path.write_bytes(data)
            cls.jpegs[(w, h)] = (path, data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_scenario(self, name, size=(1600, 1200)):
        path, data = self.jpegs[size]
        out = Path(self.tmp.name) / f'{name}.bin'
        p = subprocess.run([str(self.exe), name, str(path), str(size[0]), str(size[1]), str(out)],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        events = p.stdout.splitlines()
        cut = events.index('---SETUP_DONE')
        return events[:cut], events[cut + 1:], out.read_bytes(), data

    def assert_interlock(self, run):
        """Indicator must be HIGH for every camera read, encode and payload write, and LOW at the end."""
        level = 0
        for e in run:
            if e.startswith('GPIO4='):
                level = int(e[-1])
            elif e.startswith('FB_GET') or e.startswith('SOFT_JPEG_ENCODE'):
                self.assertEqual(level, 1, f'{e} happened with the indicator OFF')
                self.assertTrue(e.endswith('indicator=1'))
            elif e.startswith('SERIAL_WRITE'):
                self.assertEqual(level, 1, 'image bytes left the board with the indicator OFF')
        self.assertEqual(level, 0, 'indicator left ON after the command finished')

    def test_setup_never_touches_the_camera_frame_path(self):
        setup, _, _, _ = self.run_scenario('no_command')
        self.assertIn('GPIO4=0', setup)
        self.assertFalse([e for e in setup if e.startswith('FB_GET')])

    def test_idle_loop_never_captures(self):
        _, run, out, _ = self.run_scenario('no_command')
        self.assertEqual(run, [], 'firmware did something with no operator command')
        self.assertNotIn(b'MSJ1', out)

    def test_ov2640_class_capture_ordering_and_packet(self):
        _, run, out, data = self.run_scenario('ov2640_capture')
        self.assert_interlock(run)
        self.assertEqual(run[0], 'GPIO4=1')
        self.assertEqual(run[1], 'DELAY 300', 'light must be on before the exposure')
        self.assertEqual(sum(e.startswith('FB_GET') for e in run), 2)
        self.assertLess(run.index('SERIAL_FLUSH'), len(run) - 1 - run[::-1].index('GPIO4=0'))
        meta, jpeg = decode_packet(out)
        self.assertEqual(jpeg, data)
        self.assertEqual((meta['width'], meta['height']), (1600, 1200))

    def test_gc2145_class_falls_back_to_rgb565_and_soft_jpeg(self):
        setup, run, out, data = self.run_scenario('gc2145_capture', (800, 600))
        self.assertEqual([e for e in setup if e.startswith('CAM_')], ['CAM_INIT JPEG', 'CAM_DEINIT', 'CAM_INIT RGB565'])
        self.assert_interlock(run)
        self.assertTrue(any(e.startswith('SOFT_JPEG_ENCODE') for e in run))
        meta, jpeg = decode_packet(out)
        self.assertEqual(jpeg, data)
        self.assertEqual((meta['width'], meta['height']), (800, 600))

    def test_gc2145_without_psram_refuses(self):
        setup, run, out, _ = self.run_scenario('gc2145_no_psram', (800, 600))
        self.assertNotIn('CAM_INIT RGB565', setup)
        self.assertNotIn(b'MSJ1', out)
        self.assertFalse([e for e in run if e.startswith('FB_GET')])

    def test_soft_encode_failure_sends_no_packet_and_releases_indicator(self):
        _, run, out, _ = self.run_scenario('gc2145_encode_fail', (800, 600))
        self.assert_interlock(run)
        self.assertNotIn(b'MSJ1', out)
        self.assertIn(b'ERROR software JPEG encode failed', out)

    def test_indicator_latch_stuck_low_means_no_frame_is_ever_read(self):
        _, run, out, _ = self.run_scenario('indicator_stuck_low')
        self.assertFalse([e for e in run if e.startswith('FB_GET')], 'camera was read without a lit indicator')
        self.assertNotIn(b'MSJ1', out)
        self.assertIn(b'indicator latch not HIGH; capture refused', out)

    def test_indicator_dropping_midway_discards_the_frame(self):
        _, run, out, _ = self.run_scenario('indicator_drops_midway')
        self.assertNotIn(b'MSJ1', out)
        self.assertIn(b'frame discarded', out)
        self.assertEqual(run[-1] if run[-1].startswith('GPIO4') else [e for e in run if e.startswith('GPIO4')][-1], 'GPIO4=0')

    def test_camera_failure_releases_indicator(self):
        _, run, out, _ = self.run_scenario('camera_fb_fail')
        self.assert_interlock(run)
        self.assertNotIn(b'MSJ1', out)

    def test_camera_not_found_never_captures(self):
        setup, run, out, _ = self.run_scenario('camera_not_found')
        self.assertIn(b'ERROR camera init 0x105', out)
        self.assertFalse([e for e in run if e.startswith('FB_GET')])
        self.assertNotIn('GPIO4=1', run)

    def test_bringup_build_refuses_capture(self):
        _, run, out, _ = self.run_scenario('bringup_locked')
        self.assertFalse([e for e in run if e.startswith('FB_GET') or e == 'GPIO4=1'])
        self.assertIn(b'ERROR capture locked', out)
        self.assertNotIn(b'MSJ1', out)

    def test_only_the_exact_command_triggers(self):
        _, run, out, _ = self.run_scenario('unknown_command')
        self.assertFalse([e for e in run if e.startswith('FB_GET')])
        self.assertNotIn(b'MSJ1', out)
        self.assertEqual(out.count(b'ERROR unknown operator command'), 5)

    def test_lamptest_lights_without_reading_the_camera(self):
        _, run, out, _ = self.run_scenario('lamptest')
        self.assertEqual([e for e in run if e.startswith('GPIO4')], ['GPIO4=1', 'GPIO4=0'])
        self.assertIn('DELAY 3000', run)
        self.assertFalse([e for e in run if e.startswith('FB_GET')])
        self.assertNotIn(b'MSJ1', out)

    def test_info_reports_gate_state_and_no_radio(self):
        _, run, out, _ = self.run_scenario('info')
        self.assertIn(b'pins_verified=0 indicator_verified=0', out)
        self.assertIn(b'radio=unused', out)
        self.assertFalse([e for e in run if e.startswith('FB_GET')])

    def test_two_requests_give_two_separately_indicated_frames(self):
        _, run, out, data = self.run_scenario('two_requests')
        self.assert_interlock(run)
        self.assertEqual([e for e in run if e.startswith('GPIO4')], ['GPIO4=1', 'GPIO4=0', 'GPIO4=1', 'GPIO4=0'])
        self.assertEqual(out.count(b'MSJ1'), 2)

    def test_mutant_without_latch_check_is_caught(self):
        """Mutation test: delete the latch check and confirm THIS suite's assertion would fail."""
        src = (FW / 'src' / 'main.cpp').read_text()
        needle = '  if (!indicator.lit()) return nullptr;\n'
        self.assertEqual(src.count(needle), 1)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'src').mkdir()
            (d / 'mock').mkdir()
            (d / 'src' / 'main.cpp').write_text(src.replace(needle, ''))
            for f in (FW / 'mock').iterdir():
                (d / 'mock' / f.name).write_bytes(f.read_bytes())
            exe = d / 'mutant'
            p = subprocess.run(['g++', '-std=c++17', '-O1', '-I', str(d / 'mock'), str(d / 'mock' / 'harness.cpp'), '-o', str(exe)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            path, _ = self.jpegs[(1600, 1200)]
            r = subprocess.run([str(exe), 'indicator_stuck_low', str(path), '1600', '1200', str(d / 'o.bin')], capture_output=True, text=True)
            self.assertTrue([e for e in r.stdout.splitlines() if e.startswith('FB_GET')],
                            'mutant did not read the camera: the stuck-low test would not detect removal of the interlock')


if __name__ == '__main__':
    unittest.main()
