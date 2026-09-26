from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from tasks_data.imports import import_structured


class ImportTests(unittest.TestCase):
    def make_exam(self, root):
        (root / "image.png").write_bytes(b"fixture-bytes")
        exam = {
            "exam_id": "fixture",
            "max_points": 2,
            "items": [
                {
                    "id": "2.1",
                    "question": "Read the image.",
                    "source_text": "Source words.",
                    "max_points": 2,
                    "images": [
                        {
                            "path": "image.png",
                            "sha256": hashlib.sha256(b"fixture-bytes").hexdigest(),
                            "source_page": 4,
                        }
                    ],
                    "answer_format": "A string.",
                }
            ],
        }
        path = root / "exam.json"
        path.write_text(json.dumps(exam))
        return path

    def test_preserves_ids_sources_images_without_inventing_keys(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = self.make_exam(root)
            ds = import_structured(path, root / "out", {"2.1": "art"})
            self.assertEqual(ds.validate()["ready"], 1)
            t = ds.tasks[0]
            self.assertEqual(t.id, "2.1")
            self.assertEqual(t.source_refs[0].pages, (4,))
            self.assertEqual(
                (ds.root / t.image_paths[0]).read_bytes(), b"fixture-bytes"
            )
            self.assertEqual(ds.keys[0].kind, "manual")
            self.assertIsNone(ds.keys[0].expected)
            with self.assertRaises(ValueError):
                import_structured(path, root / "out", {"2.1": "art"})

    def test_unknown_type_stays_unreviewed_and_image_change_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = self.make_exam(root)
            ds = import_structured(path, root / "out")
            self.assertEqual(ds.validate()["needs_review"], 1)
            (root / "image.png").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                import_structured(path, root / "other")
            self.assertFalse((root / "other").exists())

    def test_key_in_exam_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = self.make_exam(root)
            exam = json.loads(path.read_text())
            exam["items"][0]["expected"] = "A"
            path.write_text(json.dumps(exam))
            with self.assertRaises(ValueError):
                import_structured(path, root / "out")
