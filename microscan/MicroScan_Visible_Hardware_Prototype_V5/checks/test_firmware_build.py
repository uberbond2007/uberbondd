"""REAL ESP32 cross-compilation with the pinned PlatformIO toolchain.

Needs PlatformIO (pip install platformio==6.2.0 or newer) and, on first run, network access to
download espressif32@6.9.0. Set MICROSCAN_PIO to the pio executable. If PlatformIO is absent the
tests are SKIPPED and the run must be reported as 'firmware not compiled'.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / 'firmware' / 'microscan_hw818_candidate'
PIO = os.environ.get('MICROSCAN_PIO') or shutil.which('pio') or shutil.which('platformio')
RADIO_SYMBOLS = ('esp_wifi_init', 'esp_wifi_start', 'esp_wifi_connect', 'esp_bt_controller_enable', 'esp_bluedroid_enable',
                 'nimble_port_init', 'esp_netif_init', 'lwip_socket', 'httpd_start', 'sdmmc_host_init', 'esp_now_init',
                 'esp_https_ota', 'esp_ota_begin')


@unittest.skipUnless(PIO, 'PlatformIO not available: firmware NOT compiled in this run')
class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.proj = Path(cls.tmp.name) / 'fw'
        shutil.copytree(FW, cls.proj, ignore=shutil.ignore_patterns('.pio'))
        cls.receipt = {'pio': subprocess.run([PIO, '--version'], capture_output=True, text=True).stdout.strip()}

    @classmethod
    def tearDownClass(cls):
        out = ROOT / 'reports' / 'FIRMWARE_BUILD_RECEIPT.json'
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(cls.receipt, indent=2) + '\n')
        cls.tmp.cleanup()

    def pio(self, env):
        return subprocess.run([PIO, 'run', '-d', str(self.proj), '-e', env], capture_output=True, text=True, timeout=1500)

    def test_1_capture_capable_build_is_blocked_by_both_gates(self):
        p = self.pio('hw818_capture_GATED')
        log = p.stdout + p.stderr
        self.receipt['gated'] = {'command': 'pio run -e hw818_capture_GATED', 'exit_code': p.returncode,
                                 'errors': [l.strip() for l in log.splitlines() if '#error' in l and 'main.cpp' in l]}
        self.assertNotEqual(p.returncode, 0, 'a capture-capable build compiled while the gates are 0')
        self.assertIn('HW-818 camera pin map unverified', log)
        self.assertIn('Visible capture indicator unverified', log)
        self.assertFalse((self.proj / '.pio' / 'build' / 'hw818_capture_GATED' / 'firmware.bin').exists())

    def test_2_bringup_capture_locked_build_compiles_without_warnings_or_radio(self):
        p = self.pio('hw818_bringup_capture_locked')
        log = p.stdout + p.stderr
        self.assertEqual(p.returncode, 0, log[-3000:])
        build = self.proj / '.pio' / 'build' / 'hw818_bringup_capture_locked'
        elf, binf = build / 'firmware.elf', build / 'firmware.bin'
        self.assertTrue(binf.is_file())
        own_warnings = [l for l in log.splitlines() if 'src/main.cpp' in l and 'warning' in l]
        self.assertEqual(own_warnings, [])
        core = Path(os.environ.get('PLATFORMIO_CORE_DIR', Path.home() / '.platformio'))
        nm = core / 'packages' / 'toolchain-xtensa-esp32' / 'bin' / 'xtensa-esp32-elf-nm'
        gcc = core / 'packages' / 'toolchain-xtensa-esp32' / 'bin' / 'xtensa-esp32-elf-gcc'
        syms = subprocess.run([str(nm), '-C', str(elf)], capture_output=True, text=True).stdout
        names = {line.split()[-1] for line in syms.splitlines() if line.split()}
        present = [s for s in RADIO_SYMBOLS if s in names]
        self.assertEqual(present, [], 'radio / network / storage code linked into the image')
        for needed in ('esp_camera_fb_get', 'esp_camera_init', 'frame2jpg_cb'):
            self.assertIn(needed, names, 'capture path was optimised away; the compile would prove nothing')
        strings = binf.read_bytes()
        for needle in (b'ERROR capture locked: bring-up build', b'MSJ1', b'LAMPTEST'):
            self.assertIn(needle, strings)
        fw_pkg = json.loads((core / 'packages' / 'framework-arduinoespressif32' / 'package.json').read_text())
        size = [l.strip() for l in log.splitlines() if l.startswith(('RAM:', 'Flash:'))]
        self.receipt['bringup'] = {
            'command': 'pio run -e hw818_bringup_capture_locked', 'exit_code': p.returncode,
            'platform': 'espressif32@6.9.0', 'framework_arduinoespressif32': fw_pkg['version'],
            'compiler': subprocess.run([str(gcc), '--version'], capture_output=True, text=True).stdout.splitlines()[0],
            'size': size, 'firmware_bin_bytes': binf.stat().st_size,
            'firmware_bin_sha256_THIS_BUILD_ONLY': hashlib.sha256(strings).hexdigest(),
            'radio_symbols_checked_absent': list(RADIO_SYMBOLS),
            'binary_shipped_in_release': False, 'flashed': False, 'run_on_hardware': False,
            'note': 'Image is capture-LOCKED at run time. It proves the source compiles and links for ESP32; nothing more.'}

    def test_3_gates_cannot_be_forced_from_the_command_line(self):
        ini = self.proj / 'platformio.ini'
        ini.write_text(ini.read_text() + '\n[env:attack]\nbuild_flags = -DMICROSCAN_BOARD_PINS_VERIFIED=1 -DMICROSCAN_VISIBLE_INDICATOR_VERIFIED=1\n')
        p = self.pio('attack')
        log = p.stdout + p.stderr
        self.receipt['command_line_override_attack'] = {'exit_code': p.returncode, 'blocked': p.returncode != 0}
        self.assertNotEqual(p.returncode, 0, 'gates were overridden with -D flags')
        self.assertTrue('unverified' in log or 'redefined' in log)

    def test_4_host_mock_macro_is_rejected_by_esp32_build(self):
        ini = self.proj / 'platformio.ini'
        ini.write_text(ini.read_text() + '\n[env:attack2]\nbuild_flags = -DMICROSCAN_HOST_MOCK=1\n')
        p = self.pio('attack2')
        self.receipt['host_mock_macro_attack'] = {'exit_code': p.returncode, 'blocked': p.returncode != 0}
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('MICROSCAN_HOST_MOCK must never be defined in an ESP32 build', p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()
