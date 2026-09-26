from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tasks_data.essay_bank import (
    EssayBank,
    EssayQuery,
    EssayRecord,
    EssayScope,
    EmbeddingIndex,
)


class FixtureEmbedder:
    """Deterministic test vectors, not evidence of real semantic quality."""

    identity = "test-fixture-v1"

    def __init__(self):
        self.calls = []

    def embed(self, texts, *, role):
        self.calls.append((list(texts), role))
        return [[1, 0], [0, 1]][: len(texts)] if role == "document" else [[0.98, 0.02]]


class EssayBankTests(unittest.TestCase):
    def setUp(self):
        self.original = (
            "  Teza: państwo i obywatel.\n\nArgument pierwszy — żółć.\r\nZakończenie.  "
        )
        self.record = EssayRecord(
            "constitution",
            "Oceń zmiany ustrojowe Konstytucji 3 maja 1791 roku.",
            self.original,
            EssayScope(1791, 1791, ("Rzeczpospolita",), ("ustrój",), "ocena"),
        )
        self.other = EssayRecord(
            "union",
            "Omów przyczyny i skutki unii lubelskiej w 1569 roku.",
            "Inna zapisana praca.",
        )
        self.bank = EssayBank([self.record, self.other])

    def test_exact_match_and_output_preserve_every_byte_without_network(self):
        with patch("socket.socket", side_effect=AssertionError("No network allowed")):
            result = self.bank.match(EssayQuery(self.record.question))
        self.assertEqual((result.status, result.record_id), ("matched", "constitution"))
        self.assertEqual(result.essay, self.original)
        self.assertEqual((result.generation_calls, result.embedding_calls), (0, 0))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "answer.txt"
            result.write_essay(target)
            self.assertEqual(target.read_bytes(), self.original.encode("utf-8"))

    def test_paraphrase_unrelated_and_ambiguous_are_distinct(self):
        result = self.bank.match(
            EssayQuery(
                "Oceń reformy ustrojowe wprowadzone przez Konstytucję 3 maja 1791 roku."
            )
        )
        self.assertEqual(result.record_id, "constitution")
        result = self.bank.match(EssayQuery("Napisz przepis na makaron z pomidorami."))
        self.assertEqual(
            (result.status, result.reason), ("no_match", "below_threshold")
        )
        duplicates = EssayBank(
            [self.record, replace(self.record, id="another", essay="Competing essay")]
        )
        result = duplicates.match(EssayQuery(self.record.question), min_margin=0)
        self.assertEqual(result.reason, "ambiguous")
        self.assertIsNone(result.essay)
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            result.write_essay(Path(directory) / "no.txt")

    def test_explicit_requirements_reject_close_but_incompatible_topics(self):
        variations = [
            (EssayScope(1788, 1792), "period_mismatch_or_unknown"),
            (EssayScope(1792, 1792), "period_mismatch_or_unknown"),
            (EssayScope(entities=("Francja",)), "missing_entities"),
            (EssayScope(aspects=("gospodarka",)), "missing_aspects"),
            (EssayScope(intent="porównanie"), "intent_mismatch_or_unknown"),
        ]
        for scope, expected in variations:
            with self.subTest(scope=scope):
                result = EssayBank([self.record]).match(
                    EssayQuery(self.record.question, scope)
                )
                self.assertEqual(result.reason, "requirements_not_met")
                self.assertIn(expected, result.candidates[0].exclusions)
        accepted = self.bank.match(
            EssayQuery(
                self.record.question,
                EssayScope(1791, 1791, ("RZECZPOSPOLITA",), ("ustroj",), "Ocena"),
            )
        )
        self.assertEqual(accepted.status, "matched")
        short = self.bank.match(
            EssayQuery(self.record.question, self.record.scope, min_words=300)
        )
        self.assertIn("too_short", short.candidates[0].exclusions)

    def test_unknown_scope_is_not_assumed_to_meet_declared_requirements(self):
        bank = EssayBank([replace(self.record, scope=EssayScope())])
        result = bank.match(EssayQuery(self.record.question, self.record.scope))
        self.assertEqual(result.reason, "requirements_not_met")
        client = FixtureEmbedder()
        result = bank.match(
            EssayQuery(self.record.question, self.record.scope),
            method="dense",
            embedder=client,
        )
        self.assertEqual(result.reason, "requirements_not_met")
        self.assertEqual(client.calls, [])

    def test_jsonl_roundtrip_and_invalid_records(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "bank.jsonl"
            self.bank.write_jsonl(target)
            self.assertEqual(EssayBank.from_jsonl(target).records, self.bank.records)
            for value in [
                {"id": "x", "question": "q"},
                {"id": "x", "question": "q", "essay": "e", "unexpected": 1},
                None,
            ]:
                target.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, "line 1"):
                    EssayBank.from_jsonl(target)
        with self.assertRaises(ValueError):
            EssayBank([self.record, self.record])
        for scope in [
            {"start_year": 1791},
            {"start_year": 1800, "end_year": 1700},
            {"start_year": 0, "end_year": 10},
            {"aspects": "economy"},
        ]:
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                EssayScope.from_dict(scope)

    def test_dense_index_embeds_questions_only_and_retrieves_original(self):
        client = FixtureEmbedder()
        index = self.bank.build_index(client)
        self.assertEqual(
            client.calls, [([self.record.question, self.other.question], "document")]
        )
        result = self.bank.match(
            EssayQuery("A paraphrase represented by the test vector"),
            method="dense",
            index=index,
            embedder=client,
        )
        self.assertEqual(result.essay, self.original)
        self.assertEqual(
            client.calls[-1], (["A paraphrase represented by the test vector"], "query")
        )
        self.assertEqual((result.embedding_calls, result.generation_calls), (1, 0))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            index.write(path)
            loaded = EmbeddingIndex.read(path)
            result = self.bank.match(
                EssayQuery("Offline test"),
                method="dense",
                index=loaded,
                query_vector=[1, 0],
                encoder_id=client.identity,
            )
            self.assertEqual(result.record_id, "constitution")
            self.assertEqual(result.embedding_calls, 0)

    def test_dense_rejects_stale_index_wrong_encoder_and_bad_vectors(self):
        index = self.bank.build_index(FixtureEmbedder())
        changed = EssayBank(
            [replace(self.record, question="Changed question"), self.other]
        )
        with self.assertRaisesRegex(ValueError, "stale"):
            changed.match(
                EssayQuery("q"),
                method="dense",
                index=index,
                query_vector=[1, 0],
                encoder_id=index.encoder_id,
            )
        with self.assertRaisesRegex(ValueError, "identity"):
            self.bank.match(
                EssayQuery("q"),
                method="dense",
                index=index,
                query_vector=[1, 0],
                encoder_id="wrong",
            )
        for vector in [
            [1, 0, 0],
            [0, 0],
            [float("nan"), 0],
            [float("inf"), 0],
            [True, 0],
        ]:
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                self.bank.match(
                    EssayQuery("q"),
                    method="dense",
                    index=index,
                    query_vector=vector,
                    encoder_id=index.encoder_id,
                )
        result = self.bank.match(
            EssayQuery("q"),
            method="dense",
            index=index,
            query_vector=[1, 1],
            encoder_id=index.encoder_id,
        )
        self.assertEqual(result.reason, "ambiguous")

    def test_invalid_thresholds_empty_bank_and_no_lexical_model_inputs(self):
        for threshold in [-1, 1.01, float("nan"), True]:
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                self.bank.match(EssayQuery("q"), min_score=threshold)
        with self.assertRaises(ValueError):
            self.bank.match(EssayQuery("q"), embedder=FixtureEmbedder())
        self.assertEqual(EssayBank([]).match(EssayQuery("q")).reason, "empty_bank")

    def test_bundled_complete_essays_and_paraphrase_example(self):
        examples = Path(__file__).resolve().parents[1] / "examples"
        bank = EssayBank.from_jsonl(examples / "essay-bank.jsonl")
        self.assertEqual(len(bank.records), 2)
        self.assertTrue(
            all(len(r.essay.split()) >= 300 and r.sources for r in bank.records)
        )
        query = EssayQuery.from_dict(
            json.loads((examples / "essay-query.json").read_text(encoding="utf-8"))
        )
        self.assertNotIn(query.question, [r.question for r in bank.records])
        result = bank.match(query)
        self.assertEqual(result.record_id, "demo-1791-ustroj")
        self.assertEqual(result.essay, bank.records[0].essay)
        mismatch = EssayQuery.from_dict(
            json.loads(
                (examples / "essay-query-no-match.json").read_text(encoding="utf-8")
            )
        )
        self.assertEqual(bank.match(mismatch).status, "no_match")


if __name__ == "__main__":
    unittest.main()
