# More parameters with fewer bits: 2B Q4 versus Q8

Qwen3.5 2B Q4_K_M uses **29.0% fewer learned-file bytes than 2B Q8_0**, but
does not preserve its score on both development papers. With the same mixed
Wikipedia/e-Historia corpus and harness, it scored **30/60 on 2023 and 8/60 on
2024**, versus Q8's 29/60 and 12/60. Keep it as a smaller candidate, not a proven
upgrade. The earlier 2B direct control remains best on 2024 at 16/60.

| Artifact | Learned files, decimal GB | 2023 / 60 | 2024 / 60 | Non-essay 2023 / 45 | Non-essay 2024 / 45 |
|---|---:|---:|---:|---:|---:|
| 0.8B Q8_0 | 1.036 | 27 | 12 | 15 | 12 |
| 2B Q8_0 | 2.741 | 29 | 12 | 17 | 12 |
| 2B Q4_K_M | 1.945 | 30 | 8 | 18 | 8 |

The 0.8B and 2B Q8 mixed-corpus runs are the immediately preceding controls,
reused without rerunning. Every 2023 cell includes the same 12/15 prepared essay;
the bank does not match a 2024 topic. These are provisional local rubric grades,
not independent evaluation or official competition results. No passing threshold
is established, and neither paper is a holdout. One run per cell does not measure
run-to-run variation or establish a general quantization effect.

## Size and identity

The official 2B artifacts both contain **2,274,069,824 parameters**, including
embedded vision weights. Quantization reduces the precision/storage of those
weights, not their count. The Q4 learned file is **1,945,311,744 bytes**, versus
**2,741,180,928** for Q8. It is still 87.8% larger than the 0.8B Q8 learned file
(1,036,034,688 bytes, 873,438,784 parameters). These are downloaded learned-file
sizes, not total peak RAM; context, runtime buffers and the retrieval database
have separate costs. See the [verified Q4 inventory](../models/qwen35-2b-q4-inventory.json).

Manifest and every downloaded blob were checked against their SHA-256 digests.
Before/after each run the local server's model identity and 8,192-token context
were checked. Q4 manifest: `124a03c347777e8e4e5955c33610ae01d9d90d8c2a718bfba069c498d5c7f3c9`.
All six mixed-corpus snapshots still match their pinned file hashes. Between Q4
and Q8, the only changed dependency hashes are source configuration and model
inventory. The corpus, questions, images, keys, rubrics, prompts, essay bank and
evaluator code remain identical. The [plan](2026-09-26-quantization-plan.md)
was recorded before Q4 inference.

Metadata correction: the executed Q4 `v1` configurations inherited the descriptive
`model_provenance.quantization: Q8_0` label. The requested tag, verified bytes,
inventory and live runtime all show **Q4_K_M**; that label does not select weights.
Frozen executed files and reports retain the original metadata. The two Q4 `v2`
configurations correct only this label for future preparation; no new inference
result is attributed to them.

## Runtime and failures

| Model | Paper | Question time, seconds | Known tokens | Calls | Failure/truncation |
|---|---|---:|---:|---:|---|
| 2B Q8 | 2023 | 335.6 | 85,469 | 36 | None |
| 2B Q4 | 2023 | 270.0 | 85,035 | 36 | None |
| 2B Q8 | 2024 | 439.3 | 84,055 | 40 | Essay HTTP 500; failed-call token usage unknown |
| 2B Q4 | 2024 | 304.7 | 88,496 | 40 | Task 23.2: repetitive output hit 2,200 tokens; invalid JSON |

Q4 completed all 77 planned attempts; the failed 23.2 earns zero. Its other
successful open responses were graded separately, with no unresolved grades.
The 2024 essay returns valid JSON with a normal stop but is unfinished prose,
208 whitespace-delimited words including the copied topic. Its historical
argument contains extensive false claims about Charlemagne and earns zero;
being below 300 words independently removes coherence points. It was not
automatically zeroed just for being short.

Timing includes per-question work but excludes initial model/corpus loading.
These runs shared a desktop with other file and document work. Q8's failed essay
took 120.91 seconds; this and different generated answers make the observed
runtime difference unsuitable as an isolated throughput comparison. All runs
used local hardware without paid APIs or training.

## Where scores changed

Automatically graded closed questions changed Q8→Q4 from **3→4 / 11** on 2023
and **5→2 / 7** on 2024. The remaining differences rely on local rubric review.
On 2023, identification tasks gain three points while art, cartoon and map tasks
each lose one. On 2024, identification and true/false each lose two points;
comparison gains one and choice loses one. Full per-type totals are in the
[machine-readable comparison](2026-09-26-quantization-comparison.json).

Source confusion persists: Q4 answers the 2024 Hohenzollern question using a
retrieved Charlemagne passage, and misidentifies the Monroe address as a Polish
bishops' letter. More parameters alone have not solved selection and use of
relevant evidence.

Selected grading sensitivity checks, not exhaustive bounds:

- Q4 2023: removing disputed credit for Neolithic evidence with false additions
  (1), liberum veto with an absolutism claim (11.1), US aid with invented context
  (18) and Brezhnev with false details (25.1) changes **30→26**. Q8's analogous
  selected removals give **29→25**. Looser readings of Q4 realism (15) or Katyn
  concealment (23) might add one point each.
- Q4 2024: removing emotion-based Baroque credit with inaccurate posture (12.3),
  NEP with unrelated source claims (20.1) and the partial Cold War comparison
  with false additions (22.2) changes **8→5**. Task 9 might gain one under a looser
  implicit Catholic/Arian contrast. Q8's selected removals give **12→10**, or 9
  if its own task-9 implicit contrast is rejected as well.

The current next harness experiment remains stricter retrieval relevance and a
clear distinction between exam sources and retrieved background, with the 0.8B
reference retained. For a later model-size experiment,
[Qwen3.5 4B Q4_K_M](https://ollama.com/library/qwen3.5:4b-q4_K_M) is available at
about 3.4 GB. It has not been downloaded or tested here; neither its score nor
competition eligibility is inferred from its availability.

Full reports: [Q4 2023](2026-09-26-qwen35-2b-q4-2023-ehistoria-v1.json),
[Q4 2024](2026-09-26-qwen35-2b-q4-2024-ehistoria-v1.json).
The [preceding corpus report](2026-09-26-ehistoria-comparison.md) contains all four
reference runs and validation details. Raw answers and source data remain local.
