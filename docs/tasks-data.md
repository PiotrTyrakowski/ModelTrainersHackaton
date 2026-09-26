# Task data, sources and grading boundaries

`packages/tasks-data` is the base data module. It imports existing exams, preserves their evidence and exports reviewed task inputs for evaluation. It does not create historical answers, grade essays, or turn unreviewed PDF text into a verified question dataset.

Current evaluation uses [four reviewed non-essay views](nonessay-evaluation.md),
including newly reviewed May 2025 and May 2026: 150 items / 180 points, only
Qwen3.5 2B Q4. Original candidate imports and complete papers are preserved.

## Dataset layout

```text
manifest.json          schema version, exam ID, summaries and record-file hashes
tasks.jsonl            questions, source text, visual assets and review state
sources.jsonl          source URLs, local paths, SHA-256 and provenance
grading/keys.jsonl     separate answer keys or explicit manual placeholders
raw/                   original source package/PDF and extracted page text
pages/ or assets/      preserved page renders or original question images
review-queue.json      PDF candidate boundaries and issues needing review
```

The root `data/raw/`, `data/processed/` and `artifacts/` directories are gitignored. The local exam papers, page images and extracted copyrighted passages are not committed. The public source list with hashes lives in `packages/tasks-data/examples/history-paper-sources.json`.

A `Task` has an exam ID and original item ID, prompt, source text, question type, image paths, point value, source references, task constraints and review state. `SourceRef` retains one-based **PDF file page indices**, which may differ from printed page labels, and character spans into the unmodified extracted page text. Source extraction preserves page furniture and answer lines; it does not pretend those are clean semantic task boundaries.

A `SourceRecord` records the original URI, SHA-256, local relative path, source kind and rights/provenance information. Every image used by a task requires a checksum-bearing source record. Source paths cannot escape the dataset, including through symlinks.

An `AnswerKey` lives only under `grading/`. Imports create `manual` placeholders with no expected answer. Actual keys can be added through the Python API after checking a marking scheme; they are not inferred from task wording or answer-format examples. A manual placeholder means ungraded, not incorrect.

## Structured mock import

The importer accepts the existing official format with `exam_id`, `items`, `question`, `source_text`, linked images and `answer_format`. It verifies image hashes before copying and preserves every original item ID.

```sh
tasks-data import-json /path/to/exam.json \
  --types /path/to/question-types.json \
  --source-uri https://warsawmodeltrainers.dev/exams/history-2023-mock-v1.zip \
  --output data/processed/history-2023-mock-v1
```

`--types` is a JSON mapping from each item ID to its reviewed module type. Without it, tasks remain `unknown` / `needs_review`. Supplying a type map marks structurally complete items ready; it does not establish any model's ability to answer them. The source package's formatting examples remain syntax examples, not gold labels.

An output directory must be new or empty. Choose a new dataset version when reimporting; existing work is not overwritten.

## PDF import

```sh
tasks-data import-pdf data/raw/history-2024.pdf \
  --exam-id history-2024-may \
  --source-uri https://arkusze.pl/maturalne/historia-2024-maj-matura-rozszerzona.pdf \
  --output data/processed/history-2024-may
```

The importer copies the raw PDF, writes exact per-page text, locates Polish `Zadanie` headings, links shared parent-task sources to subquestions and renders relevant full pages at 110 DPI. It preserves visual information instead of trying to reconstruct maps and pictures from text. Repeated headings are retained as separate candidates with a warning. Unknown point values remain unknown.

**Every PDF-derived item starts as `needs_review`.** Review the prompt boundaries, shared source text, visual assets, module type and point value before using it for model evaluation. A correct item count or 60-point sum does not prove each extracted boundary is correct. Essays can include continuation pages, blank answer space and rough-work pages that a reviewer should trim deliberately.

`--no-render` retains the raw PDF and text but omits PNGs; those records still cannot be exported before review. This is not OCR. Scanned pages with no extractable text remain visible in metadata. If no task markers are found, the source-only import reports zero candidate tasks; an empty dataset cannot be exported to the solver. A marking-scheme detection check rejects documents with repeated grading headings, but it is a heuristic: the caller must still supply the exam paper, not its answer key.

## Review, validate and export

```sh
tasks-data inspect data/processed/history-2024-may
tasks-data validate data/processed/history-2024-may
```

Validation checks dataset and source hashes, unique IDs, grading/task separation, image provenance, source references, PDF page bounds, character-span bounds and point consistency. It checks data integrity, not historical truth or semantic segmentation.

After actually reviewing an item:

```sh
tasks-data review-task data/processed/history-2024-may 1 \
  --type art --points 1 \
  --prompt-file /path/to/reviewed-prompt.txt \
  --source-file /path/to/reviewed-source.txt \
  --note 'Checked prompt, source text and images against PDF page 4.'
```

The original PDF, extracted page text and provenance remain preserved. The command updates the selected task and its placeholder key's point value. It does not generate an answer or certify the review automatically. The Python API can additionally adjust image paths and source spans when a reviewer corrects a boundary.

```sh
tasks-data export-inputs data/processed/history-2023-mock-v1 \
  --output artifacts/history-2023-model-inputs.jsonl
```

This produces the existing evaluator's `id/type/prompt/source_text/images/constraints/max_points` format. Image paths resolve to local absolute paths. The complete dataset must be ready; the exporter builds all records before writing and rejects mixed ready/draft data. No grading files, expected answers or private key metadata enter these inputs.

## Python API

```python
from tasks_data import Dataset

dataset = Dataset.load('data/processed/history-2023-mock-v1')
print(dataset.validate())
for task in dataset.tasks:
    print(task.id, task.question_type, task.review_status)
dataset.export_solver_inputs('artifacts/questions.jsonl')
```

For controlled modifications, use `dataclasses.replace` on an immutable `Task` or `AnswerKey`, replace the record in the dataset and call `dataset.save()`. Directly editing checksummed JSONL files makes validation fail until a deliberate dataset save rebuilds its manifest.

## Imported locally

| Paper | Items/candidates | Points detected | Ready for solver export | Expected answers imported |
|---|---:|---:|---:|---:|
| Official structured 2023 mock | 37 | 60 | 37 | 0 |
| May 2024 PDF | 40 | 60 | 0; all need review | 0 |
| May 2025 PDF | 38 | 60 | 0; all need review | 0 |
| May 2026 PDF | 39 | 60 | 0; all need review | 0 |

These **154 records** include **117 PDF candidates**. The three PDF imports retain 100 page PNGs in total, with raw PDFs, page text and source hashes. Representative map, image and shared-source pages were visually checked for preservation; all task boundaries have not been manually reviewed. Counts agree with the previously inspected papers. These are already seen development papers, not an untouched final test set.

The base-module tests cover source changes, grading leakage, unsafe paths, duplicate IDs, unknown types, shared source blocks across pages, ambiguous headings, span bounds and refusal to export unreviewed tasks. Separate tests cover the essay bank and embedding adapter.

Local import evidence: `artifacts/tasks-data-import-report.json`. A verified 37-record solver input export is at `artifacts/history-2023-model-inputs.jsonl`. Both are local ignored artifacts; neither has been uploaded to the competition.

Later updates: the [reviewed May 2024 adapter](exams/history-2024-review.md) now
provides 40 complete solver inputs and separate grading records. The original
candidate dataset above remains unchanged. Eight more
[exam/marking pairs from 2019–2026](exams/more-history-papers.md) are now downloaded
as PDFs only; they are not additional reviewed task records. June 2026 is reserved
for later evaluation and remains outside retrieval and tuning.
