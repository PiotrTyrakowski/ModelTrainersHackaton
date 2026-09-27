# Research objective

Current user override (27 September 2026, harness of models): find the
**smallest system that passes the history matura** (extended level, formula
2023, 60 points; pass = 35% = 21/60 including the essay). Essays are never
generated: prepared essays from `data/essay-bank/v2` are submitted unchanged and
the model only chooses one. Fine-tuning, several models and any quantization
are allowed. The selected system is `scripts/harness/run_system.sh`: fine-tuned
Qwen3.5-4B IQ2_M plus the Q8_0 vision projector, 2,126,891,136 learned bytes
(GGUFs in `artifacts/harness/gguf`, rebuilt by `scripts/harness/build_model.sh`).
One frozen run on the June 2026 paper scored a provisional 27–28/60, so June
2026 is no longer an untouched holdout. Identical development runs differ by up
to 4 points per paper; see `docs/results/2026-09-27-harness-of-models.md`.
The 2B-only override below is superseded for this goal; keep it and all
historical results unchanged. Do not commit `data/sft/` (CKE items and
e-Historia-derived context); rebuild it with `scripts/harness/build_sft.py`.

Previous user override (27 September 2026): **run only Qwen3.5 2B Q4_K_M**.
Temporarily exclude essays and the essay bank. Use the complete non-essay suite
in `configs/evaluation/nonessay-v1.json`: 2023 and May 2024–2026, 150 items,
180 points (45 per paper). This replaces the earlier tiny-model/full-paper run
instructions below for current experiments. Keep historical results unchanged.
Use `scripts/evaluation/nonessay_suite.py`; see `docs/nonessay-evaluation.md`.
Question coverage is expanded to four development papers; none is an untouched
holdout. June 2026 remains reserved. Do not run 0.8B or Q8 as extra controls.
The completed baseline scored 18/45, 8/45, 7/45 and 7/45 respectively: 40/180.
All 150 items ran; three answers truncated into invalid JSON. Grades are local
and provisional, with selected sensitivity documented in
`docs/results/2026-09-27-nonessay-baseline.md`. The old two-paper non-essay
responses/scores reproduced; new papers expose more source-confusion and visual
errors. The next proposed single change is stricter source-grounded retrieval
with fallback; it has not yet been implemented or measured.

The remaining notes below document historical experiments and decisions.

The objective is a small system that earns enough exam points to reach our
explicit research target. Data generation supports that objective; dataset size
is not the success metric.

For every meaningful solver, retrieval, prompt, model, or data checkpoint:

1. State the single change and the question types it should improve.
2. Run the tiny reference model on the fixed full practice paper using
   `scripts/checkpoints/checkpoint.py` and the workflow in `docs/checkpoints.md`.
3. Grade successful open answers against the separate rubrics. Keep raw answers
   immutable, record the grader and reasons, and leave unresolved grades pending.
4. Compare exam points, points by type, errors, model size and runtime with the
   preceding compatible checkpoint. Software tests are not an exam result.
5. Choose the next change from measured errors. Expand data only when it addresses
   an identified gap. A subset diagnostic is useful but is not a full checkpoint.

Use `qwen3.5:0.8b` as the initial reference. Record any model change explicitly;
do not silently replace the baseline with a larger model. Keep exam answer keys
and marking rubrics out of solver prompts and retrieval corpora. Repeatedly used
practice papers are development data, so success on them needs later confirmation
on an untouched paper.

The current working answer contract is `concise_answer_v2`: prepare with an
absolute path to `configs/checkpoints/qwen35-concise-v2.json` and select `direct`.
It scored a provisional 6/60 with zero truncated answers. The BM25 pilot's 7/60
depends on disputed grading and has four truncated answers; it is experimental,
not the selected default. The subsequent `qwen35-concise-bm25-v3.json` corpus
experiment reached a provisional 9/60 with five truncated answers and two
disputed points. The latest `qwen35-focused-bm25-v4.json` retrieval-policy change
reached a provisional 11/60 with two truncated answers and two disputed points.
The v5 typed-answer contract scored 12/60; v6 added one prepared development-topic
essay and scored 24/60 (12/15 essay), still with two truncated answers. Use
`qwen35-essay-bank-v6.json` as the current experimental harness, with v5 for its
no-bank comparison and concise direct as the historical control. The essay bank
currently covers one reviewed topic wording, prepared and graded by the same
assistant. Do not present this as generalization or independent essay grading.
Preserve grading uncertainty. Use Python 3.10+ when importing the essay package.

The second full development test uses `qwen35-2024-transfer-v1.json`: 40 questions,
60 points, reviewed inputs. With frozen v6 code/data, direct scored provisional
8/60 and BM25 9/60, with two truncations each; the bank matches no 2024 essay.
This paper had previously been inspected, so it is not untouched holdout data.
Keep both 2023 and 2024 fixed for further comparisons; do not infer general
passing ability from the narrow 2023 essay gain. See `docs/grading.md` for grading
limitations and the result reports for disputed awards.

The controlled model-size comparison reran both full papers with both variants.
The 0.8B reference scored 2023 direct/BM25 19/24 and 2024 direct/BM25 8/9.
Qwen3.5:2b Q8_0 scored 2023 direct/BM25 19/28 and 2024 direct/BM25 16/11.
Here direct excludes Wikipedia but still shares typed answers and the essay bank;
all 2023 cells include the same 12-point stored essay. The 2B artifact has
2,741,180,928 learned-file bytes. Use 2B without Wikipedia as the next experiment's
comparison control while retaining 0.8B as the tiny reference. Do not silently
replace the size objective or combine per-paper winners into a claimed system.
The next proposed single change is stricter retrieval relevance with fallback.
See docs/results/2026-09-26-model-size-comparison.md for disputed grades; the
retrieval gains from changing model are not robust to the selected sensitivity
checks. These remain development results, not a passing or independent evaluation.

The subsequent corpus-only experiment added 197 e-Historia lessons, preserving
the original Wikipedia corpus, for 286 articles / 4,638 passages. Mixed BM25
scored provisional 0.8B 27/12 and 2B Q8 29/12 on 2023/2024. The model-only Q4
comparison then scored 30/8 with 1,945,311,744 learned bytes (29% below 2B Q8).
Q4 is not a demonstrated upgrade. Keep the tiny reference and earlier 2B direct
2024 control; do not choose per-paper winners as a system. All 2023 runs include
the same 12-point stored essay. See the e-Historia and quantization comparison
reports for failures and grading sensitivity. Q4 v1 configs are frozen executed
records with an inherited descriptive Q8_0 label; live weights were verified Q4.
Use Q4 v2 configs for future runs: they correct only that metadata label and have
not themselves been run.

Eight further exam/marking PDF pairs are downloaded but not extracted into
reviewed tasks or automatic answer keys. Keep all marking files out of retrieval.
June 2026 is reserved; only its cover was inspected. Preserve this boundary until
an explicit final evaluation. See docs/exams/more-history-papers.md. Raw
e-Historia pages have no identified open redistribution licence and remain local;
retain author attribution and source hashes, not an assumed Wikipedia licence.

No official passing threshold is confirmed. Label any chosen threshold as an
experimental target and all local rubric grades as provisional. If the runtime
is unavailable, report the blocker; never substitute demo results or claim an
unperformed run. Documentation-only edits do not require another inference run.

Use the available local runtime by default. The user has not authorized charges,
credit-card entry, subscriptions, or paid resources. Do not interrupt a GPU
session owned by another team member.
