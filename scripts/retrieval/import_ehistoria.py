"""Import only the linked extended-history repetytorium; preserve source spans.

Requires lxml. Network acquisition is sequential, cached and robots-aware.
No LLM-generated history, answer keys, linked quizzes or glossary crawl.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit, urldefrag
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

from lxml import html

ORIGIN = "https://e-historia.com.pl"
BASE = ORIGIN + "/liceum-i-technikum/notatki-z-historii-zakres-rozszerzony/repetytorium-z-historii-zakres-rozszerzony"
INDEX = BASE + ".html"
UA = "ChurchBuddiesMaturaResearch/0.1 (+https://github.com/PiotrTyrakowski/ModelTrainersHackaton)"
AUTHOR = "Wiesław Zdziabek / e-Historia"
AUTHOR_URL = ORIGIN + "/o-projekcie-e-historia---wspolpraca-miedzynarodowa/4-o-autorze.html"
LICENCE = "No open redistribution licence identified; author rights retained. Local research snapshot."


class EmptyPublishedArticle(ValueError):
    """A catalogued lesson whose actual published body is empty."""


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def safe_url(value):
    value = urldefrag(value)[0]
    p = urlsplit(value)
    if (p.scheme != "https" or p.netloc != "e-historia.com.pl" or p.username or p.password
            or (p.path != "/robots.txt" and value != INDEX and not value.startswith(BASE + "/"))):
        raise ValueError("URL outside the authorized repetytorium scope")
    if p.query and not re.fullmatch(r"start=\d+", p.query):
        raise ValueError("Unexpected query parameters")
    return value


class ScopedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Fetcher:
    def __init__(self, cache, offline=False, delay=1.0):
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self.offline, self.delay, self.last = offline, max(1.0, delay), 0
        self.opener = build_opener(ScopedRedirect())
        self.robots = None

    def get(self, url):
        url = safe_url(url)
        if self.robots and not self.robots.can_fetch(UA, url):
            raise ValueError("robots.txt disallows this URL")
        stem = self.cache / sha(url)
        if stem.with_suffix('.json').exists():
            meta = json.loads(stem.with_suffix('.json').read_text())
            raw = stem.with_suffix('.html').read_bytes()
            if meta['url'] != url or sha(raw) != meta['html_sha256']:
                raise ValueError("Cached response identity mismatch")
            safe_url(meta['response_url'])
            return raw, meta
        if self.offline:
            raise ValueError(f"Missing offline cache: {url}")
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        with self.opener.open(Request(url, headers={'User-Agent': UA}), timeout=40) as r:
            safe_url(r.url)
            raw = r.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("Response exceeds bounded article size")
            meta = {'url': url, 'response_url': r.url, 'status': r.status,
                    'content_type': r.headers.get('Content-Type'),
                    'retrieved_at': datetime.now(timezone.utc).isoformat(),
                    'html_sha256': sha(raw), 'bytes': len(raw)}
        stem.with_suffix('.html').write_bytes(raw)
        write(stem.with_suffix('.json'), meta)
        return raw, meta

    def load_robots(self):
        raw, _ = self.get(ORIGIN + '/robots.txt')
        self.robots = RobotFileParser()
        self.robots.parse(raw.decode('utf-8').splitlines())
        self.delay = max(self.delay, self.robots.crawl_delay(UA) or 0)
        return sha(raw)


def discover(fetcher):
    root, _ = fetcher.get(INDEX)
    tree = html.fromstring(root.decode('utf-8'))
    classes = []
    for a in tree.xpath('//main//a[@href]'):
        url = urljoin(INDEX, a.get('href'))
        if re.fullmatch(re.escape(BASE) + r'/klasa-[1-4]-[^/?]+\.html', url):
            classes.append((clean(a.text_content()), safe_url(url)))
    classes = list(dict.fromkeys(classes))
    if len(classes) != 4:
        raise ValueError(f"Expected four class categories, found {len(classes)}")
    records = {}
    for label, category in classes:
        prefix = category.removesuffix('.html') + '/'
        pending, seen = [category], set()
        while pending:
            url = pending.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if len(seen) > 20:
                raise ValueError("Unexpected category pagination")
            raw, _ = fetcher.get(url)
            doc = html.fromstring(raw.decode('utf-8'))
            for a in doc.xpath('//main//a[@href]'):
                target = urldefrag(urljoin(url, a.get('href')))[0]
                p = urlsplit(target)
                if target.startswith(prefix) and p.path.endswith('.html') and not p.query:
                    target = safe_url(target)
                    records[target] = {'url': target, 'catalog_title': clean(a.text_content()),
                                       'class': label, 'category_url': category}
                elif target.startswith(category + '?start='):
                    pending.append(safe_url(target))
        print(f"Discovered {label}: {sum(r['class'] == label for r in records.values())} lessons", flush=True)
    if not 20 <= len(records) <= 400:
        raise ValueError("Unexpected lesson inventory; inspect before crawling")
    return list(records.values())


def parse_article(raw, entry, meta):
    doc = html.fromstring(raw.decode('utf-8'))
    bodies = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," com-content-article__body ")]')
    if len(bodies) != 1:
        raise ValueError("Expected exactly one article body; refusing page/navigation fallback")
    body = bodies[0]
    if not clean(body.text_content()) and not body.xpath('.//img|.//iframe|.//object'):
        raise EmptyPublishedArticle('Published article body is empty')
    for el in list(body.xpath('.//script|.//style|.//nav|.//form|.//*[contains(concat(" ",normalize-space(@class)," ")," eh-tabs ")]')):
        el.drop_tree()
    for el in list(body.xpath('.//p')):
        links = el.xpath('.//a[@href]')
        only_linked_pdf = (len(links) == 1 and clean(el.text_content()) == clean(links[0].text_content())
                           and urlsplit(links[0].get('href')).path.lower().endswith('.pdf'))
        if only_linked_pdf or re.match(r'^(Pracuj ze źródłami|Opracowanie tematu|Galeria ilustracji|Zobacz też|Rozwiąż quiz)\s*:', clean(el.text_content()), re.I):
            el.drop_tree()
    for br in body.xpath('.//br'):
        br.tail = ' ' + (br.tail or '')
    images = [{'src': urljoin(entry['url'], i.get('src', '')), 'alt': i.get('alt', '')}
              for i in body.xpath('.//img')]
    blocks = []

    def add(el, text, kind='paragraph'):
        text = clean(text)
        if not text or re.match(r'^(Pracuj ze źródłami|Opracowanie tematu|Galeria ilustracji|Zobacz też)\s*:', text, re.I):
            return
        if (el.tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
                or re.match(r'^[IVXLCDM]+\.\s', text)
                or re.match(r'^Najważniejsze (?:pojęcia|daty|postaci[e]?)$', text, re.I)
                or (el.tag == 'p' and len(text) <= 200 and not el.xpath('.//a')
                    and clean(''.join(el.xpath('.//strong/text()|.//b/text()'))) == text)):
            kind = 'heading'
        blocks.append({'kind': kind, 'text': text, 'dom_xpath': doc.getroottree().getpath(el)})

    def walk(el):
        if el.tag == 'table':
            for row in el.xpath('.//tr'):
                cells = [clean(c.text_content()) for c in row.xpath('./th|./td')]
                add(row, ' | '.join(cells), 'table_row')
        elif el.tag in {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            add(el, el.text_content())
        elif el.tag == 'li':
            # Keep parent list labels without duplicating nested children.
            parts = [el.text or '']
            for child in el:
                if child.tag not in {'ul', 'ol'}:
                    parts.append(child.text_content())
                parts.append(child.tail or '')
            add(el, ''.join(parts))
            for child in el:
                if child.tag in {'ul', 'ol'}:
                    walk(child)
        else:
            add(el, el.text or '')
            for child in el:
                walk(child)
                add(el, child.tail or '')
    walk(body)
    # All visible letters and numbers must survive in document order. Ignore
    # whitespace and the explicit table-cell separators in this coverage check.
    compact = lambda value: re.sub(r'\W+', '', value, flags=re.UNICODE)
    if compact(body.text_content()) != compact(''.join(b['text'] for b in blocks)):
        raise ValueError('Article text coverage mismatch; inspect unsupported HTML structure')
    if not blocks:
        raise ValueError("Empty article body")
    title = entry['catalog_title']
    if re.match(r'^\d+\.\s*\d+', blocks[0]['text']):
        title = blocks.pop(0)['text']
    elif clean(blocks[0]['text']) == clean(title):
        blocks.pop(0)
    text, section = title, 'Wstęp'
    for b in blocks:
        start = len(text) + 2
        text += '\n\n' + b['text']
        b['source_span'] = [start, len(text)]
        if b['kind'] == 'heading':
            section = b['text']
        b['section'] = section
    if len(text) < 150 or len(blocks) < 2:
        raise ValueError("Insufficient article content")
    return {'id': 'ehistoria:' + sha(entry['url'])[:20] + ':' + sha(text)[:16],
            'title': title, 'text': text, 'text_sha256': sha(text), 'source': entry['url'],
            'licence': LICENCE, 'attribution': AUTHOR, 'history_url': entry['url'],
            'author_url': AUTHOR_URL, 'class': entry['class'], 'category_url': entry['category_url'],
            'html_sha256': meta['html_sha256'], 'retrieved_at': meta['retrieved_at'],
            'response_url': meta['response_url'], 'blocks': blocks, 'images_not_transcribed': images,
            'transform': 'Article-body HTML to normalized text; headings, list items and table cells preserved; no generated facts',
            'text_coverage': 'All article-body letters and numbers retained in order, except explicitly removed navigation/related links',
            'generated': False}


def make_passages(article, limit=1300):
    spans, start, end, section = [], None, None, None
    for b in article['blocks']:
        if b['kind'] == 'heading':
            if start is not None:
                spans.append((section, start, end))
            start = end = None
            continue
        lo, hi = b['source_span']
        if start is not None and (section != b['section'] or hi - start > limit):
            spans.append((section, start, end)); start = end = None
        section = b['section']
        while hi - lo > limit:
            portion = article['text'][lo:lo + limit]
            cuts = list(re.finditer(r'[.!?]\s+', portion))
            cut = cuts[-1].end() if cuts and cuts[-1].end() > limit // 2 else portion.rfind(' ')
            cut = cut if cut > 0 else limit
            spans.append((section, lo, lo + cut)); lo += cut
        if start is None:
            start = lo
        end = hi
    if start is not None:
        spans.append((section, start, end))
    for n, (section, start, end) in enumerate(spans):
        body = article['text'][start:end]
        prefix = article['title'] + ' — ' + section + '\n'
        yield {'id': f"{article['id']}:passage:{n}:{sha(prefix + body)[:16]}",
               'text': prefix + body, 'source': article['source'], 'licence': article['licence'],
               'article_id': article['id'], 'title': article['title'], 'section': section,
               'class': article['class'], 'source_span': [start, end], 'prefix': prefix,
               'body_sha256': sha(body), 'article_text_sha256': article['text_sha256'],
               'attribution': article['attribution'], 'history_url': article['history_url'],
               'generated': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--offline', action='store_true')
    args = p.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher(out / 'html', args.offline)
    robots_hash = fetcher.load_robots()
    catalogue = discover(fetcher)
    write(out / 'catalogue.json', catalogue)
    articles, passages, failures, excluded, completed = [], [], [], [], set()
    for i, entry in enumerate(catalogue):
        try:
            raw, meta = fetcher.get(entry['url'])
            article = parse_article(raw, entry, meta)
            articles.append(article); passages.extend(make_passages(article))
            completed.add(entry['url'])
            print(f"{i+1}/{len(catalogue)} {article['class']}: {article['title']}", flush=True)
        except EmptyPublishedArticle as error:
            excluded.append({**entry, 'reason': str(error), 'html_sha256': meta['html_sha256']})
            completed.add(entry['url'])
            print(f"Excluded empty published lesson: {entry['catalog_title']}", flush=True)
        except Exception as error:
            failures.append({'url': entry['url'], 'error_type': type(error).__name__,
                             'error': str(error), 'retry_after': (getattr(error, 'headers', None) or {}).get('Retry-After')})
            break  # No retries or bypass on HTTP/rate-limit/network/parser failures.
    for name, records in [('articles', articles), ('passages', passages)]:
        (out / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    write(out / 'manifest.json', {'kind': 'e-historia-repetytorium-v1', 'source_index': INDEX,
          'selection_note': 'All lessons linked from the four user-selected repetytorium classes, independent of exam answer keys.',
          'articles': len(articles), 'passages': len(passages), 'catalogue_items': len(catalogue),
          'failures': failures, 'excluded_empty_lessons': excluded,
          'pending_titles': [x['catalog_title'] for x in catalogue if x['url'] not in completed],
          'robots_sha256': robots_hash, 'articles_sha256': sha((out / 'articles.jsonl').read_bytes()),
          'passages_sha256': sha((out / 'passages.jsonl').read_bytes()),
          'catalogue_sha256': sha((out / 'catalogue.json').read_bytes()),
          'builder_sha256': sha(Path(__file__).read_bytes()), 'generated_facts': 0,
          'quality_limit': 'Extraction and provenance checks, not independent historical fact verification; image contents not transcribed.',
          'licence': LICENCE, 'attribution': AUTHOR, 'author_url': AUTHOR_URL})
    print(f"Saved {len(articles)} articles, {len(passages)} passages, {len(failures)} failures")
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
