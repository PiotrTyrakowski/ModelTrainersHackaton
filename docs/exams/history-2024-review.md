# Reviewed second development paper: May 2024

The 2024 extended history paper has 40 separately scored items worth 60 points.
It is a different paper from the repeatedly used 2023 development exam. Its topics
had already been audited during development; it is not an untouched holdout.

The reviewed adapter retains every item, all original sources and the three essay
options. Thirty items have source images (20 distinct crops). The original exam
PDF is pinned to SHA-256
`a5f95323ad82f0b44b8c5e1c16fbc89d56dfe60db77ee4f583b76a669eb02ead`.

All relevant pages 4–29 were visually inspected against the candidate extraction.
The review removed trailing page furniture, answer-writing spaces and accidental
cross-question fragments: the French genealogy had spilled into task 12 and the
1649 engraving date into task 14. It restored the two poetry-column labels and
transcribed visible genealogy years and cartoon captions. Original figures are
cropped from rendered exam pages, preserving pixels and labels; no marking-guide
images are supplied to the model. Final crops and all 40 prompts were inspected.

The source files and transformed exam remain local and ignored. The committed
builder records crop coordinates, hashes, scope/type mapping, and review notes.
These establish input integrity, not historical competence or independent review.

## Reproduce

Use Python 3.10+ with Pillow and the existing explicit `matura-lab` dependency.
First import the public PDF into `data/processed/history-2024-may` using the
[task-data workflow](../tasks-data.md) and
[pinned paper source list](../../packages/tasks-data/examples/history-paper-sources.json).
Keep the corresponding CKE marking PDF and its extracted text separately. The
builder accepts the full extracted marking text or the existing rubric-only
`2024_solutions.txt`; all 40 IDs and point maxima must match.

```sh
python3 scripts/exams/prepare_history_2024.py \
  --candidates data/processed/history-2024-may \
  --grading-text ../work/history_papers/2024_solutions.txt \
  --grading-pdf ../work/history_papers/2024_key.pdf \
  --runner-root ../matura-lab \
  --output data/processed/history-2024-reviewed-v1
```

Use a new output directory on each rebuild. The script does not overwrite the
candidate data. Grading records are written only after the question inputs are
complete. The five automatically graded closed tasks total seven points; matching,
other open answers and the essay require separate rubric review. No answer key
or marking example is included in solver prompts or the retrieval corpus.

The measured configuration `configs/checkpoints/qwen35-2024-transfer-v1.json`
freezes the v6 model, corpus, prompts and essay bank. It runs both direct and BM25
on the full paper; the essay bank has no compatible 2024 topic. Prepare with an
absolute config path and `--variants direct bm25`. Report each system separately.
Do not select the best answer per question and present that artificial total as
a run. Cross-year scores compare coverage; they are not paired improvement deltas.
