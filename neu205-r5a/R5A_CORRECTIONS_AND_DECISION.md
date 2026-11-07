# NEU205 r5a — engineering corrections and next-experiment decision (2026-11-07)

Responds to the GPT-6 review of `NEU205_r5_NASOVOCE_EG_20261107.zip` (SHA-256 `d65425c5…947e0e`), reissued as
`NEU205_r5_review_REISSUED_20261107.zip` (SHA-256 `3a230ae8…0291cb`).
Status: **SOFTWARE + PROCEDURES ONLY.** Nothing compiled for ESP32, flashed, worn, bought or recorded.
No ASR, privacy or speech-performance claim is made.

## 0. Preservation and scope
- The r5 ZIP itself was **not in this environment** (only the review was uploaded) and no session holding it was
  reachable. r5 is therefore untouched by construction. r5a is a separate, additive package; nothing in it
  overwrites an r5 file.
- Because r5's exact frame bytes were not visible, the fixes are built so they do not depend on them:
  the sequence policy (`classify_seq`), the bounded writer (`ChunkedWavWriter`) and the channel map are
  framing-independent. `StreamParser`/`FrameLayout` is a reference framing (magic `NL`, seq u32, nsamp u16,
  int16 interleaved, CRC-32). **Adapter:** in r5's `nasolink_reader.parse`, replace the `frames_missing`
  arithmetic with `classify_seq(prev, seq, Limits())`, and replace `write_wav(..., fill_gaps=True)` with
  `ChunkedWavWriter` + `fill_gap()` (GAP only). Then run r5's 18 tests and the r5a 18 tests together. If r5's
  framing differs, set `FrameLayout` to match it, or keep r5's parser and import only the policy and writer.

## 1. Five corrections — what was done
| # | Finding | r5a action | Verified by |
|---|---|---|---|
| 1 | NasoVoce ≠ primary target | Separate Mode A (comfortable whisper), Mode B (articulation, no sound), Mode C (thought only) decisions, §5 | — |
| 2 | D-DCCRN missing | Availability checked; replacement tiers with honest expectations, §3 | arXiv HTML read |
| 3 | PDM order assumed | Order made explicit and evidence-gated (`ChannelMap` refuses to exist without bench evidence); bench analyser + checklist, §6 | 4 tests |
| 4 | Parser jump → 2,147,483,647 "missing" | `classify_seq` + `Limits` + chunked fill; 0→0x80000000 is BACKWARD (half-range, ambiguous), 0→0x7FFFFFFF is JUMP; neither is ever filled; peak memory < 1 MB in the regression test | 10 tests |
| 5 | E1 kill rule too strong | `score_pilot.py` decides per configuration only; safety stop is separate, §7 | 4 tests |

Tests: `python -m unittest discover -s tests -v` → **18/18 PASS** (Python 3.13, host only, synthetic data).
CRC detects accidental corruption only. It does not authenticate samples or prove routing or meaning.

## 2. Accurate software capability inventory
| Capability | State | Evidence |
|---|---|---|
| ESP32-S3 dual-PDM firmware (r5) | SOURCE ONLY — not compiled, not flashed | GPT-6 review |
| r5 stream reader | HAS DEFECT (unbounded gap math); r5a fix available, not yet merged into r5 | review repro; r5a tests |
| r5 dual-channel energy gate | Acquisition-side gating only; **not** speech enhancement | review |
| Published NasoVoce enhancement (D-DCCRN) | **ABSENT**; no code/weights/data release stated in the paper | §3 |
| Channel-order determination | r5a bench analyser (synthetic-tested); no real capture yet | `bench/pdm_channel_map.py` |
| Pilot scoring (WER strict/lenient, silence false words, strain, 1 m leakage, closed-set commands) | r5a tool, synthetic-tested | `experiment/score_pilot.py` |
| Android USB-CDC host path | UNTESTED | — |
| Whisper accuracy on the owner's whisper / near-lip audio | UNMEASURED | — |
| Silent (Mode B) recognition | NOT IMPLEMENTED; candidate open VSR model identified, not run | §5 |
| Hardware performance, privacy, comfort | UNMEASURED | — |

## 3. D-DCCRN: availability and realistic replacement
Paper facts, read from arXiv HTML v1 (2603.10324, CHI '26):
- Sensors: SPH0141LM4H-1 MEMS mic + V2S200D vibration sensor, 16 kHz, 16-bit, vibration mapped left and mic right.
- D-DCCRN is 438.25 M parameters, trained on about 104 h of paired data from 45 English-fluent speakers, with
  DEMAND noise augmentation and Whisper-based distillation loss.
- No statement releasing code, weights or the paired dataset was found. Whisper numeric results are only in a
  figure image (not read). The text states that vibration accuracy for whisper is worse than for normal speech;
  the air microphone carries whisper.
- **Gap:** the published model cannot be reproduced without about 100 h of paired dual-sensor data. Collecting
  that from the owner conflicts with voice protection. r5a therefore claims none of the paper's gains.

Replacement ladder (each tier must be measured against tier R0 on the same recordings before adoption):
- **R0** Raw mic channel → offline Whisper. This is the baseline, and it alone answers whether near-lip whisper
  is usable.
- **R1** Vibration (or energy) VAD gating + classical spectral subtraction/Wiener on the mic. No training. Can
  cut false words during silence; expected to add little in quiet rooms.
- **R2** An open pretrained single-channel denoiser on the mic channel (candidate: DeepFilterNet; weights and
  license **UNVERIFIED** here — check before use). Expected help only in noise. May harm whisper, whose spectrum
  differs from training speech: test, don't assume.
- **R3** Small dual-input model trained on owner data. **Not recommended now** (data burden on the voice).
- Expected performance: at best near R0 in quiet, degrading with noise. Treat any NasoVoce figure as unrelated
  to this system.

## 4. Verified Egyptian procurement (prices as shown on 2026-11-07; nothing purchased)
| Item | Seller | Price | Stock | Source |
|---|---|---|---|---|
| ESP32-S3 N16R8 UNO dev board | Makers Electronics | 525 EGP | In stock | makerselectronics.com/product/esp32-s3-n16r8-development-board-2/ |
| INMP441 I2S MEMS mic module | Free Electronic | 270 EGP | **Out of stock** | free-electronic.com/product/inmp441-mems-microphone-i2s/ |
| INMP441 ×10 / ×6 packs | Ubuy EG / Fruugo EG | 1,825 / 1,599 EGP (search snippets) | UNKNOWN (Ubuy page 403) | search results only |
| GL-119 lavalier mic, 3.5 mm | Makers | 95 EGP | In stock | makerselectronics.com search "microphone" |
| GL-121 lavalier mic, USB-C | Makers | 120 EGP | In stock | same |
| BOYA BY-MM1 mini condenser | Makers | 550 EGP | In stock | same |
| OSEPP PIEZO-01 / LDTM-028K piezo vibration | Makers | 310 / 425 EGP | In stock | makerselectronics.com search "piezo" |
| V2S200D (bare or on flex) | — | **UNKNOWN** — no Egyptian listing found | UNKNOWN | — |
| SPH0141LM4H-1 | — | **UNKNOWN** | UNKNOWN | — |
| Delivery cost, customs, lead time for imported MEMS parts | — | **UNKNOWN** | — | — |

**Cheapest scientifically defensible alternative to importing the V2S200D:**
1. **Zero cost first:** the phone's own mic at ~1.5 cm (off skin) answers the decisive question — is near-lip
   whisper intelligible to Whisper while staying inaudible at 1 m? The V2S200D adds noise robustness and VAD;
   it is not needed to answer that.
2. **Only if (1) shows promise but the phone is awkward:** a 95–120 EGP wired lavalier (GL-119/GL-121) clipped
   ~1.5 cm from the lips gives a repeatable mic position. Its quality is unknown, so it is a positioning
   aid, not a performance claim.
3. Piezo contact sensors are not substitutes: they need body contact (approval required) and their speech
   bandwidth and sensitivity are unverified.

## 5. Separate Mode decisions
- **Mode A — comfortable low-volume whisper (air mic).** Continue only through the zero-cost E1R pilot. No
  hardware purchase until a configuration passes. A NasoVoce-style glasses build is a later form factor, not
  the next experiment.
- **Mode B — articulation without sound (independent research finalist).** Cheapest credible path: offline
  lip reading from the phone's front camera.
  - The official open Auto-AVSR repository reports 20.3 % WER on LRS3 visual-only (TED-style English; license
    not yet verified).
  - Open vocabulary from a handheld phone will be worse. A **closed command set** (≈20 commands, nearest-match
    scoring) is the realistic first use.
  - Zero acoustic output, but the camera is visible and video is sensitive: process offline on the owner's own
    computer only and never upload.
  - Wearable silent-speech sensing (e.g. surface EMG) needs body contact and approval. Deferred.
- **Mode C — thought only.** No lawful, low-cost, non-invasive path that would be useful here was identified. No
  work proposed.

## 6. Bench verification checklist (before any user trial; no body contact)
1. **Wiring/SEL:** record each sensor's SEL level. ESP-IDF: SEL low = left slot, SEL high = right slot.
   NasoVoce: vibration = left, mic = right.
2. **Slot order:** firmware in stereo PDM RX (`I2S_PDM_SLOT_BOTH`). Capture `silence.wav`, `air.wav` (1 kHz tone
   from a speaker ~30 cm away, device untouched) and `contact.wav` (phone vibration motor pressed on the
   vibration-sensor housing, no tone). Save raw slot order. Run
   `python bench/pdm_channel_map.py --silence silence.wav --air air.wav --contact contact.wav`.
   Accept only `MAPPED`. The ESP-IDF v5.4 docs say "The right slot is received first in stereo mode"
   (swappable via `clk_inv`). If wiring follows NasoVoce, expect `vib_slot: 1`. If the result conflicts with
   SEL wiring, stop and inspect.
3. **Electrical cross-check:** power one sensor down; its slot must drop to the noise floor. Restore it, then
   repeat for the other sensor.
4. **Clock:** PCM 32 kHz with `I2S_PDM_DSR_8S` gives CLK = fs × 64 = 2.048 MHz (×128 with DSR_16S). Measure on
   the CLK pin with a logic analyser or scope. It must sit inside the V2S200D's normal-mode clock range
   (1.2–3.3 MHz per its user guide, as cited in the review) and the mic's range. NasoVoce used 16 kHz.
   Espressif's docs name the clock pin inconsistently across versions (CLK vs WS); trust the measurement.
5. **CDC transport (Android or host):**
   - The device enumerates as USB CDC-ACM.
   - Over 10 minutes: byte rate within 1 % of expected, CRC errors 0, `jumps` 0, `gaps` reported.
   - Inject a deliberate sequence jump from a test build: the reader must stop the segment, not fill.
   - Unplug and replug: a new segment starts and no fill is attempted.
6. Write the bench report hash into `ChannelMap(evidence=...)`. Without it the writer refuses to run.

## 7. Corrected E1 rule (E1R) and the voice-protective experiment
**A failed configuration is rejected only for that configuration** (sensor, distance, volume, mode). It never
retires Mode A, other microphones, contact sensing or Mode B.

Pre-registered thresholds (`score_pilot.py`, version E1R-1):

| Criterion | Requirement |
|---|---|
| Utterances per configuration | ≥ 20 |
| Lenient WER | ≤ 25 % |
| False words during silence | ≤ 0.5 per minute |
| Median strain | ≤ 2/10 |
| Safety stop | Any strain ≥ 4/10 stops all vocal trials that day (STOP_SAFETY) |
| Privacy label "low leakage" | Only if a second recorder at 1 m gives ≥ 80 % lenient WER |
| Mode B commands | ≥ 40 trials, accuracy ≥ 85 % |

Voice protection:
- Soft whisper only; never push volume to be recognised.
- At most 25 short sentences per configuration and 3 configurations per day; total speaking time ≤ 10 minutes.
- Pause and drink water between configurations.
- Mode B needs no voice and can run on any day.
- If any persistent hoarseness or pain follows, stop and seek a clinician's advice.

## 8. Final decision — best next experiment (zero money, about 30 minutes)
**E1R two-arm screening with what already exists:**
1. **Mode A:** the phone records soft whispered sentences at three positions — 30 cm, 5 cm, and ~1.5 cm off the
   lips (off skin, the r4 pilot).
   - A second device at 1 m records at the same time as a leakage check, if one is available.
   - Transcribe offline with the Whisper already used in NEU205.
   - Score with `score_pilot.py`.
2. **Mode B:** silently mouth 20 pre-listed commands twice to the front camera.
   - Run offline Auto-AVSR on the owner's computer, after its license and checksum are verified.
   - Score closed-set accuracy.

Decision after it:
- A near-lip config passes, including low leakage → the next spend is a **95–120 EGP lavalier** to fix
  positioning (needs approval).
- Only after that passes is a dual-sensor glasses build (ESP32-S3 525 EGP + imported sensors at UNKNOWN cost)
  worth costing.
- Mode B passes → prioritise the silent command interface (no purchase needed).
- Both fail → no hardware spend. Record the negative results, and pursue AAC and clinician-guided options.

Nothing here authorises a purchase, wearing hardware, body-contact tests or production changes.
