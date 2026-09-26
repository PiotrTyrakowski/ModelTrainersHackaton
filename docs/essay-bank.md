# Retrieve a complete essay without generating one during the exam

This implements the original strategy: prepare pairs of **question y → essay z**, compare incoming **question x** with stored questions, and return the selected **z unchanged**. The bank contains complete essays, not outlines. It never calls a text-generation endpoint, adds a preface, combines essays or rewrites a conclusion.

There are two interchangeable matchers:

| Matcher | Comparison | Learned model needed when answering? |
|---|---|---|
| `lexical` | Word and character features, TF–IDF-style cosine similarity | No; standard-library Python only |
| `dense` | Cosine similarity between question embeddings | An embedding encoder, unless the query vector is already supplied |

An embedding encoder is still a model. Dense retrieval has no generative model call, but should not be described as completely model-free. The lexical path makes no network calls. Neither path starts compute or creates service accounts.

## Run the local example

From the repository root, after installing the package:

```sh
tasks-data essay-match \
  packages/tasks-data/examples/essay-bank.jsonl \
  packages/tasks-data/examples/essay-query.json \
  --output artifacts/essay-demo/trace.json \
  --essay-output artifacts/essay-demo/answer.txt
```

Without installation, prefix the arguments with `PYTHONPATH=packages/tasks-data/src python3 -m tasks_data.cli` in place of `tasks-data`.

The example selects `demo-1791-ustroj`. `answer.txt` contains the exact UTF-8 encoding of that record's essay, including its paragraph breaks. `trace.json` reports the method, selected ID, similarity, rejected candidates and call counts. CLI output paths must be new; use a different directory for each run.

The bank includes two complete Polish essays of 364 and 390 whitespace-separated words about different aspects of the Constitution of 3 May. These are **Codex-authored demonstration drafts prepared offline**, with primary-source links in each record. They are not official answers, independently marked essays or a large enough bank to cover an exam. No score or passing result is claimed.

The deliberate period mismatch example returns `no_match`, exits with code 2 and creates no essay file:

```sh
tasks-data essay-match \
  packages/tasks-data/examples/essay-bank.jsonl \
  packages/tasks-data/examples/essay-query-no-match.json \
  --output artifacts/essay-no-match/trace.json \
  --essay-output artifacts/essay-no-match/answer.txt
```

## Bank and query formats

The bank is UTF-8 JSONL: one object per line with required `id`, `question` and `essay` strings. An essay containing newlines uses JSON `\n` escapes on that line. Additional fields:

- `scope`: optional `start_year` and `end_year` together, `entities`, `aspects`, and `intent`.
- `sources`: links or source identifiers used when preparing the essay.
- `preparation`: author/model/revision, preparation method, review state and other provenance. This is descriptive metadata, not a quality certificate.

The query is one JSON object with required `question`, optional `scope` in the same format, and optional `min_words` (default 0). Specify the actual task's minimum explicitly, for example 300. Word counts currently use whitespace splitting and are not an official exam counting algorithm.

Use the same controlled labels for scope in the bank and query. If requested, period endpoints must match exactly, the stored metadata must include every required entity/aspect, and the intent must match. Unknown stored scope does not satisfy an explicit requirement. Negative years denote BCE; there is no year zero.

**Scope is supplied by the caller; the matcher does not extract it automatically from prose.** If a requirement is omitted, it is not checked. Metadata asserts coverage but does not prove the essay actually contains the required argument. Source-image interpretation and references to task-specific exhibits also need separate handling. A high similarity can still retrieve a wrong answer, especially for negations, a different thesis or different requested evidence.

After filtering incompatible entries, the matcher rejects scores below a threshold and close ties. Defaults are `--min-score 0.3` for lexical, `0.7` for dense, and `--min-margin 0.03`. These are starting heuristics, not calibrated confidence probabilities. Tune separately for each encoder/matcher on held-out questions. Identical top scores always abstain, even with margin zero.

## Semantic retrieval with an existing embedding service

The optional adapter accepts an HTTP API with `POST /embeddings`, a JSON `{model, input, encoding_format: "float"}` request and a `{data: [{index, embedding}]}` response. Configure a compatible service you already have. There is no included hosted account or downloaded encoder. Remote services require HTTPS; local HTTP through `localhost`, `127.0.0.1` or `::1` is supported.

For a local server exposing this API at port 8080 (replace `YOUR_EMBEDDING_MODEL` and its revision):

```sh
tasks-data essay-index packages/tasks-data/examples/essay-bank.jsonl \
  --embedding-url http://127.0.0.1:8080/v1 \
  --embedding-model YOUR_EMBEDDING_MODEL \
  --embedding-revision YOUR_FIXED_REVISION \
  --output artifacts/essay-vectors/index.json

tasks-data essay-match \
  packages/tasks-data/examples/essay-bank.jsonl \
  packages/tasks-data/examples/essay-query.json \
  --method dense --index artifacts/essay-vectors/index.json \
  --embedding-url http://127.0.0.1:8080/v1 \
  --embedding-model YOUR_EMBEDDING_MODEL \
  --embedding-revision YOUR_FIXED_REVISION \
  --output artifacts/essay-dense/trace.json \
  --essay-output artifacts/essay-dense/answer.txt
```

If authentication is needed, set the service key outside this repository and pass only its environment-variable name with `--api-key-env EMBEDDING_API_KEY`. Never put keys in bank records, examples or command-line URL parameters.

Models requiring task prefixes can use `--query-prefix` and `--document-prefix`. These, the URL, model and declared revision form the encoder identity. Indexing embeds **stored questions**, not essay bodies. Matching embeds the incoming question once. The index stores question hashes and rejects a changed bank or encoder configuration. The configured revision is a caller assertion; the adapter cannot verify which weights a remote service actually serves. Pin the service and record its provenance when comparing results.

For competition execution, keep the bank and any encoder local. The currently published [hackathon rules](https://warsawmodeltrainers.dev/rules) prohibit internet use during the final exam. Remote embedding services are a development option, not an exam deployment plan. This module does not establish prize eligibility for a system with no base model.

Alternatively, use `--query-vector vector.json`, where the JSON contains exactly `encoder_id` and `vector`. The vector must come from the same encoder configuration as the index. This avoids a live embedding request; it does not remove the earlier cost or model use needed to create the vector.

The returned `embedding_calls` counts calls to the embedder interface during **matching** (0 or 1), not bank preparation, HTTP batches, or external preparation costs. `generation_calls` is always 0. Preparation of the bundled essays used Codex and is not model-free.

## Python integration

```python
from tasks_data.essay_bank import EssayBank, EssayQuery

bank = EssayBank.from_jsonl("my-bank.jsonl")
result = bank.match(EssayQuery(question=incoming_exam_question), method="lexical")
if result.status == "matched":
    answer = result.essay  # return this exact string to your existing harness
else:
    answer = None         # explicit abstention; let the caller choose a fallback
```

Pass `EssayScope` and `min_words` when the caller knows the task requirements. The CLI does not submit answers to the competition. The checkpoint adapter below explicitly connects this module to the experimental harness.

## Compare implementations honestly

Use the same bank, unseen query set and grading procedure for lexical and dense runs. Include compatible paraphrases plus close but incompatible questions: wrong period, entity, aspect, intent, negation or required source. Measure selection precision, answer coverage, no-match rate, essay points and latency separately. Selecting a bank entry is not the same as earning points for its essay.

Keep preparation essays separate from evaluation answers. Do not populate a bank from hidden benchmark answers. These public demonstration topics and already inspected development papers cannot serve as an untouched final test set.

Current verification covers exact bytes, Polish text, ambiguity, explicit scope and length exclusions, no-network lexical matching, index freshness, encoder identity, invalid vectors and HTTP response validation. Dense tests use deterministic vectors and mocked HTTP responses. **No live encoder benchmark or official essay grading has been run.** Local rubric grading is described with each measured checkpoint.

## Measured harness integration

The opt-in `reviewed_essay_v1` adapter is in
`scripts/checkpoints/essay_routing.py`, configured by
`configs/checkpoints/qwen35-essay-bank-v6.json`. It uses the existing lexical
matcher, with no additional learned model or online service:

1. Split the supplied numbered topic options and validate their labels.
2. Require a reviewed general instruction and a reviewed topic wording to obtain
   trusted scope. Whitespace and case may differ; new wording is not inferred.
3. Filter the bank by period, entities, required aspects, intent and word minimum,
   then rank stored questions by lexical similarity. Low or ambiguous matches abstain.
4. Prefix the chosen **incoming** topic number and return the essay body unchanged.
5. On `no_match`, use the ordinary tiny-model essay solver and record the reason.

Tasks with source text or images always abstain because the prepared essay has
not interpreted those exhibits. A changed century, negation, event count, general
instruction or insufficient essay length also abstains. Scope and factual quality
depend on preparation review; similarity is not proof that an essay answers a task.

The initial [bank](../data/essay-bank/history-development-v1.jsonl) contains one
original 392-word Polish essay on the Cold War in the 1950s, with sources and
fact-review notes. Its [readable body](../data/essay-bank/cold-war-1950s.txt) is
mirrored in the JSONL record; inference reads the JSONL file. The
[catalog](../data/essay-bank/reviewed-topics-v1.json) records the reviewed input
wording and scope, not a marking key. Body preparation used Codex and these
historical sources: [Korea](https://history.state.gov/milestones/1945-1952/korean-war),
[Hungary](https://history.state.gov/countries/hungary), a
[1956 diplomatic telegram](https://history.state.gov/historicaldocuments/frus1955-57v25/d158),
[Taiwan](https://history.state.gov/milestones/1953-1960/taiwan-strait-crises), and
[Cuba](https://www.archives.gov/news/topics/cuban-missile-crisis).
The argument assessing the decade is original synthesis. Source review and essay
grading by the same assistant are not independent validation.

This is deliberately narrow: **one covered topic, one reviewed wording**, chosen
after seeing a public development question. It demonstrates the exact-return
route, not a general essay solver or success on unseen topics. The module's dense
embedding option remains available for later experiments; this run does not use it.
Expanding the catalog requires reviewing new requirements, preparing compatible
essays and testing close but incompatible prompts. More essays alone do not prove
coverage or eliminate this requirement.
