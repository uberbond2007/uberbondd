import os, sys, tempfile, tracemalloc, unittest, wave
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stream"))
from nasolink_safe import (ChannelMap, ChunkedWavWriter, FrameLayout, Limits, StreamLimitError, StreamParser,
                           classify_seq, encode_frame, record)

CM = ChannelMap(vib_slot=0, evidence="test-only")


def frame(seq, n=16, a=1, b=2):
    return encode_frame(seq, [a, b] * n)


class Policy(unittest.TestCase):
    def test_reported_reproduction_is_a_jump_not_missing_frames(self):
        self.assertEqual(classify_seq(0, 0x80000000), ("BACKWARD", 0))   # exactly half-range: ambiguous -> never fill
        self.assertEqual(classify_seq(0, 0x7FFFFFFF), ("JUMP", 0))
        self.assertEqual(classify_seq(0, 0x80000001), ("BACKWARD", 0))

    def test_wrap_dup_gap(self):
        self.assertEqual(classify_seq(0xFFFFFFFF, 0), ("CONTIGUOUS", 0))
        self.assertEqual(classify_seq(5, 5), ("DUPLICATE", 0))
        self.assertEqual(classify_seq(5, 8), ("GAP", 2))
        self.assertEqual(classify_seq(5, 4), ("BACKWARD", 0))
        self.assertEqual(classify_seq(0, 4097, Limits(max_jump_frames=4096)), ("GAP", 4096))
        self.assertEqual(classify_seq(0, 4098, Limits(max_jump_frames=4096)), ("JUMP", 0))
        with self.assertRaises(ValueError):
            Limits(max_gap_fill_frames=10, max_jump_frames=5)

    def test_channel_map_requires_evidence(self):
        with self.assertRaises(ValueError):
            ChannelMap(vib_slot=0, evidence="")
        with self.assertRaises(ValueError):
            ChannelMap(vib_slot=2, evidence="x")


class Parser(unittest.TestCase):
    def test_valid_crc_jump_does_not_allocate(self):
        d = tempfile.mkdtemp(); path = os.path.join(d, "o.wav")
        tracemalloc.start()
        st = record([frame(0), frame(0x80000000), frame(0x80000001)], path, 32000, CM)
        _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        self.assertLess(peak, 1 << 20)
        self.assertEqual(st["stopped_on"], "BACKWARD"); self.assertEqual(st["filled_frames"], 0)
        self.assertEqual(st["missing_frames"], 0)
        with wave.open(path) as w:
            self.assertEqual(w.getnframes(), 16)
        st = record([frame(0), frame(0x7FFFFFFF)], os.path.join(d, "p.wav"), 32000, CM)
        self.assertEqual(st["stopped_on"], "JUMP"); self.assertEqual(st["filled_frames"], 0)

    def test_small_gap_filled_and_bounded(self):
        d = tempfile.mkdtemp()
        st = record([frame(0), frame(1), frame(4), frame(5)], os.path.join(d, "g.wav"), 32000, CM)
        self.assertEqual((st["gaps"], st["missing_frames"], st["filled_frames"]), (1, 2, 2))
        with wave.open(os.path.join(d, "g.wav")) as w:
            self.assertEqual(w.getnframes(), 16 * 6)
        with self.assertRaises(StreamLimitError):    # gap bigger than per-gap fill limit but below jump limit
            record([frame(0), frame(20)], os.path.join(d, "h.wav"), 32000, CM, Limits(max_gap_fill_frames=8))
        with self.assertRaises(StreamLimitError):    # cumulative fill cap
            record([frame(0), frame(5), frame(10), frame(15)], os.path.join(d, "i.wav"), 32000, CM,
                   Limits(max_gap_fill_frames=8, max_total_fill_frames=8))
        st = record([frame(0), frame(3)], os.path.join(d, "j.wav"), 32000, CM, fill_gaps=False)
        self.assertEqual(st["filled_frames"], 0)

    def test_corruption_resync_duplicates_and_split_feed(self):
        good = [frame(i, a=i, b=-i) for i in range(4)]
        bad = bytearray(good[1]); bad[-1] ^= 0xFF
        stream = b"garbageNL\x00" + good[0] + bytes(bad) + good[2] + good[2] + good[3][:7]
        p = StreamParser()
        evs = []
        for i in range(0, len(stream), 5):
            evs += p.feed(stream[i:i + 5])
        evs += p.feed(good[3][7:])
        self.assertEqual([e["seq"] for e in evs], [0, 2, 3])
        self.assertEqual(p.stats["crc_errors"] >= 1, True)
        self.assertEqual(p.stats["duplicates"], 1)
        self.assertEqual(p.stats["missing_frames"], 1)

    def test_oversize_frame_header_rejected_not_buffered(self):
        import struct, zlib
        body = struct.pack("<IH", 1, 65000)
        p = StreamParser(limits=Limits(max_buffer_bytes=4096))
        evs = p.feed(b"NL" + body + b"\x00" * 100 + frame(2))
        self.assertEqual([e["seq"] for e in evs], [2])

    def test_unframed_input_buffer_bounded(self):
        p = StreamParser(limits=Limits(max_buffer_bytes=1024))
        for _ in range(100):
            p.feed(b"\x00" * 1000)
        self.assertLess(len(p.buf), 8)


class Writer(unittest.TestCase):
    def test_channel_mapping_applied(self):
        d = tempfile.mkdtemp()
        for vib_slot, want in ((0, [10, 20]), (1, [20, 10])):
            path = os.path.join(d, f"m{vib_slot}.wav")
            w = ChunkedWavWriter(path, 32000, ChannelMap(vib_slot, "t")); w.write_frame([10, 20, 10, 20]); w.close()
            with wave.open(path) as r:
                import struct
                self.assertEqual(list(struct.unpack("<4h", r.readframes(2)))[:2], want)

    def test_data_cap(self):
        d = tempfile.mkdtemp()
        w = ChunkedWavWriter(os.path.join(d, "c.wav"), 32000, CM, limits=Limits(max_data_bytes=100))
        with self.assertRaises(StreamLimitError):
            for _ in range(10):
                w.write_frame([1, 2] * 8)
        w.close()


if __name__ == "__main__":
    unittest.main()
