import sqlite3
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/checkpoints"))
from focused_retrieval import FocusedRetriever, source_for_query, words


class FocusedRetrievalTests(unittest.TestCase):
    def retriever(self, records):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.execute("CREATE TABLE chunks(id,text,source,licence)")
        rows = [(str(i), text, source, "CC BY-SA") for i, (text, source) in enumerate(records)]
        # Background documents make rarity meaningful without any exam knowledge.
        rows += [(f"noise-{i}", f"Zoologia {i}\nZwierzęta afrykańskie żyją na sawannie.", f"noise/{i}", "CC BY-SA") for i in range(12)]
        db.executemany("INSERT INTO chunks VALUES (?,?,?,?)", rows)
        return FocusedRetriever(SimpleNamespace(db=db))

    def question(self, prompt, source=""):
        return SimpleNamespace(prompt=prompt, source_text=source)

    def test_polish_inflections_and_accents_share_query_terms(self):
        self.assertEqual(set(words("Łódzkiego włókiennictwa")),
                         set(words("lodzkie wlokiennictwo")))

    def test_referenced_source_is_selected_and_citations_do_not_become_clues(self):
        q = self.question("Podaj nazwę ruchu opisanego w źródle 2.",
            "Źródło 1. Konflikt azjatycki\nPierwszy tekst.\n"
            "Źródło 2. Ruch społeczny\nDrugi tekst o robotnikach.\n"
            "Na podstawie: Fałszywy Trop, Warszawa 2000, s. 10.\n[Obraz: images/SECRET.png]")
        source, refs = source_for_query(q)
        self.assertEqual(refs, ["2"])
        self.assertIn("robotnikach", source)
        self.assertNotIn("azjatycki", source)
        self.assertNotIn("Fałszywy", source)
        self.assertNotIn("SECRET", source)
        self.assertIn("SECRET", q.source_text)  # Original solver inputs are untouched.

    def test_unresolved_source_reference_preserves_all_available_text(self):
        q = self.question("Wyjaśnij źródło 9.", "Źródło 1. Pierwszy\nŹródło 2. Drugi")
        text, refs = source_for_query(q)
        self.assertEqual(refs, [])
        self.assertIn("Pierwszy", text)
        self.assertIn("Drugi", text)

    def test_retrieval_uses_source_terms_beyond_long_instructions(self):
        retriever = self.retriever([("Tkactwo\nWłókiennictwo łódzkie rozwijało fabryki.", "textiles")])
        q = self.question(("Wyjaśnij uzasadnij odpowiedź źródło " * 100), "Łódzkie włókiennictwo.")
        hits, trace = retriever.search(q)
        self.assertEqual(hits[0]["source"], "textiles")
        self.assertEqual(trace["reason"], "selected")

    def test_image_only_generic_question_can_abstain_from_retrieval(self):
        retriever = self.retriever([("Numizmatyka\nMoneta przedstawiała króla w koronie.", "coins")])
        hits, trace = retriever.search(self.question("Podaj nazwisko postaci na monecie.",
            "Moneta okolicznościowa\n[Obraz: images/Z14.png]\nhttps://example.org"))
        self.assertEqual(hits, [])
        self.assertNotEqual(trace["reason"], "selected")

    def test_one_incidental_word_does_not_pass_evidence_gate(self):
        retriever = self.retriever([("Inny temat\nPrzelotny komentarz o fabrykach.", "incidental")])
        hits, trace = retriever.search(self.question("Fabryki robotnicy Łódź"))
        self.assertEqual(hits, [])
        self.assertEqual(trace["reason"], "no_passage_passed_overlap_gate")

    def test_illustration_creation_is_not_searched_as_an_uprising(self):
        retriever = self.retriever([("Powstanie\nInterwencja przerwała powstanie.", "unrelated")])
        hits, trace = retriever.search(self.question(
            "Wyjaśnij wymowę rysunku, interpretując elementy graficzne. Uwzględnij kontekst z roku powstania tego rysunku.",
            "Rysunek z 1900 roku\n[Obraz: figure.png]"))
        self.assertEqual(hits, [])
        self.assertNotIn("powst", trace["prompt_terms"])
        self.assertNotIn("inter", trace["prompt_terms"])

    def test_rankings_are_stable_and_at_most_two_passages_per_article(self):
        records = [(f"Tkactwo — Część {i}\nŁódzkie włókiennictwo rozwijało fabryki.", "same") for i in range(4)]
        records += [("Przemysł\nŁódzkie włókiennictwo potrzebowało robotników.", "other")]
        retriever = self.retriever(records)
        q = self.question("Łódzkie włókiennictwo fabryki")
        first = retriever.search(q)
        self.assertEqual(first, retriever.search(q))
        self.assertLessEqual(sum(h["source"] == "same" for h in first[0]), 2)
        self.assertTrue(all(h["text"] in {t for t, _ in records} for h in first[0]))


if __name__ == "__main__":
    unittest.main()
