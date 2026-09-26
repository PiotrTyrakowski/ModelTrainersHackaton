# Expanded retrieval corpus — 26 September 2026

The expanded corpus raised the tiny model's provisional score from **7/60 to
9/60**, but increased truncated answers from four to five. This is a modest
development-paper result, with disputed grades, not a demonstrated passing system.

| Configuration | Points / 60 | Valid answers | Truncated | Question time |
|---|---:|---:|---:|---:|
| Concise direct v2 | 6 | 37/37 | 0 | 122.38 s |
| Original corpus, BM25 v2 | 7 provisional | 33/37 | 4 | 214.23 s |
| Expanded corpus, BM25 v3 | 9 provisional | 32/37 | 5 | 222.21 s |

All 37 questions were processed and graded; none remain pending. The same
unchanged Qwen3.5:0.8b Q8_0 model ran locally on Apple M5 Metal, with the same
concise prompt, original exam text/images, top-three BM25 search, 8,192-token
context, temperature zero, one call per question and 2,200-token output cap.
Learned model files total 1,036,034,688 bytes. No paid inference was used.

## What changed

The original 20 articles / 697 fixed-character chunks became **89 articles /
3,060 passages**. Added topics address observed gaps across the development paper.
Passages preserve paragraph or sentence boundaries and include the article title
and section. Bibliography and navigation sections are omitted. Coverage and
passage representation changed together; their effects are not separated.

Every passage was checked against its exact source span and content hash.
Every indexed record was checked against the passage file. Attribution, source
URLs and observed revision metadata are retained. These checks verify faithful
extraction, not the truth of every encyclopedia claim. No exam keys or rubrics
were added to the corpus or solver prompt.

See the [build instructions](../retrieval.md) and
[snapshot manifest and article catalogue](../retrieval/wiki-focused-v3.manifest.json).

## What the exam shows

Compared with the old retrieval run, v3 gained seven points across questions 5.2,
9.1, 9.2, 10, 14.2 and 16.1, and lost five across 4.2, 11.1, 21 and 26. The net
gain is two points. Some improvements use newly available facts, including the
Capetian lineage, Zygmunt III and Galicia. Correct selections in question 10
earned points despite false unsolicited explanations, so the score does not
establish reliable historical reasoning.

The five failed answers were 3, 7, 8, 9.3 and 22: each reached the output cap and
left incomplete JSON. The essay had 250 whitespace-delimited words and invented
rulers and chronology; it earned 0/12 historical and 0/3 coherence points.

Retrieved material for Crécy and Ostrołęka is now relevant, but the model still
fails to answer the question asked or select the correct map. Some retrieval is
plainly wrong: the coin-identification question receives medieval rulers and
Rowecki; the manifesto question receives communist-era protest material. The
cartoon answer imports Józef Bem from retrieval into an unrelated scene.

The search uses the first 80 distinct tokens from question text followed by
source text. Generic instructions can crowd out useful names and dates. It
cannot search from details present only in images. The essay query covers all
three offered topics, and still retrieves largely irrelevant material. Broad
coverage alone cannot resolve these problems.

## Grading limits and decision

All local grades are provisional Codex rubric review. Question 5.2 receives one
point for the correct lineage despite an incorrect opening date. Question 16.1
receives one for the initial source comparison despite spurious context at the
end. Removing both disputed awards gives **7/60**. Questions 1 and 4.2 were
conservatively rejected for inadequate or contradictory justification. This is
a sensitivity check, not a confidence interval or exhaustive uncertainty range.
The preceding 7/60 result also had two disputed awards.

Keep concise direct as the technically reliable reference, and v3 as the latest
retrieval experiment. Do not combine this paper's per-question winners into a
claimed benchmark result. The next isolated change should improve query terms
and evidence relevance, with an option to supply no extra passage when relevance
is weak. Then rerun this same full paper. Separating retrieved evidence from
numbered exam sources also deserves a later prompt experiment.

The topic selection used this public practice paper, so these results are not
held out. Eventual progress needs confirmation on an untouched paper. No official
passing threshold is configured, and no pass is claimed.

## Evidence and checks

The [machine-readable report](2026-09-26-qwen35-concise-bm25-v3.json) contains
per-question grades, type totals, paired score deltas, runtime, source titles,
grading sensitivity and local artifact hashes. Full raw outputs and separate
grades remain in `artifacts/checkpoints/qwen35-concise-bm25-v3/`.

All 32 successful retrieval traces match the pre-run search audit exactly. The
five failed rows have explicitly labelled offline retrieval reconstructions.
The answer export validates all 37 IDs, with five blanks for failed generations.
Runtime identity matches the pinned model digest and logs have no input-prompt
truncation warnings. Total reported tokens: **103,372**, versus 124,622 in v2.
This is one run per configuration; timing is descriptive.

Three passage-builder tests pass, covering exact spans, section exclusion and
long-paragraph splitting. The existing 17 checkpoint tests had passed before
these runs. The corpus/index build also verified every real record. The legacy
evaluator, seed snapshot and exam assets remain explicit local dependencies.
