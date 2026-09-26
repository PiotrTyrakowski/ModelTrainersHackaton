# Closed-answer formats and essay retrieval — 26 September 2026

Two separately measured changes raised the provisional 2023 development score
from **11/60 to 12/60 to 24/60**. Each checkpoint processed the full 37-item,
60-point paper with the same Qwen3.5:0.8b weights, original images and v4
89-article retrieval corpus. No official passing result is claimed.

| Run | Change | Points / 60 | Valid answers | Model calls | Question time |
|---|---|---:|---:|---:|---:|
| v4 | Previous focused retrieval | 11 | 35/37 | 37 | 150.79 s |
| v5 | Complete closed-answer schemas | 12 | 35/37 | 37 | 155.59 s |
| v6 | Prepared essay route | 24 | 35/37 | 36 | 115.82 s |

## V5: formatting is reliable; reasoning still fails

All seven closed questions returned complete, valid selections. Question 19
gained two points; question 10 lost one. The other successful open-answer strings
were byte-identical to v4. Their existing rubric assessments were retained only
after exact-byte comparison; every reuse is identified in the grading rationale.
Questions 9.3 and 23 still generated truncated JSON and earned zero.

The model chose **F, P, F for all three true/false tasks**, yielding different
scores against their distinct keys. It still selected the wrong match for one
component of 2.2 and the wrong chronology choice for 13.2. Enforcing a schema
does not establish comprehension. The gain is one development run, not a stable
estimate of improvement. No extra inference calls or retries were added.

## V6: the user's exact-return essay idea now runs in the harness

The router recognized the reviewed Cold War topic, matched it lexically to a
prepared question (score 0.6845), and returned its **392-word essay body unchanged**,
prefixed with the incoming topic number 3. It used zero generation calls and zero
embedding calls, taking approximately 0.04 seconds for this question. All other
successful answers were byte-identical to v5.

Local essay review awarded **12/15**: satisfactory, functional arguments for
Korea, Hungary and Taiwan earned 9/12 for history; a clear, sufficiently long
argument earned 3/3 for coherence. The 1962 Cuban crisis is explicitly a comparison
outside the period, not one of the three required 1950s examples. The sources,
preparation notes and exact body are in the [essay bank documentation](../essay-bank.md).

**The assistant prepared and graded this essay. This is not independent grading.**
An examiner could judge argument depth differently; 12–15 is a plausible review
range if the arguments are considered richer, not a statistical interval. The
reported score uses 12, not the most generous possibility. Earlier questionable
awards on 4.1 and 5.2 remain; removing those two yields 22/60 instead of 24/60.
Other judgment calls may exist.

The bank contains one topic selected after inspecting this public practice paper.
The routing guard currently accepts one reviewed wording, with only case and
whitespace differences. New scope, negation, requirements or task-specific exhibits
cause `no_match`, followed by the ordinary model. This result measures a narrow
prepared-data mechanism; it does **not** show general essay ability or performance
on unseen exam topics. Dense embeddings were not used.

## Reproduction and checks

Use the v5/v6 configurations and [checkpoint workflow](../checkpoints.md).
V6 additionally pins the bank, reviewed scope catalog and imported package code.
Runtime weights and Metal loading were verified. V6 used bundled Python 3.12.14
because the system's Python 3.9 cannot import the existing package (requires 3.10+).
This host-runtime change is recorded; the model server and inference settings were
unchanged. Cache warming and host conditions affect elapsed time: the total time
difference cannot all be attributed to the essay route.

The checkpoint tests pass 35 cases and the data package passes 30. New checks
cover all required answer slots, invalid choices, repeated matching values,
schema restoration, original image preservation, exact essay bytes, incoming
topic numbering, wrong scope/negation, source-specific tasks, ambiguity, length,
offline matching and fallback. Initial test execution with Python 3.9 failed on
the existing package's type annotations; the supported interpreter passed.

Machine-readable results: [v5](2026-09-26-qwen35-typed-bm25-v5.json) and
[v6](2026-09-26-qwen35-essay-bank-v6.json). Full raw outputs and separate grading
records remain in the corresponding ignored `artifacts/checkpoints/` folders.
No paid inference was used.
