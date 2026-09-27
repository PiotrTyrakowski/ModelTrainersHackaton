# Model Trainers Hackathon

Modules for preparing matura task data and comparing exam-solving systems.

## Harness of models (27 September 2026)

Goal: the smallest system that passes the history matura (formula 2023; pass
mark 21/60 including the essay). The essay is never generated; the model picks a
prepared essay. `scripts/harness/run_system.sh <exam.json> <answers.json>` runs a
fine-tuned Qwen3.5-4B at IQ2_M with the Q8_0 vision projector
(**2,126,891,136 learned bytes**), BM25 retrieval and the essay bank.

| Evaluation | Non-essay /45 | Essay /15 | Total /60 |
|---|---:|---:|---:|
| June 2026 reserved paper, one frozen run (two graders) | 15–16 | 12 | **27–28** |
| June 2023 check paper, one frozen run | 13–14 | 11–12 | 24–26 |
| June 2024 check paper, one frozen run | 8–11 | 5 | **13–16 (fail)** |
| June 2025 check paper, one frozen run | 11–12 | 14* | 25–26 |
| Four development papers × three passes | 12–20 | 4–15 (selected essays) | 18–33 (8 of 12 reach 21) |

\* Written after that topic had been seen.

Grades are provisional (Claude graders, CKE rubric).
- The system passed June 2026 and June 2023 and failed June 2024. June 2025
  passed only through an essay written after its topic had been seen.
- Over the four June papers the non-essay part averages 12–13/45, so this is a
  borderline pass, not a reliable one.

**Larger alternative.** `scripts/harness/run_system_q4.sh` is the same harness
with the base (not fine-tuned) Qwen3.5-4B Q4_K_M and the same projector
(**3,107,832,544 learned bytes**). It was declared before its runs, then run
once on each June paper:

| June paper | Non-essay /45 | Essay /15 | Total /60 |
|---|---:|---:|---:|
| 2023 | 22 | 11–12 | 33–34 |
| 2024 | 18–19 | 4–5 | 22–24 |
| 2025 | 20 | 14* | 34 |
| 2026 | 26–27 | 12 | 38–39 |

\* The same essay as above, written after that topic had been seen.

It passed every paper, even with an assumed 8/15 essay, with the widest margin
of the systems we tested. But the June papers were no longer held out when we chose to test
it, so a new paper is needed to confirm it.

**In-between size.** `scripts/harness/run_system_q3.sh` uses the base
Qwen3.5-4B Q3_K_M and allows answers of up to 600 tokens
(**2,660,283,104 learned bytes**, 14% less than the alternative). It was
declared before its runs and passed a development gate before any June run:

| June paper | Non-essay /45 | Essay /15 | Total /60 |
|---|---:|---:|---:|
| 2023 | 22–23 | 11–12 | 33–35 |
| 2024 | 18–19 | 5 | 23–24 |
| 2025 | 14 | 14* | 28 |
| 2026 | 24–25 | 5 | 29–30 |

\* The same essay as above.

- It passed every paper and reached the declared 13/45 non-essay criterion on
  each. That makes it the smallest configuration that did, though by only one
  point on June 2025.
- With this model the essay selector's votes never count, so essays are chosen
  lexically. On June 2026 that gave a 5/15 essay where the other systems chose a
  12/15 one.

**Before uploading.** Run
`python3 scripts/harness/check_submission.py <answers-template.json> <answers.json> --exam <exam.json>`.
It checks the organisers' file rules:
- every ID exactly once, with string answers;
- only the `exam_id`/`answers` and `id`/`answer` keys;
- UTF-8 and under 1 MiB;
- the essay names its topic number and has at least 300 words.

See the [results and limitations](docs/results/2026-09-27-harness-of-models.md).

## Earlier work

Our research is guided by exam points: run a fixed model after each meaningful
checkpoint, grade its answers, and choose the next change from measured errors.
Before the harness-of-models goal, the user-selected model was **Qwen3.5 2B
Q4_K_M only**, including image input, with essays excluded. See the
[four-paper workflow](docs/nonessay-evaluation.md).

Latest [non-essay baseline](docs/results/2026-09-27-nonessay-baseline.md):

| Development paper | Tasks | Points without essay |
|---|---:|---:|
| 2023 practice | 36 | 18/45 |
| May 2024 | 39 | 8/45 |
| May 2025 | 37 | 7/45 |
| May 2026 | 38 | 7/45 |
| Total | 150 | 40/180 (22.2%) |

Active reviewed coverage doubles from two to four papers. Local grades are
provisional, with item-level reasons and selected grading sensitivity. All
questions ran; three responses truncated into invalid JSON. No official pass is
claimed. The 2023/2024 non-essay results reproduce the earlier Q4 results, so
removing essays is not a solver improvement. No 0.8B or Q8 model ran in this series.

Historical full-paper experiments: [adding e-Historia to retrieval](docs/results/2026-09-26-ehistoria-comparison.md)
and [2B Q4 versus Q8](docs/results/2026-09-26-quantization-comparison.md), each
measured on both complete development papers.

| Model with mixed retrieval | Learned files | 2023 / 60 | 2024 / 60 |
|---|---:|---:|---:|
| 0.8B Q8 | 1.036 GB | 27 | 12 |
| 2B Q8 | 2.741 GB | 29 | 12 |
| 2B Q4 | 1.945 GB | 30 | 8 |

Grades are local and provisional. All 2023 cells include the same 12-point
prepared development essay; no general passing ability is established. Q4 saves
29% of learned-file storage versus Q8 but loses points on 2024. Added 197
source-preserved e-Historia lessons, giving 286 articles / 4,638 mixed passages.
Also downloaded [8 more exam/marking pairs](docs/exams/more-history-papers.md);
these are PDFs awaiting extraction/review, excluded from retrieval. June 2026
is reserved with cover checks only.

Earlier [0.8B versus 2B comparison](docs/results/2026-09-26-model-size-comparison.md):
Without Wikipedia retrieval, 2B scored provisional **19/60 on 2023 and 16/60 on
2024**, versus 19/60 and 8/60 for 0.8B. With retrieval, 2B scored 28/60 and 11/60,
versus 24/60 and 9/60. All 2023 totals include the same 12-point prepared essay.
Retrieval helped one paper and hurt the larger model on the other. These are
historical size comparisons; current runs use only 2B Q4. Grading remains provisional.

First measured baseline: [Qwen3.5:0.8b scored a provisional 3/60 on the full
practice paper](docs/results/2026-09-26-qwen35-direct.md). Its errors guide the
next experiments.

Earlier 2023 comparison: [complete closed-answer formats reached 12/60 and
prepared essay retrieval reached 24/60](docs/results/2026-09-26-typed-answers-and-essay-bank.md).
The bank covers one previously inspected topic and its author also performed the
local rubric review; the gain is not evidence of unseen-topic performance. Two
open answers still truncate. Concise direct remains the 6/60 historical control.
Grades are provisional and no passing system has been demonstrated.

[Second-paper test on 2024](docs/results/2026-09-26-2024-transfer.md): the frozen
harness scored **9/60**, versus **8/60 without retrieval**. Its essay bank correctly
found no match for the new topics. These results expose limited transfer; the
2023 result alone is not a general passing result. See [how grading works](docs/grading.md).

The first module is [`tasks-data`](packages/tasks-data): source-preserving exam
imports, separate answer keys, and a bank of complete essays that can be retrieved
without rewriting them.

```sh
python3 -m pip install -e 'packages/tasks-data[pdf,test]'
python3 -m unittest discover -s packages/tasks-data/tests -v
tasks-data essay-match packages/tasks-data/examples/essay-bank.jsonl \
  packages/tasks-data/examples/essay-query.json \
  --output artifacts/demo/trace.json --essay-output artifacts/demo/answer.txt
```

The essay bank supports text matching without a model and optional question
embeddings. It returns the chosen essay unchanged or an explicit `no_match`.
The examples remain demonstration drafts. A separately documented, source-reviewed
development essay now runs in the checkpoint harness; no exam-passing result is claimed.

- [Essay retrieval: formats, examples and limits](docs/essay-bank.md)
- [Task data: importing, reviewing and exporting exam questions](docs/tasks-data.md)
- [History retrieval: source-preserving corpus and reproducible index](docs/retrieval.md)

Exam PDFs and processed datasets stay in ignored local data folders; public source
URLs and hashes are provided for reproduction. PDF imports require the optional
`pypdf` dependency and Poppler (`pdftoppm`) for page rendering.
