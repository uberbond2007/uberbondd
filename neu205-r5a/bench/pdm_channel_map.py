#!/usr/bin/env python3
"""Decide which decoded PCM slot is the vibration sensor and which is the air microphone — from captures, not docs.

Why: ESP-IDF (v5.4 PDM RX Usage) states "The right slot is received first in stereo mode" (buffer order R,L,R,L;
swappable with clk_inv). NasoVoce maps vibration -> left, mic -> right; SEL pulled down = left slot. r5 assumed
interleaved [vib, mic]. If wiring follows NasoVoce, the real buffer is [mic, vib]. Only a capture can settle it.

Inputs: three 2-channel 16-bit WAVs recorded through the ACTUAL firmware + host reader, stored in raw slot order
(slot 0 = first int16 in the buffer). No human body contact required:
  silence.wav  — device still, room quiet (noise floor, dead/duplicated channel check)
  air.wav      — a phone/speaker ~30 cm away plays a steady tone at AIR_HZ; device not touched
  contact.wav  — a phone's vibration motor (or a tuning fork) pressed on the vibration-sensor housing, no tone played
Decision (pre-registered): mic slot = slot whose air/silence band-energy ratio exceeds the other by >= 10 dB;
vib slot = slot whose contact/silence low-band ratio exceeds the other by >= 6 dB; both must agree on opposite
slots, both channels must be live and not identical. Otherwise INCONCLUSIVE (do not ship a guess).
Electrical cross-check (strongest, optional): power one sensor down; its slot must fall to the floor.
"""
import argparse, hashlib, json, math, struct, sys, wave
from pathlib import Path

AIR_HZ = 1000.0
LOW_BAND = (80.0, 400.0)       # phone vibration motors ~150–250 Hz
AIR_MARGIN_DB, CONTACT_MARGIN_DB = 10.0, 6.0


def read_stereo(path):
    with wave.open(path) as w:
        if w.getnchannels() != 2 or w.getsampwidth() != 2:
            raise ValueError(f"{path}: need 2-channel 16-bit PCM in raw slot order")
        fs, n = w.getframerate(), w.getnframes()
        data = struct.unpack("<%dh" % (2 * n), w.readframes(n))
    return fs, [list(data[0::2]), list(data[1::2])]


def goertzel_power(x, fs, f):
    k = 2 * math.cos(2 * math.pi * f / fs); s1 = s2 = 0.0
    for v in x:
        s1, s2 = v + k * s1 - s2, s1
    return (s1 * s1 + s2 * s2 - k * s1 * s2) / max(1, len(x)) ** 2


def band_power(x, fs, lo, hi, step=20.0):
    p, f = 0.0, lo
    while f <= hi:
        p += goertzel_power(x, fs, f); f += step
    return p


def db(a, b):
    return 10 * math.log10((a + 1e-12) / (b + 1e-12))


def analyse(silence, air, contact, air_hz=AIR_HZ):
    fs = silence[0]
    if not (fs == air[0] == contact[0]):
        raise ValueError("sample rates differ between captures")
    S, A, C = silence[1], air[1], contact[1]
    reasons = []
    for slot in (0, 1):
        if max(abs(v) for v in S[slot] + A[slot] + C[slot]) == 0:
            reasons.append(f"slot {slot} is all zeros (sensor absent, SEL/pin wrong, or mono mode)")
    if A[0] == A[1] or C[0] == C[1]:
        reasons.append("slots are identical: mono duplication or both sensors on one SEL level")
    air_gain = [db(goertzel_power(A[s], fs, air_hz), goertzel_power(S[s], fs, air_hz)) for s in (0, 1)]
    con_gain = [db(band_power(C[s], fs, *LOW_BAND), band_power(S[s], fs, *LOW_BAND)) for s in (0, 1)]
    mic = 0 if air_gain[0] - air_gain[1] >= AIR_MARGIN_DB else 1 if air_gain[1] - air_gain[0] >= AIR_MARGIN_DB else None
    vib = 0 if con_gain[0] - con_gain[1] >= CONTACT_MARGIN_DB else 1 if con_gain[1] - con_gain[0] >= CONTACT_MARGIN_DB else None
    if mic is None:
        reasons.append("air tone does not separate the slots by >= %.0f dB" % AIR_MARGIN_DB)
    if vib is None:
        reasons.append("contact vibration does not separate the slots by >= %.0f dB" % CONTACT_MARGIN_DB)
    if mic is not None and vib is not None and mic == vib:
        reasons.append("air and contact tests point to the same slot")
    ok = not reasons
    return {"decision": "MAPPED" if ok else "INCONCLUSIVE", "vib_slot": vib if ok else None,
            "mic_slot": mic if ok else None, "air_gain_db": [round(g, 1) for g in air_gain],
            "contact_gain_db": [round(g, 1) for g in con_gain], "sample_rate": fs, "reasons": reasons,
            "note": "slot 0 = first int16 in the decoded buffer; map to firmware L/R only via this result"}


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--silence", required=True); a.add_argument("--air", required=True); a.add_argument("--contact", required=True)
    a.add_argument("--air-hz", type=float, default=AIR_HZ)
    x = a.parse_args(argv)
    r = analyse(read_stereo(x.silence), read_stereo(x.air), read_stereo(x.contact), x.air_hz)
    r["inputs_sha256"] = {k: hashlib.sha256(Path(getattr(x, k)).read_bytes()).hexdigest() for k in ("silence", "air", "contact")}
    r["report_sha256"] = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
    print(json.dumps(r, indent=1))
    return 0 if r["decision"] == "MAPPED" else 1


if __name__ == "__main__":
    sys.exit(main())
