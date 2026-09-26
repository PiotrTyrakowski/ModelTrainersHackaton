# Controlled small-model comparison

Decision: measure whether moving from Qwen3.5 0.8B to Qwen3.5 2B improves
history exam points before expanding retrieval data or adding new solvers.
Expected opportunities are factual identification, source/image interpretation
and following multi-part instructions. Improvement is a hypothesis.

The fixed matrix is two models × two full development papers (2023 and 2024)
× two strategies (`direct`, `bm25`). Both model tags use Q8_0 weights and image
input. Rerun the tiny reference rather than silently replacing it. Record all
eight cells, including failures, without choosing a winning answer per item.

Both strategies share the v6 typed-answer contract and prepared essay bank.
`direct` means no Wikipedia retrieval, **not a bare model**: its 2023 essay can
also come from the bank. `bm25` adds the unchanged focused retrieval policy and
89-article / 3,060-passage corpus. Keep the question inputs, original images,
bank, prompts, answer schemas and budgets fixed. Do not expand the bank during
this experiment.

Use the existing free local Ollama 0.34.4 runtime, Apple M5 Metal, 8,192-token
context, temperature 0, disabled thinking, one generation call per question,
2,200 output tokens and 120 seconds per question. Matched stored essays use
zero generation calls. Models run sequentially, with at most one loaded model.
Pin manifest and weight hashes; capture runtime identity before each paper and
loaded-model memory afterward. No paid provider or account is needed.

Grade after generation using the separate CKE keys and rubrics. Reuse an
earlier open-answer grade only when the question and answer bytes match and the
rubric is unchanged; record that reuse explicitly. Review new answers against
the same standards. Preserve raw outputs and make grading decisions auditable.
Report disputed awards separately. The same assistant reviews open answers, so
these grades remain provisional and are not an independent evaluation.

Report totals out of 60, non-essay points out of 45, essay points out of 15,
per-type points, failures, calls, token usage, learned model bytes and elapsed
question time. Separate the fixed stored-essay contribution from model gains.
Report timing descriptively: single runs with changing cache and thermal state
are not a rigorous speed benchmark. Flag any runtime interference.

Both papers have been inspected during development. Same-paper comparisons
support the next engineering decision; they do not establish unseen-paper
performance or an official competition pass. No passing threshold is assumed.
