# Model Trainers Hackathon

Modules for preparing matura task data and comparing exam-solving systems.

Our research is guided by exam points: run a tiny model on the same full paper
after each meaningful checkpoint, grade its answers, and choose the next change
from its mistakes. The initial reference is `qwen3.5:0.8b`, including image input.
See [the checkpoint workflow](docs/checkpoints.md).

Latest experiment: [0.8B versus 2B on both full papers](docs/results/2026-09-26-model-size-comparison.md).
Without Wikipedia retrieval, 2B scored provisional **19/60 on 2023 and 16/60 on
2024**, versus 19/60 and 8/60 for 0.8B. With retrieval, 2B scored 28/60 and 11/60,
versus 24/60 and 9/60. All 2023 totals include the same 12-point prepared essay.
Retrieval helps one paper and hurts the larger model on the other; stricter
relevance filtering is the next experiment. Keep 0.8B as the size reference and
2B without Wikipedia as the next comparison control. Grading remains provisional.

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
