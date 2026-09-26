from pathlib import Path
import sys
import json
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/retrieval'))
from import_ehistoria import BASE, INDEX, EmptyPublishedArticle, Fetcher, parse_article, make_passages, safe_url, sha
from combine_corpora import validate_records


class EHistoriaTests(unittest.TestCase):
    def parse(self, content):
        raw = ('<main><nav>Navigation outside article</nav><div class="com-content-article__body">'
               + content + '</div></main>').encode()
        url = BASE + '/klasa-1-example/lesson.html'
        return parse_article(raw, {'url': url, 'catalog_title': 'Example history',
                             'class': 'Class 1', 'category_url': BASE + '/klasa-1-example.html'},
                             {'html_sha256': sha(raw), 'retrieved_at': 'fixture', 'response_url': url})

    def test_short_dates_inline_text_and_navigation(self):
        a = self.parse('<div class="eh-tabs">Konspekt Streszczenie</div>'
                       '<p>1. 01. Example history</p><p>I. An era</p>'
                       '<p>Here is a sufficiently detailed source statement with <b>emphasis</b> and normal spacing.'
                       '<br>New line stays separated.</p><p>Najważniejsze daty</p><p>966 – chrzest</p>'
                       '<p>Opracowanie tematu: a related link</p>'
                       '<p>Rozwiąż quiz: promotional link</p><p><a href="/table.pdf">Linked PDF</a></p>')
        rows = list(make_passages(a))
        self.assertEqual(rows[-1]['section'], 'Najważniejsze daty')
        self.assertTrue(rows[-1]['text'].endswith('966 – chrzest'))
        self.assertIn('spacing. New line', a['text'])
        for excluded in ('Navigation', 'Konspekt', 'related link', 'promotional link', 'Linked PDF'):
            self.assertNotIn(excluded, a['text'])
        for r in rows:
            lo, hi = r['source_span']
            self.assertEqual(r['text'], r['prefix'] + a['text'][lo:hi])

    def test_plain_bold_heading_is_preserved_as_section(self):
        a = self.parse('<p><strong>A section without Roman numbering</strong></p><p>'
                       + 'Some factual source text with names and dates. ' * 4 + '</p>')
        self.assertEqual(list(make_passages(a))[0]['section'], 'A section without Roman numbering')

    def test_nested_lists_table_and_direct_container_text_survive_once(self):
        a = self.parse('<div>Introductory historical description with enough detail for a useful article.'
                       '<ul><li>Parent<ul><li>Child one</li><li>Child two</li></ul></li></ul>'
                       '<table><tr><th>Year</th><th>Event</th></tr><tr><td>966</td><td>Baptism</td></tr></table>'
                       'Another direct text node survives.</div>')
        self.assertEqual(a['text'].count('Child one'), 1)
        self.assertIn('966 | Baptism', a['text'])
        self.assertIn('Another direct text node survives.', a['text'])

    def test_long_paragraph_is_lossless_across_bounded_passages(self):
        a = self.parse('<p>I. Context</p><p>' + 'A complete historical statement. ' * 100 + '</p><p>A final date: 966.</p>')
        rows = list(make_passages(a, limit=180))
        self.assertTrue(all(r['source_span'][1] - r['source_span'][0] <= 180 for r in rows))
        expected = a['text'][a['blocks'][1]['source_span'][0]:]
        actual = ''.join(a['text'][r['source_span'][0]:r['source_span'][1]] for r in rows)
        # A paragraph boundary may be between passages; all content must remain.
        self.assertEqual(''.join(expected.split()), ''.join(actual.split()))

    def test_scope_and_missing_article_fail_closed(self):
        self.assertEqual(safe_url(INDEX), INDEX)
        for url in ('https://example.org/a', 'http://e-historia.com.pl/a',
                    'https://e-historia.com.pl/admin', BASE + '/page?download=1'):
            with self.assertRaises(ValueError): safe_url(url)
        with self.assertRaises(ValueError):
            parse_article(b'<main>Only navigation</main>', {}, {})

    def test_index_rejects_changed_body_or_misattributed_rights(self):
        a = self.parse('<p>I. Context</p><p>' + 'A sufficiently detailed historical source statement. ' * 4 + '</p>')
        rows = list(make_passages(a))
        validate_records([a], rows, 'ehistoria')
        rows[0]['text'] += ' An unsupported addition.'
        with self.assertRaisesRegex(ValueError, 'differs from source'):
            validate_records([a], rows, 'ehistoria')
        rows = list(make_passages(a)); rows[0]['licence'] = 'CC BY-SA'
        with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
            validate_records([a], rows, 'ehistoria')

    def test_empty_published_body_is_distinct_from_unsupported_page(self):
        with self.assertRaises(EmptyPublishedArticle):
            self.parse('   ')

    def test_offline_cache_checks_content_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp); raw = b'original'
            stem = cache / sha(INDEX)
            stem.with_suffix('.html').write_bytes(raw)
            stem.with_suffix('.json').write_text(json.dumps({'url': INDEX, 'response_url': INDEX, 'html_sha256': sha(raw)}))
            fetcher = Fetcher(cache, offline=True)
            self.assertEqual(fetcher.get(INDEX)[0], raw)
            stem.with_suffix('.html').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                fetcher.get(INDEX)
            with self.assertRaisesRegex(ValueError, 'Missing offline cache'):
                fetcher.get(BASE + '/missing.html')


if __name__ == '__main__': unittest.main()
