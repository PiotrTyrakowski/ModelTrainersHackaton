# Four-paper non-essay baseline, declared before inference

User request: exclude essays temporarily, add more active exams, run only 2B Q4.
The change is evaluation scope and breadth, not a new solver. Freeze the mixed
Wikipedia/e-Historia corpus, BM25 query policy, typed-answer prompt, image support,
one-call budget (120 seconds / 2,200 output tokens) and 8,192-token local context.
Remove the essay-bank route. Do not run other model sizes or quantizations.

| Development paper | Non-essay items | Maximum |
|---|---:|---:|
| 2023 practice | 36 | 45 |
| May 2024 | 39 | 45 |
| May 2025 | 37 | 45 |
| May 2026 | 38 | 45 |
| Total | 150 | 180 |

The 2023/2024 inputs are exact filtered views of the previous reviewed payloads.
The 2025/2026 inputs have now been reviewed against all relevant source pages,
including visual sources, table order and crop boundaries. Marking guides and
closed-answer keys are separate grading inputs. Both new papers were previously
downloaded/extracted and inspected; they are development data, not holdouts.
June 2026 is not opened or included in this suite.

Pin official Ollama artifact `qwen3.5:2b-q4_K_M`, manifest
`124a03c347777e8e4e5955c33610ae01d9d90d8c2a718bfba069c498d5c7f3c9`;
learned-file bytes 1,945,311,744. Record live identity before each paper and loaded
context after it. Preserve raw responses. Grade successful open answers against
the CKE rubrics, with reasons; incomplete grading remains pending, not zero.

Report every declared paper and question type, closed/manual points, runtime and
failures. This is a non-essay research score, not a full matura score or official
pass. The earlier Q4 non-essay components were 18/45 (2023) and 8/45 (2024);
removing essays must not itself be presented as a model improvement. New runs
may vary. Local rubric review is provisional and not independent.
