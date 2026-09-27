"""Check answers.json against the organisers' file rules before uploading it.

    python3 scripts/harness/check_submission.py <answers-template.json> <answers.json> [--exam exam.json] [--aligned out.json]

Rules (matura JSON guide): every template ID exactly once, as a string; every answer a string; top level only
exam_id and answers, each entry only id and answer; exam_id as in the template; UTF-8 JSON of at most 1 MiB;
each answer at most 100,000 characters; the essay names its topic number and has at least 300 words.
--aligned writes a copy in template order with exactly the template's IDs ("" for any missing answer).
Exit status 0 only when every rule holds.
"""
import argparse, json, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("template"); ap.add_argument("answers")
ap.add_argument("--exam", help="exam.json, to find the essay item (max_points 15); default id 26")
ap.add_argument("--aligned", help="write a template-aligned copy here")
args = ap.parse_args()

raw = open(args.answers, "rb").read()
problems = []
try:
    txt = raw.decode("utf-8")
except UnicodeDecodeError:
    problems.append("not UTF-8"); txt = raw.decode("utf-8", "replace")
if txt.startswith("\ufeff"):
    problems.append("starts with a byte-order mark")
a, t = json.loads(txt.lstrip("\ufeff")), json.load(open(args.template, encoding="utf-8"))
tids = [e["id"] for e in t["answers"]]
if len(raw) > 1024 * 1024:
    problems.append(f"file is {len(raw)} bytes, over 1 MiB")
if set(a) != {"exam_id", "answers"}:
    problems.append(f"top-level keys {sorted(a)}")
if a.get("exam_id") != t["exam_id"]:
    problems.append(f"exam_id {a.get('exam_id')!r} differs from the template's {t['exam_id']!r}")
ids = [e.get("id") for e in a.get("answers", [])]
if any(not isinstance(i, str) for i in ids):
    problems.append("an id is not a string")
dup = sorted({i for i in ids if ids.count(i) > 1})
miss = [i for i in tids if i not in ids]
extra = [i for i in ids if i not in tids]
for name, v in (("duplicate ids", dup), ("missing ids", miss), ("ids not in the template", extra)):
    if v:
        problems.append(f"{name} {v}")
for e in a.get("answers", []):
    if set(e) != {"id", "answer"}:
        problems.append(f"entry {e.get('id')} has keys {sorted(e)}")
    if not isinstance(e.get("answer"), str):
        problems.append(f"entry {e.get('id')} answer is {type(e.get('answer')).__name__}, not a string")
    elif len(e["answer"]) > 100_000:
        problems.append(f"entry {e['id']} answer has {len(e['answer'])} characters")
    elif re.search(r"</?think>", e["answer"]):
        problems.append(f"entry {e['id']} contains reasoning tags")

if args.exam:
    ex = json.load(open(args.exam, encoding="utf-8"))
    essay_id = next((i["id"] for i in ex["items"] if int(i.get("max_points") or 0) == 15), "26")
else:  # without the exam: the answer that names a topic, else the mock's id
    essay_id = next((e.get("id") for e in a.get("answers", []) if re.match(r"\s*Temat\s+\d", str(e.get("answer")))), "26")
essay = next((e.get("answer") for e in a.get("answers", []) if e.get("id") == essay_id), None)
if isinstance(essay, str):
    words, topic = len(essay.split()), re.match(r"\s*Temat\s+(\d+)", essay)
    if not topic:
        problems.append(f"essay {essay_id} does not start with its topic number")
    if words < 300:
        problems.append(f"essay {essay_id} has {words} words, under 300")
    print(f"essay {essay_id}: topic {topic.group(1) if topic else '?'}, {words} words")
empty = [e.get("id") for e in a.get("answers", []) if isinstance(e.get("answer"), str) and not e["answer"].strip()]
print(f"{len(ids)} answers for {len(tids)} template ids, {len(raw)} bytes, empty answers: {empty or 'none'}")

if args.aligned:
    by_id = {e.get("id"): e.get("answer") for e in a.get("answers", [])}
    out = {"exam_id": t["exam_id"],
           "answers": [{"id": i, "answer": by_id[i] if isinstance(by_id.get(i), str) else ""} for i in tids]}
    with open(args.aligned, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote template-aligned copy to {args.aligned}; check that file again before uploading")

print("OK: meets every rule" if not problems else "PROBLEMS:\n- " + "\n- ".join(problems))
sys.exit(0 if not problems else 1)
