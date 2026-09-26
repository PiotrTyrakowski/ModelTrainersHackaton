# e-Historia repetytorium import

The user-selected [extended-history repetytorium](https://e-historia.com.pl/liceum-i-technikum/notatki-z-historii-zakres-rozszerzony/repetytorium-z-historii-zakres-rozszerzony.html)
adds **197 lessons and 1,578 passages** to the local retrieval corpus. The four
class categories list 198 lessons: 64, 53, 57 and 24 respectively. The published
body of “2. 7. Sprawa Polski pod koniec wojny” is empty, so it contributes no text.
It remains an explicit exclusion in the manifest. Class 4 contributes 23 lessons.
Acquisition completed without unresolved download or parser failures.

The new mixed index contains **286 articles and 4,638 passages**: the previous
89 Wikipedia articles / 3,060 passages remain unchanged. This is the linked
repetytorium's coverage, not a claim to cover the entire history curriculum or
all material elsewhere on the site.

## Extraction and provenance

The importer follows only the four class categories and their lesson links.
It checks robots.txt, fetches sequentially with at least one second between
requests, validates redirect scope and caches responses with URL/content hashes.
Network, unexpected HTML and rate-limit errors stop acquisition. A genuinely
empty published body is recorded separately; it is never completed with guessed
history. Cached responses support offline rebuilding.

Only the article body is extracted. Menu tabs, related-reading links, quiz
promotions and linked PDF-only paragraphs are excluded. Inline text, Polish
diacritics, short dates and definitions are preserved. A coverage check requires
all retained article-body letters and numbers to survive in document order.
Headings define sections; adjacent paragraphs are grouped within a section and
long paragraphs split at sentence/word boundaries, up to 1,300 body characters.
Each passage stores its exact span in the normalized article text, title/section
prefix, hashes, author attribution and source URL. Neither indexer nor importer
uses exam keys or rubrics.

All 197 texts passed extraction coverage and passage-span checks. Representative
lessons from each class were inspected. No inline images or tables appeared in
these downloaded bodies; linked images/PDFs elsewhere are not imported. These
checks verify extraction, not the historical truth of every claim.

No LLM rewrites or supplements the historical content in this version. An LLM
could later produce search aliases or questions, but those should be separate,
explicitly generated fields linked to supporting source spans and evaluated as
a separate change. The current checkpoint still uses lexical focused BM25, not
embeddings. Stored passages can also support a later embedding experiment.

## Rights and files

The site credits [Wiesław Zdziabek](https://e-historia.com.pl/o-projekcie-e-historia---wspolpraca-miedzynarodowa/4-o-autorze.html).
No open redistribution licence was identified for this source. Its records
retain author attribution and that explicit licence status; they do not inherit
Wikipedia's CC BY-SA label. Raw HTML, extracted text, retrieval traces and indices
stay in ignored local directories. The public repository contains code and
[source catalogue / hashes](e-historia-v1.manifest.json), plus the
[mixed-corpus manifest](wiki-ehistoria-v1.manifest.json), without full lesson text.

## Reproduce locally

Use Python 3.10+ with `lxml` installed, and the existing adjacent `matura-lab`
evaluator. From this repository:

```sh
python3 scripts/retrieval/import_ehistoria.py \
  --output data/raw/retrieval/e-historia-v1

python3 scripts/retrieval/combine_corpora.py \
  --runner-root ../matura-lab \
  --wikipedia data/raw/retrieval/wiki-focused-v3 \
  --ehistoria data/raw/retrieval/e-historia-v1 \
  --output data/raw/retrieval/wiki-ehistoria-v1
```

The mixed builder requires a fresh output directory. It verifies input file
hashes, source scopes, rights metadata, unique IDs, article coverage, passage
spans and indexed text. Original records from both input corpora remain intact.
Use `--offline` on the importer to rebuild from its existing response cache.
Live pages can change: exact reproduction requires the retained local snapshot.

The four `qwen35-{08b,2b}-{2023,2024}-ehistoria-v1.json` configurations change
only the corpus, provenance and variant selection from comparison-v1. See the
[predeclared experiment](../results/2026-09-26-ehistoria-plan.md). Relevance policy,
prompt, essay bank, model weights and inference budgets remain fixed.
