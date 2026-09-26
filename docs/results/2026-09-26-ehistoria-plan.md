# e-Historia corpus experiment: declared before inference

Change only the retrieval corpus: retain all 89 Wikipedia articles / 3,060
passages and add the four classes linked by the user-selected
[extended-history repetytorium](https://e-historia.com.pl/liceum-i-technikum/notatki-z-historii-zakres-rozszerzony/repetytorium-z-historii-zakres-rozszerzony.html).
Acquisition follows category links, independently of exam answer keys. Preserve
chapter/section context, short dates and definitions. Generate no additional
historical claims. This tests adding this source together with its extraction
format, not the effect of any single lesson or paragraph size.

Hypothesis: curriculum summaries improve factual identification, dates,
institutions and evidence-based short answers. More text could also add unrelated
retrieval; improvements are not assumed. Image-only information remains outside
text retrieval.

Run the unchanged focused_bm25_v1 / typed_answer_v3 harness with the unchanged
essay bank on both fixed full development papers (2023 and 2024), first with the
0.8B reference and then 2B. Freeze all four configurations before inference.
Compare each BM25 cell with its same-model/same-paper comparison-v1 cell. Reuse
the previous direct controls since they do not use this corpus; do not claim
they were rerun. Retain 2B direct as the alternative comparison control.

Record complete points, non-essay points, points by question type, actual
retrieved sources, errors, truncations, tokens and runtime. Grade open answers
separately against the frozen rubrics. Reuse a provisional previous grade only
when question hash, rubric hash and exact answer agree and matching previous
grades do not conflict. Review changed outputs; preserve uncertainty, especially
for essays and borderline explanations. All local grades remain provisional
and are not independent expert grading. No official pass threshold is assumed.

Use already downloaded, hash-verified local Ollama models. No external model
service, payment, training or LLM-based augmentation is part of this experiment.
The public repository retains code, configurations, provenance metadata and
result summaries. Raw third-party text, HTML, search traces and indices stay in
ignored local data directories, with source-specific attribution and rights.
