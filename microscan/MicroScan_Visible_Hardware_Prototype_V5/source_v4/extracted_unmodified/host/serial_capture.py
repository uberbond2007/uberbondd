"""Operator-initiated ONE-SHOT capture over an existing, visibly labelled USB-serial bench camera.

Linux/macOS POSIX serial only. No Wi-Fi, discovery, background monitoring, or retries
that trigger additional captures. A correct physical indicator and board configuration
are prerequisites, not checked by this software.
"""
from __future__ import annotations
import argparse
import json
import os
import select
import struct
import termios
import time
from pathlib import Path
from microscan_usb_packet import HEADER, MAGIC, MAX_FRAME_BYTES, FrameError, decode_packet

BAUDS = {9600: termios.B9600, 115200: termios.B115200}
MAX_PREFIX = 4096

class CaptureError(RuntimeError):
    pass


def set_serial_raw(fd: int, baud: int) -> None:
    if baud not in BAUDS:
        raise CaptureError('Only 9600 or 115200 baud are supported')
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0  # iflag
    attrs[1] = 0  # oflag
    attrs[2] = termios.CS8 | termios.CLOCAL | termios.CREAD
    attrs[3] = 0  # lflag
    attrs[4] = BAUDS[baud]
    attrs[5] = BAUDS[baud]
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def read_one_packet(fd: int, timeout: float = 180, cap_bytes: int = MAX_FRAME_BYTES) -> bytes:
    """Read MSJ1 packet, ignoring bounded serial boot messages and false magic."""
    if not (0 < timeout <= 300):
        raise ValueError('Timeout out of range')
    deadline = time.monotonic() + timeout
    buf = bytearray()
    needed = None
    while True:
        if needed is not None and len(buf) >= needed:
            packet = bytes(buf[:needed])
            try:
                decode_packet(packet)
                return packet
            except FrameError as exc:
                raise CaptureError(f'Camera frame failed integrity check: {exc}') from exc
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CaptureError('Timed out receiving a complete camera packet')
        ready, _, _ = select.select([fd], [], [], min(remaining, 1))
        if not ready:
            continue
        chunk = os.read(fd, 4096)
        if not chunk:
            continue
        buf.extend(chunk)
        if needed is None:
            while True:
                pos = buf.find(MAGIC)
                if pos < 0:
                    if len(buf) > MAX_PREFIX:
                        del buf[:-3]  # keep possible partial magic suffix
                    break
                if pos:
                    del buf[:pos]
                if len(buf) < HEADER.size:
                    break
                _, frame_len, w, h, _ = HEADER.unpack_from(buf)
                if not (2 <= frame_len <= min(cap_bytes, MAX_FRAME_BYTES)) or not (1 <= w <= 5000 and 1 <= h <= 5000):
                    # A false header may be followed immediately by a real one.
                    del buf[:4]
                    continue
                needed = HEADER.size + frame_len
                break
        if len(buf) > cap_bytes + HEADER.size + MAX_PREFIX:
            raise CaptureError('Serial buffer exceeded hard cap')


def capture(port: str, jpeg_path: Path, timeout: float = 180, baud: int = 115200):
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        set_serial_raw(fd, baud)
        # Explicit foreground request; no repeated capture on failure.
        os.write(fd, b'CAPTURE\n')
        packet = read_one_packet(fd, timeout)
        meta, jpeg = decode_packet(packet)
        jpeg_path.parent.mkdir(parents=True, exist_ok=True)
        jpeg_path.write_bytes(jpeg)
        return {'path': str(jpeg_path), **meta, 'source': 'operator_requested_serial_capture'}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description='One-shot, visibly indicated USB-serial bench capture')
    parser.add_argument('--port', required=True, help='Serial port from a physically verified open camera')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--baud', type=int, choices=sorted(BAUDS), default=115200)
    parser.add_argument('--indicator-confirmed', action='store_true', help='Operator has confirmed an obvious physical recording indicator')
    args = parser.parse_args()
    if not args.indicator_confirmed:
        parser.error('Capture disabled: --indicator-confirmed is required after physical verification')
    try:
        print(json.dumps(capture(args.port, args.output, args.timeout, args.baud), indent=2))
    except (CaptureError, OSError, FrameError) as exc:
        parser.exit(2, f'FAIL: {exc}\n')

if __name__ == '__main__':
    main()
