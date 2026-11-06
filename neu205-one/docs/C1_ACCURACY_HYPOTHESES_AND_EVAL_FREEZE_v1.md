# NEU205 C1 — accuracy hypotheses and independent evaluation freeze (pre-registration v1, 2026-11-06)

Role: Chief Scientific Architect / Independent Medical Falsifier (C1). Written and committed **before** any
candidate below is run on any data. Base: frozen system f89d3e2 / results de150af (checkpoint v05).

Scope note: the C1 assignment comment (mohammedwessam2007/uberbondd#1609) could not be read from this session
(different repository owner; session limit). This document is derived from the founder's instruction text and the
v05 evidence. Reconcile with the C1 contract when it is reachable; where they conflict, the contract wins.

Status: SOURCE + TESTS ONLY. No model was run, no private data was present in this container, no result below is
measured. Not a clinical or educational certification of any kind.

## 0. Where the evidence stands (from v05, not re-measured)
- TEST-1 (443 supported / 107 unsupported): 60.5 % correct, **10.8 % confidently wrong**, 98.1 % correct refusals.
  Bars: ≥ 80 % / ≤ 5 % / ≥ 95 %. Two of three fail.
- DEV oracle control: with the gold passage, Qwen3-1.7B still misses → dominant residual error is model
  reasoning, not retrieval.
- **TEST-1 is now EXPOSED.** Its error list was read (by the grader, the previous session and this one). Any
  number computed on it from now on is post-exposure and may only be reported as a secondary, labelled
  counterfactual — never as release evidence.
- **The historical exam is EXPOSED** (baseline score, failure taxonomy and snippets were seen before the Qwen
  system was designed). Retired as accuracy evidence. Only a paper no agent has ever seen can reopen that lane.

Decision objective (fixed): reduce confident errors first. A change that raises correct answers but also
raises the confidently-wrong rate or the unsupported false-answer count is **rejected**, whatever its other gains.

## 1. Three falsifiable hypotheses

### H1 — Extrinsic-term grounding gate (implemented: `retrieval/grounding_gate.py`)
Mechanism: deterministic, model-free. Rebuild the exact evidence Qwen saw (`sentence_evidence` is a pure
function), take every answer-novel content term (stemmed; not in the question; not a generic/positional word)
and abstain (`NOT_IN_BOOK`) if the evidence never contains it. Zero latency on the phone (string ops).
- Claim: a material share of confident errors name a structure/drug/nucleus absent from the passages
  (v05 examples of this shape: "middle meningeal" for the ICA branch; "external laryngeal"; "spinal ganglion";
  a nerve given for platysma blood supply).
- Prediction (DEV, 45 supported + 30 unsupported, frozen Qwen3.5-4B outputs + existing independent grades):
  confidently wrong falls by ≥ 50 % (4 → ≤ 2) while correct falls by ≤ 2 items; unsupported false answers stay 0.
- **Falsified if** wrong falls < 30 % **or** correct falls > 5 points (≥ 3 of 45). Variant (`strict` vs
  `lenient`) is chosen on DEV only by: fewest wrong, then fewest correct lost.
- Known non-target (pinned by `test_known_limitation_inversion_passes`): polarity inversions built from
  evidence terms (Parkinson's → phenothiazines; hyporeflexia ← UMN). H1 must never be reported as fixing these.
- Cost of being wrong: more refusals; no new false content. Fully reversible.

### H2 — Claim-to-sentence entailment check (to build; targets inversions)
Mechanism: Qwen outputs the answer and the index of the single evidence sentence it relies on; a second short,
greedy pass with the evidence kept as the cached KV prefix asks "Does sentence [k] state that ⟨answer⟩? YES/NO".
Speak only on YES **and** H1 PASS; otherwise `NOT_IN_BOOK`.
- Claim: the residual dangerous errors are reasoning/polarity errors that a verification question exposes more
  reliably than open generation does.
- Prediction (DEV): beyond H1, removes ≥ 2 additional wrong answers including ≥ 1 polarity/inversion error, with
  ≤ 2 additional correct answers lost; host extra latency ≤ 1.5 s p50 (cached prefix, ≤ 4 decode tokens).
- **Falsified if** no additional wrong answer is removed on DEV, or correct loss > 2, or the verifier says YES to
  ≥ 50 % of the known-wrong DEV answers (a rubber-stamp verifier is worse than none: it adds false confidence).
- Same-model self-verification is correlated with the generator; report agreement rates, do not treat YES as
  independent evidence.

### H3 — Reasoning capacity (Qwen3.5-9B / Qwen3-8B, Q4_K_M) under the same pipeline (+H1, +H2 if adopted)
- Claim: the oracle control shows a capacity ceiling; a larger model of the same family reduces reasoning errors.
- Prediction (DEV): ≥ 3 more correct and ≤ the same number of wrong than Qwen3.5-4B on the same evidence.
- **Falsified if** correct gain < 3 or wrong increases. **Separately vetoed** (not falsified) if phone RAM/latency
  makes it unusable: requires measured phone TTFT ≤ 2× the 4B figure and no OOM, from Codex's phone runs.
- Model files only by SHA-256-verified download; phone `qwen.gguf` identity stays MODEL_ID_UNVERIFIED until the
  owner runs `gguf_identity.py`.

### Rejected now (would increase confident errors or break blindness)
- Letting Qwen use its own medical knowledge when passages are insufficient (the exam prompt did this). For a
  spoken study source it converts refusals into unverifiable answers. Rejected for the assistant.
- Any threshold, prompt, stop-list or variant choice informed by TEST-1 or the exam. Forbidden.
- Lowering the bars. They were fixed before TEST-1 and stay fixed.
- Larger evidence windows as a default: +4 correct for 1.7B on DEV but 3 false answers vs 1 and ×1.9 TTFT.

## 2. Independent evaluation freeze — TEST-2 (implemented: `retrieval/eval_freeze.py`)

Order of events (enforced by the tool; each step hashed into an append-only ledger):
1. **Author** fresh probes. New agent sessions receive only book pages + the authoring rubric. They never see
   engine code, prompts, outputs, the v05 error list, TEST-1/DEV items or this document's examples.
   Size: ≥ 400 supported + ≥ 100 unsupported, stratified by book thirds, with a **safety-critical stratum ≥ 25 %**
   (drug therapy and its direction, lesion signs UMN/LMN, laterality, nerve/vessel at risk, decussation level).
   A separate non-author agent removes items whose `source_quote` overlaps TEST-1/DEV (≥ 85 % token overlap).
2. **Seal**: `eval_freeze.py seal` hashes the probe files and the pre-registered candidate list
   (name, config commit SHA, model SHA-256). Maximum 4 candidates: `control` (f89d3e2), best H1 variant,
   H1+H2 (if H2 survives DEV), best H3 (if it survives DEV and the phone veto). The seal is never rewritten.
3. **Admit → run → record**, one run per candidate. `admit` refuses an unregistered or changed config, edited
   probes, or a second run. `record` hashes the raw output before anyone grades it.
4. **Grade** blind: an independent agent that authored no probes grades shuffled outputs under random labels with
   the existing rubric and book text; `check-grade` refuses outputs not recorded before grading.
5. **Report** every sealed candidate, including losers, with Wilson 95 % CIs.

Release-relevant verdict: a candidate passes only if its TEST-2 point estimates meet all three bars
(correct ≥ 80 %, confidently wrong ≤ 5 %, unsupported refusal ≥ 95 %) **and** it has zero confidently-wrong
answers in the safety-critical stratum's "dangerous inversion" class as judged by the grader. Passing is host
evidence only; phone accuracy must be re-checked on device, and none of this is a medical certification.

Expected honest outcome: H1/H2 can plausibly bring confident errors near the 5 % bar mainly by refusing more;
reaching ≥ 80 % correct at the same time is unlikely without H3 or better evidence. If correct and wrong bars
cannot both be met, the truthful output is "safe-but-incomplete refuser" vs "fails", decided by the owner.

## 3. Next actions (ordered, each needs the private bundle `NEU205_INTELLIGENCE_v05_PRIVATE.zip`)
1. H1 on DEV: `grounding_gate.py --work W --run <DEV 3.5-4B run> --graded <DEV grades> --variant strict|lenient`.
   Seconds, no model. Record verdict against §1 before anything else.
2. Same on TEST-1 as a **labelled post-exposure** counterfactual only.
3. Build H2 on DEV; then H3 download-by-hash and DEV run.
4. Commission TEST-2 authors; seal; run admitted candidates once; blind grade; report.

## 4. Private artifact preservation
- Book- and exam-derived files exist only in the owner-delivered bundle (sha256 `74afd03d…7825`, 120 files,
  verified on re-read on 2026-11-03). They are not in this repository and were not in this container.
- The 2026-11-03 container that produced it should be assumed reclaimed. The bundle copy in the owner's Claude
  app is the only known copy: owner should save it to private storage and keep the full SHA-256.
- Code, hashes and aggregate numbers only are public. Per-item outputs, grades, probes and gate rows are private.
