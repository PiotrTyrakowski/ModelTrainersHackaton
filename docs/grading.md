# What these scores mean

The local experiments use public CKE history papers and their accompanying
official marking guides. They do not reproduce the hackathon's automatic grader,
and the reported totals are not official leaderboard scores.

Closed questions have separate keys containing the correct choices and the
official partial-credit rules. Code validates the answer labels and calculates
points. A well-formed answer can still be wrong. The solver receives the available
choices and required answer shape, never which choice is correct.

Successful open answers are reviewed by Codex against the separate CKE rubric.
The rubric can require both a correct conclusion and a source-based explanation;
a correct name alone is insufficient when justification is required. Every award
records a reason and grader. Unresolved grades remain pending. Truncated outputs
that cannot form a valid answer earn zero; no answer repair is performed after
inference. Original raw outputs remain immutable in `run.json`; grading goes to
`run-graded.json`.

For essays in these papers, historical argumentation is worth up to 12 points and
coherence up to 3. Argument depth and coverage of the three required elements
determine the history score, with deductions for factual errors. Fewer than 300
words means zero for coherence; it does not automatically mean zero for history.
Word count alone does not establish argument quality. We record whitespace-based
counts and inspect borderline cases; the 392-word stored essay is safely over
the threshold under ordinary counting conventions.

The stored Cold War essay received a local 12/15: three satisfactory arguments
(9) plus coherence (3). **The same assistant wrote and graded this essay.**
Fact checking against historical sources is useful but is not independent grading.
An independent history examiner or a blinded second review is needed before
treating such an award as reliable. The result report identifies disputed awards
and sensitivity checks; these are not statistical confidence intervals.

Public papers already inspected, used to select retrieval topics, or used to
prepare essays are development data. Testing a second paper with a frozen harness
helps detect narrow coverage, but it cannot turn a previously inspected paper into
an untouched holdout. Cross-year totals also reflect different questions and
difficulty; only same-paper paired results measure the observed difference between
two configurations.

See the [2023 format/essay experiment](results/2026-09-26-typed-answers-and-essay-bank.md)
and [2024 input review](exams/history-2024-review.md). The reproducible checkpoint
snapshot hashes the exam, questions, images, keys and rubrics separately.
