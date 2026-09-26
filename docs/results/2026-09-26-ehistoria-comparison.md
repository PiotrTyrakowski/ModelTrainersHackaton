# Adding e-Historia: four full development-paper results

The new corpus produced modest provisional score gains in all four measured
cells. It also increased answer truncations for the tiny model on 2024. The
best earlier 2024 control remains 2B without retrieval at 16/60; this experiment
does not establish a passing system or a reason to select the mixed retriever
as the default.

| Model | Paper | Wikipedia only / 60 | Mixed corpus / 60 | Non-essay / 45, before → after | Essay / 15, after |
|---|---|---:|---:|---|---:|
| 0.8B Q8 | 2023 | 24 | **27** | 12 → 15 | 12 |
| 0.8B Q8 | 2024 | 9 | **12** | 9 → 12 | 0 |
| 2B Q8 | 2023 | 28 | **29** | 16 → 17 | 12 |
| 2B Q8 | 2024 | 11 | **12** | 10 → 12 | 0, request failed |

Every 2023 cell still includes the same prepared 12-point essay. Its author and
grader are the same assistant. The 2024 bank matches no topic. Direct controls
were reused from the preceding comparison, not rerun: 0.8B 19/8 and 2B 19/16
on 2023/2024 respectively. Do not combine per-paper winners into a claimed system.

## What changed and what was checked

Added [197 e-Historia lessons / 1,578 passages](../retrieval/e-historia.md) to the
unchanged 89 Wikipedia articles / 3,060 passages. One of 198 catalogued lessons
has an empty published body, explicitly recorded as excluded. The mixed index
has 286 articles / 4,638 passages. An offline rebuild reproduces every extracted
record exactly; source spans, hashes, attribution and all original Wikipedia
records were verified. No LLM-generated history or exam keys entered retrieval.

The [predeclared plan](2026-09-26-ehistoria-plan.md) froze both full papers,
focused retrieval policy, typed prompt, essay bank, model weights and budgets.
Snapshot comparisons show only the corpus and source-config file hashes changed.
The shorter runtime-label wording also triggers an environment-change flag, but
the actual runtime remains Python 3.12.14, Ollama 0.34.4, Apple M5 Metal, context
8,192. Live model digests and context were verified for every cell. Downloads,
file validation and document work shared this desktop; timing is an observed
run cost, not an isolated performance benchmark.

All 154 planned question attempts completed. Successful open responses were
graded separately using frozen CKE rubrics. Exact prior answer/question/rubric
matches reuse provisional grades only when previous matching grades agree.
Raw answers are unchanged. The wrapper reports no unresolved grades; that does
not mean grading is objectively certain.

## Runtime and failures

| Model, paper | Seconds | Known tokens | Output truncations | Other failures |
|---|---:|---:|---|---|
| 0.8B, 2023 | 268.1 | 90,779 | 9.3, 13.1 | None |
| 0.8B, 2024 | 414.3 | 100,046 | 1, 2, 9, 16.1, 22.1, 23.2 | None |
| 2B, 2023 | 335.6 | 85,469 | None | None |
| 2B, 2024 | 439.3 | 84,055 | None recorded | Essay 26: HTTP 500 after 120.91 seconds |

The final essay request reached the local server's two-minute failure/cancellation
boundary. It earns zero as a failed attempt, not as a judged essay. Token figures
are recorded usage; absent usage for a failed call is unknown, not free inference.
The wrapper's generic over-budget list does not flag this failed request despite
its elapsed time exceeding the nominal 120-second budget; the explicit failure
and duration above take precedence.

## Retrieval evidence and remaining gaps

Among successful answers, e-Historia appears in recorded retrieved context for
15/35, 30/34, 17/37 and 33/39 answers respectively. These are exposure counts,
not relevance or recall percentages, and include the stored-essay denominator.

On 2024 task 3.1, the tiny model now receives the chapter on Augustus and names
him correctly. In task 3.2, both models receive Roman-government material; only
2B gives both required offices. Task 5.2 still retrieves medieval Rus, Ottoman
expansion and crusade material, and both models fail the requested Byzantine
identification. In several answers the model treats retrieved notes as if they
were numbered sources supplied by the exam. More source coverage does not solve
that distinction or image interpretation.

Closed-question points change from 5→7 and 4→5 for 0.8B, and 3→3 and 4→5 for
2B, on 2023/2024. These are the portions scored automatically; the remaining
changes depend on provisional rubric review.

## Grading sensitivity

These are selected disputed-award removals, not confidence intervals or
exhaustive lower bounds. Individual reasons remain in the linked JSON reports.

- 0.8B 2023: removing malformed Hansa identification (4.1) and correct-name
  answers with false additions (9.1, 14.2) changes 27→24. The previous comparison
  gives 24→22 under its selected disputed removals. Task 11.1 might gain one
  point under a looser political-weapon reading.
- 0.8B 2024: removing 8.1, 8.2, 15.1 and both 22.2 points changes 12→7, compared
  with the previous 9→5 sensitivity. Task 15.2 could gain one under a looser
  implied-comparison reading.
- 2B 2023: removing 13.1, 16.1 and two task-18 points changes 29→25, compared
  with the preceding 28→22 sensitivity. A looser reading of Katyn concealment in
  task 23 could add one point.
- 2B 2024: removing correct identifications with false additions in 8.1 and 13
  changes 12→10, compared with the preceding 11→8 sensitivity. Contextual “August”
  in 3.1 and partial readings of 6 or 12.3 could receive more credit from a reviewer.
  Rejecting the implicit Catholic/Arian contrast in task 9 would remove one more
  point (12→9 together with the two preceding removals).

Both papers have development exposure. Confirm any selected system on a reserved
paper, with independent review of borderline answers, before claiming transfer.
The next retrieval experiment should test stronger relevance checks and explicit
distinction between exam sources and retrieved background. The user's separate
quantization experiment is documented in its own plan and comparison.

## Artifacts

[Machine-readable matrix](2026-09-26-ehistoria-comparison.json), plus full reports:
[0.8B 2023](2026-09-26-qwen35-08b-2023-ehistoria-v1.json),
[0.8B 2024](2026-09-26-qwen35-08b-2024-ehistoria-v1.json),
[2B 2023](2026-09-26-qwen35-2b-2023-ehistoria-v1.json),
[2B 2024](2026-09-26-qwen35-2b-2024-ehistoria-v1.json).

Validation: 11 retrieval tests, 35 checkpoint tests and 30 task-data tests passed.
The adjacent legacy evaluator was not edited.
