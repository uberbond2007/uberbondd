# UberMind V11: Opus Intelligence Distillation Lab

**State:** bounded, offline, public-safe research apparatus. Builds on V10 automatic router `498b98c6e49eb52de96c59c97bbbe41e15f2b4d4`, not a replacement. No claim of achieving Opus-parity, retraining model weights, Claude Pro usage savings, or autonomous cloud deployment.

## Design

1. **Teach:** Opus solves a representative new task in an authenticated *Claude Code Pro* session. Independently review its decision and focused tests. Compile source/input/output fingerprints and named checks into a reusable recipe. No private corpus, legal books or credentials in public Git.
2. **Reuse:** for an identical, low-risk task, verify three SHA-256 fingerprints. Check evidence and stop on any source/input/output change, novelty, high risk, missing tests, or missing acceptance. `EXACT_REUSE_CANDIDATE` means potentially reusable, never proof of independent review.
3. **Delegate:** Haiku for bounded extraction/routine source lookup, Sonnet for implementation, main Opus for novel or critical uncertainty. Avoid parallel overhead unless justified. Existing six V10 agent definitions remain unchanged.
4. **Falsify:** independent blind held-out comparisons. Count **every** inference call, including failed cheap passes, Opus recovery, retries and final review. Trigger fallback if candidate quality is below baseline or critical failures occur. Do not cherry-pick task families.
5. **Measure:** local API-price proxies, transcript token data and UI weekly/session consumption are different metrics. The lab never infers an authenticated subscription savings multiplier from prices or self-authored JSON scores. Meter reset and rounded percentages destroy precise attribution.

## Use (offline, no inference)

```bash
python3 -m unittest discover -s tools/ubermind-cloud -p 'test_distill_v11.py' -v
python3 tools/ubermind-cloud/distill_v11.py compile /tmp/synthetic-recipe.json
python3 tools/ubermind-cloud/distill_v11.py reuse /tmp/compiled.json --case /tmp/case.json --root /safe/repo
python3 tools/ubermind-cloud/distill_v11.py benchmark /tmp/matched-evaluations.json
```

The CLI emits JSON to stdout. `compile` output must be saved by an approved operator (there is **no automatic persistence**). It never executes a test command or authenticates a reviewer. `reuse` requires path/bytes hashes to match inside the designated root; the checks and independent_acceptance fields remain **untrusted attestations**. `benchmark` outputs **REVIEW_CANDIDATE** at best, meaning human/Opus adjudication is still necessary. No JSON field can assert `opus_equivalence_proven` or `authenticated_claude_pro_meter` true.

### Recipe format (synthetic paths)

```json
{
  "id": "lead_report_v1",
  "task_class": "synthetic_lead_reporting",
  "teacher_model": "opus",
  "source": {"path": "fixtures/source.txt", "sha256": "<actual 64-character lowercase hex>"},
  "input": {"path": "fixtures/input.json", "sha256": "<actual 64-character lowercase hex>"},
  "output": {"path": "fixtures/result.json", "sha256": "<actual 64-character lowercase hex>"},
  "acceptance_checks": ["source_exact", "result_matches", "negative_case"],
  "escalation_triggers": ["source_changed", "new_input", "new_task_class", "novelty", "high_risk", "failed_check", "missing_evidence"]
}
```

The teacher-model label must come from actual session evidence outside this recipe; entering `"opus"` does not certify it. No free-text instructions from third-party materials should be executed as code.

### Benchmark format

Each `task` has unique `task_id`, `heldout:true`, `same_task:true` and `opus`/`distilled` records. Each run contains **all** `calls` with `model`, `usage`, and `purpose`, plus `accepted`, `quality` (0–1), `critical_failures`, `evaluator` and `producer`. Top-level required keys: `units`, `tasks`, `quality_tolerance`, `quality_floor`. The units must be uniform (`token_proxy`, `api_equivalent_usd`, or `meter_percentage_points`); do not mix them. Independent evaluator identity and scores require external proof.

**Promotion evidence threshold:** no critical failures, task-paired heldouts not seen by the distillation process, independently verified acceptance and a quality lower bound meeting the all-Opus result. Use a real before/after provider meter with windows and reset information. Until then all savings are a scenario, not a verified subscription multiplier. Tail risk and user safety override economical routing.

## Known limits

- Exact cache is narrow. A new prompt/input or a different source version must return to normal V10 routing or Opus.
- SHA-256 integrity doesn't prove a source is correct or honest, or that a test script was genuinely run.
- No model calls, fine-tuning, embeddings, or always-on service in this package. The six agents are requested by Claude Code when it decides to delegate; source rule is guidance, not forced deterministic switching.
- No automatic uploads, purchases, cloud pushes, production deployments, customer contact or private data extraction.
- Claude Pro usage limits are plan-level provider behavior; API price ratios cannot be equated to actual allowance bars without matched evidence.

## Explicit validation gates before production

Run the 23 offline tests; inspect the actual branch diff; perform one authenticated low-risk Claude Cloud **read-only** smoke task; then run 20 blinded matched tasks once approved. Compare accepted outcomes, critical regressions, median/total consumption, retries and retries' Opus recovery costs. Stop and rollback if quality loses. No live Claude benchmark or cost savings is claimed by creating this file.

**Continuity:** The 890 founder ideas, 52 original doctrine atlas, Ω46 EQ and lawful books remain outside this PUBLIC repo; source retrieval stays in the authorized private workspace. Preserve V10 and PHOENIX checkpoints and exact hashes. Relevant lenses: Ω47·15 efficient operations, Ω50·27 actual outcomes, Ω51·33 adversarial falsification, Ω52·46 formal verification limits.
