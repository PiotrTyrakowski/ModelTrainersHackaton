"""Validate and merge essay-bank slices into one JSONL (data/essay-bank/v2/bank.jsonl)."""
import glob, json, sys
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "data/essay-bank/v2"
out, seen, bad = [], set(), []
for fn in sorted(glob.glob(str(root / "slice-*.jsonl"))) + [str(root / "friend.jsonl")]:
    for n, l in enumerate(open(fn, encoding="utf-8")):
        if not l.strip():
            continue
        try:
            e = json.loads(l)
        except Exception as ex:
            bad.append((fn, n, "json")); continue
        w = len((e.get("essay") or "").split())
        if not e.get("id") or e["id"] in seen or w < 320 or not e.get("topics"):
            bad.append((Path(fn).name, n, e.get("id"), w)); continue
        seen.add(e["id"]); out.append(e)
(root / "bank.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in out), encoding="utf-8")
from collections import Counter
print("entries", len(out), "by slice", dict(Counter(e.get("slice", "?") for e in out)), "rejected", bad[:10])
