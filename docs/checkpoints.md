# Smallest-model exam checkpoints

Measure a tiny model on a fixed paper before expanding the system. After a meaningful change, rerun the same paper and compare points by question type. The first candidate is the image-capable `qwen3.5:0.8b`; its pinned learned files total **1,036,034,688 bytes**. This is a candidate, not a demonstrated passing model or a claim that no smaller model can work.

The wrapper uses the existing `matura-lab` evaluator as an explicit local dependency. It does not vendor that evaluator: provide its checkout using `--runner-root`. The essay route imports the repository's `tasks-data` package directly. Use Python 3.10 or newer; the macOS system Python 3.9 cannot import this package. The checkpoint wrapper needs no external Python libraries.

## Prepare and run

Run these commands from this repository, with the existing evaluator at `../matura-lab`. A model server must already be running and independently verified to serve the pinned weights. Preparation is offline; `run` sends exam questions and images to the configured server.

```sh
python3 scripts/checkpoints/checkpoint.py prepare \
  --runner-root ../matura-lab \
  --config configs/tiny-qwen35-full.json \
  --output artifacts/checkpoints/qwen35-direct-local-v1 \
  --variants direct \
  --base-url http://127.0.0.1:18081/v1 \
  --runtime-label 'local macOS arm64 / Apple M5 Metal / Ollama 0.34.4' \
  --note 'First full-paper tiny-model baseline; provisional grading'

python3 scripts/checkpoints/checkpoint.py run \
  artifacts/checkpoints/qwen35-direct-local-v1
```

The full configuration selects 37 questions worth 60 points, including questions with images and the essay. Input coverage means the questions are supplied to the solver; it does not prove that the model can solve each type. The default wrapper selection is `direct` only. Select `--variants direct bm25` explicitly to compare implementations, with the required corpus available.

The preparation snapshot hashes the source and effective configuration, all evaluator Python/module files, these checkpoint scripts, exam inputs, images, coverage contract, answer keys, grading rubrics when available, corpus when used, and verified model inventory. It records selected IDs, question hashes, model identity and learned size. Do not edit pinned files during a run. A changed experiment needs a newly prepared directory. Runtime identity and availability still require a separate operator check; recording a model name cannot prove which weights a server loads.

`--target-points` is optional. Supply `--target-label` with the reason for any explicit experimental target. No threshold is assumed; without one, reports say `target_not_specified`. Even reaching a target is reported as provisional, never as an official competition pass.

## Run artifacts and interrupted runs

Each completed answer is immediately flushed to `answers.partial.jsonl`. A successful run produces `run.json`, `run-state.json`, and `checkpoint-report.json` / `.md`. Original predictions, raw model output, usage, question time and errors remain in `run.json`. The compact checkpoint report includes:

- Earned points and full-paper denominator, plus a score range for unresolved grades or planned questions not yet run.
- Per-type totals; separate lists for pending grading, excluded items, abstentions and missing planned items.
- Technical errors, detected format errors, budget overruns and truncated responses.
- Known token counts with unknown-call counts, model bytes and per-question latency statistics.

The wrapper refuses to run a directory that has already started. On interruption, the answer journal remains; no complete-exam result is claimed and automatic resume is not implemented. Prepare a new directory for a fresh run. A process killed without cleanup may leave `run-state.json` as `running`; check the process separately. Selected-but-not-run items and deliberately excluded items are not interchangeable.

Latencies include per-question processing and inference. Model startup and corpus loading are not included in the sum of question times. Missing token usage is unknown, not zero. Reported model-call counts follow the existing evaluator; separate embedding requests may not supply token usage. These local budgets are experiment settings, not evidence of an organiser runtime limit.

## Grade open answers separately

The existing 2023 keys automatically score only seven closed questions worth 11 points. Other successful answers need grading against the separate official rubrics. They remain pending until graded. Keep answer keys and rubrics outside the solver context.

Create a JSONL grades file with one record per question and variant. This is a format example, not a grade for a real answer:

```json
{"question_id":"EXAMPLE_ID","variant":"direct","points":0,"reason":"Explain the rubric-based decision.","grader":"Reviewer name or version"}
```

Use absolute paths when invoking the evaluator from another directory:

```sh
# From the legacy matura-lab directory:
python3 -m matura_lab.cli grade \
  /absolute/checkpoint/run.json /absolute/grades.jsonl \
  --output /absolute/checkpoint/run-graded.json

# From this repository:
python3 scripts/checkpoints/checkpoint.py report /absolute/checkpoint \
  --run-report /absolute/checkpoint/run-graded.json \
  --output /absolute/checkpoint/checkpoint-graded.json
```

Never overwrite the raw `run.json`. Regrading can change only points, grading rationale and grader metadata; the wrapper rejects changes to predictions or execution metadata. Store each report with a fresh output name. The wrapper checks grade ranges and provenance consistency, but cannot judge the correctness of a human assessment.

## Compare the next checkpoint

For the next completed, graded experiment, add:

```sh
python3 scripts/checkpoints/checkpoint.py report /absolute/next-checkpoint \
  --run-report /absolute/next-checkpoint/run-graded.json \
  --previous /absolute/previous-checkpoint/checkpoint-graded.json \
  --output /absolute/next-checkpoint/checkpoint-graded.json
```

Comparisons require the same exam, question inputs, keys, rubric and full-paper maximum. Changed model, configuration, dependencies and execution environment are flagged. Comparisons are paired by variant name. Full-exam score deltas require both reports to cover and grade the entire paper; otherwise only common graded-item deltas are shown. Those partial deltas are not an overall improvement claim. Use the same grading standard and review borderline answers consistently.

To compare different variants explicitly, set `comparison_variant_map` in the
prepared configuration, for example `{"bm25": "direct"}`. The report then pairs
the new `bm25` answers with the preceding checkpoint's `direct` answers by
question ID, and records both variant names. Invalid mappings are rejected.

## Concise answer and retrieval experiments

`configs/checkpoints/qwen35-concise-v2.json` selects `concise_answer_v2`. It uses
a shorter Polish prompt and a JSON schema containing only a string `answer`.
The complete justification belongs in that string; there is no separate model
generated evidence list. The prompt requests up to 100 words for short open
answers, item labels for closed tasks, and exactly one 300–350-word essay topic.
These length instructions are soft constraints, not guaranteed limits.

The explicit adapter in `scripts/checkpoints/answer_contract.py` temporarily
replaces the legacy direct/BM25 functions only for that named contract, restores
them afterward, and leaves the legacy evaluator files unchanged. It supports
only `direct` and `bm25`, and requires the matching answer-only response schema.
Both strategies use the same prompt builder. BM25 adds the existing retriever's
top three corpus passages and stores those actual passages in the answer trace;
it does not ask the model to invent citations. No answer keys or rubrics enter
that prompt builder.

Use an absolute config path when preparing: relative config paths resolve
against `--runner-root`. For example, from this repository:

```sh
python3 scripts/checkpoints/checkpoint.py prepare \
  --runner-root ../matura-lab \
  --config "$PWD/configs/checkpoints/qwen35-concise-v2.json" \
  --output artifacts/checkpoints/my-concise-direct-run --variants direct \
  --runtime-label 'record the verified local runtime here'
```

For the retrieval-only comparison, use
`configs/checkpoints/qwen35-concise-bm25-v2.json` and `--variants bm25`. Its
20-article Wikipedia corpus is a development pilot, not general history
coverage. Model weights, question inputs, scoring rules, temperature, one-call
budget and 2,200-token output cap are unchanged between these experiments.

The subsequent corpus comparison uses
`configs/checkpoints/qwen35-concise-bm25-v3.json` with `--variants bm25` and pairs
against the v2 BM25 graded report. Build its separate local index using the
[retrieval instructions](retrieval.md). It changes only the corpus (coverage and
passage representation), retaining the search algorithm and inference settings.
The [measured result](results/2026-09-26-retrieval-corpus-v3.md) is provisional
9/60 with five truncated answers.

The subsequent search-policy comparison uses
`configs/checkpoints/qwen35-focused-bm25-v4.json` and `--variants bm25`, paired
against the v3 graded report. The corpus, answer prompt and model are unchanged.
Its explicit `focused_bm25_v1` policy is described in
[focused retrieval](retrieval/focused-search.md). The measured result is a
provisional [11/60 with two truncated answers](results/2026-09-26-focused-retrieval-v4.md).

After the first baseline, fix the largest measured loss of points: malformed answers, missed parts of an instruction, missing evidence, weak image interpretation or the essay. Change one factor at a time. Compare retrieval and deterministic tools on the same paper before trying a smaller model or more aggressive quantisation. Keep every learned component in the size accounting. The papers already inspected during development are not untouched final evaluation data.

## Complete closed answers and prepared essays

`configs/checkpoints/qwen35-typed-bm25-v5.json` selects `typed_answer_v3`.
For reviewed closed tasks, the response schema requires every slot and restricts
its value to the choices in the question metadata. A deterministic renderer then
returns a plain answer string. It permits repeated matching values, retains the
original images, and restores the ordinary schema after each call, even on failure.
Unknown layouts and tasks explicitly requesting an explanation retain the free-text
contract. These constraints guarantee neither historical correctness nor adherence
by every possible provider; returned values are validated locally too.

`configs/checkpoints/qwen35-essay-bank-v6.json` adds the
[reviewed essay route](essay-bank.md#measured-harness-integration).
The checkpoint snapshot additionally hashes the bank, reviewed scope catalog and
all Python files in the imported `tasks-data` package. Matched essays need no
generation or embedding call. Their unchanged body hash, selected topic, match
attempts and word count are recorded. All other questions use v5 behavior.

Prepare either configuration using an absolute path and `--variants bm25`.
Both retain the v4 corpus, tiny model and inference budget. Grading stays separate
from inference. A prepared essay selected for an already inspected practice topic
is development data, not evidence of generalization.

## Offline verification

```sh
python3 -m unittest discover -s tests/checkpoints -v
```

Tests use synthetic reports and an interrupted evaluator stub. They exercise pending-score accounting, full-paper denominators, missing versus excluded items, invalid scores/identities, failure categories, partial comparisons, dependency changes, immutable predictions and journaling. These tests make no inference calls and establish software behavior, not exam performance.
