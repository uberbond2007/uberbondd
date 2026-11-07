"""r5a bounded NasoLink stream reader: sequence-gap policy, fail-closed limits, chunked WAV output.

Corrects GPT-6 review finding: r5 `nasolink_reader.parse` computed frames_missing with uint32 modular arithmetic, so a
valid-CRC jump 0 -> 0x80000000 reported 2,147,483,647 missing frames and `write_wav(..., fill_gaps=True)` could try
to allocate gigabytes of zero padding.

Design (independent of r5's exact frame bytes):
  * `classify_seq(prev, cur, limits)` decides CONTIGUOUS / GAP(n) / DUPLICATE / BACKWARD / JUMP. Only a GAP no larger
    than `limits.max_gap_fill_frames` may ever be zero-filled; JUMP and BACKWARD start a new segment and are never filled.
  * `ChunkedWavWriter` streams frames and zero fill to disk in bounded chunks and refuses to exceed `max_data_bytes`
    or `max_total_fill_frames`. Memory use is O(chunk), not O(gap).
  * `StreamParser` resynchronises on a magic word, verifies CRC, bounds its buffer, and emits events. Its byte layout
    (`FrameLayout`) is an r5a REFERENCE layout: it must be reconciled with the real r5 firmware framing before use
    (see README "Adapter"). The policy and writer above do not depend on it.
  * Channel order is NEVER assumed. Writers require an explicit `ChannelMap` produced by the bench procedure.

CRC detects accidental corruption only. It does not authenticate samples, prove correct sensor routing, or make the
audio medically meaningful.
"""
import struct, wave, zlib
from dataclasses import dataclass

U32 = 1 << 32


class StreamLimitError(Exception):
    """A configured safety limit was reached; the caller must stop or start a new recording."""


@dataclass(frozen=True)
class Limits:
    max_gap_fill_frames: int = 8            # largest single gap that may be zero-filled (8 frames ~ tens of ms)
    max_jump_frames: int = 4096             # gaps above this are JUMP (resync), never "missing frames"
    max_total_fill_frames: int = 256        # cumulative zero fill per recording
    max_frame_samples: int = 4096           # per channel, per frame
    max_buffer_bytes: int = 1 << 16         # parser buffer while hunting for a frame
    max_data_bytes: int = 512 << 20         # WAV data cap per file (<< 4 GiB RIFF limit)
    fill_chunk_frames: int = 1              # zero fill written one frame at a time

    def __post_init__(self):
        if not (0 <= self.max_gap_fill_frames <= self.max_jump_frames < U32 // 2):
            raise ValueError("require 0 <= max_gap_fill_frames <= max_jump_frames < 2**31")
        if self.max_data_bytes >= (1 << 32) - 64:
            raise ValueError("WAV data cannot reach 4 GiB")


def classify_seq(prev, cur, limits=Limits()):
    """Return (kind, missing). kind in CONTIGUOUS, GAP, DUPLICATE, BACKWARD, JUMP. `missing` is only non-zero for GAP."""
    if prev is None:
        return "FIRST", 0
    if not (0 <= prev < U32 and 0 <= cur < U32):
        raise ValueError("sequence numbers are uint32")
    delta = (cur - prev) % U32
    if delta == 0:
        return "DUPLICATE", 0
    if delta == 1:
        return "CONTIGUOUS", 0
    if delta >= U32 // 2:
        return "BACKWARD", 0
    missing = delta - 1
    if missing > limits.max_jump_frames:
        return "JUMP", 0
    return "GAP", missing


@dataclass(frozen=True)
class ChannelMap:
    """Which interleaved PCM slot carries which sensor. Must come from a bench capture, not from documentation."""
    vib_slot: int
    evidence: str            # e.g. bench report sha256; empty string is rejected

    def __post_init__(self):
        if self.vib_slot not in (0, 1):
            raise ValueError("vib_slot must be 0 or 1")
        if not self.evidence:
            raise ValueError("channel map requires bench evidence (report hash); refusing to assume order")

    @property
    def mic_slot(self):
        return 1 - self.vib_slot


class ChunkedWavWriter:
    """Writes one sensor channel (or both, as 2-ch WAV in [vib, mic] order) as 16-bit PCM with bounded memory."""

    def __init__(self, path, sample_rate, channel_map, channels="both", limits=Limits()):
        if channels not in ("both", "vib", "mic"):
            raise ValueError(channels)
        self.map, self.sel, self.limits = channel_map, channels, limits
        self.nch = 2 if channels == "both" else 1
        self.w = wave.open(str(path), "wb")
        self.w.setnchannels(self.nch); self.w.setsampwidth(2); self.w.setframerate(sample_rate)
        self.data_bytes = 0
        self.filled_frames = 0
        self.samples_per_frame = None

    def _guard(self, nbytes):
        if self.data_bytes + nbytes > self.limits.max_data_bytes:
            raise StreamLimitError("max_data_bytes reached; start a new file")

    def write_frame(self, interleaved):
        """`interleaved` = sequence of int16 in device slot order [s0, s1, s0, s1, ...]."""
        if len(interleaved) % 2:
            raise ValueError("stereo frame must have an even sample count")
        n = len(interleaved) // 2
        if n > self.limits.max_frame_samples:
            raise StreamLimitError("frame larger than max_frame_samples")
        if self.samples_per_frame is None:
            self.samples_per_frame = n
        vib = interleaved[self.map.vib_slot::2]; mic = interleaved[self.map.mic_slot::2]
        if self.sel == "both":
            out = [x for pair in zip(vib, mic) for x in pair]
        else:
            out = list(vib if self.sel == "vib" else mic)
        b = struct.pack("<%dh" % len(out), *out)
        self._guard(len(b)); self.w.writeframesraw(b); self.data_bytes += len(b)

    def fill_gap(self, frames):
        """Zero-fill a policy-approved GAP. Never called for JUMP/BACKWARD. Bounded per gap and per file."""
        if frames <= 0:
            return
        if frames > self.limits.max_gap_fill_frames:
            raise StreamLimitError("gap exceeds max_gap_fill_frames; refuse to fill")
        if self.filled_frames + frames > self.limits.max_total_fill_frames:
            raise StreamLimitError("max_total_fill_frames reached; recording too lossy")
        if self.samples_per_frame is None:
            raise StreamLimitError("cannot size a gap before the first frame")
        chunk = bytes(2 * self.nch * self.samples_per_frame * self.limits.fill_chunk_frames)
        left = frames
        while left > 0:
            k = min(left, self.limits.fill_chunk_frames)
            b = chunk[: 2 * self.nch * self.samples_per_frame * k]
            self._guard(len(b)); self.w.writeframesraw(b); self.data_bytes += len(b); left -= k
        self.filled_frames += frames

    def close(self):
        self.w.close()   # wave module rewrites RIFF/data sizes on close


# ---- reference framing (r5a; reconcile with real r5 firmware before use) -------------------------------------
@dataclass(frozen=True)
class FrameLayout:
    magic: bytes = b"NL"
    # header after magic: seq u32, nsamp u16 (per channel), little endian; payload int16 interleaved; crc32 of header+payload
    header: str = "<IH"
    crc: str = "crc32"

    @property
    def hsize(self):
        return struct.calcsize(self.header)


def encode_frame(seq, interleaved, layout=FrameLayout()):
    body = struct.pack(layout.header, seq, len(interleaved) // 2) + struct.pack("<%dh" % len(interleaved), *interleaved)
    return layout.magic + body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


class StreamParser:
    """Incremental parser. feed(bytes) -> list of events (dicts). Never allocates in proportion to a sequence jump."""

    def __init__(self, layout=FrameLayout(), limits=Limits()):
        self.layout, self.limits = layout, limits
        self.buf = bytearray()
        self.prev = None
        self.stats = {"frames": 0, "crc_errors": 0, "resync_bytes": 0, "gaps": 0, "missing_frames": 0,
                      "jumps": 0, "backward": 0, "duplicates": 0, "segments": 1}

    def feed(self, data):
        self.buf += data
        events = []
        L, m = self.layout, self.layout.magic
        while True:
            i = self.buf.find(m)
            if i < 0:
                keep = len(m) - 1
                self.stats["resync_bytes"] += max(0, len(self.buf) - keep)
                del self.buf[: max(0, len(self.buf) - keep)]
                break
            if i:
                self.stats["resync_bytes"] += i; del self.buf[:i]
            if len(self.buf) < len(m) + L.hsize:
                break
            seq, nsamp = struct.unpack_from(L.header, self.buf, len(m))
            if nsamp == 0 or nsamp > self.limits.max_frame_samples:
                self.stats["resync_bytes"] += 1; del self.buf[:1]; continue
            total = len(m) + L.hsize + 4 * nsamp + 4
            if total > self.limits.max_buffer_bytes:
                self.stats["resync_bytes"] += 1; del self.buf[:1]; continue
            if len(self.buf) < total:
                break
            body = bytes(self.buf[len(m): total - 4])
            (crc,) = struct.unpack_from("<I", self.buf, total - 4)
            if zlib.crc32(body) & 0xFFFFFFFF != crc:
                self.stats["crc_errors"] += 1; del self.buf[:1]; continue
            samples = list(struct.unpack_from("<%dh" % (2 * nsamp), body, L.hsize))
            del self.buf[:total]
            kind, missing = classify_seq(self.prev, seq, self.limits)
            if kind == "DUPLICATE":
                self.stats["duplicates"] += 1; continue
            if kind == "BACKWARD":
                self.stats["backward"] += 1; self.stats["segments"] += 1
            elif kind == "JUMP":
                self.stats["jumps"] += 1; self.stats["segments"] += 1
            elif kind == "GAP":
                self.stats["gaps"] += 1; self.stats["missing_frames"] += missing
            self.prev = seq; self.stats["frames"] += 1
            events.append({"kind": kind, "seq": seq, "missing": missing, "samples": samples})
        if len(self.buf) > self.limits.max_buffer_bytes:
            raise StreamLimitError("parser buffer exceeded; stream is not framed as expected")
        return events


def record(chunks, path, sample_rate, channel_map, limits=Limits(), layout=FrameLayout(), fill_gaps=True):
    """Parse an iterable of byte chunks into a WAV. Gaps within policy are filled (bounded); JUMP/BACKWARD close the
    current segment: the remainder is NOT written to this file and the stats say so (fail closed, no fabrication)."""
    p = StreamParser(layout, limits)
    w = ChunkedWavWriter(path, sample_rate, channel_map, "both", limits)
    stopped = None
    try:
        for c in chunks:
            for ev in p.feed(c):
                if ev["kind"] in ("JUMP", "BACKWARD"):
                    stopped = ev["kind"]; break
                if ev["kind"] == "GAP" and fill_gaps:
                    w.fill_gap(ev["missing"])
                w.write_frame(ev["samples"])
            if stopped:
                break
    finally:
        w.close()
    return dict(p.stats, stopped_on=stopped, filled_frames=w.filled_frames, data_bytes=w.data_bytes)
