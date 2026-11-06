# NEU205 C1 decision memo v2 — three causes of incorrect/incomplete answers (2026-11-07)

Role: Chief Scientific Architect / Independent Medical Falsifier. Inputs: mission kit 2026-11-07
(zip SHA-256 `2b0b2b2d…98f38e7`, 8/8 internal hashes verified) and live PR #1611 head `d3682fe5` (read-only).
Evidence below is **aggregate reports** from the sealed runs; the private rows were not available in this
environment, so every cause is a hypothesis to confirm on private DEV before any change. Supersedes the
priority order in `C1_ACCURACY_HYPOTHESES_AND_EVAL_FREEZE_v1.md` (that memo predates the v12/v13b results).

## Where accuracy is lost (Claude v12 sealed companion run, 336 supported)
296 correct, **23 partial**, **13 abstain**, 4 wrong. The gap to 90 % (≥ 303) is 7 items, and it sits in
partial + abstain, not in wrong answers. So a gate that adds refusals (my earlier H1) lowers the score here
and is **demoted**: it stays a candidate only if the native path measures > 2 % assertive wrong.

## Cause 1 — incomplete multi-element answers (largest class)
Evidence: partial answers dropped a second required element although the gold page was retrieved; v13b
("complete only for multi-part") moved exposed items 54 → 65 correct with wrong unchanged at 4, but 19
partials remain. v13 (looser) doubled wrong to 10 — the safety cost of pushing completeness is real.
- Strategy: deterministic required-element count from the question form (explicit numerals, "and"-joined
  targets, plural targets) passed to the prompt as "the question asks for N items"; no count → unchanged.
- Cheapest falsifier: private DEV (150) paired, blinded grading: partial→correct ≥ +5 with **0** new wrong.
- Stop rule: any new assertive wrong, or TTFT +> 10 %. Safety downside: padding with invented elements.

## Cause 2 — evidence lost between retrieval and the prompt (abstentions)
Evidence: 13 abstentions = 7 retrieval misses + 6 refusals with the gold page present. WARP: right page
among candidates 150/150, but the complete supporting quote survived into the final packet only 127/150
(84.7 %). About 1 in 6 questions lose their warrant at packing time, before the model reasons.
- Strategy: quote-preserving packing — when a sentence ranks top-3, keep it whole plus its neighbour instead
  of word-budget truncation; drop lower-ranked material first.
- Cheapest falsifier (no model): complete-quote-in-packet on DEV must rise from 127/150 to ≥ 143/150 (95 %)
  with prompt tokens ≤ +10 %. Only then a model DEV run: abstain → correct ≥ +3, 0 new wrong.
- Stop rule: packet recall gain < 8 items or token growth > 10 %. Downside: longer prompts, more distractors.

## Cause 3 — the measured path is not the shipping path
Evidence: 88.1 % / 1.2 % wrong was measured on the Python companion. The phone runs `NativeBrain` +
`EvidenceIndex`. `tools/gate_parity_report.py` on live #1611 source finds two divergent bands:
coverage [0.20, 0.25) — companion refuses without generation, **phone lets Qwen answer**; [0.45, 0.50) —
phone adds the "partly relevant" caution, companion does not. Ranking is the same (phone loads BM25-only,
`bm25-v1`). Codex's earlier native run scored 275/336 with **22** wrong (older prompt, different set).
Native v13b accuracy is unmeasured. The low band is the plausible route for weak-evidence assertive errors.
- Strategy: (a) count DEV items whose best coverage falls in each band (index only, no model); (b) if ≥ 3
  DEV items fall in [0.20, 0.25), run native DEV with companion thresholds vs current, paired, blinded.
- Advance threshold: assertive wrong falls with ≤ 1 correct lost per 150; otherwise keep phone thresholds and
  record the negative result. Change belongs to Codex; this memo is the measured proposal, not an edit.
- Release consequence now: TEST-2 must score the **native** candidate; a companion score cannot stand in.

## Fresh blind set (deliverable 2)
`evaluation/select_blind_set.py` (rules `neu205-select-1`, 6 synthetic tests) + committed
`TEST2_SELECTION_PREREGISTRATION_v1.md` (its hash is the selection seed). Synthetic end-to-end check:
selector → PR #1611 `compile_sealed_drafts.py` compiled 400 + 100 with 0 dropped. Not yet run on the real pool.
Declared limitation: the pool lives in the implementer's workspace → `LIMITED-INDEPENDENCE` label unless a
pool authored outside it is used.

## Private custody (this environment)
NOT RECOVERED here (never present in this container): book PDF `c3298e8c…`, corpus `d886e875…`, 757 pool and
reviews, exposed sets, keys, predictions, GGUF, APK `5818ba78…`, v05 bundle `74afd03d…7825`. Known holders:
Codex private workspace (`/workspace/neu205-private/…`), owner's ChatGPT Library `/NEU205_Backups/`, owner's
Claude app (v05 bundle). Nothing private was written to Git.

## Exact next command (in the environment holding the private pool, after the candidate freeze)
```
python neu205-one/evaluation/select_blind_set.py --drafts $POOL/*.jsonl --reviews $REVIEWS \
  --exposed $EXPOSED/* --semantic-triage $TRIAGE --pages $BOOK_PAGES \
  --preregistration neu205-one/docs/TEST2_SELECTION_PREREGISTRATION_v1.md \
  --selected $PRIV/test2_selected.jsonl --ledger $PRIV/test2_exclusions.jsonl --receipt $PRIV/test2_receipt.json
```
then `compile_sealed_drafts.py` → `sealed_source_eval.py validate/freeze` → frozen native run → seal → blind grade.

## Receipt
AGENT / ROLE: Claude / C1 Chief Scientific Architect, Independent Medical Falsifier
BASE_HEAD / NEW_HEAD: `afb48fd` → this commit, branch `claude/vibrant-cori-ptieu2` (uberbond2007/uberbondd). PR #1611 (`d3682fe5`) read only; not modified.
ACTIONS ACTUALLY RUN: kit hash check 8/8; selector + 6 synthetic tests; selector→`compile_sealed_drafts.py` end-to-end (500 compiled, 0 dropped); gate parity report on live #1611 source; PR #1611 `test_sealed_source_eval` still OK.
TESTS: evaluation 6/6, tools 2/2, retrieval 14/14 — synthetic integrity only, not accuracy evidence.
CORRECTNESS/REFUSAL/WRONG: no new measurement; no model run; no private data present.
PREREGISTRATION SHA-256: `ede95818c670d963b8765717114dafddb5b1951a7bd552543cd1b771c17622ed`.
PRIVATE ARTIFACT CUSTODY: NOT RECOVERED in this environment (holders listed above).
BLOCKER: real selection, native run and blind grading need the private pool/book/model in one environment.
STATUS: EXPERIMENTAL (tooling verified on synthetic data; real TEST-2 not frozen).
