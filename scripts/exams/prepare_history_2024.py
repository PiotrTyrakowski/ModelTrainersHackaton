#!/usr/bin/env python3
"""Build reviewed 2024 development inputs from local public-paper candidates.

Input normalization only: no answer keys enter question prompts. The marking
document is processed separately into grading records. Raw PDFs stay local.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from PIL import Image


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def clean(text):
    lines = []
    for line in text.replace("\f", "\n").splitlines():
        line = line.strip()
        if (not line or line.startswith(("Więcej arkuszy", "MHIP-")) or
                re.fullmatch(r"Strona \d+ z \d+", line) or
                re.fullmatch(r"\d+(?:\.\d+)?\.", line) or
                re.fullmatch(r"0[–-]\d+(?:[–-]\d+)*", line)):
            continue
        lines.append(line)
    return "\n".join(lines)


# Primary types and figure regions reviewed against all relevant PDF pages.
TYPES = {
    "1": "comparison", "2": "map", "3.1": "identification", "3.2": "identification",
    "4": "art", "5.1": "map", "5.2": "map", "6": "art", "7": "chronology",
    "8.1": "identification", "8.2": "comparison", "9": "art", "10": "choice",
    "11.1": "matching", "11.2": "explanation", "12.1": "identification",
    "12.2": "identification", "12.3": "art", "13": "identification",
    "14.1": "map", "14.2": "choice", "15.1": "identification", "15.2": "comparison",
    "16.1": "cartoon", "16.2": "choice", "17.1": "explanation", "17.2": "identification",
    "18": "cartoon", "19.1": "true_false", "19.2": "identification",
    "20.1": "comparison", "20.2": "true_false", "21": "art", "22.1": "identification",
    "22.2": "comparison", "23.1": "explanation", "23.2": "data_table",
    "24": "map", "25": "cartoon", "26": "essay",
}
# page, top, bottom as fractions of the rendered full page. Width retained.
FIGURES = {
    "1": (4, .23, .62), "2": (5, .26, .68), "4": (7, .12, .55),
    "5": (8, .27, .68), "6": (9, .20, .66), "8": (11, .07, .52),
    "9": (12, .12, .70), "10": (13, .12, .35), "11": (14, .035, .50),
    "12": (15, .07, .51), "13": (16, .12, .51), "14": (17, .07, .50),
    "16": (19, .10, .50), "17": (20, .42, .70), "18": (21, .20, .69),
    "19": (22, .11, .61), "21": (24, .12, .42), "23": (26, .10, .54),
    "24": (27, .12, .48), "25": (28, .12, .51),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--grading-text", type=Path, required=True)
    parser.add_argument("--grading-pdf", type=Path, required=True)
    parser.add_argument("--runner-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new output directory")
    sys.path.insert(0, str(args.runner_root.resolve()))
    from matura_lab.coverage import fingerprint
    from matura_lab.submissions import import_exam
    root = args.candidates
    manifest = json.loads((root / "manifest.json").read_text())
    if sha(root / "raw/exam.pdf") != "a5f95323ad82f0b44b8c5e1c16fbc89d56dfe60db77ee4f583b76a669eb02ead":
        raise ValueError("Unexpected exam PDF")
    if sha(root / "tasks.jsonl") != manifest["files"]["tasks.jsonl"]:
        raise ValueError("Candidate data changed")
    candidates = [json.loads(l) for l in (root / "tasks.jsonl").read_text().splitlines()]
    assert set(TYPES) == {q["id"] for q in candidates}
    out = args.output.resolve(); (out / "images").mkdir(parents=True)
    figures = {}
    for parent, (page, top, bottom) in FIGURES.items():
        original = root / f"pages/page-{page:03d}.png"
        im = Image.open(original).convert("RGB")
        bbox = [0, int(im.height * top), im.width, int(im.height * bottom)]
        path = out / f"images/task-{parent}.png"
        im.crop(bbox).save(path)
        figures[parent] = {"path": str(path.relative_to(out)), "sha256": sha(path),
                           "source_page": page, "pixel_bbox": bbox, "page_sha256": sha(original)}
    items = []; specs = []
    for raw in candidates:
        id = raw["id"]; parent = id.split(".")[0]; kind = TYPES[id]
        prompt = re.sub(r"^Zadanie [\d.]+\s*\(0[–-]\d+\)\s*", "", raw["prompt"])
        source = raw["source_text"]
        if not source and id != "26":
            boundary = re.search(r"(?m)^(Rozstrzygnij|Sformułuj|Wyjaśnij|Dokończ|Podaj|Na podstawie przedstawionego)\b", prompt)
            assert boundary, id
            source, prompt = prompt[:boundary.start()], prompt[boundary.start():]
        # Everything after answer-space labels/lines is furniture, never an instruction.
        prompt = re.split(r"(?m)^\s*(?:Rozstrzygnięcie:|Uzasadnienie:|Wydarzenie:|Podobieństwo A:|Fragment A\s*[–-]|[.•… ]{5,}|•\s*\.{5,}|WYPRACOWANIE)", prompt)[0]
        prompt, source = clean(prompt), clean(source)
        source = re.sub(r"^Zadanie [\d.]+\s*\n", "", source)
        if parent == "12":
            source = re.sub(r"Franciszek I\n.*?(?=Źródło 2\.)", "", source, flags=re.S)
        if parent == "14":
            source = source.replace("30 stycznia 1649\n", "")
        if parent == "15":
            source = source.replace("Wersja A: Wersja B:", "Wersja A:")
            source = source.replace("\nNasz Chłopicki wojak dzielny, śmiały!", "\nWersja B:\nNasz Chłopicki wojak dzielny, śmiały!")
        if parent == "11":
            source += "\nTranskrypcja władców z tablicy (źródło 2): Franciszek I – król Francji od 1515, zmarł 1547; Henryk II – od 1547, zmarł 1559; Franciszek II – od 1559, zmarł 1560; Karol IX – od 1560, zmarł 1574; Henryk III – od 1574, zmarł 1589; Henryk IV – 1589–1610. Pełne relacje rodzinne przedstawia obraz."
        if parent == "16":
            source += "\nNapisy na ilustracji: Zakaz wstępu; Ameryka dla Amerykanów; Wuj Sam; Nikaragua, Wenezuela; Portugalia, Francja, Hiszpania, Niemcy; Przejęcie Wenezueli."
        if parent == "17":
            source += "\nNapis na ilustracji: Kapitulacja pod Sedanem."
        images = [figures[parent]] if parent in figures else []
        if images:
            source += "\n[Ilustracja do zadania: " + images[0]["path"] + "]"
        structure = {"kind": "open", "slots": ["Cała odpowiedź z wymaganymi częściami"]}
        if kind == "true_false":
            structure = {"kind": "true_false", "slots": ["1", "2", "3"], "allowed_values": ["P", "F"]}
        elif kind == "choice":
            structure = {"kind": "choice", "slots": ["Litera odpowiedzi"], "allowed_values": ["A", "B", "C", "D"]}
        elif id == "11.1":
            structure["slots"] = ["Fragment A: władca", "Fragment B: władca"]
        elif kind == "essay":
            structure = {"kind": "essay", "slots": ["Numer tematu", "Całe wypracowanie"], "min_words": 300, "topic_options": ["1", "2", "3"]}
        item = {"id": id, "question": prompt, "source_text": source.strip(), "images": images,
                "max_points": raw["max_points"], "answer_format": "Tekst zawierający kompletną odpowiedź; zachowaj oznaczenia pozycji."}
        spec = {"id": id, "item_sha256": fingerprint(item), "primary_type": kind,
                "modules": [kind], "requirements": [prompt], "answer_structure": structure,
                "images": [im["path"] for im in images]}
        if kind == "essay":
            parts = re.split(r"(?m)^([123])\.\s+", prompt)
            assert len(parts) == 7
            spec["topic_requirements"] = [{"topic": parts[i], "requirements": [parts[i+1].strip()]} for i in (1, 3, 5)]
        items.append(item); specs.append(spec)
    exam = {"exam_id": "history-2024-may-reviewed-v1", "max_points": 60,
            "instructions": "Rozwiąż zadania po polsku, uwzględniając wszystkie dostarczone źródła i ilustracje.", "items": items}
    assert len(items) == 40 and sum(i["max_points"] for i in items) == 60
    contract = {"schema_version": 1, "exam_id": exam["exam_id"], "exam_sha256": fingerprint(exam), "items": specs}
    write(out / "exam.json", exam); write(out / "types.json", TYPES); write(out / "coverage.json", contract)
    write(out / "answers-template.json", {"exam_id": exam["exam_id"], "answers": [{"id": i["id"], "answer": ""} for i in items]})
    import_exam(out / "exam.json", TYPES, out / "input", contract)

    # Marking phase is isolated: nothing below is fed back into the inputs above.
    text = args.grading_text.read_text()
    sections = re.split(r"(?m)^Zadanie (\d+(?:\.\d+)?)\. \(0[–-](\d+)\)\s*", text)
    rubrics = {sections[i]: {"id": sections[i], "max_points": int(sections[i+1]),
               "rubric_and_examples": sections[i+2].strip()} for i in range(1, len(sections), 3)}
    assert set(rubrics) == set(TYPES), set(TYPES) - set(rubrics)
    closed = {"10": "A", "14.2": "C", "16.2": "B"}
    tf = {"19.1": ["F", "P", "P"], "20.2": ["F", "P", "F"]}
    keys = []
    for item in items:
        id = item["id"]; assert rubrics[id]["max_points"] == item["max_points"]
        key = {"id": id, "kind": "manual"}
        if id in closed:
            key.update(kind="choice", options=["A", "B", "C", "D"], expected=closed[id])
        elif id in tf:
            key.update(kind="labelled_components", labels=["1", "2", "3"], allowed_values=["P", "F"], expected=tf[id], points_by_correct={"0": 0, "1": 0, "2": 1, "3": 2})
        keys.append(key)
    (out / "grading").mkdir()
    for name, rows in [("keys", keys), ("rubrics", list(rubrics.values()))]:
        (out / f"grading/{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    write(out / "review-manifest.json", {"reviewer": "Codex text and visual source review; not independent expert review",
        "review_date": "2026-09-26", "items": 40, "points": 60, "source_pdf_sha256": sha(root / "raw/exam.pdf"),
        "candidate_sha256": sha(root / "tasks.jsonl"), "grading_pdf_sha256": sha(args.grading_pdf),
        "grading_text_sha256": sha(args.grading_text), "builder_sha256": sha(__file__),
        "review_notes": ["All relevant pages 4–29 visually inspected; discarded trailing headers and blank writing pages.",
            "Separated instructions and sources; preserved source wording and original figures.",
            "Removed genealogy spillover from task 12 and unrelated engraving date from task 14.",
            "Restored poetry column labels; transcribed visible genealogy and cartoon labels.",
            "Image crops retain original pixels and labels; crops use source pages, not marking pages.",
            "Previously audited public paper: second development test, not untouched holdout."],
        "image_regions": figures})
    print(json.dumps({"output": str(out), "items": len(items), "points": 60, "image_items": sum(bool(i["images"]) for i in items)}))


if __name__ == "__main__":
    main()
