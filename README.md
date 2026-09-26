# Model Trainers Hackathon

Modules for preparing matura task data and comparing exam-solving systems.

Our research is guided by exam points: run a tiny model on the same full paper
after each meaningful checkpoint, grade its answers, and choose the next change
from its mistakes. The initial reference is `qwen3.5:0.8b`, including image input.
See [the checkpoint workflow](docs/checkpoints.md).

First measured baseline: [Qwen3.5:0.8b scored a provisional 3/60 on the full
practice paper](docs/results/2026-09-26-qwen35-direct.md). Its errors guide the
next experiments.

Latest comparison: [focused evidence selection raised the provisional score
from 9/60 to 11/60](docs/results/2026-09-26-focused-retrieval-v4.md), with two
truncated answers versus five previously. V4 is the current retrieval candidate;
concise direct remains the 6/60 control with no truncation. Grades are provisional
and no passing system has been demonstrated.

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
The included essays are demonstration drafts; no exam-passing result is claimed.

- [Essay retrieval: formats, examples and limits](docs/essay-bank.md)
- [Task data: importing, reviewing and exporting exam questions](docs/tasks-data.md)
- [History retrieval: source-preserving corpus and reproducible index](docs/retrieval.md)

Exam PDFs and processed datasets stay in ignored local data folders; public source
URLs and hashes are provided for reproduction. PDF imports require the optional
`pypdf` dependency and Poppler (`pdftoppm`) for page rendering.
