# Model Trainers Hackathon

Modules for preparing matura task data and comparing exam-solving systems.

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

Exam PDFs and processed datasets stay in ignored local data folders; public source
URLs and hashes are provided for reproduction. PDF imports require the optional
`pypdf` dependency and Poppler (`pdftoppm`) for page rendering.
