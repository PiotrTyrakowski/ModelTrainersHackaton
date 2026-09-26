from pathlib import Path
import tempfile
import unittest
from tasks_data.pdf_import import segment_pages, import_pdf


class PdfImportTests(unittest.TestCase):
    def test_shared_sources_cross_pages_and_character_spans(self):
        pages = [
            "Cover\nZadanie 2.\nShared source.",
            "Zadanie 2.1. (0–1)\nFirst prompt.\nZadanie 2.2. (0–2)\nSecond prompt.",
            "Zadanie 3. (0–1)\nLast prompt.",
        ]
        tasks = segment_pages(pages, "exam")
        self.assertEqual([t.id for t in tasks], ["2.1", "2.2", "3"])
        self.assertEqual([t.max_points for t in tasks], [1, 2, 1])
        for task in tasks[:2]:
            self.assertIn("Shared source.", task.source_text)
            self.assertEqual(task.source_refs[0].pages, (1, 2))
            for span in task.source_refs[0].spans:
                self.assertTrue(pages[span.page - 1][span.start : span.end])
            self.assertEqual(task.review_status, "needs_review")
        self.assertIn("First prompt.", tasks[0].prompt)
        self.assertNotIn("Second prompt.", tasks[0].prompt)

    def test_duplicates_empty_pages_and_unrecognised_points_remain_visible(self):
        tasks = segment_pages(["Zadanie 1.\nA\nZadanie 1.\nB"], "exam")
        self.assertEqual([t.id for t in tasks], ["1~1", "1~2"])
        self.assertIsNone(tasks[0].max_points)
        self.assertTrue(any("Duplicate" in note for note in tasks[0].review_notes))
        self.assertEqual(segment_pages(["", "No headers"], "exam"), [])

    def test_real_pdf_extraction_preserves_raw_and_blocks_export(self):
        from reportlab.pdfgen.canvas import Canvas

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "paper.pdf"
            c = Canvas(str(pdf))
            c.drawString(50, 750, "Zadanie 1. (0-1)")
            c.drawString(50, 730, "Source and question")
            c.save()
            ds = import_pdf(pdf, root / "out", "fixture", render=False)
            self.assertEqual(ds.validate()["tasks"], 1)
            self.assertEqual((root / "out/raw/exam.pdf").read_bytes(), pdf.read_bytes())
            self.assertTrue((root / "out/raw/pages.jsonl").exists())
            with self.assertRaises(ValueError):
                ds.export_solver_inputs(root / "inputs.jsonl")

    def test_reject_marking_scheme(self):
        from reportlab.pdfgen.canvas import Canvas

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "key.pdf"
            c = Canvas(str(pdf))
            for _ in range(3):
                c.drawString(50, 750, "Zasady oceniania")
                c.showPage()
            c.save()
            with self.assertRaises(ValueError):
                import_pdf(pdf, root / "out", "fixture", render=False)

    def test_archived_page_texts_and_spans_are_validated(self):
        from dataclasses import replace
        from reportlab.pdfgen.canvas import Canvas
        from tasks_data import SourceRef, PageSpan

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "paper.pdf"
            c = Canvas(str(pdf))
            c.drawString(50, 750, "Zadanie 1. (0-1)")
            c.drawString(50, 730, "Prompt")
            c.save()
            ds = import_pdf(pdf, root / "out", "fixture", render=False)
            ds.tasks = [
                replace(
                    ds.tasks[0],
                    source_refs=(
                        SourceRef("exam-pdf", (1,), (PageSpan(1, 0, 99999),)),
                    ),
                )
            ]
            with self.assertRaises(ValueError):
                ds.validate()
