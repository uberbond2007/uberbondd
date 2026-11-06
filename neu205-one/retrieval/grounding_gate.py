#!/usr/bin/env python3
"""H1 grounding gate: abstain when the answer asserts content terms the evidence never contains.

Deterministic, model-free, offline. It reconstructs the exact evidence Qwen saw (qwen_eval.sentence_evidence is a
pure function of question + retrieved chunks + word budget) and checks every *answer-novel* content term
(stemmed, stop words removed, not already in the question, not a generic answer word) against the evidence terms.

What it can catch: extrinsic content — a structure, drug or nucleus named in the answer that the passages never
mention (e.g. "middle meningeal" when the evidence only says "middle cerebral").
What it CANNOT catch (documented limitation, asserted in tests): inversions built from terms the evidence does
contain (e.g. "Parkinson's is treated with phenothiazines" when the passage says phenothiazines CAUSE
parkinsonism). H2 targets that class.

Usage (re-scores a frozen, independently graded run; no model, no network):
  grounding_gate.py --work WORKDIR --run RUN.json --graded GRADED.json [--budget-words 110]
                    [--variant strict|lenient] --out GATED.json
GRADED.json: {"<item id>": "correct"|"partial"|"wrong"|"refused"|"correct_refusal"|"false_answer"} from the
independent grader. Gating converts an answered item into "refused" (supported) / "correct_refusal" (unsupported);
it never upgrades an item, so the re-score is an exact counterfactual of the frozen outputs.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bm25 import tokens

# Words an answer can contain without asserting book content. Stemmed through bm25.tokens at import.
_GENERIC = """answer book passage passages text according states stated says said called known termed named
structure structures part parts region area found located seen occurs occur result results cause causes caused due
because therefore thus usually typically mainly mostly mainly also both each either neither other another one two
three first second third side sides left right upper lower main major minor small large type types form forms role
helps help involved involves involve important include includes including such well example level levels
lie lies lying run runs running pass passes passing close near next beside along via through""".split()
GENERIC = set(t for w in _GENERIC for t in tokens(w))
# Same refusal pattern as qwen_eval.REFUSAL (kept in sync by test_refusal_pattern_matches_harness).
REFUSAL = re.compile(r"not_in_book|not in (the|your) (book|passages)|passages do not|does not (say|mention|contain)", re.I)


def novel_terms(question, answer):
    q = set(tokens(question))
    seen, out = set(), []
    for t in tokens(answer):
        if t in q or t in GENERIC or t in seen or len(t) < 3 or t.isdigit():
            continue
        seen.add(t); out.append(t)
    return out


def gate(question, answer, evidence_texts, variant="strict"):
    """Return {"decision": "PASS"|"ABSTAIN"|"ALREADY_REFUSED", "novel": [...], "unsupported": [...]}."""
    if not answer.strip() or REFUSAL.search(answer):
        return {"decision": "ALREADY_REFUSED", "novel": [], "unsupported": []}
    ev = set()
    for e in evidence_texts:
        ev.update(tokens(e))
    nov = novel_terms(question, answer)
    uns = [t for t in nov if t not in ev]
    if variant == "strict":
        ok = not uns
    elif variant == "lenient":  # pre-registered alternative: tolerate one stray term in a substantive answer
        ok = len(uns) == 0 or (len(uns) == 1 and len(nov) >= 4)
    else:
        raise ValueError(variant)
    return {"decision": "PASS" if ok else "ABSTAIN", "novel": nov, "unsupported": uns}


def gated_verdict(kind, graded, decision):
    if decision != "ABSTAIN":
        return graded
    return "refused" if kind == "supported" else "correct_refusal"


def summarise(rows):
    from collections import Counter
    sup = [r for r in rows if r["kind"] == "supported"]
    uns = [r for r in rows if r["kind"] != "supported"]
    cs, cu = Counter(r["gated"] for r in sup), Counter(r["gated"] for r in uns)
    n = max(1, len(sup)); m = max(1, len(uns))
    return {"supported_n": len(sup), "supported": dict(cs), "correct_rate": round(cs["correct"] / n, 4),
            "wrong_rate": round(cs["wrong"] / n, 4), "unsupported_n": len(uns), "unsupported": dict(cu),
            "refusal_rate": round(cu["correct_refusal"] / m, 4) if uns else None,
            "gate_flips": {"wrong->refused": sum(1 for r in sup if r["graded"] == "wrong" and r["gated"] == "refused"),
                           "correct->refused": sum(1 for r in sup if r["graded"] == "correct" and r["gated"] == "refused"),
                           "partial->refused": sum(1 for r in sup if r["graded"] == "partial" and r["gated"] == "refused"),
                           "false_answer->refusal": sum(1 for r in uns if r["graded"] == "false_answer" and r["gated"] == "correct_refusal")}}


def main():
    from qwen_eval import sentence_evidence
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True); ap.add_argument("--run", required=True); ap.add_argument("--graded", required=True)
    ap.add_argument("--budget-words", type=int, default=110); ap.add_argument("--evidence-mode", choices=["sentences", "chunks"], default="sentences")
    ap.add_argument("--variant", choices=["strict", "lenient"], default="strict"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    chunks = {c["chunk_id"]: c for c in (json.loads(l) for l in open(os.path.join(a.work, "corpus.jsonl"), encoding="utf-8"))}
    run = json.load(open(a.run)); graded = json.load(open(a.graded))
    rows = []
    for r in run["rows"]:
        if r["id"] not in graded:
            raise SystemExit(f"ungraded item {r['id']}: refuse to re-score a partial grading")
        cands = [chunks[c] for c in r["evidence_chunks"]]
        ev = sentence_evidence(r["question"], cands, a.budget_words) if a.evidence_mode == "sentences" else cands
        g = gate(r["question"], r["answer"], [e["verbatim_text"] for e in ev], a.variant)
        rows.append({"id": r["id"], "kind": r["kind"], "graded": graded[r["id"]], "decision": g["decision"],
                     "unsupported_terms": g["unsupported"], "gated": gated_verdict(r["kind"], graded[r["id"]], g["decision"])})
    out = {"variant": a.variant, "summary": summarise(rows), "rows": rows,
           "scope": "OFFLINE counterfactual on frozen outputs; private (contains item ids/terms) — do not publish"}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
