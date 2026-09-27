"""Build a blinded grading packet for one paper from several configurations' answers, and split the
grader's output back into per-configuration grade files.

make:  python grading_packet.py make --paper data/generated/dev-exams/2025 --runs cfgA=a.json cfgB=b.json --out packet.json
split: python grading_packet.py split --packet packet.json --grades graded.json --outdir grades/
Only manually graded items (open + essay) go into the packet; identical answers are graded once.
Existing grades (--reuse dir) for identical (item, answer) pairs are carried over and not re-sent.
"""
import argparse, hashlib, json, random
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["make", "split"])
ap.add_argument("--paper"); ap.add_argument("--runs", nargs="*"); ap.add_argument("--out")
ap.add_argument("--packet"); ap.add_argument("--grades"); ap.add_argument("--outdir")
ap.add_argument("--reuse", default=None, help="json cache {sha: {points, why}}")
a = ap.parse_args()


def h(item_id, text):
    return hashlib.sha256((item_id + "\x00" + (text or "").strip()).encode()).hexdigest()[:16]


if a.cmd == "make":
    paper = Path(a.paper)
    exam = json.loads((paper / "exam.json").read_text(encoding="utf-8"))
    keys = {json.loads(l)["id"]: json.loads(l) for l in open(paper / "keys.jsonl", encoding="utf-8")}
    rubrics = {json.loads(l)["id"]: json.loads(l) for l in open(paper / "rubrics.jsonl", encoding="utf-8")}
    cache = json.loads(Path(a.reuse).read_text()) if a.reuse and Path(a.reuse).exists() else {}
    runs = dict(r.split("=", 1) for r in a.runs)
    answers = {name: {x["id"]: x["answer"] for x in json.loads(Path(p).read_text(encoding="utf-8"))["answers"]} for name, p in runs.items()}
    items, mapping = [], {}
    for it in exam["items"]:
        if keys.get(it["id"], {"kind": "manual"})["kind"] != "manual":
            continue
        uniq = {}
        for name in runs:
            txt = answers[name].get(it["id"], "")
            sha = h(it["id"], txt)
            mapping.setdefault(it["id"], {})[name] = sha
            if sha not in cache:
                uniq[sha] = txt
        if not uniq:
            continue
        order = list(uniq.items()); random.Random(it["id"]).shuffle(order)
        items.append({"id": it["id"], "max_points": it["max_points"], "question": it["question"],
                      "source_text": (it.get("source_text") or "")[:3000],
                      "images": [str((paper / (im["path"] if isinstance(im, dict) else im)).resolve()) for im in it.get("images", [])],
                      "rubric": rubrics.get(it["id"], {}).get("rubric_and_examples", ""),
                      "answers": [{"answer_id": sha, "text": txt} for sha, txt in order]})
    Path(a.out).write_text(json.dumps({"paper": str(paper), "items": items, "mapping": mapping, "runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    # the grader only ever sees this file: no run names, no mapping
    Path(a.out).with_suffix(".grader.json").write_text(json.dumps({"items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("items", len(items), "answers to grade", sum(len(i["answers"]) for i in items))
else:
    packet = json.loads(Path(a.packet).read_text(encoding="utf-8"))
    graded = json.loads(Path(a.grades).read_text(encoding="utf-8"))  # {answer_id: {points, why}}
    cache_path = Path(a.reuse) if a.reuse else None
    cache = json.loads(cache_path.read_text()) if cache_path and cache_path.exists() else {}
    cache.update(graded)
    if cache_path:
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    for name in packet["runs"]:
        g = {}
        for iid, per in packet["mapping"].items():
            sha = per[name]
            if sha in cache:
                g[iid] = cache[sha]
        (out / f"{name}.grades.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name, "graded items", len(g))
