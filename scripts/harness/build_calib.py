"""Calibration text for llama-imatrix: Polish history passages from the retrieval index plus chat-formatted
old-formula practice items (data/sft). Contains no dev or final exam papers, keys or rubrics.

python build_calib.py --index data/raw/retrieval/wiki-ehistoria-v1/index.sqlite --sft data/sft/nonessay-v1.jsonl --out calib.txt
"""
import argparse, json, random, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SYSTEM

ap = argparse.ArgumentParser()
ap.add_argument("--index", required=True)
ap.add_argument("--sft", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--passages", type=int, default=160)
ap.add_argument("--items", type=int, default=80)
ap.add_argument("--seed", type=int, default=7)
a = ap.parse_args()
rnd = random.Random(a.seed)
rows = sqlite3.connect(a.index).execute("select text from chunks").fetchall()
parts = [r[0].strip() for r in rnd.sample(rows, min(a.passages, len(rows)))]
recs = [json.loads(l) for l in open(a.sft, encoding="utf-8")]
for r in rnd.sample(recs, min(a.items, len(recs))):
    it = r["item"]
    user = (it.get("source_text") or "").strip() + "\n\n" + it["question"].strip()
    ans = r.get("answer") or r.get("target") or ""
    if isinstance(ans, dict):
        ans = ans.get("answer", "")
    parts.append(f"<|im_start|>system\n{SYSTEM}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n"
                 f"<|im_start|>assistant\n{ans}<|im_end|>")
rnd.shuffle(parts)
Path(a.out).write_text("\n\n".join(parts), encoding="utf-8")
print("parts", len(parts), "chars", sum(map(len, parts)))
