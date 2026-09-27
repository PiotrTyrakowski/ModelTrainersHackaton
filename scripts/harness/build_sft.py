"""Build the non-essay SFT set for the small-model harness.

Input: the teammate's SFT records (~/Downloads/finetuine/data/sft_v2.jsonl):
formula-2015 CKE papers (2015-2022) plus synthetic CKE-style items, some with
BM25 encyclopedia context. Essays are dropped (they come from the essay bank).
Every record from a 2023+ session is dropped, and any record whose source/question
text overlaps a formula-2023 paper (all dev papers, the June 2026 reserve, and the
teammate's eval set) by 8-gram containment > 0.10 is dropped as contamination.

python scripts/harness/build_sft.py --src ~/Downloads/finetuine --out data/sft/nonessay-v1.jsonl
"""
import argparse, glob, json, re, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import kind

ap = argparse.ArgumentParser()
ap.add_argument("--src", default=str(Path.home() / "Downloads/finetuine"))
ap.add_argument("--out", required=True)
ap.add_argument("--threshold", type=float, default=0.10)
args = ap.parse_args()
root = Path(__file__).resolve().parents[2]
src = Path(args.src)


def grams(t, n=8):
    w = re.findall(r"\w+", (t or "").lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


held = set()
for fn in glob.glob(str(root / "data/processed/*/input/questions.jsonl")):
    for l in open(fn, encoding="utf-8"):
        q = json.loads(l); held |= grams(q.get("source_text", "")) | grams(q.get("prompt", ""))
for fn in glob.glob(str(root / "data/processed/*/exam.json")) + glob.glob(str(root / "data/processed/*/raw/exam.json")):
    for it in json.load(open(fn, encoding="utf-8")).get("items", []):
        held |= grams(it.get("source_text", "")) | grams(it.get("question", ""))
for l in open(src / "data/cke/eval.jsonl", encoding="utf-8"):  # all formula-2023 papers incl. the June 2026 reserve
    it = json.loads(l)["item"]; held |= grams(it.get("source_text", "")) | grams(it.get("question", ""))
for it in json.load(open(src / "data/mock/exam.json", encoding="utf-8"))["items"]:
    held |= grams(it.get("source_text", "")) | grams(it.get("question", ""))

out, stats = [], {"essay": 0, "post2022": 0, "contam": 0, "empty": 0}
for l in open(src / "data/sft_v2.jsonl", encoding="utf-8"):
    r = json.loads(l)
    it = r["item"]
    if kind(it) == "essay":
        stats["essay"] += 1; continue
    if re.match(r"cke-(2023|2024|2025|2026)", r["uid"]):
        stats["post2022"] += 1; continue
    if not (r.get("answer") or "").strip():
        stats["empty"] += 1; continue
    g = grams(it.get("source_text", "")) | grams(it.get("question", ""))
    if g and len(g & held) / len(g) > args.threshold:
        stats["contam"] += 1; continue
    rec = {"uid": r["uid"], "item": {k: it.get(k) for k in ("id", "max_points", "question", "source_text", "answer_format")}, "answer": r["answer"].strip()}
    rec["item"]["images"] = []
    if r.get("context"):
        rec["context"] = r["context"]
    out.append(rec)
random.Random(0).shuffle(out)
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
from collections import Counter
print("kept", len(out), "dropped", stats, "kinds", Counter(kind(r["item"]) for r in out), "with ctx", sum("context" in r for r in out))
