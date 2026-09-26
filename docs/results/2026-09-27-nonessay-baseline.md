# Qwen3.5 2B Q4: four non-essay development papers

**150 tasks / 180 possible points; provisional score 40/180 (22.2%).** Only the
user-selected `qwen3.5:2b-q4_K_M` ran. Every essay and the essay-bank route was
excluded. No official passing result is claimed.

| Paper | Items | Non-essay points | Closed keys | Open/manual | Question time |
|---|---:|---:|---:|---:|---:|
| 2023 | 36 | 18/45 | 4/11 | 14/34 | 235.08s |
| 2024 | 39 | 8/45 | 2/7 | 6/38 | 283.31s |
| 2025 | 37 | 7/45 | 4/7 | 3/38 | 273.91s |
| 2026 | 38 | 7/45 | 1/7 | 6/38 | 206.00s |

The 2023/2024 scores reproduce the non-essay portions of the earlier Q4 runs.
All 74 successful responses across those two papers match their earlier question
hash and exact prediction; the 2024 truncation also recurs. This is a scope
change and broader evaluation, not a measured solver improvement. The earlier
30/60 for 2023 included a 12-point prepared essay, which is absent here.

## What this adds

Active reviewed coverage doubles from two to four papers. May 2025 and May 2026
now have complete non-essay prompts, source images, type contracts, separate
closed keys and CKE rubrics. None of the four is an untouched holdout. June 2026
remains reserved. The eight additional PDF pairs are still acquisition-only.

Frozen model: 2,274,069,824 parameters; Q4_K_M learned-file bytes 1,945,311,744.
Manifest: `124a03c347777e8e4e5955c33610ae01d9d90d8c2a718bfba069c498d5c7f3c9`.
Mixed BM25 retrieval, typed answers, image inputs, one call / 120 seconds / 2,200
output tokens and context 8,192 remain fixed. The corpus has 286 articles / 4,638
passages. No new exam answers or marking guides enter retrieval.

## Failure pattern

| Primary type | Points / maximum |
|---|---:|
| art | 5/15 |
| cartoon | 1/20 |
| choice | 6/12 |
| chronology | 1/5 |
| comparison | 6/27 |
| data_table | 0/3 |
| explanation | 1/12 |
| genealogy | 0/2 |
| identification | 12/37 |
| map | 3/18 |
| matching | 1/11 |
| true_false | 4/18 |

Primary types group overlapping skills; denominators differ across papers.
Maps score 3/18 and cartoons 1/20. Adding 2025/2026 confirms that low performance
is not confined to the 2024 paper. This does not prove equal difficulty or
isolate the cause of cross-year differences.

A directly inspected retrieval failure is 2025 task 1.2: the source asks about
Egyptian mummification and belief in an afterlife, while the actual retrieved
passages discuss Greek and Roman religion. The response follows those passages
and earns zero. In 2026 task 7, the model describes modern colonialism instead of
the Reconquista shown on the map. In 2026 task 24 it mistakes the cartoonist’s
name for the depicted figure and misses the Soviet suppression allegory.
These observed errors support testing source-grounded retrieval gating and better
visual interpretation; they do not establish the causal benefit of either fix.

Next controlled experiment: keep this model and all four papers fixed; require
retrieved passages to agree with the supplied source’s entity/period cues, with
a source-only fallback when there is no sufficiently relevant match. Do not
expand the corpus again before measuring that change. A later separate experiment
can address diagrams and maps. Neither proposed change was run in this baseline.

## Format failures and execution

- 2024 task 23.2: truncated at the output cap, invalid JSON, zero points.
- 2025 task 21.1: the same failure category, zero points.
- 2026 task 22: the same failure category, zero points.

All 150 planned calls completed; 147 returned usable answers. No transport errors
or 120-second overruns occurred. Observed question time totals 998.30s
(16.64 minutes); all calls reported usage, 337,437 total tokens.
These are desktop measurements including question processing, not an isolated
throughput benchmark or a confirmed competition runtime allowance. All four
loaded-model records show only the pinned Q4 artifact and context 8,192. Local
inference only; no charges or external model services. The task-owned server
was stopped after the run.

## Grading and uncertainty

Closed keys contribute 11/32. Open/manual items contribute 29/148, including
zero for the three format failures. Successful open answers were graded against
separate CKE rubrics with an item-level reason. No grades remain pending. Prior
grades were reused only on exact question, answer and individual-rubric matches
with agreement among matching old grades (62 reused manual grades; 60 new ones).
Raw model answers and execution records were not modified.

| Paper | Recorded score | Selected stricter reading | Selected lenient reading |
|---|---:|---:|---:|
| 2023 | 18/45 | 14/45 | 18/45 |
| 2024 | 8/45 | 5/45 | 8/45 |
| 2025 | 7/45 | 6/45 | 12/45 |
| 2026 | 7/45 | 5/45 | 10/45 |

These alternatives are selected sensitivities, not exhaustive lower/upper bounds
or confidence intervals. They total 30–48/180 under the specified choices.
The JSON pending-score interval [40, 40] means grading is complete; it does not
mean the manual assessment is certain.

- 2023: removing awards for 1, 11.1, 18 and 25.1 gives 14/45; 2024: removing
  awards for 12.3, 20.1 and 22.2 gives 5/45. See the earlier
  [quantization review](2026-09-26-quantization-comparison.md) for reasons.
- 2025: reject unrelated cargo claims in 3.1 to remove one point. Leniently accept
  the correct fragment amid errors in 7.1, the red-facade description in 8, the
  women’s-voting-rights explanation despite a wrong movement name in 17.1, the
  first sentence of 22, and a broad opposition-success similarity in 24.1 to add
  up to five. The recorded rubric review explains why these latter awards were
  withheld.
- 2026: require explicit A/B mapping in 1 and reject silver/confused exemption
  language in 5.2 to remove two. Accept the geographical contrast amid errors in
  4.1, the correct middle sentence despite contradictions in 11, and the later
  shared-event explanation despite the opening “no” in 14.2 to add up to three.

The assistant prepared these inputs and graded the responses; this is not an
independent expert assessment or the competition judge. No competition submission
was made. Retain this uncertainty when deciding whether a later change helped.

## Validation and artifacts

43 checkpoint tests passed, including eight new non-essay scope/accounting tests.
All four prepared snapshots still match their input, image, model inventory,
rubric, corpus and evaluator hashes. All 150 item/type/image references were
checked. Reviewed PDF boundaries and P/F row order were inspected; source PDFs
and original full-paper datasets remain unchanged. The adjacent evaluator was
not edited and remains an explicit local dependency.

- [Predeclared plan](2026-09-27-nonessay-plan.md)
- [Suite results and selected sensitivity](2026-09-27-nonessay-baseline.json)
- [Preparation and running instructions](../nonessay-evaluation.md)
- [2023 per-question grades and provenance](2026-09-27-qwen35-2b-q4-2023-nonessay-v1.json)
- [2024 per-question grades and provenance](2026-09-27-qwen35-2b-q4-2024-nonessay-v1.json)
- [2025 per-question grades and provenance](2026-09-27-qwen35-2b-q4-2025-nonessay-v1.json)
- [2026 per-question grades and provenance](2026-09-27-qwen35-2b-q4-2026-nonessay-v1.json)
