import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/checkpoints"))
from answer_contract import solve
from closed_answers import CONTRACT, layout, render


class ClosedAnswerTests(unittest.TestCase):
    def question(self, kind="true_false", slots=None, values=None):
        return SimpleNamespace(type="choice" if kind == "multi_choice" else kind,
            prompt="Oceń każde stwierdzenie.", source_text="Źródło", images=["map.png"],
            constraints={"coverage": {"answer_structure": {"kind": kind,
                "slots": slots or ["1", "2", "3"], "allowed_values": values or ["P", "F"]}}})

    def test_requires_every_slot_and_current_labels(self):
        structure = layout(self.question())
        self.assertEqual(render({"3": "F", "1": "F", "2": "P"}, structure), "1: F\n2: P\n3: F")
        for invalid in ({"1": "P"}, {"1": "P", "2": "P", "3": "yes"},
                        {"1": "P", "2": "P", "3": "F", "4": "P"}, []):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                render(invalid, structure)

    def test_repeated_matching_values_are_allowed(self):
        structure = layout(self.question("matching", ["X", "Y"], ["4", "9"]))
        self.assertEqual(render({"X": "9", "Y": "9"}, structure), "X: 9\nY: 9")

    def test_single_and_multiple_choices(self):
        self.assertEqual(render({"Selection": "Z"}, layout(self.question("choice", ["Selection"], ["W", "Z"]))), "Z")
        self.assertEqual(render({"1": "D", "2": "A"}, layout(self.question("multi_choice", ["1", "2"], ["A", "D"]))), "1: D\n2: A")

    def test_explanation_and_unknown_shapes_fall_back(self):
        q = self.question()
        q.prompt += " Uzasadnij."
        self.assertIsNone(layout(q))
        q.prompt = "Inne zadanie"
        q.constraints = {}
        self.assertIsNone(layout(q))

    def test_provider_gets_schema_and_original_images_then_restores_schema(self):
        q = self.question()
        original = {"original": True}
        seen = []
        client = SimpleNamespace(response_format=original)
        def generate(text, question, budget, **kwargs):
            seen.append((text, question, client.response_format))
            return '{"1":"P","2":"F","3":"F"}'
        client.generate = generate
        result = solve(q, {"client": client, "budget": object(), "output_contract": CONTRACT})
        self.assertEqual(result["answer"], "1: P\n2: F\n3: F")
        self.assertIs(client.response_format, original)
        self.assertIs(seen[0][1], q)
        self.assertNotIn("jednym polem answer", seen[0][0])
        self.assertEqual(seen[0][2]["json_schema"]["schema"]["required"], ["1", "2", "3"])
        client.generate = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("provider down"))
        with self.assertRaises(RuntimeError):
            solve(q, {"client": client, "budget": object(), "output_contract": CONTRACT})
        self.assertIs(client.response_format, original)


if __name__ == "__main__":
    unittest.main()
