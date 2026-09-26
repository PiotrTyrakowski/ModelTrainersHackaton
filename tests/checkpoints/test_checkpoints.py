import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/checkpoints'))
from checkpoint import check_snapshot, digest, file_hash, report_checkpoint, run_checkpoint, write
from reporting import build_report, markdown


def fixture():
    config = {'variants': ['direct'], 'strategy': {'output_contract': 'complete_answer_v1'}}
    items = [{'id': str(i), 'type': kind, 'max_points': points, 'question_hash': f'h{i}', 'selected': True}
             for i, kind, points in [(1, 'choice', 1), (2, 'essay', 15), (3, 'image', 2)]]
    snapshot = {'schema_version': 1, 'checkpoint': 'test', 'exam_id': 'test-exam', 'items': items,
                'exam_max_points': 18, 'exam_sha256': 'exam', 'keys_sha256': 'keys', 'key_semantic_hash': 'semkeys',
                'selected_dataset_hash': 'dataset', 'config_sha256': digest(config), 'files': {},
                'model': 'test-model', 'model_artifact_hash': 'weights', 'model_provenance': {'total_learned_bytes': 100},
                'execution_environment': 'test only', 'target': {'points': 10, 'basis': 'experimental'}, 'runner_root': '/unused'}
    rows = [{'question_id': i['id'], 'type': i['type'], 'variant': 'direct', 'max_points': i['max_points'],
             'question_hash': i['question_hash'], 'status': 'ok', 'points': 1 if i['id'] == '1' else None,
             'seconds': 2, 'calls': 1, 'prediction': {'answer': 'example', 'evidence': []},
             'usage': [{'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}], 'raw_responses': []}
            for i in items]
    run = {'config': config, 'model': 'test-model', 'demo': False, 'results': rows, 'dataset_hash': 'dataset', 'key_hash': 'semkeys'}
    return snapshot, run


class ReportingTests(unittest.TestCase):
    def test_pending_are_unknown_not_wrong(self):
        snapshot, run = fixture()
        report = build_report(snapshot, run)
        row = report['variants']['direct']
        self.assertEqual((row['score_lower_bound'], row['score_upper_bound']), (1, 18))
        self.assertEqual(row['pending_max_points'], 17)
        self.assertEqual(row['target_status'], 'grading_incomplete')
        self.assertEqual(row['by_type']['essay']['exam_max_points'], 15)
        self.assertIn('not an official pass', markdown(report))

    def test_missing_and_excluded_separate(self):
        snapshot, run = fixture()
        snapshot['items'][2]['selected'] = False
        run['results'] = run['results'][:1]
        row = build_report(snapshot, run)['variants']['direct']
        self.assertEqual(row['selected_not_run_ids'], ['2'])
        self.assertEqual(row['excluded_ids'], ['3'])
        self.assertEqual(row['exam_max_points'], 18)
        self.assertEqual(row['score_upper_bound'], 16)
        self.assertEqual(row['target_status'], 'run_incomplete')

    def test_target_never_defaults_to_pass(self):
        snapshot, run = fixture()
        for row in run['results']: row['points'] = row['max_points']
        snapshot['target']['points'] = None
        self.assertEqual(build_report(snapshot, run)['variants']['direct']['target_status'], 'target_not_specified')
        snapshot['target']['points'] = 10
        self.assertEqual(build_report(snapshot, run)['variants']['direct']['target_status'], 'reached_provisionally')

    def test_rejects_invalid_rows(self):
        mutations = [lambda rs: rs.append(copy.deepcopy(rs[0])),
                     lambda rs: rs[0].update(question_id='unknown'),
                     lambda rs: rs[0].update(question_hash='changed'),
                     lambda rs: rs[0].update(points=2),
                     lambda rs: rs[0].update(points=float('nan')),
                     lambda rs: rs[0].update(seconds=-1),
                     lambda rs: rs[0].update(status='error', points=1),
                     lambda rs: rs[0].update(calls=.5)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                snapshot, run = fixture(); mutation(run['results'])
                with self.assertRaises(ValueError): build_report(snapshot, run)

    def test_failure_categories_and_unknown_usage(self):
        snapshot, run = fixture()
        run['results'][0].update(status='error', error_type='JSONDecodeError', prediction=None, points=0,
                                 usage=[None], raw_responses=[{'content': '{', 'finish_reason': 'length'}])
        run['results'][1].update(status='error', error_type='TimeoutError', prediction=None, points=0, usage=[])
        run['results'][2].update(status='over_budget', points=0)
        row = build_report(snapshot, run)['variants']['direct']
        self.assertEqual(row['format_failure_ids'], ['1'])
        self.assertEqual(row['technical_failure_ids'], ['2'])
        self.assertEqual(row['over_budget_ids'], ['3'])
        self.assertEqual(row['truncated_ids'], ['1'])
        self.assertEqual(row['tokens']['total_tokens'], {'known_sum': 30, 'reported_calls': 1, 'unknown_calls': 2})
        self.assertEqual(row['target_status'], 'invalid_submission_format')

    def test_no_overall_gain_claim_with_ungraded_items(self):
        snapshot, run = fixture(); before = build_report(snapshot, run)
        run['results'][0]['points'] = 0
        comparison = build_report(snapshot, run, before)['comparison']
        self.assertEqual(comparison['variants'][0]['common_graded_delta'], -1)
        self.assertIsNone(comparison['variants'][0]['full_exam_delta'])
        snapshot['keys_sha256'] = 'new-keys'
        self.assertEqual(build_report(snapshot, run, before)['comparison']['status'], 'incomparable')

    def test_complete_paired_delta(self):
        snapshot, run = fixture()
        for row in run['results']: row['points'] = 0
        before = build_report(snapshot, run)
        run['results'][1]['points'] = 9
        report = build_report(snapshot, run, before)
        self.assertEqual(report['comparison']['variants'][0]['full_exam_delta'], 9)


class SnapshotTests(unittest.TestCase):
    def prepared(self, directory):
        snapshot, run = fixture()
        write(directory / 'snapshot.json', snapshot); write(directory / 'config.json', run['config'])
        return snapshot, run

    def test_dependency_and_config_changes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); snapshot, run = self.prepared(directory)
            dependency = directory / 'dependency.txt'; dependency.write_text('original')
            snapshot['files']['dependency'] = {'path': str(dependency), 'sha256': file_hash(dependency)}
            write(directory / 'snapshot.json', snapshot)
            check_snapshot(directory)
            dependency.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Pinned dependency changed'): check_snapshot(directory)
            write(directory / 'config.json', {'changed': True})
            with self.assertRaisesRegex(ValueError, 'configuration changed'): check_snapshot(directory, verify_files=False)

    def test_grading_cannot_rewrite_prediction(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); _, run = self.prepared(directory)
            write(directory / 'run.json', run)
            run['results'][0]['prediction']['answer'] = 'rewritten'
            write(directory / 'graded.json', run)
            with self.assertRaisesRegex(ValueError, 'Grading changed predictions'):
                report_checkpoint(directory, directory / 'graded.json')

    def test_report_is_offline_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); _, run = self.prepared(directory); write(directory / 'run.json', run)
            with patch('urllib.request.urlopen', side_effect=AssertionError('No network allowed')):
                report_checkpoint(directory)
            self.assertTrue((directory / 'checkpoint-report.md').is_file())
            with self.assertRaisesRegex(ValueError, 'output exists'): report_checkpoint(directory)

    def test_interrupt_preserves_answer_journal(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); snapshot, run = self.prepared(directory)
            snapshot['runner_root'] = temp; write(directory / 'snapshot.json', snapshot)
            class InterruptedEvaluator:
                def run(self, config, on_result):
                    on_result(run['results'][0]); raise KeyboardInterrupt()
            with patch('checkpoint.legacy', return_value=(InterruptedEvaluator(), None, None)):
                with self.assertRaises(KeyboardInterrupt): run_checkpoint(directory)
            journal = (directory / 'answers.partial.jsonl').read_text().splitlines()
            self.assertEqual(len(journal), 1)
            self.assertEqual(json.loads(journal[0])['question_id'], '1')
            self.assertFalse((directory / 'run.json').exists())
            with self.assertRaisesRegex(ValueError, 'already started'): run_checkpoint(directory)


if __name__ == '__main__': unittest.main()
