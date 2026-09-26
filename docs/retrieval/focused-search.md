# Focused lexical retrieval

`focused_bm25_v1` changes evidence selection while retaining the v3 corpus,
concise answer prompt, model and inference budget. Select it through
`strategy.query_policy` in `configs/checkpoints/qwen35-focused-bm25-v4.json`.
The old policy remains the default for previous configurations.

The policy is implemented in `scripts/checkpoints/focused_retrieval.py`, which
is automatically hashed with the other checkpoint scripts. It reads the pinned
SQLite corpus and builds an in-memory lexical index, without modifying the
corpus file or calling another model.

## What it does

- Removes generic Polish task instructions and visual-format words from search
  terms. It omits image filenames, URLs and detected bibliographic lines.
- If a question explicitly references numbered sources that can all be resolved,
  searches those source blocks. Otherwise it preserves all available source text.
  The original text and images sent to the answering model remain untouched.
- Uses the entire cleaned input instead of its first 80 distinct tokens. It
  normalises accents and uses five-character prefixes for longer words as a
  lightweight Polish inflection heuristic.
- Scores passages with BM25-style term frequency and document rarity, giving
  query terms from the instruction twice the weight and title matches a boost.
- Requires two informative overlapping terms, or an informative article-title
  match. Common terms and years alone cannot satisfy this gate. A term is
  informative only if present in less than 20% of corpus passages and absent
  from the broad-term exclusion list.
- Keeps candidates scoring at least 45% of the best eligible score, at most two
  per article and at most three overall. It can return no additional evidence.

Trace records contain the selected source references, normalised query terms,
selected passage IDs, lexical scores and matched terms. Actual passage text is
saved separately in `retrieved_evidence`. An empty retrieval result does not
abstain from the exam question: the model still receives the original exam
materials and answers it.

## Limits and evaluation

This is a deterministic lexical heuristic, not semantic understanding, verified
historical truth, a lemmatiser, or a trained reranker. Prefix collisions and
unrecognised word endings remain possible. The overlap gate does not prove
relevance; multiple different essay topics can still compete within one query.
No OCR or new visual analysis was added. The constants and stopwords were
inspected using the development questions, not fitted to held-out data.

The policy contains no question IDs, answer mappings or access to grading files.
It adds no learned parameters or external inference calls. Its initial index
construction is included in the first question's measured time.

The full checkpoint uses the same 37-question / 60-point paper and compares with
v3. Software checks exercise source selection, preservation of original inputs,
Polish normalisation, long-query handling, weak-match rejection, stable rankings
and article diversity. Exam performance must be assessed from the separately
graded run, not inferred from these checks.
