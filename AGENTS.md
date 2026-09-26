# Research objective

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
disputed points. It is the latest retrieval comparison, while concise direct
remains the technically reliable reference. Preserve this distinction.

No official passing threshold is confirmed. Label any chosen threshold as an
experimental target and all local rubric grades as provisional. If the runtime
is unavailable, report the blocker; never substitute demo results or claim an
unperformed run. Documentation-only edits do not require another inference run.

Use the available local runtime by default. The user has not authorized charges,
credit-card entry, subscriptions, or paid resources. Do not interrupt a GPU
session owned by another team member.
