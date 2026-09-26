"""Validate Wikipedia + e-Historia snapshots and create a separate mixed index."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from import_ehistoria import BASE, LICENCE, sha, write


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_records(articles, passages, source_kind):
    by_id = {a['id']: a for a in articles}
    require(bool(articles) and bool(passages), 'Empty corpus')
    require(len(by_id) == len(articles), 'Duplicate article IDs')
    require(len({a['source'] for a in articles}) == len(articles), 'Duplicate source URLs')
    require(len({p['id'] for p in passages}) == len(passages), 'Duplicate passage IDs')
    for a in articles:
        require(sha(a['text']) == a['text_sha256'], 'Article text hash mismatch')
        url = urlsplit(a['source'])
        if source_kind == 'wikipedia':
            require(url.scheme == 'https' and url.netloc == 'pl.wikipedia.org' and url.path.startswith('/wiki/'), 'Unexpected Wikipedia URL')
            require(a['licence'].startswith('CC BY-SA'), 'Missing Wikipedia licence')
        elif source_kind == 'ehistoria':
            require(a['source'].startswith(BASE + '/') and url.netloc == 'e-historia.com.pl'
                    and not url.query and not url.fragment, 'Unexpected e-Historia URL')
            require(a['licence'] == LICENCE and a['generated'] is False, 'Source rights or generation flag mismatch')
        else:
            raise ValueError('Unsupported source kind')
    for p in passages:
        a = by_id[p['article_id']]
        lo, hi = p['source_span']
        require(0 <= lo < hi <= len(a['text']), 'Invalid source span')
        body = a['text'][lo:hi]
        require(sha(body) == p['body_sha256'] and p['article_text_sha256'] == a['text_sha256'], 'Passage hash mismatch')
        require(p['prefix'] == a['title'] + ' — ' + p['section'] + '\n', 'Unverified prefix')
        require(p['text'] == p['prefix'] + body, 'Passage differs from source span')
        require(all(p[k] == a[k] for k in ('source', 'licence', 'attribution', 'history_url', 'title')), 'Passage provenance mismatch')
    require({p['article_id'] for p in passages} == set(by_id), 'Unrepresented article')


def load(directory, kind):
    manifest = json.loads((directory / 'manifest.json').read_text())
    require(not manifest['failures'] and not manifest['pending_titles'], 'Incomplete source acquisition')
    for name in ('articles', 'passages'):
        require(sha((directory / f'{name}.jsonl').read_bytes()) == manifest[f'{name}_sha256'], 'Input file hash mismatch')
    articles, passages = [read_lines(directory / f'{name}.jsonl') for name in ('articles', 'passages')]
    require(len(articles) == manifest['articles'] and len(passages) == manifest['passages'], 'Count mismatch')
    validate_records(articles, passages, kind)
    return articles, passages, manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wikipedia', required=True)
    p.add_argument('--ehistoria', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--runner-root', required=True)
    args = p.parse_args()
    out = Path(args.output)
    require(not out.exists(), 'Use a fresh corpus directory')
    all_articles, all_passages, sources = [], [], []
    for kind, path in [('wikipedia', args.wikipedia), ('ehistoria', args.ehistoria)]:
        root = Path(path)
        articles, passages, manifest = load(root, kind)
        all_articles.extend(articles); all_passages.extend(passages)
        sources.append({'kind': kind, 'manifest_sha256': sha((root / 'manifest.json').read_bytes()), 'manifest': manifest})
    require(len({a['id'] for a in all_articles}) == len(all_articles), 'Cross-source article ID collision')
    require(len({p['id'] for p in all_passages}) == len(all_passages), 'Cross-source passage ID collision')
    out.mkdir(parents=True)
    for name, records in [('articles', all_articles), ('passages', all_passages)]:
        (out / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    sys.path.insert(0, str(Path(args.runner_root).resolve()))
    from matura_lab.retrieval import Corpus
    corpus = Corpus(out / 'index.sqlite')
    size = max(len(r['text']) for r in all_passages) + 1
    count = corpus.add(all_passages, size=size, overlap=0)
    indexed = corpus.db.execute('SELECT text,source,licence FROM chunks').fetchall()
    require(count == len(all_passages), 'Indexed passage count mismatch')
    require(sorted(indexed) == sorted((r['text'].strip(), r['source'], r['licence']) for r in all_passages), 'Index text/provenance mismatch')
    corpus.db.close()
    manifest = {'kind': 'wikipedia-plus-ehistoria-v1', 'articles': len(all_articles), 'passages': count,
                'sources': sources, 'failures': [], 'pending_titles': [],
                'selection_note': 'Unchanged Wikipedia v3 plus all four classes of the user-selected repetytorium. No exam answer keys or generated historical supplements.',
                'articles_sha256': sha((out / 'articles.jsonl').read_bytes()),
                'passages_sha256': sha((out / 'passages.jsonl').read_bytes()),
                'index_sha256': sha((out / 'index.sqlite').read_bytes()),
                'index_chunks': count, 'legacy_add_size': size, 'legacy_add_overlap': 0,
                'builder_sha256': sha(Path(__file__).read_bytes()),
                'verification': 'Input hashes, scoped source URLs, attribution, exact article spans and indexed text verified; original source records unchanged',
                'quality_limit': 'Historical claims not independently verified; site images not transcribed; development corpus, not held-out evaluation data'}
    write(out / 'manifest.json', manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k != 'sources'}, indent=2))


if __name__ == '__main__': main()
