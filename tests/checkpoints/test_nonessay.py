import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/evaluation'), str(ROOT / 'scripts/exams')]
from build_nonessay import select_nonessay
from nonessay_suite import aggregate
from reporting import build_report
from test_checkpoints import fixture


class NonessayTests(unittest.TestCase):
    def parent(self):
        exam = {'items': [{'id': '1', 'max_points': 45}, {'id': '2', 'max_points': 15}]}
        types = {'1': 'open', '2': 'essay'}
        rows = [{'id': '1', 'prompt': 'Original'}, {'id': '2', 'prompt': 'Essay'}]
        return exam, types, rows, copy.deepcopy(rows), copy.deepcopy(rows)

    def test_keeps_exact_payload_and_excludes_essay(self):
        args = self.parent(); before = copy.deepcopy(args)
        self.assertEqual(select_nonessay(*args), ({'1'}, {'2'}))
        self.assertEqual(args, before)

    def test_rejects_missing_grading_or_duplicate_parent(self):
        args = self.parent(); args[-1].pop()
        with self.assertRaises(ValueError): select_nonessay(*args)
        args = self.parent(); args[0]['items'].append(copy.deepcopy(args[0]['items'][0]))
        with self.assertRaises(ValueError): select_nonessay(*args)

    def test_rejects_wrong_denominator_or_absent_essay(self):
        args = self.parent(); args[0]['items'][0]['max_points'] = 44
        with self.assertRaises(ValueError): select_nonessay(*args)
        args = self.parent(); args[1]['2'] = 'open'
        with self.assertRaises(ValueError): select_nonessay(*args)

    def report(self, pending=False):
        snap, run = fixture()
        snap['exam_max_points'] = 45
        snap['items'] = [snap['items'][0]]
        snap['items'][0].update(max_points=45)
        run['results'] = [run['results'][0]]
        run['results'][0].update(max_points=45, variant='bm25', points=None if pending else 9)
        run['config']['variants'] = ['bm25']
        report = build_report(snap, run)
        suite = {'model': {'tag': 'test-model', 'manifest_sha256': 'weights'},
                 'papers': [{'name': 'test', 'exam_id': 'test-exam', 'items': 1, 'points': 45}]}
        return suite, report

    def test_percentage_uses_nonessay_denominator(self):
        suite, report = self.report()
        result = aggregate(suite, [report])
        self.assertEqual((result['earned_points_so_far'], result['max_points'], result['score_percent']), (9, 45, 20))

    def test_pending_is_unknown_not_zero_score(self):
        suite, report = self.report(pending=True)
        result = aggregate(suite, [report])
        self.assertFalse(result['complete'])
        self.assertIsNone(result['score_percent'])
        self.assertEqual(result['possible_points'], [0, 45])

    def test_rejects_missing_and_duplicate_reports(self):
        suite, report = self.report()
        for reports in [[], [report, report]]:
            with self.assertRaises(ValueError): aggregate(suite, reports)

    def test_rejects_other_model_or_full_paper_denominator(self):
        suite, report = self.report()
        for change in ['digest', 'tag', 'denominator']:
            r = copy.deepcopy(report)
            if change == 'digest': r['model_artifact_hash'] = 'other'
            if change == 'tag': r['model'] = '0.8B'
            if change == 'denominator': r['variants']['bm25']['exam_max_points'] = 60
            with self.assertRaises(ValueError): aggregate(suite, [r])

    def test_rejects_essay_in_result(self):
        suite, report = self.report(); report['items'][0]['type'] = 'essay'
        with self.assertRaises(ValueError): aggregate(suite, [report])


if __name__ == '__main__': unittest.main()
