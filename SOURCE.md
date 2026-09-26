Made during the Warsaw Model Trainers hackathon, Kolektyw3, 25–27.09.2026

Team: ChurchBuddies.

This repository contains the tasks-data module and exact essay-bank retrieval.
It does not yet represent a complete final competition submission.

- Exam source URLs and checksums: [history-paper-sources.json](packages/tasks-data/examples/history-paper-sources.json).
- Each locally imported dataset keeps source URLs, hashes, page references and review status. Raw exam content is excluded from Git.
- The demonstration essays were written with Codex during preparation. Each record links the relevant chapters of the Constitution of 3 May, transcribed by the Sejm Library. They are original demonstration drafts, not official answers or independently graded work.
- Python standard-library code is used for matching. PDF extraction optionally uses `pypdf`, rendering uses Poppler, and PDF tests use `reportlab`; those dependencies retain their own licences.
- No model weights or Wikipedia-derived datasets are included. A team code licence has not yet been selected.

The required opening attribution comes from the [hackathon rules](https://warsawmodeltrainers.dev/rules).
