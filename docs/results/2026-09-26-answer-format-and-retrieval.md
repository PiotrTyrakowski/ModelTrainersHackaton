# Answer-format and retrieval checkpoints — 26 September 2026

Subsequent checkpoint: [expanded corpus v3](2026-09-26-retrieval-corpus-v3.md)
measures the user's requested coverage expansion. The results below describe
the preceding v2 experiments.

The concise answer contract improved the tiny Qwen system from a provisional
**3/60 to 6/60** and eliminated incomplete JSON. Adding the existing Wikipedia
retriever produced a provisional **7/60**, but that one-point difference depends
on judgement calls and came with four failed answers. Keep **concise direct** as
the working reference; retain BM25 as an experimental alternative.

| Configuration | Points / 60 | Valid answer objects | Truncated answers | Question time | Total tokens |
|---|---:|---:|---:|---:|---:|
| Original direct | 3 | 33/37 | 4 | 317.49 s | 83,652 |
| Concise direct v2 | 6 | 37/37 | 0 | 122.38 s | 53,215 |
| Concise + BM25 v2 | 7 provisional | 33/37 | 4 | 214.23 s | 124,622 |

Every run processed all 37 questions, including image tasks and the essay.
No grades remain pending. All use the same unchanged Qwen3.5:0.8b Q8_0 weights,
1,036,034,688 learned bytes, local Apple M5 Metal runtime, 8,192-token context,
temperature zero, one call per question and 2,200 output tokens. No cloud
inference charges were incurred. Each configuration was run once; timing is
descriptive, and the concise-direct run includes a restarted server's first load.

These are development-paper results with Codex rubric review, not official
examiner grades or evidence of passing an unseen exam. No organiser-confirmed
passing threshold is set.

## First change: a concise complete answer

The prompt now asks for a single JSON string field, `answer`, containing the
entire response and any required justification. It omits the separately generated
evidence list. It asks for short answers, labelled decisions for closed tasks,
and exactly one essay topic. The same original source text and images still
reach the model. No answer keys, rubrics or example solutions enter its prompt.

The change earned six new points across questions 4.2, 10, 11.2, 13.2, 16.1 and
21, while losing the original three points on questions 3 and 19: a net gain of
three points. It fixed technical completion, but the model still copied some
questions, invented facts and omitted requested elements.

The essay was complete JSON but only 236 words. Its rulers, dates and arguments
were historically wrong, so it received 0/12 for historical narrative and 0/3
for coherence under the minimum-length rule. Valid output alone is insufficient.

## Second change: add existing factual retrieval

The same concise prompt receives the existing retriever's three highest-ranked
passages. No new documents, embeddings, model weights or extra generation calls
were added. All **697 indexed passages** were checked against the original
**20 Polish Wikipedia articles** before the run. This is a development-specific
pilot corpus, not comprehensive coverage.

The scored result increased by one point compared with concise direct, but:

- Questions 3, 6, 9.1 and 25.1 hit the output cap and produced incomplete JSON.
- Retrieval frequently supplied the wrong period or topic. The November Uprising
  questions received WWII material; the medieval Polish essay received material
  about the Commonwealth, communist Poland and ancient Sparta.
- Useful evidence was sometimes present but misused. The retrieved material for
  25.2 explicitly named Jaruzelski and martial law, yet the model supplied a wrong
  person and the wrong action.
- Compared with concise direct, retrieval gained points on 2.1, 11.1, 21 and the
  essay, but lost points on 10, 13.2 and 16.1.

The model's 308-word essay received **0/12 historical points** and a borderline
**1/3 coherence point**: it repeats an entire block and contradicts its thesis,
but has a topic statement and linked claims. Question 11.1 also received a
borderline point for describing veto as a political weapon and Sejm disruption,
despite serious additional errors. Removing both disputed awards would give
**5/60**, below concise direct. This sensitivity check is not a statistical
confidence interval or a guarantee that all other grades would be upheld.

Consequently the current RAG run does not establish a reliable improvement.
It consumes more tokens, reintroduces failures, and sometimes steers the model
away from the supplied exam sources. Do not select per-question winners from
this paper and present their combined score as a measured system result.

## Decision and next measured test

Use `configs/checkpoints/qwen35-concise-v2.json` with `--variants direct` as the
reference. Keep the BM25 configuration for reproducible comparisons.

The next retrieval change should target the observed search failure: extract
useful historical query terms, check period/entity relevance, and allow no
retrieval when evidence is weak. Evaluate that separately before growing the
corpus. The model also fails with relevant evidence present, so compare a
slightly larger model on the same paper before committing to extensive work
around this 0.8B candidate. A smaller passing system remains the objective.

The existing essay-bank examples do not cover this paper's topics. They were
not used or forced into a nearest match. Test essay retrieval independently when
appropriate source-grounded essays exist, and confirm eventual gains on an
untouched paper.

## Saved evidence

- [Concise-direct result and per-question grades](2026-09-26-qwen35-concise-direct-v2.json)
- [Retrieval result, paired comparison and grading sensitivity](2026-09-26-qwen35-concise-bm25-v2.json)
- [Original baseline](2026-09-26-qwen35-direct.md)
- [Commands and checkpoint rules](../checkpoints.md)

Full raw outputs, separate grading records, source/config hashes, live model
identity, runtime evidence and answer exports remain locally in the corresponding
`artifacts/checkpoints/qwen35-concise-*-v2/` directories. The retrieval run also
has an audit of corpus passages: successful traces match the saved generation
trace exactly; failed rows are explicitly labelled as offline reconstruction
from the pinned deterministic retriever.

Validation: 17 checkpoint tests passed. Both exports validate all 37 IDs; concise
direct has no blanks and retrieval has four blanks from failed generations.
Runtime logs show no input-prompt truncation warnings. The legacy evaluator and
exam assets remain separate local dependencies.
