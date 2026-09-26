#!/usr/bin/env python3
"""Prepare, run and report fixed matura checkpoints using an existing evaluator.

Only `run` contacts a model. `prepare` and `report` are offline operations.
The old evaluator is an explicit, hashed dependency rather than a silent copy.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def jsonl(path):return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def legacy(root):
    root=Path(root).resolve()
    if not (root/'matura_lab/experiments.py').is_file():raise ValueError('runner-root must contain matura_lab/experiments.py')
    if 'matura_lab' in sys.modules:
        loaded=Path(sys.modules['matura_lab'].__file__).resolve().parent.parent
        if loaded!=root:raise ValueError('A different evaluator is already imported; start a fresh process')
    sys.path.insert(0,str(root))
    return importlib.import_module('matura_lab.experiments'),importlib.import_module('matura_lab.core'),importlib.import_module('matura_lab.coverage')


def prepare(runner_root,config_path,output,variants=None,target_points=None,target_label=None,note='',base_url=None,runtime_label=None):
    root=Path(runner_root).resolve();out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Choose a new empty checkpoint directory')
    _,core,coverage=legacy(root)
    source=Path(config_path);source=source if source.is_absolute() else root/source
    cfg=read(source)
    if cfg.get('demo'):raise ValueError('Checkpoint runs require a real solver, not the demo')
    if variants is not None:cfg['variants']=variants
    if base_url is not None:
        from urllib.parse import urlsplit
        parsed=urlsplit(base_url)
        if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Use an HTTP(S) endpoint without embedded credentials, query or fragment')
        cfg['model']['base_url']=base_url.rstrip('/')
    if runtime_label is not None:cfg['execution_environment']=runtime_label
    if cfg['variants']==['direct']:
        for name in ['corpus','corpus_provenance','embedding']:cfg.pop(name,None)
    def absolute(path):return str((root/path).resolve()) if not Path(path).is_absolute() else str(Path(path).resolve())
    if not cfg.get('rubrics'):
        candidate=Path(absolute(cfg['keys'])).with_name('rubrics.jsonl')
        if candidate.is_file():cfg['rubrics']=str(candidate)
    for name in ['questions','keys','rubrics','corpus','facts','fact_documents']:
        if cfg.get(name):cfg[name]=absolute(cfg[name])
    essay_bank=cfg.get('strategy',{}).get('essay_bank')
    if essay_bank:
        for name in ['bank','catalog']:essay_bank[name]=absolute(essay_bank[name])
    if not cfg.get('coverage'):raise ValueError('A reviewed complete exam coverage contract is required')
    for name in ['exam','types','contract']:cfg['coverage'][name]=absolute(cfg['coverage'][name])
    prov=cfg.get('model_provenance',{})
    if prov.get('inventory'):prov['inventory']=absolute(prov['inventory'])
    old=os.getcwd()
    try:
        os.chdir(root);raw=jsonl(cfg['questions']);coverage_result=coverage.enforce_run(cfg,raw)
    finally:os.chdir(old)
    questions=[core.Question.from_dict(q) for q in raw]
    selected=core.select_question_ids(cfg,{q.id:q.type for q in questions})
    full=read(cfg['coverage']['exam']);ids={q.id for q in questions}
    if ids!={item['id'] for item in full['items']}:raise ValueError('Question input must retain the complete exam; select subsets through config only')
    maximum=sum(q.max_points for q in questions)
    if target_points is not None and not 0<target_points<=maximum:raise ValueError('Target must be positive and no greater than the full exam total')
    identity=prov.get('manifest_sha256') or prov.get('expected_sha256')
    if not identity or not prov.get('download_verified'):raise ValueError('Pin verified model artifact hashes before preparing a neural checkpoint')
    files={}
    def capture(role,path):files[role]={'path':str(Path(path).resolve()),'sha256':file_hash(path)}
    capture('source_config',source)
    for name in ['questions','keys','rubrics','corpus','facts','fact_documents']:
        if cfg.get(name):capture(name,cfg[name])
    for name in ['exam','types','contract']:capture('coverage_'+name,cfg['coverage'][name])
    if prov.get('inventory'):capture('model_inventory',prov['inventory'])
    for path in sorted((root/'matura_lab').rglob('*')):
        if path.is_file() and path.suffix in {'.py','.json'} and '__pycache__' not in path.parts:capture('runner:'+str(path.relative_to(root)),path)
    for i,path in enumerate(sorted({image for q in questions for image in q.images})):capture(f'image:{i}',absolute(path))
    for path in sorted(Path(__file__).parent.glob('*.py')):capture('checkpoint_tool:'+path.name,path)
    if essay_bank:
        for name in ['bank','catalog']:capture('essay_bank:'+name,essay_bank[name])
        package=Path(__file__).resolve().parents[2]/'packages/tasks-data/src/tasks_data'
        for path in sorted(package.glob('*.py')):capture('essay_package:'+path.name,path)
    snapshot={'schema_version':1,'checkpoint':out.name,'prepared_at':datetime.now(timezone.utc).isoformat(),'runner_root':str(root),
              'note':note,'config_sha256':digest(cfg),'files':files,'exam_id':full['exam_id'],'exam_max_points':maximum,
              'exam_sha256':files['coverage_exam']['sha256'],'keys_sha256':files['keys']['sha256'],
              'key_semantic_hash':digest(jsonl(cfg['keys'])),'selected_ids':selected,
              'selected_dataset_hash':digest([asdict(q) for q in questions if q.id in selected]),
              'items':[{'id':q.id,'type':q.type,'max_points':q.max_points,'question_hash':digest(asdict(q)),'selected':q.id in selected} for q in questions],
              'model':cfg['model']['model'],'model_artifact_hash':identity,'model_provenance':prov,
              'execution_environment':cfg.get('execution_environment','not recorded; verify separately'),
              'model_identity_note':'Artifact metadata is pinned. The operator must separately verify that the live server serves these weights.',
              'target':{'points':target_points,'basis':target_label or ('experimental target; not organiser-confirmed' if target_points is not None else 'not specified')},
              'grading_status':'local/provisional until explicitly established otherwise','coverage_preflight':coverage_result}
    out.mkdir(parents=True,exist_ok=True);write(out/'config.json',cfg);write(out/'snapshot.json',snapshot)
    return snapshot


def check_snapshot(directory,verify_files=True):
    directory=Path(directory);snapshot=read(directory/'snapshot.json');config=read(directory/'config.json')
    if digest(config)!=snapshot['config_sha256']:raise ValueError('Prepared configuration changed')
    if verify_files:
        for role,entry in snapshot['files'].items():
            if file_hash(entry['path'])!=entry['sha256']:raise ValueError(f'Pinned dependency changed: {role}; prepare a new checkpoint')
    return snapshot,config


def run_checkpoint(directory):
    directory=Path(directory).resolve();snapshot,config=check_snapshot(directory)
    if any((directory/name).exists() for name in ['run.json','answers.partial.jsonl','run-state.json']):raise ValueError('Checkpoint already started; prepare a new directory')
    experiments,_,_=legacy(snapshot['runner_root'])
    write(directory/'run-state.json',{'status':'running','started_at':datetime.now(timezone.utc).isoformat()})
    old=os.getcwd()
    try:
        os.chdir(snapshot['runner_root'])
        with (directory/'answers.partial.jsonl').open('x',encoding='utf-8') as journal:
            def save(row):
                journal.write(json.dumps(row,ensure_ascii=False)+'\n');journal.flush()
                print(f'{row["variant"]} {row["question_id"]}: {row["status"]}; points={row["points"]}; {row["seconds"]:.2f}s',flush=True)
            from answer_contract import use_answer_contract
            with use_answer_contract(config):
                result=experiments.run(config,on_result=save)
        check_snapshot(directory)
        write(directory/'run.json',result)
        write(directory/'run-state.json',{'status':'complete','completed_at':datetime.now(timezone.utc).isoformat(),'run_sha256':file_hash(directory/'run.json')})
    except BaseException as error:
        write(directory/'run-state.json',{'status':'interrupted_or_failed','error_type':type(error).__name__,
              'note':'Completed responses are retained in answers.partial.jsonl. This is not a complete exam score.'})
        raise
    finally:os.chdir(old)
    return result


def report_checkpoint(directory,run_path=None,previous=None,output=None):
    from reporting import build_report,markdown
    directory=Path(directory).resolve();snapshot,config=check_snapshot(directory,verify_files=False)
    run_path=Path(run_path).resolve() if run_path else directory/'run.json'
    run=read(run_path)
    if digest(run['config'])!=snapshot['config_sha256'] or run['dataset_hash']!=snapshot['selected_dataset_hash'] or run['key_hash']!=snapshot['key_semantic_hash']:
        raise ValueError('Run does not match the checkpoint config/data/grading contract')
    if run.get('demo') or run['model']!=snapshot['model']:raise ValueError('Unexpected solver identity')
    original=directory/'run.json'
    state_path=directory/'run-state.json'
    if original.exists() and state_path.exists():
        state=read(state_path)
        if state.get('run_sha256') and file_hash(original)!=state['run_sha256']:raise ValueError('Original run was modified; use a separate file for grading')
    if run_path!=original and original.exists():
        raw=read(original);allowed={'points','grade_reason','grader'}
        strip=lambda rows:[{k:v for k,v in row.items() if k not in allowed} for row in rows]
        if strip(raw['results'])!=strip(run['results']):raise ValueError('Grading changed predictions or execution metadata')
    report=build_report(snapshot,run,read(previous) if previous else None)
    report['source_report_sha256']=file_hash(run_path);report['source_report']=str(run_path)
    target=Path(output) if output else directory/'checkpoint-report.json'
    if target.exists():raise ValueError('Report output exists; choose a new name after grading')
    write(target,report);target.with_suffix('.md').write_text(markdown(report),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--runner-root',required=True);p.add_argument('--config',default='configs/tiny-qwen35-full.json');p.add_argument('--output',required=True);p.add_argument('--variants',nargs='+',default=['direct']);p.add_argument('--target-points',type=float);p.add_argument('--target-label');p.add_argument('--note',default='');p.add_argument('--base-url');p.add_argument('--runtime-label')
    p=sub.add_parser('run');p.add_argument('checkpoint')
    p=sub.add_parser('report');p.add_argument('checkpoint');p.add_argument('--run-report');p.add_argument('--previous');p.add_argument('--output')
    args=parser.parse_args()
    if args.command=='prepare':
        result=prepare(args.runner_root,args.config,args.output,args.variants,args.target_points,args.target_label,args.note,args.base_url,args.runtime_label)
        print(json.dumps({'prepared':str(Path(args.output).resolve()),'model':result['model'],'selected_items':len(result['selected_ids']),
                          'exam_points':result['exam_max_points'],'target':result['target']},indent=2))
    elif args.command=='run':
        run_checkpoint(args.checkpoint)
        report=report_checkpoint(args.checkpoint)
        print(json.dumps(report['variants'],ensure_ascii=False,indent=2))
    else:
        report=report_checkpoint(args.checkpoint,args.run_report,args.previous,args.output)
        print(json.dumps(report['variants'],ensure_ascii=False,indent=2))


if __name__=='__main__':main()
