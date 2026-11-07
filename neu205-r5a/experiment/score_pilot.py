#!/usr/bin/env python3
"""Score the r5a zero-cost pilot (E1R). Pre-registered thresholds live in THRESHOLDS; edit only by new version.

Rows (JSONL, private, kept on the owner's device/computer):
  {"config": "A_phone_30cm|A_phone_5cm|A_nearlip_1p5cm|B_camera_commands|...", "kind": "utterance|silence|command",
   "reference": "...", "hypothesis": "...", "duration_s": 3.2, "leak_hypothesis": "... (optional, 1 m recorder)"}
  {"config": "...", "kind": "comfort", "strain_0_10": 1, "note": "..."}
Decision per configuration. A failure rejects ONLY that configuration (sensor, distance, mode); it never retires the
whole track. Any strain >= STOP_STRAIN ends all whisper trials for the day and routes to the non-vocal Mode B/AAC path.
"""
import argparse, json, re, sys
from collections import defaultdict

VERSION = "E1R-1"
THRESHOLDS = {"min_utterances": 20, "max_lenient_wer": 0.25, "max_false_words_per_min": 0.5,
              "max_median_strain": 2, "stop_strain": 4, "min_leak_wer_for_private": 0.80,
              "min_commands": 40, "min_command_accuracy": 0.85}
FILLERS = {"um", "uh", "erm", "hmm", "ah"}
NUM = {str(i): w for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                       "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
CONTR = {"don't": "do not", "can't": "cannot", "it's": "it is", "i'm": "i am", "won't": "will not", "isn't": "is not"}


def strict_tokens(t):
    return t.split()


def lenient_tokens(t):
    t = t.lower()
    for k, v in CONTR.items():
        t = t.replace(k, v)
    out = []
    for w in re.findall(r"[a-z0-9]+", t):
        w = NUM.get(w, w)
        if w not in FILLERS:
            out.append(w)
    return out


def edits(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def wer(pairs, tok):
    e = n = 0
    for ref, hyp in pairs:
        r, h = tok(ref), tok(hyp)
        e += edits(r, h); n += len(r)
    return e / n if n else None


def score(rows, commands=None, th=THRESHOLDS):
    by = defaultdict(list)
    for r in rows:
        by[r["config"]].append(r)
    out = {}
    stop_all = False
    for cfg, rs in sorted(by.items()):
        utt = [(r["reference"], r["hypothesis"]) for r in rs if r["kind"] == "utterance"]
        sil = [r for r in rs if r["kind"] == "silence"]
        cmd = [r for r in rs if r["kind"] == "command"]
        strain = sorted(r["strain_0_10"] for r in rs if r["kind"] == "comfort")
        leak = [(r["reference"], r["leak_hypothesis"]) for r in rs if r["kind"] == "utterance" and r.get("leak_hypothesis") is not None]
        sil_min = sum(r.get("duration_s", 0) for r in sil) / 60
        false_words = sum(len(lenient_tokens(r["hypothesis"])) for r in sil)
        res = {"n_utterances": len(utt), "strict_wer": wer(utt, strict_tokens), "lenient_wer": wer(utt, lenient_tokens),
               "silence_minutes": round(sil_min, 2), "false_words_per_min": round(false_words / sil_min, 2) if sil_min else None,
               "median_strain": strain[len(strain) // 2] if strain else None, "max_strain": strain[-1] if strain else None,
               "leak_lenient_wer_1m": wer(leak, lenient_tokens) if leak else None}
        reasons = []
        if res["max_strain"] is not None and res["max_strain"] >= th["stop_strain"]:
            stop_all = True; res["decision"] = "STOP_SAFETY"; out[cfg] = res; continue
        if cmd:
            if not commands:
                raise ValueError("command rows need the pre-registered command list")
            ok = sum(nearest(r["hypothesis"], commands) == r["reference"] for r in cmd)
            res["n_commands"] = len(cmd); res["command_accuracy"] = round(ok / len(cmd), 3)
            if len(cmd) < th["min_commands"]:
                reasons.append("INSUFFICIENT_N")
            elif res["command_accuracy"] < th["min_command_accuracy"]:
                reasons.append("accuracy below threshold")
        if utt:
            if len(utt) < th["min_utterances"]:
                reasons.append("INSUFFICIENT_N")
            elif res["lenient_wer"] > th["max_lenient_wer"]:
                reasons.append("lenient WER above threshold")
        if not utt and not cmd:
            reasons.append("INSUFFICIENT_N")
        if res["false_words_per_min"] is None and utt:
            reasons.append("no silence probe recorded")
        elif res["false_words_per_min"] is not None and res["false_words_per_min"] > th["max_false_words_per_min"]:
            reasons.append("false words during silence")
        if res["median_strain"] is None:
            reasons.append("no comfort rating")
        elif res["median_strain"] > th["max_median_strain"]:
            reasons.append("median strain above threshold")
        res["privacy_label"] = ("UNMEASURED" if res["leak_lenient_wer_1m"] is None else
                                "LOW_LEAKAGE_AT_1M" if res["leak_lenient_wer_1m"] >= th["min_leak_wer_for_private"] else "AUDIBLE_AT_1M")
        res["decision"] = ("INSUFFICIENT_N" if reasons == ["INSUFFICIENT_N"] else
                           "CONFIG_REJECTED" if reasons else "CONFIG_PASSES")
        res["reasons"] = reasons; res["scope"] = "this configuration only"
        out[cfg] = res
    return {"version": VERSION, "thresholds": th, "configs": out, "stop_all_vocal_trials": stop_all}


def nearest(hyp, commands):
    h = " ".join(lenient_tokens(hyp))   # character-level distance on normalized text; ties -> alphabetical
    return min(commands, key=lambda c: (edits(" ".join(lenient_tokens(c)), h), c))


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--rows", required=True); a.add_argument("--commands")
    x = a.parse_args(argv)
    rows = [json.loads(l) for l in open(x.rows, encoding="utf-8") if l.strip()]
    cmds = [l.strip() for l in open(x.commands, encoding="utf-8") if l.strip()] if x.commands else None
    print(json.dumps(score(rows, cmds), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
