import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/checkpoints"))
from answer_contract import solve
from essay_routing import route


class EssayRoutingTests(unittest.TestCase):
    def setUp(self):
        self.settings = {"version": "reviewed_essay_v1",
            "bank": str(ROOT / "data/essay-bank/history-development-v1.jsonl"),
            "catalog": str(ROOT / "data/essay-bank/reviewed-topics-v1.json"),
            "min_score": 0.3, "min_margin": 0.03}
        catalog = json.loads(Path(self.settings["catalog"]).read_text())
        self.topic = catalog["topics"][0]["question"]
        self.q = SimpleNamespace(type="essay", images=[], source_text="", constraints={
            "min_words": 300, "coverage": {"answer_structure": {"kind": "essay", "min_words": 300, "topic_options": ["1", "2"]}}},
            prompt=catalog["introductions"][0] + "\n1. Inny temat.\n2. " + self.topic)

    def test_exact_body_correct_incoming_topic_number_and_zero_model_calls(self):
        record = json.loads(Path(self.settings["bank"]).read_text())
        with patch('urllib.request.urlopen', side_effect=AssertionError("No network")):
            result = solve(self.q, {"essay_bank": self.settings})
        self.assertEqual(result["answer"], "Temat 2.\n\n" + record["essay"])
        self.assertEqual(result["essay_routing"]["generation_calls"], 0)
        self.assertGreaterEqual(result["essay_routing"]["essay_words"], 300)

    def test_changed_scope_negation_and_requirements_abstain(self):
        for old, new in [("50.", "60."), ("osiągnęła", "nie osiągnęła"), ("trzy", "cztery")]:
            q = copy.deepcopy(self.q); q.prompt = q.prompt.replace(old, new)
            with self.subTest(change=new):
                answer, trace = route(q, self.settings)
                self.assertIsNone(answer); self.assertEqual(trace["status"], "no_match")
        q = copy.deepcopy(self.q); q.prompt = "Dodatkowo omów gospodarkę.\n" + q.prompt
        self.assertEqual(route(q, self.settings)[1]["reason"], "global_requirements_not_reviewed")

    def test_sources_and_too_long_minimum_abstain(self):
        q = copy.deepcopy(self.q); q.images = ["exhibit.png"]
        self.assertEqual(route(q, self.settings)[1]["reason"], "task_specific_sources")
        q = copy.deepcopy(self.q); q.source_text = "Required document"
        self.assertIsNone(route(q, self.settings)[0])
        self.q.constraints["min_words"] = 500
        self.assertIsNone(route(self.q, self.settings)[0])

    def test_no_match_uses_normal_generation(self):
        self.q.prompt = self.q.prompt.replace("50.", "60.")
        calls = []
        client = SimpleNamespace(generate=lambda *a, **kw: calls.append(a) or '{"answer":"New answer"}')
        result = solve(self.q, {"essay_bank": self.settings, "client": client, "budget": object()})
        self.assertEqual(result["answer"], "New answer")
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["essay_routing"]["status"], "no_match")

    def test_ambiguous_bank_abstains(self):
        record = json.loads(Path(self.settings["bank"]).read_text())
        duplicate = copy.deepcopy(record); duplicate["id"] = "duplicate"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bank.jsonl"
            path.write_text(json.dumps(record) + "\n" + json.dumps(duplicate) + "\n")
            settings = {**self.settings, "bank": str(path)}
            answer, trace = route(self.q, settings)
            self.assertIsNone(answer)
            self.assertEqual(trace["attempts"][-1]["reason"], "ambiguous")


if __name__ == "__main__":
    unittest.main()
