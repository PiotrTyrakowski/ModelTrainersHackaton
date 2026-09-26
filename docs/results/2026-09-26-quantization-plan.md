# 2B Q4 versus Q8: declared before Q4 inference

At the user's request, test whether a model larger than 0.8B with more aggressive
weight quantization offers a useful size/score tradeoff. The downloaded official
Ollama `qwen3.5:2b-q4_K_M` artifact reports 2,274,069,824 parameters, the same as
the already tested 2B Q8_0. Its verified learned file is 1,945,311,744 bytes,
versus 2,741,180,928 for Q8_0, a 29.0% reduction. Both include image capabilities.
This is still larger than the 0.8B Q8 artifact (1,036,034,688 bytes).

Change only the model artifact/provenance from the 2B e-Historia Q8 experiment.
Retain both fixed full development papers, mixed corpus, focused retrieval,
typed answers, essay bank, one-call budget, 2,200-token output limit and 8,192-token
context. Run after all Q8 corpus tests finish, with one model loaded at a time.
Keep the completed 0.8B e-Historia runs as the tiny-size reference. No extra tiny
rerun is needed for identical frozen reference settings.

Compare full and non-essay points, per-type points, failures, truncations,
runtime, tokens and learned-file bytes. Grade successful open answers separately
against frozen rubrics; reuse only exact answer/question/rubric matches. Local
grades remain provisional and non-independent, including essays. No pass
threshold is assumed. More parameters or fewer bits do not establish a score
improvement before measurement.

The [official tag catalogue](https://ollama.com/library/qwen3.5/tags) also lists
4B Q4_K_M at about 3.4 GB. That is a possible later candidate; it is not part of
this controlled quantization comparison. No paid service or model training is
used.
