from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/retrieval'))
from build_corpus import passages, sha


class PassageTests(unittest.TestCase):
    def article(self, body):
        text = 'Example history\n\n' + body
        return {'id': 'wiki:1:2', 'title': 'Example history', 'text': text,
                'text_sha256': sha(text), 'source': 'https://pl.wikipedia.org/wiki/Example',
                'licence': 'CC BY-SA 4.0', 'attribution': 'Contributors', 'history_url': 'https://example.org/history'}

    def test_body_is_exact_source_span_with_provenance(self):
        article = self.article('A historical statement with enough detail to make this paragraph useful.\n\n== Middle Ages ==\n\nAnother historical statement that is long enough to retain as a useful paragraph.')
        rows = list(passages(article))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]['section'], 'Middle Ages')
        for row in rows:
            start, end = row['source_span']
            self.assertEqual(row['text'], row['prefix'] + article['text'][start:end])
            self.assertEqual(row['body_sha256'], sha(article['text'][start:end]))
            self.assertEqual(row['source'], article['source'])

    def test_bibliography_subsections_removed_without_losing_next_section(self):
        article = self.article('== Bibliografia ==\n\nA long bibliographic entry that must not become retrieved historical evidence.\n\n=== Books ===\n\nAnother bibliography entry that must not be included in the corpus passages.\n\n== History ==\n\nA real historical paragraph with enough detail to be included in the corpus.')
        rows = list(passages(article))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['section'], 'History')

    def test_long_paragraph_uses_bounded_spans_and_stable_ids(self):
        article = self.article(('One complete historical sentence with enough source detail. ' * 60).strip())
        rows = list(passages(article, limit=300))
        self.assertGreater(len(rows), 5)
        self.assertEqual(rows, list(passages(article, limit=300)))
        for row in rows:
            start, end = row['source_span']
            self.assertLessEqual(end-start, 300)
            self.assertEqual(row['text'][len(row['prefix']):], article['text'][start:end])


if __name__ == '__main__': unittest.main()
