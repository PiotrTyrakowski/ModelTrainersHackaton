"""Run one pinned model on every paper in an explicit non-essay suite."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/checkpoints'))
from checkpoint import prepare, run_checkpoint, report_checkpoint, read, write


def verify_config(cfg, runner_root, entry, model):
    if cfg['model']['model'] != model['tag'] or cfg['model_provenance']['manifest_sha256'] != model['manifest_sha256']:
        raise ValueError('Suite requires the declared single model artifact')
    if cfg.get('strategy', {}).get('essay_bank') or cfg.get('question_ids') or cfg.get('types'):
        raise ValueError('No essay bank or partial selection in a non-essay suite')
    exam = read(Path(runner_root) / cfg['coverage']['exam'])
    types = read(Path(runner_root) / cfg['coverage']['types'])
    if exam.get('evaluation_scope', {}).get('kind') != 'nonessay' or 'essay' in types.values():
        raise ValueError('Requires an explicit non-essay input view')
    if cfg['exam_id'] != entry['exam_id'] or exam['exam_id'] != entry['exam_id']:
        raise ValueError('Config and suite must refer to the same paper')
    if (len(exam['items']) != entry['items'] or set(types) != {x['id'] for x in exam['items']}
            or sum(x['max_points'] for x in exam['items']) != entry['points'] or entry['points'] != 45):
        raise ValueError('Incomplete paper or wrong non-essay denominator')
    if cfg['variants'] != ['bm25']:
        raise ValueError('This frozen suite compares the BM25 harness only')


def aggregate(suite, reports):
    if len(reports) != len(suite['papers']) or len({r['exam_id'] for r in reports}) != len(reports):
        raise ValueError('Missing or duplicate paper reports')
    rows = []
    for entry, report in zip(suite['papers'], reports):
        if report['exam_id'] != entry['exam_id'] or report['model_artifact_hash'] != suite['model']['manifest_sha256']:
            raise ValueError('Wrong paper or model artifact')
        if report['model'] != suite['model']['tag'] or set(report['variants']) != {'bm25'}:
            raise ValueError('Wrong model or harness variant')
        s = report['variants']['bm25']
        if s['exam_max_points'] != entry['points'] or s['exam_items'] != entry['items'] or not s['full_exam_selected']:
            raise ValueError('Report does not cover the full non-essay scope')
        if 'essay' in s['by_type'] or any(x['type'] == 'essay' for x in report['items']):
            raise ValueError('Essay leaked into non-essay results')
        rows.append({'paper': entry['name'], 'checkpoint': report['checkpoint'], 'points': s['earned_points'],
                     'max_points': s['exam_max_points'], 'run_complete': s['run_complete'], 'grading_complete': s['grading_complete'],
                     'possible_points': [s['score_lower_bound'], s['score_upper_bound']], 'pending_ids': s['pending_ids'],
                     'missing_ids': s['selected_not_run_ids'], 'calls': s['calls'], 'seconds': s['latency_seconds']['sum'],
                     'tokens': s['tokens']['total_tokens'], 'technical_failure_ids': s['technical_failure_ids'],
                     'format_failure_ids': s['format_failure_ids'], 'truncated_ids': s['truncated_ids'],
                     'by_type': {k: {'points': v['earned_points'], 'max_points': v['exam_max_points'], 'pending_ids': v['pending_ids']}
                                 for k, v in s['by_type'].items()}})
    complete = all(r['run_complete'] and r['grading_complete'] for r in rows)
    maximum = sum(r['max_points'] for r in rows); earned = sum(r['points'] for r in rows)
    return {'scope': 'All non-essay tasks in the four declared development papers; not a full matura score',
            'grading': 'Provisional local rubric review, not independent or official', 'model': suite['model'],
            'complete': complete, 'earned_points_so_far': earned, 'max_points': maximum,
            'score_percent': 100 * earned / maximum if complete else None,
            'possible_points': [sum(r['possible_points'][i] for r in rows) for i in range(2)],
            'papers': rows}


def live_identity(config, model, loaded=False):
    base = config['model']['base_url'].removesuffix('/v1')
    with urllib.request.urlopen(base + ('/api/ps' if loaded else '/api/tags'), timeout=15) as response:
        state = json.load(response)
    matches = [x for x in state['models'] if x['name'] == model['tag'] and x['digest'] == model['manifest_sha256']]
    if not matches or (loaded and matches[0].get('context_length') != 8192):
        raise ValueError('Live model digest/context does not match the frozen suite')
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('command', choices=['prepare', 'run', 'report'])
    p.add_argument('--suite', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runner-root', type=Path, default=ROOT.parent / 'matura-lab')
    a = p.parse_args(); suite = read(a.suite); out = a.output.resolve()
    if len({x['name'] for x in suite['papers']}) != len(suite['papers']): raise ValueError('Duplicate paper names')
    if a.command == 'prepare':
        if out.exists(): raise ValueError('Use a fresh suite directory')
        for entry in suite['papers']:
            cfg = read(ROOT / entry['config']); verify_config(cfg, a.runner_root, entry, suite['model'])
        out.mkdir(parents=True)
        write(out / 'suite.json', suite)
        write(out / 'provenance.json', {'suite_sha256': hashlib.sha256(a.suite.read_bytes()).hexdigest(),
              'runner_root': str(a.runner_root.resolve()), 'suite_runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        for entry in suite['papers']:
            prepare(a.runner_root, ROOT / entry['config'], out / entry['name'], variants=['bm25'],
                    runtime_label='local macOS arm64 / Apple M5 Metal / Ollama 0.34.4 / context 8192',
                    note='User-requested 2B Q4 only; complete non-essay scope 45 points; no prepared essay route')
            print('PREPARED', entry['name'], entry['items'], 'items / 45 points', flush=True)
    else:
        if read(out / 'suite.json') != suite: raise ValueError('Suite configuration changed')
        if a.command == 'run':
            for entry in suite['papers']:
                folder = out / entry['name']; cfg = read(folder / 'config.json')
                write(folder / 'runtime-tags.json', live_identity(cfg, suite['model']))
                print('START', entry['name'], flush=True)
                run_checkpoint(folder); report_checkpoint(folder)
                write(folder / 'runtime-ps.json', live_identity(cfg, suite['model'], loaded=True))
                print('COMPLETE', entry['name'], flush=True)
        else:
            reports = []
            for entry in suite['papers']:
                folder = out / entry['name']; path = folder / 'checkpoint-graded.json'
                if not path.exists(): path = folder / 'checkpoint-report.json'
                reports.append(read(path))
            result = aggregate(suite, reports); write(out / 'suite-report.json', result)
            print(json.dumps({k: result[k] for k in ['complete', 'earned_points_so_far', 'max_points', 'score_percent', 'possible_points']}))


if __name__ == '__main__': main()
