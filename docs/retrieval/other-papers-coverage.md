# Coverage audit across other matura papers

**Later update, 26 September:** the 2024 paper now has a separately reviewed
40-item input package and two complete tiny-model runs: 8/60 direct and 9/60 with
retrieval, both provisional. See the [second-paper results](../results/2026-09-26-2024-transfer.md).
The original candidate datasets remain unchanged; 2025 and 2026 still await full
input review and evaluation. The table below records the earlier audit state.

Checked on 26 September 2026 against the saved question extracts, imported task
manifests and the 89-article v3 retrieval corpus. This is a preliminary topic
audit, not a completed review of all source images, task boundaries or answers.
No solver input, retrieval index or model was changed, so no new inference run
is reported.

## What has actually been checked

| Paper | Imported records | Ready for evaluation in tasks-data | Full tiny-Qwen run |
|---|---:|---:|---|
| 2023 structured practice paper | 37 | 37; grading maintained in the separate evaluator | Yes |
| May 2024 | 40 candidates | 0; all need review and grading attachment | No |
| May 2025 | 38 candidates | 0; all need review and grading attachment | No |
| May 2026 | 39 candidates | 0; all need review and grading attachment | No |

The three later papers total 117 candidates. Their raw PDFs, page images and text
are retained locally. Marking schemes are also available locally, but their
answers have not been attached to these task datasets. Existing manual grading
placeholders do not contain expected answers.

The v3 corpus expansion was selected primarily from gaps on the 2023 paper.
It should not be described as comprehensive coverage of these other papers.

## Concrete gaps suggested by the other papers

These are topic bundles to investigate, not a complete inventory or verified
Wikipedia article titles. A missing dedicated article does not prove a fact is
absent from all other articles; a passing mention does not establish enough
evidence to answer a question.

| Topic bundle | Question evidence | Current corpus limitation |
|---|---|---|
| Classical architecture and Roman institutions | 2024: 3.2, 4; 2025: 3.1–3.2 | Greek and Roman topics are narrow; architectural coverage concentrates on Gothic and Renaissance styles. |
| Medieval society, settlement and land rents | 2024: 6; 2026: 5.1–5.2 | Lubeck urban law is present, but this is not a full collection on estates, rural settlement and obligations. |
| Charlemagne and medieval empire | 2024: essay 26, option 1 | No dedicated article; a preliminary term scan finds only mentions in three other articles. |
| Religious toleration, Polish Brethren and French religious conflict | 2024: 9, 11.2; 2026: 10.1–10.2 | General Reformation coverage exists; specific movements and settlements need evidence checks. |
| Jagiełło and the union at Krewo | 2025: essay 25, option 1; 2026: essay 26, option 1 | No dedicated articles; the union is mentioned in the Commonwealth article. |
| Industrialisation, factory workers and social change | 2025: 13 and essay 25, option 2; 2026: 16.1–16.2 and essay 26, option 2 | No dedicated industrial-revolution collection; scattered mentions are insufficient to establish broad coverage. |
| American Civil War, cotton trade and abolitionism | 2025: 15.1–15.2 | No dedicated article; the initial Polish Civil War term scan found no matches. |
| Soviet economic policies: NEP and collectivisation | 2024: 20.1–20.2 | No dedicated articles; the initial NEP term scan found no matches. |
| Polish independence and war in 1939 | 2024: essay 26, option 3; 2026: essay 26, option 3 | General Second Republic and WWII articles exist; sufficient diplomatic, military and economic evidence has not been established. |
| Communist crises and the transition of 1989 | 2025: 24.1–24.2 and essay 25, option 3 | PRL, Hungary 1956 and Solidarity provide partial coverage; comparison across countries needs a broader evidence check. |

Term scans are discovery aids only. Inflections, synonyms and source extraction
can hide matches. They are not measured recall, a coverage percentage, or proof
that retrieval will return a useful passage.

## Next evaluation work

1. Review the 2024 candidates into a second complete development exam, preserving
   shared source text and the original images. Attach its marking scheme only
   under grading, then verify item IDs and the 60-point denominator.
2. Use the same current tiny model and fixed corpus on that second paper before
   changing retrieval. This supplies an actual cross-paper baseline.
3. Prioritise topic bundles recurring across years, particularly industrialisation,
   medieval institutions and religious/political documents. Add sourced general
   history evidence, not completed exam answers.
4. Measure whether search retrieves relevant evidence separately from whether the
   model uses it correctly. Re-run complete papers after corpus/search changes;
   do not select and combine per-question winners.
5. Reserve a genuinely uninspected paper for later confirmation. The 2024–2026
   papers have already informed this audit and cannot serve as untouched tests.

Some tasks ask for evidence already present in a text, map, image or table.
External history coverage alone cannot fix failures to read those materials.
Keep source interpretation, factual retrieval and answer completion separately
visible in the error analysis.

Source provenance and file hashes:
[paper source manifest](../../packages/tasks-data/examples/history-paper-sources.json).
Import requirements: [task-data documentation](../tasks-data.md).
