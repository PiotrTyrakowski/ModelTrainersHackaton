from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tasks_data.cli import main
from tasks_data.essay_bank import EssayRecord, EssayBank, EssayQuery, EmbeddingIndex


class CliTests(unittest.TestCase):
    def fixture(self, root):
        essay = "  Zażółć gęślą jaźń.\r\nDruga linia.\n"
        bank = EssayBank([EssayRecord("e", "Przyczyny rewolucji francuskiej", essay)])
        bank.write_jsonl(root / "bank.jsonl")
        (root / "query.json").write_text(
            json.dumps({"question": "Przyczyny rewolucji francuskiej"})
        )
        return bank, essay

    def test_lexical_match_preserves_exact_bytes_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, essay = self.fixture(root)
            with redirect_stdout(io.StringIO()), patch(
                "socket.socket", side_effect=AssertionError("network forbidden")
            ):
                main(
                    [
                        "essay-match",
                        str(root / "bank.jsonl"),
                        str(root / "query.json"),
                        "--essay-output",
                        str(root / "answer.txt"),
                        "--output",
                        str(root / "trace.json"),
                    ]
                )
            self.assertEqual((root / "answer.txt").read_bytes(), essay.encode())
            self.assertEqual(
                json.loads((root / "trace.json").read_text())["status"], "matched"
            )

    def test_no_match_has_distinct_exit_and_no_stale_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            (root / "query.json").write_text(
                json.dumps({"question": "Unrelated task", "min_words": 300})
            )
            with redirect_stdout(io.StringIO()), self.assertRaises(
                SystemExit
            ) as caught:
                main(
                    [
                        "essay-match",
                        str(root / "bank.jsonl"),
                        str(root / "query.json"),
                        "--essay-output",
                        str(root / "answer.txt"),
                        "--output",
                        str(root / "trace.json"),
                    ]
                )
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse((root / "answer.txt").exists())
            self.assertEqual(
                json.loads((root / "trace.json").read_text())["status"], "no_match"
            )
            (root / "answer.txt").write_text("Keep this user file")
            with self.assertRaises(ValueError):
                main(
                    [
                        "essay-match",
                        str(root / "bank.jsonl"),
                        str(root / "query.json"),
                        "--essay-output",
                        str(root / "answer.txt"),
                    ]
                )
            self.assertEqual((root / "answer.txt").read_text(), "Keep this user file")

    def test_dense_precomputed_vector_needs_no_http(self):
        class Vectors:
            identity = "fixture-encoder"

            def embed(self, texts, *, role):
                return [[1.0, 0.0] for _ in texts]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bank, essay = self.fixture(root)
            bank.build_index(Vectors()).write(root / "index.json")
            (root / "vector.json").write_text(
                json.dumps({"encoder_id": "fixture-encoder", "vector": [1, 0]})
            )
            with redirect_stdout(io.StringIO()), patch(
                "socket.socket", side_effect=AssertionError("network forbidden")
            ):
                main(
                    [
                        "essay-match",
                        str(root / "bank.jsonl"),
                        str(root / "query.json"),
                        "--method",
                        "dense",
                        "--index",
                        str(root / "index.json"),
                        "--query-vector",
                        str(root / "vector.json"),
                        "--essay-output",
                        str(root / "answer.txt"),
                    ]
                )
            self.assertEqual((root / "answer.txt").read_bytes(), essay.encode())

    def test_reject_colliding_output_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            with self.assertRaises(ValueError):
                main(
                    [
                        "essay-match",
                        str(root / "bank.jsonl"),
                        str(root / "query.json"),
                        "--output",
                        str(root / "same"),
                        "--essay-output",
                        str(root / "same"),
                    ]
                )
            self.assertFalse((root / "same").exists())
