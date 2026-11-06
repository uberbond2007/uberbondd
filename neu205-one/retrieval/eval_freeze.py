#!/usr/bin/env python3
"""Independent-evaluation freeze for NEU205 (C1). Makes a fresh blinded TEST-2 mechanically checkable.

Three ordered events, each recorded with hashes so a later reader can verify the order was respected:
  1. seal      — hash the fresh probe files (authored by agents that never saw engine code, TEST-1 items, the
                 error list or any candidate output) and the PRE-REGISTERED candidate list (config commit SHA +
                 model file sha256 per candidate). Nothing is run yet.
  2. admit     — before a candidate touches TEST-2: refuse unless (a) the probe files still hash to the seal,
                 (b) the candidate is in the sealed list with the same config SHA and model hash, and (c) it has
                 not already been run (one run per candidate; no retries after seeing output).
  3. record    — after the run, hash the raw output file and append it to the ledger BEFORE grading. A grade
                 file is only accepted if its run hash is in the ledger.

The ledger is append-only JSON lines next to the seal. The probe files and outputs are private (book-derived);
only hashes and counts belong in the public repository.

  eval_freeze.py seal   --probes P1.json [P2 ...] --candidates CANDS.json --seal SEAL.json
  eval_freeze.py admit  --seal SEAL.json --probes ... --candidate NAME --config-sha SHA --model-sha256 HEX
  eval_freeze.py record --seal SEAL.json --candidate NAME --output RUN.json
  eval_freeze.py check-grade --seal SEAL.json --output RUN.json
CANDS.json: [{"name": "...", "config_sha": "<git sha>", "model_sha256": "<hex>", "hypothesis": "H1|H2|H3|control"}]
"""
import argparse, hashlib, json, os, sys, time


class FreezeError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _probe_digest(paths):
    files = sorted([os.path.basename(p), sha256_file(p)] for p in paths)
    items = 0
    for p in paths:
        data = json.load(open(p, encoding="utf-8"))
        items += len(data) if isinstance(data, list) else 0
    return files, items


def _ledger_path(seal_path):
    return seal_path + ".ledger.jsonl"


def _ledger(seal_path):
    p = _ledger_path(seal_path)
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []


def _append(seal_path, rec):
    rec = dict(rec, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(_ledger_path(seal_path), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def seal(probes, candidates, seal_path):
    if os.path.exists(seal_path):
        raise FreezeError("seal already exists; a seal is never rewritten (make TEST-3 instead)")
    names = [c["name"] for c in candidates]
    if len(set(names)) != len(names) or not candidates:
        raise FreezeError("candidate names must be unique and non-empty")
    for c in candidates:
        if not (c.get("config_sha") and c.get("model_sha256")):
            raise FreezeError(f"candidate {c.get('name')} lacks config_sha/model_sha256")
    files, items = _probe_digest(probes)
    doc = {"schema": "neu205-eval-freeze-1", "probe_files": files, "items": items,
           "candidates": sorted(candidates, key=lambda c: c["name"]),
           "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    doc["seal_sha256"] = hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()
    json.dump(doc, open(seal_path, "w"), indent=1, sort_keys=True)
    return doc


def _load_seal(seal_path):
    doc = json.load(open(seal_path))
    body = {k: v for k, v in doc.items() if k != "seal_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != doc.get("seal_sha256"):
        raise FreezeError("seal file was edited after sealing")
    return doc


def admit(seal_path, probes, name, config_sha, model_sha256):
    doc = _load_seal(seal_path)
    files, _ = _probe_digest(probes)
    if files != doc["probe_files"]:
        raise FreezeError("probe files differ from the seal (edited, added or removed)")
    cand = next((c for c in doc["candidates"] if c["name"] == name), None)
    if cand is None:
        raise FreezeError(f"candidate {name} was not pre-registered")
    if cand["config_sha"] != config_sha or cand["model_sha256"] != model_sha256:
        raise FreezeError(f"candidate {name} config/model differs from pre-registration")
    if any(r["event"] in ("admit", "record") and r["candidate"] == name for r in _ledger(seal_path)):
        raise FreezeError(f"candidate {name} already admitted; one run per candidate")
    return _append(seal_path, {"event": "admit", "candidate": name, "config_sha": config_sha})


def record(seal_path, name, output):
    _load_seal(seal_path)
    led = _ledger(seal_path)
    if not any(r["event"] == "admit" and r["candidate"] == name for r in led):
        raise FreezeError(f"candidate {name} was never admitted")
    if any(r["event"] == "record" and r["candidate"] == name for r in led):
        raise FreezeError(f"output for {name} already recorded")
    return _append(seal_path, {"event": "record", "candidate": name, "output_sha256": sha256_file(output)})


def check_grade(seal_path, output):
    h = sha256_file(output)
    for r in _ledger(seal_path):
        if r["event"] == "record" and r["output_sha256"] == h:
            return r
    raise FreezeError("output not recorded before grading (or changed since)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal"); s.add_argument("--probes", nargs="+", required=True); s.add_argument("--candidates", required=True); s.add_argument("--seal", required=True)
    a = sub.add_parser("admit"); a.add_argument("--seal", required=True); a.add_argument("--probes", nargs="+", required=True)
    a.add_argument("--candidate", required=True); a.add_argument("--config-sha", required=True); a.add_argument("--model-sha256", required=True)
    r = sub.add_parser("record"); r.add_argument("--seal", required=True); r.add_argument("--candidate", required=True); r.add_argument("--output", required=True)
    g = sub.add_parser("check-grade"); g.add_argument("--seal", required=True); g.add_argument("--output", required=True)
    x = ap.parse_args(argv)
    try:
        if x.cmd == "seal":
            res = seal(x.probes, json.load(open(x.candidates)), x.seal)
            res = {"seal_sha256": res["seal_sha256"], "items": res["items"], "candidates": [c["name"] for c in res["candidates"]]}
        elif x.cmd == "admit":
            res = admit(x.seal, x.probes, x.candidate, x.config_sha, x.model_sha256)
        elif x.cmd == "record":
            res = record(x.seal, x.candidate, x.output)
        else:
            res = check_grade(x.seal, x.output)
    except FreezeError as e:
        print("REFUSED:", e, file=sys.stderr)
        return 2
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
