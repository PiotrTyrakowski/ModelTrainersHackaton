"""Score answers.json: closed items automatically from keys.jsonl; open items and essays from a manual
grades file ({"id": {"points": x, "why": "..."}}) produced by rubric grading. Missing grades = pending.

python score.py --answers answers.json --keys keys.jsonl [--grades grades.json] [--exam exam.json]
"""
import argparse, json, re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--answers", required=True)
ap.add_argument("--keys", required=True)
ap.add_argument("--grades", default=None)
ap.add_argument("--exam", default=None)
ap.add_argument("--json", action="store_true")
args = ap.parse_args()

ans = {a["id"]: a["answer"] for a in json.load(open(args.answers, encoding="utf-8"))["answers"]}
keys = {json.loads(l)["id"]: json.loads(l) for l in open(args.keys, encoding="utf-8") if l.strip()}
grades = json.load(open(args.grades, encoding="utf-8")) if args.grades and Path(args.grades).exists() else {}
maxp = {}
if args.exam:
    maxp = {i["id"]: i["max_points"] for i in json.load(open(args.exam, encoding="utf-8"))["items"]}


def closed_points(k, a):
    if k["kind"] == "choice":
        m = re.search(r"\b([A-F])\b", a or "")
        return 1 if m and m.group(1) == k["expected"] else 0
    if k["kind"] == "labelled_components":
        got = {}
        for l in (a or "").splitlines():
            mm = re.match(r"^\s*([0-9A-Za-z]{1,3})\s*:\s*(\S+)", l)
            if mm:
                got[mm.group(1)] = mm.group(2)
        correct = sum(1 for lab, exp in zip(k["labels"], k["expected"]) if got.get(lab) == exp)
        return k["points_by_correct"][str(correct)]
    return None


tot = closed = closed_max = open_pts = open_max = 0
pending = []
rows = []
for iid in list(keys) + [i for i in maxp if i not in keys]:
    k = keys.get(iid, {"kind": "manual"})
    mp = maxp.get(iid)
    p = closed_points(k, ans.get(iid)) if k["kind"] != "manual" else None
    if p is not None:
        closed += p; closed_max += (mp or max(k.get("points_by_correct", {"1": 1}).values()))
    else:
        g = grades.get(iid)
        if g is None:
            pending.append(iid); p = 0
        else:
            p = g["points"] if isinstance(g, dict) else g
        open_pts += p; open_max += mp or 0
    tot += p
    rows.append((iid, k["kind"], p, mp))
res = {"total": tot, "closed": closed, "closed_max": closed_max, "manual": open_pts, "manual_max": open_max, "pending": pending, "items": rows}
if args.json:
    print(json.dumps(res, ensure_ascii=False))
else:
    print(f"total {tot} | closed {closed}/{closed_max} | manual {open_pts}/{open_max} | pending {len(pending)}: {','.join(pending)}")
