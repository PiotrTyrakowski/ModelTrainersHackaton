# Current evaluation: 2B Q4, four papers, no essays

The user requested only `qwen3.5:2b-q4_K_M` and temporarily removed essays from
research. The active suite now covers **150 non-essay items / 180 points**:
2023 practice (36 items), May 2024 (39), May 2025 (37), May 2026 (38).
Each paper contributes all its 45 non-essay points. This doubles active paper
coverage from two to four. These are development papers; June 2026 stays reserved.
The [coverage manifest](exams/nonessay-v1-coverage.json) lists every item ID and
point total by question type for all four papers.

The 15-point essays are excluded from both input and denominator. The essay bank
is absent from the configs. The original 60-point datasets and historical scores
remain intact. A result out of 45 is not a full matura result or evidence of an
official pass. See the [predeclared plan](results/2026-09-27-nonessay-plan.md).

## Input preparation and review

`scripts/exams/build_nonessay.py` provides two explicit paths:

- `derive`: an exact filtered view of a previously reviewed full paper. Original
  question payloads, source texts and absolute image references are retained.
  The original image directories therefore remain an explicit local dependency.
- `reviewed`: build 2025/2026 from geometrically reviewed PDF regions, preserving
  original source images and item IDs. Region specs under `configs/exams/reviews`
  contain coordinates and type mappings; grading specs are separate files.

For May 2025, every relevant source page 4–27 was visually inspected; for May
2026, pages 3–26. All 75 prompts were checked after extraction. A word-boundary
audit found and corrected crops cutting prompt lines, final options, source
captions or biography text. Question crops exclude margin scoring boxes.
P/F statements come from PDF table cells in original row order, with explicit
1/2/3 labels, avoiding interleaved row numbers and answer columns. Figures remain
original pixel crops. This is assistant review, not independent expert review.

All scored IDs and point maxima match the separate CKE marking records. The
May 2025 paper labels its essay 25, but the downloaded marking guide labels the
essay 26 and repeats that heading. The grading spec explicitly excludes 26;
all non-essay IDs match without renumbering. The builder rejects duplicate
**scored** marking IDs. No essay content is used in this evaluation.
The 2025 marking example for task 12 also swaps the source numbers for the bank
charter and banknote; the required negative answer and historical chronology are
clear. Grading follows those substantive requirements and records the label
anomaly rather than changing the exam inputs.

For 2025 there are six automatically scored closed items worth seven points;
for 2026 there are seven worth seven points. Other answers require rubric review.
Choice answers use exact A–D keys; P/F scoring follows each item’s marking rule
(both statements required for a one-point item; 3/3 gives two points and 2/3 one
point for the three-statement item). No marking text enters solver inputs or RAG.

Raw PDFs, crops, grading text and transformed exam inputs remain local/ignored.
Public [source URLs and hashes](../packages/tasks-data/examples/history-paper-sources.json)
identify the exam files. The marking PDFs and existing rubric-only extracted
texts are explicit local dependencies, pinned in each `*-grading.json`; this
repository does not distribute them. Review specs and provenance do not grant
a redistribution licence for exam source materials.

## Build the views

Use Python 3.10+, `pdfplumber`, Pillow, the existing `matura-lab` evaluator and
the [PDF candidate-import workflow](tasks-data.md). The 2023 and 2024 full-paper
inputs must already be present at the paths in the source configs. Use fresh
output directories: the builder refuses to overwrite earlier datasets.

```sh
for YEAR in 2023 2024; do
  python3 scripts/exams/build_nonessay.py --runner-root ../matura-lab \
    --output data/processed/history-$YEAR-nonessay-v1 derive \
    --config configs/checkpoints/qwen35-2b-q4-$YEAR-ehistoria-v2.json
done

for YEAR in 2025 2026; do
  python3 scripts/exams/build_nonessay.py --runner-root ../matura-lab \
    --output data/processed/history-$YEAR-may-nonessay-v1 reviewed \
    --spec configs/exams/reviews/history-$YEAR-may-nonessay-v1.json \
    --candidates data/processed/history-$YEAR-may \
    --grading-pdf ../work/history_papers/${YEAR}_key.pdf \
    --grading-text ../work/history_papers/${YEAR}_solutions.txt
done
```

The old candidate datasets remain `needs_review`; the new reviewed views live in
different directories. Downloading or parsing a PDF alone does not activate it
as a reliable scored exam. The [eight additional downloaded pairs](exams/more-history-papers.md)
are still outside this four-paper suite.

## Run and grade

The suite manifest pins one model artifact and all four configs. The frozen
mixed BM25 corpus still has 286 articles / 4,638 passages. One model call per
question, 120 seconds and 2,200 output tokens are local experiment limits, not
confirmed competition limits. No alternative models are started by this suite.

With the pinned local Ollama model server at `127.0.0.1:18081` and 8,192 context:

```sh
python3 scripts/evaluation/nonessay_suite.py prepare \
  --suite configs/evaluation/nonessay-v1.json \
  --output artifacts/nonessay-v1/checkpoints
python3 scripts/evaluation/nonessay_suite.py run \
  --suite configs/evaluation/nonessay-v1.json \
  --output artifacts/nonessay-v1/checkpoints
```

Preparation checks complete 45-point coverage and records pinned dependencies.
Runs are sequential; each checks the live artifact digest, then records loaded
model/context after finishing. Completed responses are journalled immediately.
Do not rerun an already started suite directory; preserve it and prepare a new
directory for a fresh attempt. There is no automatic resume or retry selection.

Apply open-answer grades in a separate file using the
[checkpoint grading workflow](checkpoints.md#grade-open-answers-separately), and
write `checkpoint-graded.json` for each paper. Raw answers remain immutable.
Every grade needs a rubric-based reason and reviewer. A prior grade may be reused
only when the question hash, exact answer string and individual rubric content
match, and matching prior grades agree. Missing grades remain unknown.

```sh
python3 scripts/evaluation/nonessay_suite.py report \
  --suite configs/evaluation/nonessay-v1.json \
  --output artifacts/nonessay-v1/checkpoints
```

The aggregate requires all four reports, the same model and full non-essay
coverage. It uses graded reports when present, otherwise shows pending bounds.
It withholds a percentage until every answer has run and grading is complete.
Per-paper and per-type points remain visible; there is no selection of winners
from different configurations. General checkpoint reports call their configured
scope “full exam”; here that scope is explicitly the **45-point non-essay view**.
