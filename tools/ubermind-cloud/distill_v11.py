#!/usr/bin/env python3
"""V11 Opus cognition distillation lab: offline, fail-closed, no model calls.

A recipe is a source-locked *hypothesis*, not a trained model or quality proof.
No subprocess, network, shell execution, filesystem writes, API calls, or billing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

HEX = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
RISK = {"low", "medium", "high", "critical"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def check_digest(value, label):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError("invalid " + label)


def check_id(value, label):
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError("invalid " + label)


def check_number(value, label, upper=None):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (upper is not None and value > upper):
        raise ValueError("invalid " + label)
    return value


def verify_path(root, relative, expected):
    check_digest(expected, "file hash")
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise ValueError("invalid relative path")
    p = Path(relative)
    if p.is_absolute() or any(v in ("..", "") for v in p.parts):
        raise ValueError("path traversal")
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be directory")
    target = root / p
    if target.is_symlink() or any(part.is_symlink() for part in list(target.parents) if part != root and root in part.parents):
        raise ValueError("symlink denied")
    resolved = target.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("path outside root") from exc
    if not resolved.is_file() or resolved.stat().st_size > 2_000_000:
        raise ValueError("missing or oversize evidence")
    actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return actual == expected


def compile_recipe(raw):
    """Source-locked teacher decision envelope. Compilation never certifies the teacher."""
    needed = {"id", "task_class", "teacher_model", "source", "input", "output", "acceptance_checks", "escalation_triggers"}
    if type(raw) is not dict or set(raw) != needed:
        raise ValueError("recipe schema mismatch")
    check_id(raw["id"], "id")
    check_id(raw["task_class"], "task class")
    if raw["teacher_model"] != "opus":
        raise ValueError("teacher must be Opus, not inferred from other model")
    for label in ("source", "input", "output"):
        val = raw[label]
        if type(val) is not dict or set(val) != {"path", "sha256"}:
            raise ValueError("invalid " + label + " reference")
        if not isinstance(val["path"], str) or not val["path"]:
            raise ValueError("missing path")
        check_digest(val["sha256"], label + " sha256")
    if type(raw["acceptance_checks"]) is not list or not raw["acceptance_checks"]:
        raise ValueError("requires acceptance checks")
    for check in raw["acceptance_checks"]:
        check_id(check, "check id")
    if len(set(raw["acceptance_checks"])) != len(raw["acceptance_checks"]):
        raise ValueError("duplicate checks")
    allowed = {"source_changed", "new_input", "new_task_class", "novelty", "high_risk", "failed_check", "missing_evidence"}
    triggers = raw["escalation_triggers"]
    if type(triggers) is not list or set(triggers) != allowed:
        raise ValueError("all safety triggers required")
    return {"state": "UNVERIFIED_TEACHER_RECIPE", "recipe_sha256": sha(raw), "recipe": raw,
            "note": "Hash locks content, not accuracy, model identity, consent, or a completed test."}


def reuse_gate(compiled, case, root):
    if type(compiled) is not dict or set(compiled) != {"state", "recipe_sha256", "recipe", "note"}:
        raise ValueError("compiled recipe envelope required")
    r = compiled["recipe"]
    if compile_recipe(r)["recipe_sha256"] != compiled["recipe_sha256"]:
        return {"state": "HOLD_TAMPERED_RECIPE", "allow_live_model_call": False}
    required = {"task_class", "risk", "novel", "source", "input", "output", "checks", "independent_acceptance"}
    if type(case) is not dict or set(case) != required:
        raise ValueError("case schema mismatch")
    if case["risk"] not in RISK or type(case["novel"]) is not bool or type(case["independent_acceptance"]) is not bool:
        raise ValueError("invalid risk/evidence flags")
    reasons = []
    if case["task_class"] != r["task_class"]:
        reasons.append("NEW_TASK_CLASS")
    if case["risk"] in {"high", "critical"}:
        reasons.append("HIGH_RISK")
    if case["novel"]:
        reasons.append("NOVEL_WORK")
    for name in ("source", "input", "output"):
        if case[name] != r[name]:
            reasons.append(name.upper() + "_CHANGED")
        elif not verify_path(root, r[name]["path"], r[name]["sha256"]):
            reasons.append(name.upper() + "_HASH_MISMATCH")
    checks = case["checks"]
    if type(checks) is not dict or set(checks) != set(r["acceptance_checks"]) or any(type(v) is not bool for v in checks.values()):
        reasons.append("MISSING_OR_INVALID_CHECKS")
    elif not all(checks.values()):
        reasons.append("FAILED_CHECK")
    if not case["independent_acceptance"]:
        reasons.append("NO_INDEPENDENT_ACCEPTANCE")
    return {"state": "EXACT_REUSE_CANDIDATE" if not reasons else "HOLD_FOR_NEW_REVIEW",
            "reasons": sorted(set(reasons)), "allow_live_model_call": False,
            "source_and_files_exact": not any("CHANGED" in x or "MISMATCH" in x for x in reasons),
            "quality_equivalence_verified": False,
            "note": "Checks/acceptance are claims in the input. This gate cannot authenticate a reviewer, test execution, or semantic correctness. A candidate is not automatic promotion."}


def benchmark(payload):
    """Paired offline task ledger; includes ALL charged calls and rework.

    Quality scores are independently *asserted*, not independently proved by JSON.
    """
    if type(payload) is not dict or set(payload) != {"units", "tasks", "quality_tolerance", "quality_floor"}:
        raise ValueError("benchmark schema")
    if payload["units"] not in {"api_equivalent_usd", "token_proxy", "meter_percentage_points"}:
        raise ValueError("incomparable units")
    floor = check_number(payload["quality_floor"], "floor", 1)
    tolerance = check_number(payload["quality_tolerance"], "tolerance", 1)
    rows = payload["tasks"]
    if type(rows) is not list or not 1 <= len(rows) <= 500:
        raise ValueError("tasks required")
    seen = set(); totals = {"opus": 0.0, "distilled": 0.0}; fail_ids=[]; incomplete=[]
    for item in rows:
        if type(item) is not dict or set(item) != {"task_id", "heldout", "same_task", "opus", "distilled"}:
            raise ValueError("task row schema")
        check_id(item["task_id"], "task id")
        if item["task_id"] in seen:
            raise ValueError("duplicate task id")
        seen.add(item["task_id"])
        if item["heldout"] is not True or item["same_task"] is not True:
            raise ValueError("not a matched unseen task")
        evaluations={}
        for label in ("opus", "distilled"):
            run = item[label]
            if type(run) is not dict or set(run) != {"calls", "accepted", "quality", "critical_failures", "evaluator", "producer"}:
                raise ValueError("run schema")
            check_number(run["quality"], "quality", 1)
            if type(run["accepted"]) is not bool or type(run["critical_failures"]) is not int or run["critical_failures"] < 0:
                raise ValueError("bad acceptance evidence")
            check_id(run["evaluator"], "evaluator")
            check_id(run["producer"], "producer")
            if type(run["calls"]) is not list or not run["calls"]:
                raise ValueError("missing usage calls")
            spent=0
            for call in run["calls"]:
                if type(call) is not dict or set(call) != {"model", "usage", "purpose"}:
                    raise ValueError("call schema")
                if call["model"] not in {"opus", "sonnet", "haiku", "native"} or call["purpose"] not in {"generation", "review", "retry", "recovery", "tool"}:
                    raise ValueError("call metadata")
                spent += check_number(call["usage"], "call usage")
            totals[label]+=spent
            evaluations[label]=run
            if run["evaluator"] == run["producer"]:
                incomplete.append(item["task_id"]+":"+label+":not_independent")
        b=evaluations["opus"];d=evaluations["distilled"]
        if (not d["accepted"] or d["quality"] < floor or d["quality"] + tolerance < b["quality"]
            or d["critical_failures"] or b["critical_failures"]):
            fail_ids.append(item["task_id"])
    base=totals["opus"];new=totals["distilled"]
    if base <= 0:
        raise ValueError("baseline costs required")
    savings=(base-new)/base
    reliable=(not fail_ids and not incomplete)
    return {"state": "REVIEW_CANDIDATE" if reliable else "HOLD_QUALITY_OR_PROVENANCE",
            "tasks":len(rows), "total_baseline":round(base,6), "total_distilled":round(new,6),
            "modeled_savings_percent":round(100*savings,3),
            "equivalent_work_multiplier":round(base/new,3) if new else None,
            "failed_quality_task_ids":fail_ids, "incomplete_evaluation":incomplete,
            "units":payload["units"], "authenticated_claude_pro_meter":False,
            "opus_equivalence_proven":False,
            "note":"All provided calls including retries counted. JSON scores and evaluator identities are unverified claims; verify blind acceptance and meter sessions externally before deployment."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("compile", "reuse", "benchmark"))
    p.add_argument("input", type=Path)
    p.add_argument("--case", type=Path)
    p.add_argument("--root", type=Path)
    a=p.parse_args()
    if not a.input.is_file() or a.input.is_symlink() or a.input.stat().st_size > 250_000:
        p.error("input must be bounded local JSON file")
    payload=json.loads(a.input.read_text(encoding="utf-8"))
    if a.action=="compile": result=compile_recipe(payload)
    elif a.action=="benchmark": result=benchmark(payload)
    else:
        if not a.case or not a.root:
            p.error("reuse requires --case and --root")
        result=reuse_gate(payload,json.loads(a.case.read_text()),a.root)
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
