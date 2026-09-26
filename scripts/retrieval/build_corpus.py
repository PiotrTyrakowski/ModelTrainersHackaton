"""Fetch traceable Polish Wikipedia articles and build source-preserving passages."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def fetch_article(title):
    query = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": 2,
        "prop": "extracts|info|pageprops", "ppprop": "disambiguation",
        "explaintext": 1, "exsectionformat": "wiki", "inprop": "url",
        "redirects": 1, "titles": title,
    })
    req = urllib.request.Request("https://pl.wikipedia.org/w/api.php?" + query,
        headers={"User-Agent": "ChurchBuddiesMaturaResearch/0.1 (https://github.com/PiotrTyrakowski/ModelTrainersHackaton)"})
    with urllib.request.urlopen(req, timeout=40) as response:
        page = json.load(response)["query"]["pages"][0]
    if page.get("missing") or "disambiguation" in page.get("pageprops", {}):
        raise ValueError("Missing or ambiguous article")
    text = page.get("extract", "").strip()
    if len(text) < 150:
        raise ValueError("Article has insufficient plaintext")
    text = page["title"] + "\n\n" + text
    return {
        "id": f"plwiki:{page['pageid']}:{page['lastrevid']}",
        "title": page["title"], "requested_title": title, "text": text,
        "source": page["fullurl"], "observed_latest_revision": page["lastrevid"],
        "history_url": "https://pl.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": page["title"], "action": "history"}),
        "licence": "CC BY-SA 4.0; https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution": "Polish Wikipedia contributors; see article history",
        "retrieved_at": datetime.now(timezone.utc).isoformat(), "text_sha256": sha(text),
        "transform": "MediaWiki plaintext extraction with article-title prefix; revision is observed metadata, content identity is the text hash",
    }


SKIP = {"przypisy", "bibliografia", "linki zewnętrzne", "zobacz też", "uwagi", "źródła"}


def passages(article, limit=1300):
    """Keep exact body spans, section context and readable boundaries, no summaries."""
    text = article["text"]
    section, level, skipping = "Wstęp", 0, False
    spans = []
    for m in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, re.S):
        body = m.group()
        heading = re.fullmatch(r"(={2,6})\s*(.*?)\s*\1", body)
        if heading:
            current_level = len(heading[1])
            if not skipping or current_level <= level:
                skipping = heading[2].casefold() in SKIP
                level = current_level
            section = heading[2]
            continue
        if skipping or body == article["title"]:
            continue
        start, end = m.span()
        while end - start > limit:
            # Prefer full sentences, then whitespace; never glue different sections.
            portion = text[start:start + limit]
            candidates = list(re.finditer(r"[.!?]\s+", portion))
            cut = candidates[-1].end() if candidates and candidates[-1].end() > limit // 2 else portion.rfind(" ")
            if cut <= 0: cut = limit
            spans.append((section, start, start + cut))
            start += cut
        if start < end: spans.append((section, start, end))
    for i, (section, start, end) in enumerate(spans):
        body = text[start:end]
        if len(body.strip()) < 50: continue
        prefix = f"{article['title']} — {section}\n"
        value = prefix + body
        yield {
            "id": f"{article['id']}:passage:{i}:{sha(value)[:16]}",
            "text": value, "source": article["source"], "licence": article["licence"],
            "article_id": article["id"], "title": article["title"], "section": section,
            "source_span": [start, end], "body_sha256": sha(body),
            "article_text_sha256": article["text_sha256"], "prefix": prefix,
            "attribution": article["attribution"], "history_url": article["history_url"],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed-documents")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    topics = json.loads(Path(args.topics).read_text())
    titles = list(dict.fromkeys(t for ts in topics["groups"].values() for t in ts))
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    path = out / "articles.jsonl"
    records = read_lines(path) if path.exists() else read_lines(args.seed_documents) if args.seed_documents else []
    failures = []
    def save_articles():
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    save_articles()
    completed = {r.get("requested_title", r["title"]) for r in records} | {r["title"] for r in records}
    completed.update(t for r in records for t in r.get("aliases", []))
    if not args.offline:
        for title in titles:
            if title in completed: continue
            try:
                record = fetch_article(title)
                existing = next((r for r in records if r["id"] == record["id"]), None)
                if existing is None:
                    records.append(record)
                else:
                    existing["aliases"] = sorted(set(existing.get("aliases", [])) | {title})
                completed.add(title); save_articles()
                print(f"Fetched {record['title']}: {len(record['text'])} characters", flush=True)
            except urllib.error.HTTPError as e:
                failures.append({"title": title, "status": e.code, "retry_after": e.headers.get("Retry-After")})
                print(f"HTTP {e.code}: stopped; respect Retry-After before resuming", flush=True)
                break
            except (ValueError, KeyError) as e:
                failures.append({"title": title, "error": str(e)})
                print(f"Skipped {title}: {e}", flush=True)
            except (urllib.error.URLError, TimeoutError) as e:
                failures.append({"title": title, "error": str(e)})
                print("Network failure: stopped; resume later", flush=True)
                break
            time.sleep(1)
    data = []
    for article in records:
        if sha(article["text"]) != article["text_sha256"]: raise ValueError("Article hash mismatch")
        data.extend(passages(article))
    target = out / "passages.jsonl"
    target.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in data))
    write(out / "manifest.json", {
        "kind": topics["kind"], "selection_note": topics["selection_note"],
        "articles": len(records), "passages": len(data), "failures": failures,
        "pending_titles": [t for t in titles if t not in completed],
        "articles_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "passages_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "topics_sha256": hashlib.sha256(Path(args.topics).read_bytes()).hexdigest(),
        "transform": "Exact paragraph/sentence spans; title and section prefixes; omit bibliography/navigation; no generated facts or exam answer keys",
        "quality_limit": "Provenance and passage boundaries verified; encyclopedia claims are not independently fact-checked",
    })
    print(f"Saved {len(records)} articles / {len(data)} passages; pending {len([t for t in titles if t not in completed])}")
    if failures: raise SystemExit(1)


if __name__ == "__main__":
    main()
