"""Offline, conservative accounting for fixed exam checkpoints."""
from __future__ import annotations
import math
import statistics


def number(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f'Invalid {name}')
    return value


def format_failure(row, string_answer):
    prediction = row.get('prediction')
    if prediction is not None:
        return not isinstance(prediction, dict) or 'answer' not in prediction or (string_answer and not isinstance(prediction['answer'], str))
    # A parse failure with a recorded generation is distinct from a transport error.
    return bool(row.get('raw_responses')) and row.get('error_type') == 'JSONDecodeError'


def summarise(items, rows, target, string_answer):
    indexed = {r['question_id']: r for r in rows}
    selected = [i for i in items if i['selected']]
    missing = [i for i in selected if i['id'] not in indexed]
    excluded = [i for i in items if not i['selected']]
    pending = [r for r in rows if r['points'] is None]
    earned = sum(r['points'] for r in rows if r['points'] is not None)
    seconds = sorted(r['seconds'] for r in rows)
    bad_format = [r for r in rows if format_failure(r, string_answer)]
    failures = [r for r in rows if r['status'] == 'error' and r not in bad_format]
    usage = [entry for r in rows for entry in r.get('usage', [])]
    calls = sum(r['calls'] for r in rows)
    tokens = {}
    for field in ['prompt_tokens', 'completion_tokens', 'total_tokens']:
        known = [u[field] for u in usage if isinstance(u, dict) and u.get(field) is not None]
        for value in known: number(value, field)
        tokens[field] = {'known_sum': sum(known) if known else None, 'reported_calls': len(known),
                         'unknown_calls': max(calls, len(usage)) - len(known)}
    if target is None: target_status = 'target_not_specified'
    elif missing: target_status = 'run_incomplete'
    elif pending: target_status = 'grading_incomplete'
    elif bad_format: target_status = 'invalid_submission_format'
    else: target_status = 'reached_provisionally' if earned >= target else 'below_target'
    return {
        'earned_points': earned, 'exam_max_points': sum(i['max_points'] for i in items),
        'score_lower_bound': earned, 'score_upper_bound': earned + sum(r['max_points'] for r in pending) + sum(i['max_points'] for i in missing),
        'exam_items': len(items), 'selected_items': len(selected), 'processed_items': len(rows),
        'answered_items': sum(isinstance(r.get('prediction'), dict) and bool(r['prediction'].get('answer')) for r in rows),
        'empty_answer_items': sum(isinstance(r.get('prediction'), dict) and r['prediction'].get('answer') == '' for r in rows),
        'selected_not_run_ids': [i['id'] for i in missing], 'selected_not_run_points': sum(i['max_points'] for i in missing),
        'excluded_ids': [i['id'] for i in excluded], 'excluded_points': sum(i['max_points'] for i in excluded),
        'pending_ids': [r['question_id'] for r in pending], 'pending_max_points': sum(r['max_points'] for r in pending),
        'abstained_ids': [r['question_id'] for r in rows if r['status'] == 'abstained'],
        'technical_failure_ids': [r['question_id'] for r in failures],
        'format_failure_ids': [r['question_id'] for r in bad_format],
        'over_budget_ids': [r['question_id'] for r in rows if r['status'] == 'over_budget'],
        'truncated_ids': [r['question_id'] for r in rows if any(raw.get('finish_reason') == 'length' for raw in r.get('raw_responses', []))],
        'run_complete': not missing, 'full_exam_selected': not excluded, 'grading_complete': not pending,
        'target_status': target_status, 'calls': calls, 'tokens': tokens,
        'latency_seconds': {'sum': sum(seconds), 'mean': statistics.mean(seconds) if seconds else None,
                            'median': statistics.median(seconds) if seconds else None,
                            'p95': seconds[math.ceil(.95 * len(seconds)) - 1] if seconds else None,
                            'max': max(seconds) if seconds else None},
    }


def compare(current, previous):
    if current['comparison_contract'] != previous.get('comparison_contract'):
        return {'status': 'incomparable', 'reason': 'Exam inputs, answer keys, rubric, or maximum points differ'}
    changes = [field for field in ['model_artifact_hash', 'config_sha256', 'dependency_hashes', 'execution_environment']
               if current.get(field) != previous.get(field)]
    pairs = []
    for variant, now in current['variants'].items():
        before = previous.get('variants', {}).get(variant)
        if before is None: continue
        old_rows = {r['question_id']: r for r in previous['items'] if r['variant'] == variant}
        common = [(r, old_rows[r['question_id']]) for r in current['items']
                  if r['variant'] == variant and r['question_id'] in old_rows
                  and r['points'] is not None and old_rows[r['question_id']]['points'] is not None]
        complete = all(s['run_complete'] and s['grading_complete'] and s['full_exam_selected'] for s in [now, before])
        pairs.append({'variant': variant, 'full_exam_delta': now['earned_points'] - before['earned_points'] if complete else None,
                      'common_graded_items': len(common), 'common_graded_max_points': sum(a['max_points'] for a, _ in common),
                      'common_graded_delta': sum(a['points'] - b['points'] for a, b in common),
                      'type_deltas': {kind: sum(a['points'] - b['points'] for a, b in common if a['type'] == kind)
                                      for kind in sorted({a['type'] for a, _ in common})}})
    return {'status': 'paired_local_comparison', 'previous_checkpoint': previous['checkpoint'],
            'changed_factors': changes, 'variants': pairs,
            'note': 'Common graded item deltas are not a full-exam improvement. Changes in graders or runtime can affect comparison.'}


def build_report(snapshot, run, previous=None):
    items = snapshot['items']
    specs = {item['id']: item for item in items}
    if len(specs) != len(items): raise ValueError('Duplicate exam IDs')
    variants = run['config']['variants']
    if not variants or len(set(variants)) != len(variants): raise ValueError('Invalid variants')
    seen = set()
    for row in run['results']:
        pair = (row['variant'], row['question_id'])
        spec = specs.get(row['question_id'])
        if pair in seen or row['variant'] not in variants or spec is None or not spec['selected']:
            raise ValueError('Duplicate, unknown, or excluded result ID')
        seen.add(pair)
        if any(row[field] != spec[field] for field in ['type', 'max_points', 'question_hash']):
            raise ValueError('Result differs from pinned question')
        if row['status'] not in {'ok', 'error', 'over_budget', 'abstained'}: raise ValueError('Unknown result status')
        if row['points'] is not None and number(row['points'], 'points') > spec['max_points']: raise ValueError('Points exceed maximum')
        if row['status'] != 'ok' and row['points'] != 0: raise ValueError('Failed or abstained result must have zero points')
        number(row['seconds'], 'latency'); number(row['calls'], 'calls')
        if int(row['calls']) != row['calls']: raise ValueError('Calls must be an integer')
    string_answer = run['config'].get('strategy', {}).get('output_contract') == 'complete_answer_v1'
    summaries = {}
    for variant in variants:
        rows = [r for r in run['results'] if r['variant'] == variant]
        summary = summarise(items, rows, snapshot['target']['points'], string_answer)
        summary['by_type'] = {kind: summarise([i for i in items if i['type'] == kind], [r for r in rows if r['type'] == kind], None, string_answer)
                              for kind in sorted({i['type'] for i in items})}
        summaries[variant] = summary
    hashes = {role: f['sha256'] for role, f in snapshot['files'].items()}
    report = {
        'schema_version': 1, 'checkpoint': snapshot['checkpoint'], 'exam_id': snapshot['exam_id'],
        'grading_status': 'local/provisional; not an official pass', 'target': snapshot['target'],
        'model': snapshot['model'], 'model_artifact_hash': snapshot['model_artifact_hash'],
        'learned_weight_bytes': snapshot['model_provenance'].get('total_learned_bytes'),
        'config_sha256': snapshot['config_sha256'], 'dependency_hashes': hashes,
        'execution_environment': snapshot['execution_environment'],
        'comparison_contract': {'exam': snapshot['exam_sha256'], 'keys': snapshot['keys_sha256'],
                                'rubric': hashes.get('rubrics'), 'question_inputs': hashes.get('questions'),
                                'exam_max_points': snapshot['exam_max_points']},
        'variants': summaries,
        'items': [{key: row.get(key) for key in ['question_id', 'type', 'variant', 'max_points', 'question_hash', 'status', 'points', 'grader', 'grade_reason']}
                  for row in run['results']],
        'notes': ['Pending grades and selected-but-not-run items remain unknown; excluded items contribute zero to the full-paper total.',
                  'Latency is per-question wall time including processing; token counts are partial when the server does not report usage.',
                  'Model artifact metadata does not by itself verify live server identity. Development results are not an untouched final test.'],
    }
    if previous is not None: report['comparison'] = compare(report, previous)
    return report


def markdown(report):
    lines = [f'# Checkpoint: {report["checkpoint"]}', '',
             f'Model: {report["model"]}; learned weights: {report["learned_weight_bytes"]} bytes.',
             f'Runtime: {report["execution_environment"]}.', '', report['grading_status'] + '.',
             f'Target: {report["target"]["points"]}; basis: {report["target"]["basis"]}.', '',
             '| Variant | Earned / full paper | Possible range | Processed | Pending | Excluded | Target status |',
             '|---|---:|---:|---:|---:|---:|---|']
    for variant, row in report['variants'].items():
        lines.append(f'| {variant} | {row["earned_points"]:g}/{row["exam_max_points"]:g} | {row["score_lower_bound"]:g}–{row["score_upper_bound"]:g} | {row["processed_items"]}/{row["exam_items"]} | {len(row["pending_ids"])} | {len(row["excluded_ids"])} | {row["target_status"]} |')
        lines.extend(['', f'## {variant}: points by question type', '', '| Type | Earned / maximum | Pending | Not run | Excluded |', '|---|---:|---:|---:|---:|'])
        for kind, sub in row['by_type'].items():
            lines.append(f'| {kind} | {sub["earned_points"]:g}/{sub["exam_max_points"]:g} | {len(sub["pending_ids"])} | {len(sub["selected_not_run_ids"])} | {len(sub["excluded_ids"])} |')
        lines.extend(['', f'Calls: {row["calls"]}; total question time: {row["latency_seconds"]["sum"]:.2f}s.',
                      f'Technical failures: {row["technical_failure_ids"]}; format failures: {row["format_failure_ids"]}; over budget: {row["over_budget_ids"]}; truncated: {row["truncated_ids"]}.', ''])
    if report.get('comparison'):
        import json
        lines.extend(['## Comparison', '', '```json', json.dumps(report['comparison'], ensure_ascii=False, indent=2), '```', ''])
    lines.extend(report['notes'])
    return '\n'.join(lines) + '\n'
