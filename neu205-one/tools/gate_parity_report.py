#!/usr/bin/env python3
"""Report evidence-gate decision parity between the companion backend and the native Android index.

Reads the thresholds straight from source (no hard-coded copies), then tabulates the decision each side makes at
the boundary coverages the PHOENIX checkpoint asked for. A coverage value is a property of the retrieved passages,
so parity of the decision function is necessary (not sufficient) for parity of behaviour: the two sides also
rank passages differently (companion: BM25 search; native: fused rank) and that must be tested with real data.

  gate_parity_report.py --companion backend/evidence_adapter.py --native core/.../EvidenceIndex.java
Exit 0 = identical decision functions; 1 = divergent (report lists the bands); 2 = constants not found.
"""
import argparse, json, re, sys

BOUNDARIES = (0.0, 0.19, 0.20, 0.22, 0.24, 0.25, 0.30, 0.44, 0.45, 0.47, 0.49, 0.50, 0.60, 1.0)


def companion_thresholds(src):
    m = re.search(r"status='NONE' if not passages or best<\s*([0-9.]+)\s*else 'WEAK' if best<\s*([0-9.]+)\s*else 'OK'", src)
    return (float(m.group(1)), float(m.group(2))) if m else None


def native_thresholds(src):
    ok = re.search(r"OK_COVERAGE\s*=\s*([0-9.]+)", src); weak = re.search(r"WEAK_COVERAGE\s*=\s*([0-9.]+)", src)
    rule = re.search(r'best < WEAK_COVERAGE \? "NONE" : best < OK_COVERAGE \? "WEAK" : "OK"', src)
    return (float(weak.group(1)), float(ok.group(1))) if ok and weak and rule else None


def decide(c, none_below, weak_below):
    return "NONE" if c < none_below else "WEAK" if c < weak_below else "OK"


def report(comp, nat):
    rows = [{"coverage": c, "companion": decide(c, *comp), "native": decide(c, *nat)} for c in BOUNDARIES]
    lo_n, hi_n = sorted((comp[0], nat[0])); lo_w, hi_w = sorted((comp[1], nat[1]))
    bands = []
    if lo_n != hi_n:
        bands.append({"band": [lo_n, hi_n], "companion": decide(lo_n, *comp), "native": decide(lo_n, *nat),
                      "effect": "one side refuses without generation, the other lets Qwen answer"})
    if lo_w != hi_w:
        bands.append({"band": [lo_w, hi_w], "companion": decide(lo_w, *comp), "native": decide(lo_w, *nat),
                      "effect": "one side adds the 'partly relevant' caution instruction, the other does not"})
    return {"companion_none_below_weak_below": comp, "native_none_below_weak_below": nat,
            "identical": not bands, "divergent_bands": bands, "boundary_table": rows}


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("--companion", required=True); a.add_argument("--native", required=True)
    x = a.parse_args(argv)
    comp = companion_thresholds(open(x.companion, encoding="utf-8").read())
    nat = native_thresholds(open(x.native, encoding="utf-8").read())
    if not comp or not nat:
        print("REFUSED: gate constants/rule not found; source changed shape", file=sys.stderr); return 2
    r = report(comp, nat); print(json.dumps(r, indent=1)); return 0 if r["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
