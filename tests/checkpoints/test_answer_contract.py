import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/checkpoints"))
from answer_contract import CONTRACT, SCHEMA, prompt, solve, use_answer_contract


class AnswerContractTests(unittest.TestCase):
    def setUp(self):
        self.q = SimpleNamespace(type="comparison", prompt="Compare both sources and justify.",
                                 source_text="Original source text", images=("original.png",))

    def test_preserves_inputs_and_does_not_inject_example_answers(self):
        text = prompt(self.q, [])
        self.assertIn(self.q.prompt, text)
        self.assertIn(self.q.source_text, text)
        self.assertIn("uzasadnienie", text)
        self.assertNotIn('"answer":', text)  # No pre-filled candidate answer.
        self.q.type = "essay"
        self.assertIn("300–350", prompt(self.q, []))
        self.assertIn("dokładnie jeden temat", prompt(self.q, []))

    def test_same_question_and_budget_reach_provider(self):
        calls = []
        budget = object()
        client = SimpleNamespace(generate=lambda *args, **kwargs:
                                 calls.append((args, kwargs)) or '{"answer":"Finished answer"}')
        result = solve(self.q, {"client": client, "budget": budget})
        self.assertEqual(result, {"answer": "Finished answer", "evidence": []})
        self.assertIs(calls[0][0][1], self.q)  # Images remain on the original object.
        self.assertIs(calls[0][0][2], budget)
        self.assertEqual(calls[0][1], {"temperature": 0})

    def test_retrieval_trace_is_actual_corpus_content(self):
        passages = [{"id": "source-1", "source": "https://example.org/source", "text": "A fact."}]
        seen = []
        fake = SimpleNamespace(evidence=lambda q, ctx, mode: passages)
        client = SimpleNamespace(generate=lambda text, *a, **kw: seen.append(text) or '{"answer":"A fact."}')
        with patch.dict(sys.modules, {"matura_lab.strategies": fake}):
            result = solve(self.q, {"client": client, "budget": object()}, retrieval=True)
        self.assertEqual(result["retrieved_evidence"], passages)
        self.assertIn("A fact.", seen[0])
        self.assertNotIn("DODATKOWE MATERIAŁY", prompt(self.q, []))

    def test_rejects_incomplete_and_wrong_type_answers(self):
        for raw in ['{"answer":"unfinished', '{"answer":3}', '{"answer":"x","extra":1}']:
            with self.subTest(raw=raw), self.assertRaises((ValueError, json.JSONDecodeError)):
                solve(self.q, {"client": SimpleNamespace(generate=lambda *a, **kw: raw), "budget": object()})

    def test_registry_restored_even_after_error_and_config_is_explicit(self):
        originals = {"direct": object(), "bm25": object()}
        fake = SimpleNamespace(STRATEGIES=originals.copy())
        config = {"strategy": {"output_contract": CONTRACT}, "variants": ["direct", "bm25"],
                  "model": {"response_format": {"json_schema": {"schema": copy.deepcopy(SCHEMA)}}}}
        with patch.dict(sys.modules, {"matura_lab.strategies": fake}):
            with self.assertRaises(RuntimeError):
                with use_answer_contract(config):
                    self.assertNotEqual(fake.STRATEGIES, originals)
                    raise RuntimeError("interrupted")
            self.assertEqual(fake.STRATEGIES, originals)
            config["model"]["response_format"]["json_schema"]["schema"] = {}
            with self.assertRaises(ValueError), use_answer_contract(config):
                pass


if __name__ == "__main__":
    unittest.main()
