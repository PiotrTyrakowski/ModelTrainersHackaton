"""Build explicit 45-point non-essay views; never alter the original papers.

Reviewed PDF regions contain source/command geometry only. Marking records are
read in a separate final phase and never enter input text or images.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write_lines(path, rows):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))


def select_nonessay(exam, types, questions, keys, rubrics):
    """Retain every non-essay item and preserve the exact question payloads."""
    ids = {x['id'] for x in exam['items']}
    if len(ids) != len(exam['items']) or set(types) != ids or any({x['id'] for x in rows} != ids or len(rows) != len(ids)
                                for rows in [questions, keys, rubrics]):
        raise ValueError('Inputs, types, keys and rubrics must cover every parent item once')
    excluded = {id for id, kind in types.items() if kind == 'essay'}
    if len(excluded) != 1:
        raise ValueError('Expected exactly one excluded essay')
    if sum(x['max_points'] for x in exam['items'] if x['id'] in excluded) != 15:
        raise ValueError('Expected a 15-point essay')
    kept = ids - excluded
    if sum(x['max_points'] for x in exam['items'] if x['id'] in kept) != 45:
        raise ValueError('Expected all 45 non-essay points')
    return kept, excluded


def derive(config, runner_root, output):
    from matura_lab.coverage import fingerprint, validate_contract
    cfg = read(config); base = Path(runner_root).resolve()
    resolve = lambda p: (base / p).resolve()
    paths = {k: resolve(v) for k, v in cfg['coverage'].items() if k in {'exam', 'types', 'contract'}}
    paths.update(questions=resolve(cfg['questions']), keys=resolve(cfg['keys']))
    paths['rubrics'] = resolve(cfg['rubrics']) if cfg.get('rubrics') else paths['keys'].with_name('rubrics.jsonl')
    exam, types, contract = [read(paths[k]) for k in ['exam', 'types', 'contract']]
    questions, keys, rubrics = [lines(paths[k]) for k in ['questions', 'keys', 'rubrics']]
    kept, excluded = select_nonessay(exam, types, questions, keys, rubrics)
    view = copy.deepcopy(exam); view['items'] = [x for x in view['items'] if x['id'] in kept]
    view['exam_id'] += '-nonessay-v1'; view['max_points'] = 45
    view['evaluation_scope'] = {'kind': 'nonessay', 'parent_exam_id': exam['exam_id'],
                              'parent_max_points': 60, 'excluded_ids': sorted(excluded), 'excluded_points': 15}
    specs = copy.deepcopy(contract); specs['items'] = [x for x in specs['items'] if x['id'] in kept]
    specs['exam_id'] = view['exam_id']; specs['exam_sha256'] = fingerprint(view)
    types = {k: v for k, v in types.items() if k in kept}
    validate_contract(view, types, specs)
    write(output / 'exam.json', view); write(output / 'types.json', types); write(output / 'coverage.json', specs)
    for name, rows in [('input/questions', questions), ('grading/keys', keys), ('grading/rubrics', rubrics)]:
        write_lines(output / (name + '.jsonl'), [x for x in rows if x['id'] in kept])
    write(output / 'review-manifest.json', {'scope': view['evaluation_scope'], 'items': len(kept), 'points': 45,
          'source_files': {k: {'path': str(v), 'sha256': sha(v)} for k, v in paths.items()},
          'builder_sha256': sha(__file__), 'note': 'Exact original question payloads and original absolute image references retained. Original full-paper files unchanged.'})
    return view


def clean(text):
    kept = []
    for line in text.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r'[. …•_]+', line):
            continue
        line = re.sub(r'[. …_]{4,}', ' …', line)
        if line in {'Uzasadnienie:', 'Uzasadnienie: …'}:
            continue
        kept.append(line)
    return '\n'.join(kept)


def region_text(pdf, region, right=535):
    p, top, bottom = region[:3]; page = pdf.pages[p - 1]
    if not 0 <= top < bottom <= 1:
        raise ValueError('Invalid region')
    # Exclude the grading boxes in the margins; source images retain full width.
    crop = page.crop((70, top * page.height, right, bottom * page.height))
    return clean(crop.extract_text(x_tolerance=2, y_tolerance=3) or '')


def true_false_prompt(pdf, region, count):
    p, top, bottom = region; page = pdf.pages[p - 1]
    tables = page.crop((70, top * page.height, 535, bottom * page.height)).find_tables()
    if len(tables) != 1:
        raise ValueError('Expected one reviewed P/F table')
    table = tables[0]; rows = table.extract()
    if len(rows) != count or any(row[-2:] != ['P', 'F'] for row in rows):
        raise ValueError('P/F table geometry differs from reviewed statement count')
    instruction = region_text(pdf, [p, top, table.bbox[1] / page.height], right=528)
    statements = []
    for i, row in enumerate(rows, 1):
        cells = [x for x in row[:-2] if x and not re.fullmatch(r'\d+\.', x.strip())]
        if len(cells) != 1:
            raise ValueError('Ambiguous P/F statement cell')
        statements.append(f'{i}. ' + ' '.join(cells[0].split()))
    return instruction + '\n' + '\n'.join(statements)


def reviewed(spec_path, candidates, grading_pdf, grading_text, output):
    import pdfplumber
    from PIL import Image
    from matura_lab.coverage import fingerprint
    from matura_lab.submissions import import_exam
    spec = read(spec_path); source_pdf = candidates / 'raw/exam.pdf'
    if sha(source_pdf) != spec['source_pdf_sha256']:
        raise ValueError('Unexpected source PDF')
    original = lines(candidates / 'tasks.jsonl')
    maxima = {q['id']: q['max_points'] for q in original}
    expected = set(maxima) - {spec['excluded_essay_id']}
    items = []; contracts = []; types = {}; images_audit = []
    (output / 'images').mkdir(parents=True)
    with pdfplumber.open(source_pdf) as pdf:
        for group in spec['groups']:
            sources = []; images = []
            for n, region in enumerate(group['sources']):
                sources.append(region_text(pdf, region))
                if region[3]:
                    p, top, bottom = region[:3]
                    original_page = candidates / f'pages/page-{p:03d}.png'
                    im = Image.open(original_page).convert('RGB')
                    bbox = [0, int(im.height * top), im.width, int(im.height * bottom)]
                    relative = f'images/task-{group["id"]}-{n}.png'
                    im.crop(bbox).save(output / relative)
                    image = {'path': relative, 'sha256': sha(output / relative)}
                    images.append(image)
                    images_audit.append({**image, 'source_page': p, 'pixel_bbox': bbox, 'page_sha256': sha(original_page)})
            for q in group['items']:
                id = q['id']; kind = q['type']; prompt = region_text(pdf, q['region'], right=528)
                prompt = re.sub(r'^Zadanie ' + re.escape(id) + r'\. \(0[–-]\d+\)\s*', '', prompt)
                if not prompt or re.search(r'Zadanie \d+|Zasady oceniania|WYPRACOWANIE', prompt):
                    raise ValueError(f'Invalid command boundary: {id}: {prompt[:80]}')
                structure = {'kind': 'open', 'slots': q.get('slots', ['Cała odpowiedź z wymaganymi częściami'])}
                if kind == 'choice':
                    structure = {'kind': 'choice', 'slots': ['Litera odpowiedzi'], 'allowed_values': ['A', 'B', 'C', 'D']}
                elif kind == 'true_false':
                    structure = {'kind': 'true_false', 'slots': [str(i + 1) for i in range(q['statements'])], 'allowed_values': ['P', 'F']}
                    prompt = true_false_prompt(pdf, q['region'], q['statements'])
                item = {'id': id, 'question': prompt, 'source_text': '\n\n'.join(sources), 'images': images,
                        'max_points': maxima[id], 'answer_format': 'Tekst zawierający kompletną odpowiedź; zachowaj oznaczenia pozycji.'}
                items.append(item); types[id] = kind
                contracts.append({'id': id, 'item_sha256': fingerprint(item), 'primary_type': kind, 'modules': [kind],
                                  'requirements': [prompt], 'answer_structure': structure, 'images': [x['path'] for x in images]})
    if {q['id'] for q in items} != expected or len(items) != len(expected) or sum(q['max_points'] for q in items) != 45:
        raise ValueError('Review must cover every non-essay item exactly once / 45 points')
    eid = f'history-{spec["year"]}-may-nonessay-v1'
    exam = {'exam_id': eid, 'max_points': 45, 'instructions': 'Rozwiąż zadania po polsku, uwzględniając wszystkie dostarczone źródła i ilustracje.',
            'evaluation_scope': {'kind': 'nonessay', 'parent_max_points': 60, 'excluded_ids': [spec['excluded_essay_id']], 'excluded_points': 15}, 'items': items}
    contract = {'schema_version': 1, 'exam_id': eid, 'exam_sha256': fingerprint(exam), 'items': contracts}
    write(output / 'exam.json', exam); write(output / 'types.json', types); write(output / 'coverage.json', contract)
    write(output / 'answers-template.json', {'exam_id': eid, 'answers': [{'id': x['id'], 'answer': ''} for x in items]})
    import_exam(output / 'exam.json', types, output / 'input', contract)
    # Grading-only phase starts here. Never read marking text to construct inputs.
    marking = re.split(r'(?m)^Zadanie (\d+(?:\.\d+)?)\. \(0[–-](\d+)\)\s*', grading_text.read_text())
    rubrics = {marking[i]: {'id': marking[i], 'max_points': int(marking[i + 1]), 'rubric_and_examples': marking[i + 2].strip()}
               for i in range(1, len(marking), 3)}
    keys = []
    grading_spec = read(spec_path.with_name(spec_path.stem + '-grading.json'))
    scored_marking_ids = [marking[i] for i in range(1, len(marking), 3) if marking[i] not in grading_spec['excluded_ids']]
    if len(scored_marking_ids) != len(set(scored_marking_ids)):
        raise ValueError('Duplicate scored item in marking source')
    if set(rubrics) - set(grading_spec['excluded_ids']) != expected:
        raise ValueError('Marking IDs do not match every non-essay item')
    if sha(grading_pdf) != grading_spec['grading_pdf_sha256'] or sha(grading_text) != grading_spec['grading_text_sha256']:
        raise ValueError('Unexpected marking source')
    for item in items:
        id = item['id']
        if rubrics[id]['max_points'] != item['max_points']:
            raise ValueError('Marking maximum mismatch')
        key = {'id': id, 'kind': 'manual'}
        if id in grading_spec['choice']:
            key.update(kind='choice', options=['A', 'B', 'C', 'D'], expected=grading_spec['choice'][id])
        if id in grading_spec['true_false']:
            values = list(grading_spec['true_false'][id]); n = len(values)
            key.update(kind='labelled_components', labels=[str(i + 1) for i in range(n)], allowed_values=['P', 'F'], expected=values,
                       points_by_correct={str(i): (i - 1 if n == 3 and i >= 2 else int(i == n)) for i in range(n + 1)})
        keys.append(key)
    write_lines(output / 'grading/keys.jsonl', keys)
    write_lines(output / 'grading/rubrics.jsonl', [rubrics[x['id']] for x in items])
    write(output / 'review-manifest.json', {'reviewer': 'Codex text and visual review; not independent expert review',
          'scope': exam['evaluation_scope'], 'items': len(items), 'points': 45, 'source_pdf_sha256': sha(source_pdf),
          'review_spec_sha256': sha(spec_path), 'grading_pdf_sha256': sha(grading_pdf), 'grading_text_sha256': sha(grading_text),
          'grading_spec_sha256': sha(spec_path.with_name(spec_path.stem + '-grading.json')), 'builder_sha256': sha(__file__),
          'image_regions': images_audit, 'note': 'Reviewed page regions preserve original sources and figures. No marking material or essay is supplied to the model.'})
    return exam


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--runner-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); sub = p.add_subparsers(dest='mode', required=True)
    d = sub.add_parser('derive'); d.add_argument('--config', type=Path, required=True)
    r = sub.add_parser('reviewed'); r.add_argument('--spec', type=Path, required=True); r.add_argument('--candidates', type=Path, required=True)
    r.add_argument('--grading-pdf', type=Path, required=True); r.add_argument('--grading-text', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise ValueError('Use a new output directory')
    sys.path.insert(0, str(a.runner_root.resolve()))
    exam = derive(a.config, a.runner_root, a.output) if a.mode == 'derive' else reviewed(a.spec, a.candidates, a.grading_pdf, a.grading_text, a.output)
    print(json.dumps({'exam_id': exam['exam_id'], 'items': len(exam['items']), 'nonessay_points': exam['max_points']}))


if __name__ == '__main__': main()
