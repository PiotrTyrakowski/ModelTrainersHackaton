"""Validate a source-preserving corpus and build a fresh legacy BM25 index."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from build_corpus import read_lines, sha, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner-root", required=True)
    parser.add_argument("--corpus-directory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.runner_root).resolve()))
    from matura_lab.retrieval import Corpus

    root, output = Path(args.corpus_directory), Path(args.output)
    if output.exists():
        raise ValueError("Use a fresh index path; do not mix corpus versions")
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["pending_titles"] or manifest["failures"]:
        raise ValueError("Finish corpus acquisition before indexing")
    for name in ("articles", "passages"):
        if hashlib.sha256((root / f"{name}.jsonl").read_bytes()).hexdigest() != manifest[f"{name}_sha256"]:
            raise ValueError(f"{name} file hash mismatch")
    articles = read_lines(root / "articles.jsonl")
    records = read_lines(root / "passages.jsonl")
    by_id = {a["id"]: a for a in articles}
    if len(by_id) != len(articles) or len({a["title"] for a in articles}) != len(articles):
        raise ValueError("Duplicate articles")
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate passage IDs")
    for r in records:
        a = by_id[r["article_id"]]
        start, end = r["source_span"]
        body = a["text"][start:end]
        assert 0 <= start < end <= len(a["text"])
        assert sha(a["text"]) == a["text_sha256"] == r["article_text_sha256"]
        assert sha(body) == r["body_sha256"]
        assert r["text"] == r["prefix"] + body
        assert all(r[k] == a[k] for k in ("source", "licence", "attribution", "history_url"))
        assert r["source"].startswith("https://pl.wikipedia.org/")
    size = max(len(r["text"]) for r in records) + 1
    corpus = Corpus(output)
    count = corpus.add(records, size=size, overlap=0)
    assert count == len(records)
    indexed = corpus.db.execute("SELECT text,source,licence FROM chunks").fetchall()
    assert sorted(indexed) == sorted((r["text"].strip(), r["source"], r["licence"]) for r in records)
    corpus.db.close()
    result = {
        **manifest, "index_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "index_chunks": count, "legacy_add_size": size, "legacy_add_overlap": 0,
        "verification": "Every indexed passage matches its exact article span plus title/section prefix; unique IDs and canonical titles; no secondary splitting",
        "builder_sha256": sha(Path(__file__).with_name("build_corpus.py").read_text()),
        "indexer_sha256": sha(Path(__file__).read_text()),
    }
    write(output.with_suffix(".manifest.json"), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
