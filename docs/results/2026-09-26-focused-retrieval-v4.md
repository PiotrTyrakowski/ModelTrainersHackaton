# Focused retrieval checkpoint — 26 September 2026

Changing evidence selection raised the provisional score from **9/60 to 11/60**,
reduced incomplete answers from five to two, and reduced measured question time
from 222.21 to 150.79 seconds. This is one development-paper run per configuration,
with local rubric review, not an official or held-out passing result.

| Configuration | Points / 60 | Valid answers | Truncated | Question time | Total tokens |
|---|---:|---:|---:|---:|---:|
| Concise direct v2 | 6 | 37/37 | 0 | 122.38 s | 53,215 |
| Expanded corpus, legacy search v3 | 9 provisional | 32/37 | 5 | 222.21 s | 103,372 |
| Same corpus, focused search v4 | 11 provisional | 35/37 | 2 | 150.79 s | 92,143 |

All 37 questions, including original image inputs and the essay, were processed.
All grades are complete: 34 successful answers were reviewed against separate
rubrics, one was scored automatically, and two failed generations earned zero.

## The isolated change

The harness now searches the full cleaned query, uses explicitly referenced
source blocks, removes generic instructions and bibliographic noise, handles some
Polish word endings through lexical prefixes, boosts article-title matches, and
filters weak or redundant passages. It can provide no additional evidence.

These mechanisms form one retrieval-policy replacement; their individual effects
are not separated. The answering prompt, 89-article / 3,060-passage corpus,
unchanged Qwen3.5:0.8b Q8_0 weights, original exam inputs, temperature zero,
one-call budget, 2,200-token output cap and 8,192-token context are unchanged.
There are no new model calls, embeddings or learned parameters.

The run used the existing local Apple M5 Metal runtime, with no paid inference.
Learned model files total 1,036,034,688 bytes. Initial lexical-index construction
is included in the first question's time. See [the policy details and limits](../retrieval/focused-search.md).

## Gains, losses and remaining errors

V4 gains one point each on 3, 4.1, 4.2, 7, 11.1 and 21, while losing one each on
9.1, 9.2, 10 and 14.2: six gained, four lost, net two. No per-question winners
were combined into a synthetic score.

Retrieval now finds Neolithic material for question 1, architectural material
for 7 and the Communist Manifesto for 16.2. Nevertheless, the model invents visual
details in 1 and gives false manifesto authors in 16.2. Search relevance is not
sufficient for a correct answer. Questions 14.1 and 18 receive no additional
passages and still earn zero; skipping weak evidence has not solved their vision
and reasoning failures.

Question 7 earns one point for two correct style names despite invalid features.
Some true/false decisions earn partial credit despite false unsolicited
explanations. Matching task 2.2 and chronology task 13.2 still copy source text
without making the required selection. These are targets for a later
question-type-specific answer-format experiment.

Questions 9.3 and 23 hit the output cap and leave incomplete JSON. The essay
contains 271 whitespace-delimited words and invented rulers and chronology,
earning 0/12 for history and 0/3 for coherence. It remains a major lost-points
category; this checkpoint did not add an essay-bank solver.

## Grading uncertainty and decision

Two positive awards deserve particular review: 4.1 uses a malformed but
recognisable Hanseatic name; 5.2 gives the required genealogy but opens with false
chronological/circumstantial claims. Removing both yields **9/60**. The preceding
v3 result also contains two disputed awards. Other judgement calls exist; this
sensitivity check is not a confidence interval or exhaustive uncertainty bound.

Use v4 as the current retrieval candidate and keep concise direct as the
no-retrieval control. V4 has the highest provisional score measured so far and
fewer failures than v3, but the score difference needs independent grading and
another paper. No official passing threshold has been configured and no pass
is claimed. Other-year questions have been audited for topic gaps, but this
result is still on the fixed 2023 development paper.

## Saved evidence and validation

The [machine-readable result](2026-09-26-qwen35-focused-bm25-v4.json) contains
per-question grades, paired deltas, type totals, retrieval terms/scores, source
titles, grading sensitivity and artifact hashes. Full raw outputs, separate
grading records and source passages remain in
`artifacts/checkpoints/qwen35-focused-bm25-v4/`.

All 35 successful evidence and retrieval-policy traces match the pre-run audit
exactly. The two failed rows have labelled offline reconstructions. The answer
export validates all 37 IDs, with two blank failed answers. Runtime digest and
GPU loading match the pinned model; logs show no input-prompt truncation warnings.
All 25 checkpoint tests pass, including eight new focused-retrieval checks.
The legacy evaluator and exam assets remain explicit local dependencies.
