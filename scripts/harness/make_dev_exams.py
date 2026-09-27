"""Write organiser-format exam.json files (60 points, essay included) for the four development papers.

2023 is the organisers' own mock input (raw/exam.json). 2024-2026 are rebuilt from the reviewed
non-essay inputs plus the essay task; closed-item answer_format strings are derived from the key
*structure* only (labels / allowed values), never from the expected answers.
Output: data/generated/dev-exams/<year>/{exam.json,keys.jsonl,rubrics.jsonl}
"""
import json, re, shutil
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OPEN_FORMAT, ESSAY_FORMAT

root = Path(__file__).resolve().parents[2]
P = root / "data/processed"
OUT = root / "data/generated/dev-exams"
PAPERS = {
    "2023": ("history-2023-nonessay-v1", None),
    "2024": ("history-2024-nonessay-v1", ("history-2024-reviewed-v1/input/questions.jsonl", "26")),
    "2025": ("history-2025-may-nonessay-v1", ("history-2025-may/tasks.jsonl", "25")),
    "2026": ("history-2026-may-nonessay-v1", ("history-2026-may/tasks.jsonl", "26")),
}


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def fmt(key):
    if key["kind"] == "choice":
        return key["options"][0]
    if key["kind"] == "labelled_components":
        vals = key["allowed_values"]
        if set(vals) == {"P", "F"}:
            return "\n".join(f"{l}: {'PF'[i % 2]}" for i, l in enumerate(key["labels"]))
        return "\n".join(f"{l}: {vals[0]}" for l in key["labels"])
    return OPEN_FORMAT


def clean_essay(prompt):
    prompt = re.sub(r"^\s*Zadanie\s+\d+\.\s*\(0[–-]15\)\s*", "", prompt)
    prompt = prompt.split("WYPRACOWANIE")[0]
    lines = [l.rstrip() for l in prompt.splitlines()]
    return re.sub(r"\n{2,}", "\n", "\n".join(lines)).strip()


for year, (nonessay, essay) in PAPERS.items():
    d = OUT / year; d.mkdir(parents=True, exist_ok=True)
    keys = {k["id"]: k for k in jl(P / nonessay / "grading/keys.jsonl")}
    shutil.copy(P / nonessay / "grading/keys.jsonl", d / "keys.jsonl")
    rub = jl(P / nonessay / "grading/rubrics.jsonl")
    ess_rub = [r for r in jl(P / "history-2024-reviewed-v1/grading/rubrics.jsonl") if r["id"] == "26"][0]
    if year == "2023":
        raw = json.loads((P / "history-2023-mock-v1/raw/exam.json").read_text(encoding="utf-8"))
        base = P / "history-2023-mock-v1/raw"
        assets = P / "history-2023-mock-v1/assets"
        items = []
        for it in raw["items"]:
            it = dict(it)
            imgs = []
            for im in it.get("images", []):
                cand = [base / im["path"], assets / im["path"], assets / Path(im["path"]).name, assets / "images" / Path(im["path"]).name]
                path = next((c for c in cand if c.exists()), None)
                imgs.append(str(path.resolve()) if path else im["path"])
            it["images"] = imgs
            items.append(it)
        essay_id = "26"
    else:
        items = []
        for q in jl(P / nonessay / "input/questions.jsonl"):
            items.append({"id": q["id"], "max_points": q["max_points"], "question": q["prompt"], "source_text": q.get("source_text", ""),
                          "images": q.get("images", []), "answer_format": fmt(keys[q["id"]])})
        path, essay_id = essay
        e = [r for r in jl(P / path) if str(r["id"]) == essay_id][0]
        items.append({"id": essay_id, "max_points": 15, "question": clean_essay(e["prompt"]), "source_text": "", "images": [], "answer_format": ESSAY_FORMAT})
    rub.append({**ess_rub, "id": essay_id})
    (d / "rubrics.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rub), encoding="utf-8")
    (d / "images").mkdir(exist_ok=True)
    for it in items:  # copy images next to exam.json and reference them relatively (portable to the GPU VM)
        rel = []
        for j, src_img in enumerate(it["images"]):
            name = f"{it['id']}-{j}{Path(src_img).suffix}"
            shutil.copy(src_img, d / "images" / name)
            rel.append({"path": f"images/{name}"})
        it["images"] = rel
    exam = {"exam_id": f"dev-{year}", "max_points": sum(i["max_points"] for i in items), "items": items}
    (d / "exam.json").write_text(json.dumps(exam, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [i["id"] for i in items for p in i["images"] if not (d / p["path"]).exists()]
    print(year, len(items), "items", exam["max_points"], "pts", "missing images:", missing)
