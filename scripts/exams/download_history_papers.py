"""Download configured public exam/marking pairs; preserve PDFs, no solver import.

Requires curl, lxml and pypdf. Only cover identity is checked. Question content
and answer keys are neither printed nor inserted into retrieval.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urljoin, urlsplit

from lxml import html
from pypdf import PdfReader


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, output):
    p = urlsplit(url)
    if p.scheme != 'https' or p.netloc != 'arkusze.pl' or p.query or p.fragment:
        raise ValueError('Unexpected download URL')
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        temporary = output.with_suffix(output.suffix + '.part')
        subprocess.run(['curl', '-fsSL', '--proto', '=https', '--proto-redir', '=https',
                        '--max-redirs', '3', '--max-time', '60', '--max-filesize', '30000000',
                        url, '-o', str(temporary)], check=True)
        temporary.replace(output)
        time.sleep(1)
    return output.read_bytes()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text()); out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    previous = json.loads((out / 'manifest.json').read_text()) if (out / 'manifest.json').exists() else None
    if previous:
        for paper in previous['papers']:
            for f in paper['files'].values():
                if sha(out / f['path']) != f['sha256']:
                    raise ValueError('Existing snapshot hash mismatch')
    records = []
    for paper in cfg['papers']:
        eid = paper['exam_id']
        if not re.fullmatch(r'history-20\d\d-(may|june)', eid):
            raise ValueError('Unexpected exam ID')
        landing = out / eid / 'landing.html'
        doc = html.fromstring(fetch(paper['landing_url'], landing))
        candidates = set()
        for a in doc.xpath('//a[@href]'):
            url = urljoin(paper['landing_url'], a.get('href'))
            pattern = rf'https://arkusze\.pl/maturalne/historia-{paper["year"]}-{paper["month"]}-matura-rozszerzona(-odpowiedzi)?\.pdf'
            if re.fullmatch(pattern, url): candidates.add(url)
        if len(candidates) != 2:
            raise ValueError(f'Expected exactly one exam and marking guide for {eid}')
        record = {**paper, 'landing_sha256': sha(landing), 'files': {}}
        for url in sorted(candidates):
            role = 'marking' if '-odpowiedzi.pdf' in url else 'exam'
            relative = Path(eid) / ('grading/marking.pdf' if role == 'marking' else 'input/exam.pdf')
            path = out / relative; raw = fetch(url, path)
            if not raw.startswith(b'%PDF-'):
                raise ValueError('Downloaded file is not a PDF')
            reader = PdfReader(path)
            # Public mirrored PDFs may use PDF permission flags with an empty
            # reader password. Preserve their original bytes and restrictions.
            if reader.is_encrypted and not reader.decrypt(''):
                raise ValueError('PDF requires a reader password')
            if len(reader.pages) < 5:
                raise ValueError('Unexpected PDF structure')
            cover = reader.pages[0].extract_text() or ''
            normalized = re.sub(r'\s+', ' ', cover).casefold()
            if 'histori' not in normalized or str(paper['year']) not in normalized:
                raise ValueError(f'PDF cover subject/year mismatch: {eid} {role}')
            if role == 'marking' and not any(t in normalized for t in ('oceniania', 'odpowiedzi')):
                raise ValueError('Missing marking-guide identity')
            record['files'][role] = {'path': str(relative), 'url': url, 'sha256': sha(path),
                                     'bytes': len(raw), 'pages': len(reader.pages),
                                     'pdf_encryption_flag': reader.is_encrypted,
                                     'validation': 'PDF parses; subject/year on first page verified; content not reviewed'}
        records.append(record)
        manifest = {'version': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
                    'source_index': cfg['source_index'], 'config_sha256': sha(Path(args.config)),
                    'builder_sha256': sha(Path(__file__)), 'papers': records,
                    'pending_ids': [p['exam_id'] for p in cfg['papers'] if p['exam_id'] not in {r['exam_id'] for r in records}],
                    'status': 'downloaded PDF pairs only; task extraction, visual/source review and grading attachment still required',
                    'rights': 'CKE exam documents with third-party source materials, retrieved from a third-party mirror. Raw PDFs remain local.',
                    'leakage_boundary': 'All files excluded from RAG and current checkpoint inputs; marking PDFs stored under grading.'}
        (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        print(eid, {k: v['pages'] for k, v in record['files'].items()}, flush=True)


if __name__ == '__main__': main()
