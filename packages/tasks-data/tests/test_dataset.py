from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest
from tasks_data import Task, SourceRecord, SourceRef, AnswerKey, Dataset
from tasks_data.dataset import sha256_file


class DatasetTests(unittest.TestCase):
    def fixture(self, root):
        (root / "source.txt").write_text("A source, not an answer key.")
        source = SourceRecord(
            "s",
            "Source",
            "reference",
            "https://example.org/source",
            sha256_file(root / "source.txt"),
            "source.txt",
        )
        task = Task(
            "1",
            "exam",
            "Question?",
            question_type="choice",
            source_refs=(SourceRef("s"),),
            max_points=1,
            review_status="ready",
        )
        return Dataset("exam", [task], [source], [AnswerKey("1")], root=root)

    def test_roundtrip_export_has_no_keys_and_detects_changed_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds = self.fixture(root)
            ds.save()
            loaded = Dataset.load(root)
            self.assertEqual(
                [asdict(t) for t in loaded.tasks], [asdict(t) for t in ds.tasks]
            )
            path = root / "inputs.jsonl"
            loaded.export_solver_inputs(path)
            self.assertNotIn("expected", path.read_text())
            self.assertNotIn("grading", path.read_text())
            (root / "source.txt").write_text("Changed")
            with self.assertRaises(ValueError):
                Dataset.load(root)

    def test_rejects_grade_leakage_duplicate_ids_and_wrong_points(self):
        with self.assertRaises(ValueError):
            Task.from_dict({"id": "1", "exam_id": "e", "prompt": "p", "expected": "A"})
        with self.assertRaises(ValueError):
            Task("1", "e", "p", constraints={"nested": {"gold_answer": "A"}})
        with tempfile.TemporaryDirectory() as d:
            ds = self.fixture(Path(d))
            ds.tasks.append(ds.tasks[0])
            with self.assertRaises(ValueError):
                ds.validate()
            ds.tasks = ds.tasks[:1]
            ds.keys = [AnswerKey("1", max_points=2)]
            with self.assertRaises(ValueError):
                ds.validate()

    def test_review_and_path_boundaries(self):
        for p in ["/tmp/outside", "../outside", "a/../../outside", "a\\outside"]:
            with self.subTest(p=p), self.assertRaises(ValueError):
                Task("1", "e", "p", image_paths=(p,))
        with tempfile.TemporaryDirectory() as d:
            ds = self.fixture(Path(d))
            ds.tasks = [replace(ds.tasks[0], review_status="needs_review")]
            with self.assertRaises(ValueError):
                ds.export_solver_inputs(Path(d) / "inputs.jsonl")
            self.assertFalse((Path(d) / "inputs.jsonl").exists())

    def test_grading_sources_cannot_feed_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            ds = self.fixture(Path(d))
            ds.sources = [replace(ds.sources[0], kind="grading_pdf")]
            with self.assertRaises(ValueError):
                ds.validate()
