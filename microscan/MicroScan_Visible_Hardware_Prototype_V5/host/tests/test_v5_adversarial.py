"""V5 adversarial transport tests: corruption, fragmentation, resync, error lines, ready banner.
All run on Linux pseudo-terminals with synthetic JPEGs. They exercise the HOST code only."""
import io
import select
import os
import pty
import random
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zlib
from pathlib import Path
from PIL import Image

HOST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOST))
from microscan_usb_packet import HEADER, MAGIC, FrameError, build_packet, decode_packet
from serial_capture import BAUDS, CaptureError, capture, read_one_packet, transfer_seconds, wait_for_ready


def jpeg(w=96, h=64, seed=1):
    rnd = random.Random(seed)
    im = Image.new('RGB', (w, h))
    im.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)) for _ in range(w * h)])
    b = io.BytesIO()
    im.save(b, format='JPEG', quality=90)
    return b.getvalue()


class Device:
    """A pty-backed fake board. script(master) runs in a thread once the port is open."""
    def __init__(self, script):
        self.master, self.slave = pty.openpty()
        self.port = os.ttyname(self.slave)
        self.requests = []
        self.thread = threading.Thread(target=script, args=(self,), daemon=True)
        self.thread.start()

    def read_request(self, timeout=3.0):
        end = time.monotonic() + timeout
        got = b''
        while time.monotonic() < end and not got.endswith(b'\n'):
            try:
                if select.select([self.master], [], [], 0.05)[0]:
                    got += os.read(self.master, 64)
            except OSError:
                break
        self.requests.append(got)
        return got

    def send(self, data, split=4096, gap=0.0):
        for i in range(0, len(data), split):
            os.write(self.master, data[i:i + split])
            if gap:
                time.sleep(gap)

    def close(self):
        self.thread.join(timeout=1)
        os.close(self.master)
        os.close(self.slave)


class Adversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img = jpeg()
        cls.packet = build_packet(cls.img, 96, 64)

    def run_capture(self, script, timeout=3.0, **kw):
        dev = Device(script)
        try:
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / 'o.jpg'
                try:
                    res = capture(dev.port, out, timeout, **kw)
                    return res, out.read_bytes(), dev
                except CaptureError as exc:
                    self.assertFalse(out.exists(), 'a rejected frame must never be written')
                    return exc, None, dev
        finally:
            dev.close()

    def test_every_single_bit_flip_in_header_is_rejected_or_harmless(self):
        # Flip each header bit; the frame must never decode to different image bytes.
        for bit in range(HEADER.size * 8):
            p = bytearray(self.packet)
            p[bit // 8] ^= 1 << (bit % 8)
            try:
                meta, data = decode_packet(bytes(p))
            except FrameError:
                continue
            self.fail(f'header bit {bit} flipped but packet still accepted: {meta}')

    def test_random_payload_corruption_always_rejected(self):
        rnd = random.Random(7)
        for _ in range(400):
            p = bytearray(self.packet)
            i = rnd.randrange(HEADER.size, len(p))
            p[i] ^= 1 << rnd.randrange(8)
            with self.assertRaises(FrameError):
                decode_packet(bytes(p))

    def test_truncation_at_every_length_rejected(self):
        for n in range(0, len(self.packet), 37):
            with self.assertRaises(FrameError):
                decode_packet(self.packet[:n])

    def test_crc_collision_guard_needs_real_jpeg(self):
        junk = bytes(1000)
        pkt = HEADER.pack(MAGIC, len(junk), 96, 64, zlib.crc32(junk) & 0xffffffff) + junk
        with self.assertRaises(FrameError):
            decode_packet(pkt)

    def test_random_fragmentation_patterns(self):
        rnd = random.Random(3)
        for trial in range(6):
            cuts = sorted(rnd.sample(range(1, len(self.packet)), 12))
            parts = [self.packet[a:b] for a, b in zip([0] + cuts, cuts + [len(self.packet)])]

            def script(dev, parts=parts):
                dev.read_request()
                dev.send(b'ets Jun  8 2016 00:22:57\r\nrst:0x1\r\n')
                for part in parts:
                    os.write(dev.master, part)
                    time.sleep(0.002)
            res, data, _ = self.run_capture(script)
            self.assertEqual(data, self.img, f'trial {trial}')

    def test_long_garbage_prefix_with_magic_split_across_reads(self):
        rnd = random.Random(11)
        noise = bytes(rnd.randrange(256) for _ in range(9000)).replace(b'MSJ1', b'XXXX').replace(b'ERROR ', b'error_')

        def script(dev):
            dev.read_request()
            dev.send(noise + self.packet[:2], split=4096, gap=0.01)   # 'MS' ends a read
            time.sleep(0.05)
            dev.send(self.packet[2:], split=5, gap=0.0005)
        res, data, _ = self.run_capture(script, timeout=6)
        self.assertEqual(data, self.img)

    def test_three_false_headers_then_real(self):
        false = b'MSJ1' + struct.pack('<IHHI', 0xFFFFFFFF, 0, 0, 0)

        def script(dev):
            dev.read_request()
            dev.send(false * 3 + self.packet, split=7)
        res, data, _ = self.run_capture(script)
        self.assertEqual(data, self.img)

    def test_plausible_false_header_fails_closed_without_second_request(self):
        false = b'MSJ1' + struct.pack('<IHHI', 40, 96, 64, 1234) + bytes(40)

        def script(dev):
            dev.read_request()
            dev.send(false + self.packet)
        res, data, dev = self.run_capture(script)
        self.assertIsInstance(res, CaptureError)
        self.assertEqual(len(dev.requests), 1)

    def test_firmware_error_line_fails_fast(self):
        def script(dev):
            dev.read_request()
            dev.send(b'ERROR capture locked: bring-up build, hardware gates not verified\r\n')
        t0 = time.monotonic()
        res, data, dev = self.run_capture(script, timeout=30)
        self.assertIsInstance(res, CaptureError)
        self.assertIn('capture locked', str(res))
        self.assertLess(time.monotonic() - t0, 5, 'must not wait out the 30 s timeout')

    def test_error_text_inside_jpeg_payload_is_not_misread(self):
        im = self.img[:-2] + b'\nERROR fake\n' + self.img[-2:]   # text inside the binary payload, after the header
        try:
            pkt = build_packet(im, 96, 64)
            decode_packet(pkt)
        except FrameError:
            self.skipTest('constructed payload not a decodable JPEG on this Pillow')

        def script(dev):
            dev.read_request()
            dev.send(pkt, split=9)
        res, data, _ = self.run_capture(script)
        self.assertEqual(data, im)

    def test_exactly_one_capture_request_is_sent(self):
        def script(dev):
            dev.read_request()
            dev.send(self.packet)
            time.sleep(0.2)
            dev.read_request(timeout=0.3)
        res, data, dev = self.run_capture(script)
        self.assertEqual(dev.requests[0], b'CAPTURE\n')
        self.assertEqual(dev.requests[1], b'', 'host must not send anything after its one request')

    def test_wait_ready_sends_request_only_after_banner(self):
        order = []

        def script(dev):
            time.sleep(0.2)   # let the host open the port and leave cooked/echo mode first
            dev.send(b'rst:0x1 (POWERON_RESET)\r\n')
            time.sleep(0.3)
            early = b''
            if select.select([dev.master], [], [], 0)[0]:
                early = os.read(dev.master, 64)
            order.append(early)
            dev.send(b'MICROSCAN_VISIBLE_USB_READY; type CAPTURE and newline\r\n')
            dev.read_request()
            dev.send(self.packet)
        res, data, dev = self.run_capture(script, timeout=5, wait_ready=5)
        self.assertNotIn(b'CAPTURE', order[0], 'CAPTURE was sent before the READY banner')
        self.assertTrue(res['ready_banner_seen'])
        self.assertEqual(data, self.img)

    def test_wait_ready_reports_boot_error(self):
        def script(dev):
            time.sleep(0.2)
            dev.send(b'ERROR camera init 0x105\r\n')
        res, data, dev = self.run_capture(script, timeout=5, wait_ready=3)
        self.assertIsInstance(res, CaptureError)
        self.assertIn('0x105', str(res))

    def test_wait_ready_timeout_then_single_request(self):
        def script(dev):
            dev.read_request(timeout=4)
            dev.send(self.packet)
        res, data, dev = self.run_capture(script, timeout=5, wait_ready=0.4)
        self.assertFalse(res['ready_banner_seen'])
        self.assertEqual(data, self.img)

    def test_all_declared_bauds_configure_a_port(self):
        for baud in BAUDS:
            def script(dev):
                dev.read_request()
                dev.send(self.packet)
            res, data, _ = self.run_capture(script, baud=baud)
            self.assertEqual(res['baud'], baud)

    def test_unsupported_baud_refused(self):
        m, s = pty.openpty()
        try:
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(CaptureError):
                    capture(os.ttyname(s), Path(d) / 'x.jpg', 1, baud=57600)
        finally:
            os.close(m)
            os.close(s)

    def test_transfer_time_arithmetic(self):
        self.assertAlmostEqual(transfer_seconds(250_000, 115200), (250_000 + 16) * 10 / 115200)
        self.assertAlmostEqual(transfer_seconds(250_000, 115200), 21.703, places=2)
        self.assertLess(transfer_seconds(250_000, 921600), 2.8)
        with self.assertRaises(ValueError):
            transfer_seconds(1, 0)

    def test_cli_refuses_without_indicator_confirmation(self):
        p = subprocess.run([sys.executable, str(HOST / 'serial_capture.py'), '--port', '/dev/null', '--output', '/tmp/never.jpg'],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn('--indicator-confirmed is required', p.stderr)

    def test_host_code_has_no_network_or_loop_capture(self):
        for name in ('serial_capture.py', 'microscan_usb_packet.py'):
            src = (HOST / name).read_text()
            for banned in ('import socket', 'import requests', 'urllib', 'http.client', 'import asyncio', 'while True:\n        os.write'):
                self.assertNotIn(banned, src, f'{banned!r} in {name}')
        self.assertEqual((HOST / 'serial_capture.py').read_text().count("os.write(fd, b'CAPTURE\\n')"), 1)


if __name__ == '__main__':
    unittest.main()
