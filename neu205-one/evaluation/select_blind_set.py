#!/usr/bin/env python3
"""Pre-registered, deterministic selection of a fresh blind NEU205 set from the private draft pool.

Fills the gap between the reviewed draft pool (e.g. the 757-row inventory) and the existing chain
    compile_sealed_drafts.py  ->  sealed_source_eval.py validate/freeze  ->  seal-predictions  ->  grade
Nothing here reads predictions, solver code or model output. Every exclusion is decided by a fixed rule,
recorded per draft BEFORE any candidate inference, and the random order is derived from the SHA-256 of the
preregistration file, so selection cannot be re-rolled after the fact without changing a hashed input.

Private inputs (never commit): drafts JSONL (compile_sealed_drafts schema + optional draft_id/figure_dependent),
reviews JSONL, exposed question files, optional semantic-triage JSONL, page-text JSONL.
Outputs: selected drafts (private), per-draft exclusion ledger (private), aggregate receipt (counts and hashes
only; safe to publish). Outputs are created exclusively and never overwritten.

  select_blind_set.py --drafts D1.jsonl [D2 ...] --reviews R.jsonl --exposed E1.json[l] [E2 ...]
      --pages pages.jsonl --preregistration PREREG.md [--semantic-triage T.jsonl]
      [--target-supported 400] [--target-unsupported 100] [--development-cutoff 60]
      --selected OUT.jsonl --ledger LEDGER.jsonl --receipt RECEIPT.json
"""
import argparse, hashlib, json, re, sys
from functools import lru_cache
from collections import Counter, defaultdict
from pathlib import Path

RULES_VERSION = "neu205-select-1"
NEAR_JACCARD = 0.60          # content-token Jaccard against an exposed or sibling question
NEAR_CONTAINMENT = 0.80      # char 5-gram containment (shorter in longer)
TEMPLATE_JACCARD = 0.50      # unsupported "same template" clustering
TEMPLATE_CAP = 2             # max unsupported items kept per template cluster
PAGE_CAP = 3                 # max supported items per source page (clustering limit)
SAFETY_SHARE = 0.25          # minimum share of safety-critical supported items when available
BANDS = ((61, 120), (121, 180), (181, 240), (241, 299))
EXCLUDING_TRIAGE = {"same", "substantial", "partial"}

STOP = set("""a an the is are was were be been being and or of in on for from to by with at into about as that this
these those it its what which who whom whose how why where when does do did can could should would may might there
here tell me please describe explain define give list name main you your i my we our s also then than so such any
all following""".split())
SAFETY = re.compile(
    r"\b(ipsi|contra)lateral|\b(left|right|bilateral|unilateral)\b|\b(afferent|efferent|ascending|descending)\b|"
    r"decussat|\b(not|except|never|without|absent|unless)\b|\d|\b[CTLS][1-8]\b|segment|"
    r"lesion|injur|damage|palsy|paraly|deficit|syndrome|drug|treat|therap|contraindicat|dose|"
    r"hyper|hypo|reflex", re.I)


class SelectionError(Exception):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.casefold()).strip()


@lru_cache(maxsize=None)
def content_tokens(t):
    return frozenset({w for w in norm(t).split() if w not in STOP and len(w) > 1})


@lru_cache(maxsize=None)
def grams(t, n=5):
    s = norm(t).replace(" ", "")
    return frozenset(s[i:i + n] for i in range(max(1, len(s) - n + 1)))


def similar(a, b, jac=NEAR_JACCARD):
    ta, tb = content_tokens(a), content_tokens(b)
    if ta and tb and len(ta & tb) / len(ta | tb) >= jac:
        return True
    ga, gb = grams(a), grams(b)
    small, big = (ga, gb) if len(ga) <= len(gb) else (gb, ga)
    return bool(small) and len(small & big) / len(small) >= NEAR_CONTAINMENT


def read_rows(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return [json.loads(l) for l in text.splitlines() if l.strip()]


def exposed_questions(paths):
    out = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("question", "prompt", "utterance_text") and isinstance(v, str):
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    for p in paths:
        walk(read_rows(p))
    return out


def draft_id(r):
    return r.get("draft_id") or "D" + sha(norm(r.get("question", "")).encode())[:12]


def order_key(seed, did):
    return sha((seed + ":" + did).encode())


def safety_critical(r):
    return bool(SAFETY.search(r.get("question", "") + " " + (r.get("quote") or "")))


def band(page):
    for i, (lo, hi) in enumerate(BANDS):
        if lo <= page <= hi:
            return i
    return None


def review_status(reviews):
    """Eligible only with >=1 accept and no reject; any hold blocks. Missing review is not eligible."""
    if not reviews:
        return "EXCL_REVIEW_MISSING"
    d = {r.get("decision") for r in reviews}
    if "reject" in d:
        return "EXCL_REVIEW_REJECT"
    if "hold" in d or "accept" not in d:
        return "EXCL_REVIEW_HOLD"
    return None


def select(drafts, reviews, exposed, pages, prereg_bytes, triage=(), target_s=400, target_u=100, dev_cutoff=60):
    if target_s < 400 or target_u < 100:
        raise SelectionError("targets below the 400/100 floor")
    seed = sha(prereg_bytes)
    rev = defaultdict(list)
    for r in reviews:
        rev[r.get("draft_id")].append(r)
    tri = defaultdict(set)
    for t in triage:
        tri[t.get("draft_id")].add(t.get("exposed_match"))
    exp_norm = {norm(q) for q in exposed}
    reasons, eligible, seen_ids = {}, [], set()
    for r in drafts:
        did = draft_id(r)
        if did in seen_ids:
            raise SelectionError(f"duplicate draft id {did}")
        seen_ids.add(did)
        why = []
        if not isinstance(r.get("question"), str) or not r["question"].strip() or "supported" not in r or "task_type" not in r:
            reasons[did] = ["EXCL_SCHEMA"]; continue
        sup = bool(r["supported"])
        if r.get("figure_dependent"):
            why.append("EXCL_FIGURE")
        if sup:
            pg = r.get("page")
            if not isinstance(pg, int) or pg <= dev_cutoff or band(pg) is None:
                why.append("EXCL_DEV_OR_PAGE")
            elif not r.get("quote") or r["quote"] not in pages.get(pg, ""):
                why.append("EXCL_QUOTE")
        else:
            anchors = r.get("anchors") or []
            if not anchors or not r.get("rationale"):
                why.append("EXCL_ABSENCE_AUDIT")
            elif any(a.casefold() in t.casefold() for a in anchors for t in pages.values()):
                why.append("EXCL_ABSENCE_HIT")
        if norm(r["question"]) in exp_norm:
            why.append("EXCL_EXPOSED_EXACT")
        elif any(similar(r["question"], q) for q in exposed):
            why.append("EXCL_EXPOSED_NEAR")
        if tri[did] & EXCLUDING_TRIAGE:
            why.append("EXCL_EXPOSED_SEMANTIC")
        rs = review_status(rev.get(did))
        if rs:
            why.append(rs)
        if why:
            reasons[did] = why
        else:
            eligible.append((did, r))
    # within-pool near duplicates: keep the first in seeded order
    eligible.sort(key=lambda x: order_key(seed, x[0]))
    kept = []
    for did, r in eligible:
        if any(similar(r["question"], k["question"]) for _, k in kept):
            reasons[did] = ["EXCL_WITHIN_DUP"]
        else:
            kept.append((did, r))
    # unsupported template cap
    clusters, kept2 = [], []
    for did, r in kept:
        if r["supported"]:
            kept2.append((did, r)); continue
        c = next((c for c in clusters if similar(r["question"], c[0], TEMPLATE_JACCARD)), None)
        if c is None:
            clusters.append([r["question"], 1]); kept2.append((did, r))
        elif c[1] < TEMPLATE_CAP:
            c[1] += 1; kept2.append((did, r))
        else:
            reasons[did] = ["EXCL_TEMPLATE_CAP"]
    sup = [(d, r) for d, r in kept2 if r["supported"]]
    uns = [(d, r) for d, r in kept2 if not r["supported"]]
    chosen_s = _stratified_supported(sup, target_s, reasons)
    chosen_u = _diverse_unsupported(uns, target_u, reasons)
    selected = chosen_s + chosen_u
    sel_ids = {d for d, _ in selected}
    for d, _ in kept2:
        if d not in sel_ids and d not in reasons:
            reasons[d] = ["NOT_SELECTED_QUOTA"]
    return seed, selected, reasons


def _stratified_supported(items, target, reasons):
    per_page = Counter()
    by_band = defaultdict(lambda: ([], []))   # band -> (safety, other), already in seeded order
    for d, r in items:
        by_band[band(r["page"])][0 if safety_critical(r) else 1].append((d, r))
    quotas = _even_quotas(target, {b: len(s) + len(o) for b, (s, o) in by_band.items()})
    out = []
    for b, q in sorted(quotas.items()):
        s, o = by_band[b]
        want_safety = min(len(s), max(int(round(q * SAFETY_SHARE)), 0))
        picked = []
        for pool, limit in ((s, want_safety), (s + o, q)):
            for d, r in pool:
                if len(picked) >= limit:
                    break
                if (d, r) in picked or per_page[r["page"]] >= PAGE_CAP:
                    continue
                picked.append((d, r)); per_page[r["page"]] += 1
        for d, r in s + o:
            if (d, r) not in picked and per_page[r["page"]] >= PAGE_CAP:
                reasons.setdefault(d, ["EXCL_PAGE_CAP"])
        out += picked
    return out


def _even_quotas(target, avail):
    quotas, left, open_ = {b: 0 for b in avail}, target, {b for b, n in avail.items() if n}
    while left and open_:
        share = max(1, left // len(open_))
        for b in sorted(open_):
            add = min(share, avail[b] - quotas[b], left)
            quotas[b] += add; left -= add
        open_ = {b for b in open_ if quotas[b] < avail[b]}
    return quotas


def _diverse_unsupported(items, target, reasons):
    by_type = defaultdict(list)
    for d, r in items:
        by_type[r.get("task_type", "unknown")].append((d, r))
    out, i = [], 0
    while len(out) < target and any(i < len(v) for v in by_type.values()):
        for t in sorted(by_type):
            if i < len(by_type[t]) and len(out) < target:
                out.append(by_type[t][i])
        i += 1
    return out


def receipt(seed, selected, reasons, inputs, targets):
    sup = [r for _, r in selected if r["supported"]]
    uns = [r for _, r in selected if not r["supported"]]
    rc = Counter(x for v in reasons.values() for x in v)
    return {"rules_version": RULES_VERSION, "order_seed_sha256_of_preregistration": seed,
            "input_sha256": inputs, "targets": targets,
            "selected_supported": len(sup), "selected_unsupported": len(uns),
            "supported_shortfall": max(0, targets["supported"] - len(sup)),
            "unsupported_shortfall": max(0, targets["unsupported"] - len(uns)),
            "supported_by_band": {f"{lo}-{hi}": sum(1 for r in sup if band(r["page"]) == i) for i, (lo, hi) in enumerate(BANDS)},
            "supported_safety_critical": sum(1 for r in sup if safety_critical(r)),
            "distinct_supported_pages": len({r["page"] for r in sup}),
            "unsupported_task_types": len({r.get("task_type") for r in uns}),
            "exclusion_reason_counts": dict(sorted(rc.items())),
            "limits": ["lexical near-duplicate rules only; unmatched paraphrases may remain",
                       "review decisions are provisional AI reviews unless stated otherwise; no clinical validation",
                       "operator attests no candidate prediction exists for any selected item"],
            "freeze_ready": len(sup) >= targets["supported"] and len(uns) >= targets["unsupported"]}


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__)
    for k in ("drafts", "exposed"):
        a.add_argument("--" + k, nargs="+", required=True)
    for k in ("reviews", "pages", "preregistration", "selected", "ledger", "receipt"):
        a.add_argument("--" + k, required=True)
    a.add_argument("--semantic-triage")
    a.add_argument("--target-supported", type=int, default=400)
    a.add_argument("--target-unsupported", type=int, default=100)
    a.add_argument("--development-cutoff", type=int, default=60)
    x = a.parse_args(argv)
    for out in (x.selected, x.ledger, x.receipt):
        if Path(out).exists():
            print(f"REFUSED: {out} exists; selections are never overwritten", file=sys.stderr); return 2
    files = list(x.drafts) + list(x.exposed) + [x.reviews, x.pages, x.preregistration] + ([x.semantic_triage] if x.semantic_triage else [])
    inputs = {Path(f).name + ("" if i == 0 else f"#{i}"): sha(Path(f).read_bytes()) for i, f in enumerate(files)}
    pages = {r["pdf_page_1based"]: r["text"] for r in read_rows(x.pages)}
    drafts = [r for f in x.drafts for r in read_rows(f)]
    try:
        seed, selected, reasons = select(drafts, read_rows(x.reviews), exposed_questions(x.exposed), pages,
                                         Path(x.preregistration).read_bytes(),
                                         read_rows(x.semantic_triage) if x.semantic_triage else (),
                                         x.target_supported, x.target_unsupported, x.development_cutoff)
    except SelectionError as e:
        print("REFUSED:", e, file=sys.stderr); return 2
    with open(x.ledger, "x", encoding="utf-8") as f:
        for d in sorted(reasons):
            f.write(json.dumps({"draft_id": d, "reasons": reasons[d]}) + "\n")
    with open(x.selected, "x", encoding="utf-8") as f:
        for d, r in selected:
            f.write(json.dumps(dict(r, draft_id=d)) + "\n")
    rec = receipt(seed, selected, reasons, inputs, {"supported": x.target_supported, "unsupported": x.target_unsupported})
    rec["selected_sha256"] = sha(Path(x.selected).read_bytes()); rec["ledger_sha256"] = sha(Path(x.ledger).read_bytes())
    with open(x.receipt, "x", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps(rec, indent=1, sort_keys=True))
    return 0 if rec["freeze_ready"] else 3


if __name__ == "__main__":
    sys.exit(main())
