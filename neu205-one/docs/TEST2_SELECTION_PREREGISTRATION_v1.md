# NEU205 TEST-2 selection preregistration v1 (C1, 2026-11-07)

This file's exact bytes are the selection seed: `select_blind_set.py` orders eligible drafts by
SHA-256(SHA-256(this file) + ":" + draft_id). It is committed before any selection run, so the draw
cannot be re-rolled without a visible change. Do not edit; supersede with v2 and say why.

Rules version: `neu205-select-1` (code: `neu205-one/evaluation/select_blind_set.py`).

## Population
- Source: the owner-private reviewed draft pool (757-row inventory plus supplements), original PDF
  SHA-256 `c3298e8c5f7f807604be10f7376d67f05eb315dd982276263e8f6ad2e8e70940`; pages 1–60 reserved for DEV.
- Exposed sets used for overlap exclusion (all that the operator can locate; list hashes in the receipt):
  150 v05 DEV, v05 TEST 443+107, Codex 437 (336+101), Claude v12 sealed 437 (manifest `3b4eafd2…`),
  v13b 100+70 exposed subset, historical exam, every other historical question file (≥1,137 questions).

## Fixed exclusions (applied and logged per draft before any candidate inference)
schema invalid; figure/table dependent; supported page ≤ 60 or outside 61–299; supported quote not an exact
page-text substring; unsupported without anchors+rationale or with an anchor present anywhere in the source;
normalized exact match with an exposed question; lexical near match (content-token Jaccard ≥ 0.60 or char
5-gram containment ≥ 0.80); semantic triage `same|substantial|partial`; review missing, hold, or any reject;
within-pool near duplicate (keep first in seeded order); > 2 unsupported per template cluster (Jaccard ≥ 0.50);
> 3 supported items per source page.

## Allocation
- Supported: exactly 400, spread evenly over bands 61–120 / 121–180 / 181–240 / 241–299 (remainder
  redistributed to bands with capacity), ≥ 25 % of each band's quota from safety-critical items
  (laterality, direction, decussation, negation/exception, numbers/segments, lesion/deficit, drug/therapy,
  reflex tone) when available.
- Unsupported: exactly 100, round-robin across unsupported task types for diversity.
- Shortfall is reported, never filled by relaxing rules. `freeze_ready=false` blocks the freeze.

## Sequence (must hold; audit trail = hashes)
1. Candidate frozen first: native code commit, prompt, corpus `d886e875…`, GGUF SHA-256, runtime config.
2. Run selector → compile_sealed_drafts.py → sealed_source_eval.py validate/freeze (manifest exclusive-create).
3. Run the frozen candidate once on question-only rows; seal predictions before any grading.
4. Blind grading by reviewers who authored no items and do not see candidate identity; two reviews per
   item, disagreements adjudicated; AI-only review labelled as such; no clinical validation claimed.
5. Every frozen item stays in its denominator; post-freeze ambiguity goes to an `indeterminate` column.

## Pre-declared metrics and gates (unchanged from the shared contract)
Supported fully correct ≥ 90 % (stretch 95 %); reviewer-marked assertive wrong ≤ 2 % of supported;
unsupported refused ≥ 95 %; 0 observed fabricated citations. Wilson 95 % intervals. Reported on the native
(phone-path) candidate; a companion result is labelled as such and is not a phone-path score.

## Independence limitation declared in advance
The draft pool was authored and stored in the implementing agent's workspace. Selection and compilation print
only counts and hashes, but the implementer could previously read the pool. Results will therefore be labelled
`LIMITED-INDEPENDENCE (implementer-custodied pool)` unless the candidate's freeze commit predates the pool's
creation or a pool authored outside the implementer's environment is used.
