# Source-preserving history retrieval corpus

The v3 development corpus contains **89 Polish Wikipedia articles and 3,060
passages**, expanding the original 20-article pilot. It targets gaps observed on
the public 2023 practice paper: medieval towns and dynasties, art, nineteenth
century history, and twentieth century treaties and politics. Topic selection
has seen that paper. This is development data, not an untouched evaluation.

The [other-paper coverage audit](retrieval/other-papers-coverage.md) records what
has been imported from 2024–2026, what still needs review, and topic gaps beyond
the 2023 paper. Those other papers have not yet received a full tiny-model run.

Each passage contains an exact article-text span plus its article title and
section heading. Paragraphs stay intact where possible; long ones split at
sentence or word boundaries. Bibliography, notes and navigation sections are
excluded. Nothing generates new historical claims or copies exam answer keys.

Source URLs, contributor-history links, CC BY-SA 4.0 attribution, observed
revision metadata and content hashes accompany the data. The text hash identifies
the actual downloaded extract: MediaWiki's cached extract is not guaranteed to
match its separately reported latest revision. These checks establish provenance
and faithful extraction, not independent factual verification of Wikipedia.

## Build locally

From this repository, with the existing `matura-lab` evaluator and seed corpus
available in the adjacent directory:

```sh
python3 scripts/retrieval/build_corpus.py \
  --topics configs/retrieval/history-topics-v3.json \
  --seed-documents ../matura-lab/data/corpora/wiki-pilot/documents.jsonl \
  --output data/raw/retrieval/wiki-focused-v3

python3 scripts/retrieval/build_index.py \
  --runner-root ../matura-lab \
  --corpus-directory data/raw/retrieval/wiki-focused-v3 \
  --output data/raw/retrieval/wiki-focused-v3/index.sqlite
```

The downloader saves after each article and resumes completed titles. It rejects
missing or ambiguous pages, and stops on HTTP or network failures; observe any
recorded `Retry-After` before retrying. Use `--offline` to rebuild passages from
saved articles. The indexer requires a fresh output path and complete acquisition,
checks all content hashes, source spans and canonical-title uniqueness, then
verifies that each indexed passage matches its source. It prevents additional
character-based splitting by the legacy indexer.

The build requires the original seed file to reproduce this corpus; topic titles
alone describe only the expansion. Live downloads may change. Retain the ignored
raw snapshot to reproduce the exact experiment. The public
[manifest and article catalogue](retrieval/wiki-focused-v3.manifest.json) records
the observed snapshot without committing the full article texts.

## Measure usefulness

Use `configs/checkpoints/qwen35-concise-bm25-v3.json` with the
[checkpoint workflow](checkpoints.md). It keeps the model, concise prompt, top-three
BM25 search and inference budget unchanged. Coverage and passage representation
change together, so the result cannot separate their individual effects.

The initial retrieval inspection already shows a remaining limitation: relevant
material for Crécy and Ostrołęka now appears among the top results, but generic
question wording can still retrieve unrelated periods. Queries use the first 80
distinct tokens of the question followed by source text. Longer questions can
therefore exclude useful source terms. Image-only information cannot guide this
text search. More articles alone do not solve these query failures.

Keep grading keys and rubrics outside this corpus. Save actual retrieved passages
with model responses, assess complete exam points, and later confirm improvements
on an untouched paper. Do not select per-question winners from the development
paper and claim their combined score as a measured system.
