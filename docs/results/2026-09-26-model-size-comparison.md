# Qwen3.5 0.8B versus 2B on two full history papers

The 2B model improved the 2024 result without Wikipedia retrieval from **8/60 to
16/60**. On 2023 that configuration stayed at **19/60**. Adding the current
retriever helped the 2B model on 2023 but hurt it on 2024. These are provisional
local grades, not official competition scores or evidence of passing unseen exams.

For the next experiment, use **2B without Wikipedia as the comparison control**
and test a stronger relevance filter against it. Retain 0.8B as the smallest-model
reference. Do not select different answers per question or report the best
configuration from each paper as one system. No production default was changed.

## Fixed comparison

The [experiment plan](2026-09-26-model-size-comparison-plan.md) specifies two
models × two papers × two strategies. All eight full-paper runs completed:
308 question attempts, 304 generation calls, no paid API calls. Four stored
2023 essays used no generation call. Both development papers had already been
inspected; neither is an untouched holdout.

The only solver change between paired model configurations is the model identity.
Prompts, typed answer schemas, source images, 89-article / 3,060-passage corpus,
retrieval policy, essay bank and budgets stayed fixed. Both use Q8_0 weights,
image input, temperature zero, disabled thinking, 8,192-token context, one call,
2,200 output tokens and 120 seconds per question. All run snapshots and raw-output
hashes were checked after completion.

**Without Wikipedia (`direct`) still includes the shared typed-answer contract
and prepared essay bank. It is not a bare-model baseline.** The same 392-word
stored essay supplies 12 provisional points in all four 2023 cells. The rendered
answer has 394 whitespace-separated tokens including “Temat 3.”. The bank finds
no match for any 2024 topic.

## Results

| Model | Wikipedia retrieval | 2023 total / 60 | 2023 non-essay / 45 | 2024 total / 60 | 2024 non-essay / 45 |
|---|---|---:|---:|---:|---:|
| 0.8B | Off | 19 | 7 | 8 | 8 |
| 0.8B | On | 24 | 12 | 9 | 9 |
| 2B | Off | 19 | 7 | 16 | 14 |
| 2B | On | 28 | 16 | 11 | 10 |

The tiny reference reproduced the earlier 2023 retrieval and both 2024 totals.
All 58 successful 2023 open answers matched previously graded answers exactly.
On 2024, 65 of 66 successful open answers matched; the changed answer to task 2
with retrieval still earned zero. Reuse required matching question hashes,
answer strings and rubric hashes, and each reused grade records its origin.

On 2024 without retrieval, the 2B model improved Byzantium identification,
the Monroe Doctrine comparison, Hohenzollern identification and NEP recognition.
It also completed every answer. Its automatically scored closed tasks improved
from 4/7 to 6/7. However, on 2023 its closed score fell from 5/11 to 2/11 without
retrieval, and from 5/11 to 3/11 with retrieval. Larger does not mean uniformly
more accurate.

The newly generated 2024 essays remain weak: 124 words and 2/15 without retrieval;
237 words including copied instructions and 1/15 with retrieval. Both lose all
coherence points for being below 300 words. Their history awards credit only
superficial argument and deduct factual errors. They do not approach the quality
of the prepared development-topic essay.

## Why retrieval is the next target

On 2024, adding retrieval to 2B reduced the total from 16 to 11 and non-essay
points from 14 to 10. The stored traces show specific relevance failures:

- Task 3.1 asks about Octavian Augustus. Retrieved passages begin with Bolesław II
  Szczodry, the Constitution of 3 May and the Polish–Lithuanian Commonwealth; the
  answer becomes Bolesław II Szczodry.
- Task 3.2 asks for Roman republican offices. A retrieved passage about the March
  Constitution appears in an answer about Polish institutions.
- Task 5.2 is answered correctly as Byzantium without retrieval. The retrieved
  passages concern World War I, ancient Greek geography and Casimir III; the
  answer becomes Rome and Athens.
- Task 23.2 misreads a simple referendum table in both configurations. Better
  document retrieval alone cannot replace reliable table reasoning.

These are observed paired outputs and retrieved contexts, not proof that every
error has the same cause. The next single change should be a stricter retrieval
acceptance rule with a no-retrieval fallback. Freeze that rule before rerunning
both complete papers. Deterministic table/date modules remain a separate later
experiment; do not combine their effects into the same checkpoint.

## Grading uncertainty

Closed answers use the separate official key and partial-credit rules. Codex
reviewed open answers against the separate CKE rubrics. The same assistant wrote
and graded the stored essay, and graded the new model essays. These assessments
are neither independent nor official. Every item has an award, reason and grader
in the linked reports; raw predictions remain unchanged locally.

Selected sensitivity checks illustrate how interpretation affects the totals:

| Configuration | Reported | Selected stricter treatment |
|---|---:|---:|
| 0.8B, 2023, retrieval | 24 | 22 without disputed tasks 4.1 and 5.2 |
| 2B, 2023, no retrieval | 19 | 16 without task 1 and the two-point task 18 award |
| 2B, 2023, retrieval | 28 | 22 without tasks 6, 9.1, 13.1, 16.1 and two points on 18 |
| 0.8B, 2024, no retrieval | 8 | 6 without tasks 8.2 and 15.1 |
| 0.8B, 2024, retrieval | 9 | 5 without tasks 8.2, 15.1 and two points on 22.2 |
| 2B, 2024, no retrieval | 16 | 13 without task 23.1 and the two essay points |
| 2B, 2024, retrieval | 11 | 8 without tasks 20.1, 21 and the essay point |

The 2023 direct 2B answers on tasks 6 and 7 could instead receive one additional
point each under a looser reading. Prior 2024 direct 0.8B tasks 3.1 and 22.2 also
have potential upward interpretations. These selected scenarios are not confidence
intervals, exhaustive bounds or an independent regrade. The 2023 retrieval gain
and 2024 retrieval gain from changing model are not robust to these judgments.
The 2024 result without retrieval provides the clearest reason to keep testing 2B.

## Runtime and artifact size

| Model | Paper | Retrieval | Seconds | Model calls | Tokens | Truncated answers |
|---|---|---|---:|---:|---:|---|
| 0.8B | 2023 | Off | 91.539 | 36 | 52,642 | None |
| 0.8B | 2023 | On | 146.920 | 36 | 89,620 | 9.3, 23 |
| 0.8B | 2024 | Off | 119.406 | 40 | 45,717 | 16.1, 25 |
| 0.8B | 2024 | On | 225.222 | 40 | 90,554 | 16.1, 26 |
| 2B | 2023 | Off | 358.787 | 36 | 52,328 | 5.2 |
| 2B | 2023 | On | 310.427 | 36 | 84,303 | None |
| 2B | 2024 | Off | 218.110 | 40 | 39,879 | None |
| 2B | 2024 | On | 421.253 | 40 | 86,437 | 6 |

Times sum question processing/inference and exclude initial corpus loading.
Models ran sequentially on local Apple M5 Metal with Ollama 0.34.4 and Python
3.12.14. Download verification overlapped part of the first 0.8B run. Cache,
thermal state and other machine load were not controlled, so this is descriptive
timing, not a rigorous speed comparison. All eight failures were truncated
answers; no item exceeded the configured time budget. No input-truncation warning
was found in the runtime log. Both model loads offloaded all 26 layers to GPU.
The task-owned server was stopped after the runs.

The 0.8B artifact has 873,438,784 parameters and 1,036,034,688 learned-file bytes.
The tag named 2B reports 2,274,069,824 parameters and 2,741,180,928 learned-file
bytes including vision weights. The complete 2B registry manifest and every blob
checksum were verified. See [its inventory](../models/qwen35-2b-q8-inventory.json)
and the [official model registry](https://ollama.com/library/qwen3.5:2b).
Runtime-reported loaded GPU allocation was about 1.16 GB and 2.51 GB respectively;
these are snapshots, not measured peak application memory.

## Reproduction and audit

Use the four `configs/checkpoints/qwen35-{08b,2b}-{2023,2024}-comparison-v1.json`
configurations with the [checkpoint workflow](../checkpoints.md). Preserve the
verified local model inventory at the configured path. Preparation requires
the existing local evaluator and reviewed exam inputs; these are explicit
dependencies, and full copyrighted exam/key copies are not committed.

- [Machine-readable comparison and validation](2026-09-26-model-size-comparison.json)
- [0.8B / 2023 report](2026-09-26-qwen35-08b-2023-comparison-v1.json)
- [0.8B / 2024 report](2026-09-26-qwen35-08b-2024-comparison-v1.json)
- [2B / 2023 report](2026-09-26-qwen35-2b-2023-comparison-v1.json)
- [2B / 2024 report](2026-09-26-qwen35-2b-2024-comparison-v1.json)

All four preparation preflights verified full coverage; every successful open
answer was graded separately, every snapshot dependency remained unchanged, raw
run hashes were preserved, and live model digests/context sizes matched the
prepared identities. No solver code changed, so no additional implementation
unit tests were needed. No competition submission was made.
