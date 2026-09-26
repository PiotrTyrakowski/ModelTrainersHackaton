"""Import official structured exam inputs without loading expected answers."""

from pathlib import Path
import json
import shutil
from .models import Task, SourceRecord, SourceRef, AnswerKey, safe_relative
from .dataset import Dataset, sha256_file


def new_output(path):
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise ValueError(
            "Output directory must be new or empty; do not overwrite an existing dataset"
        )
    path.mkdir(parents=True, exist_ok=True)
    return path


def import_structured(exam_path, output, type_map=None, source_uri=None):
    exam_path = Path(exam_path).resolve()
    exam = json.loads(exam_path.read_text(encoding="utf-8"))
    items = exam["items"]
    ids = [i["id"] for i in items]
    if (
        not items
        or any(not isinstance(i, str) or not i for i in ids)
        or len(ids) != len(set(ids))
    ):
        raise ValueError("Exam needs unique nonempty item IDs")
    if type_map is not None and set(type_map) != set(ids):
        raise ValueError("Type map must cover every exam item exactly once")
    # A question package can contain an answer-format example, not a gold key.
    for item in items:
        if {"answer", "expected", "correct_answer", "solution", "rubric"} & set(item):
            raise ValueError(
                "Answer-bearing exam items cannot enter the input importer"
            )
    planned = []
    for item in items:
        for image in item.get("images", []):
            relative = safe_relative(image["path"])
            source = (exam_path.parent / relative).resolve()
            if not source.is_relative_to(exam_path.parent) or not source.is_file():
                raise ValueError("Image is missing or outside the exam package")
            if sha256_file(source) != image["sha256"]:
                raise ValueError("Image checksum mismatch")
            planned.append((relative, source, image))
    root = new_output(output)
    (root / "raw").mkdir()
    shutil.copy2(exam_path, root / "raw/exam.json")
    exam_source = SourceRecord(
        "exam",
        exam.get("title", exam["exam_id"]),
        "structured_exam",
        source_uri or exam.get("source_url") or exam_path.as_uri(),
        sha256_file(exam_path),
        "raw/exam.json",
        metadata={
            "upstream_exam_id": exam["exam_id"],
            "original_source_url": exam.get("source_url"),
            "input_contract": "separate text and images",
        },
    )
    sources = [exam_source]
    assets = {}
    for relative, source, image in planned:
        if relative in assets:
            continue
        target = "assets/" + relative
        dest = root / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        sid = "image:" + relative
        assets[relative] = (target, sid)
        sources.append(
            SourceRecord(
                sid,
                relative,
                "image",
                exam_source.uri + "#" + relative,
                sha256_file(dest),
                target,
                metadata={"upstream_page": image.get("source_page")},
            )
        )
    tasks = []
    keys = []
    for item in items:
        images = item.get("images", [])
        pages = tuple(
            sorted(
                {
                    i["source_page"]
                    for i in images
                    if type(i.get("source_page")) is int and i["source_page"] > 0
                }
            )
        )
        kind = type_map[item["id"]] if type_map else "unknown"
        task = Task(
            item["id"],
            exam["exam_id"],
            item["question"],
            kind,
            item.get("source_text", ""),
            tuple(assets[i["path"]][0] for i in images),
            (SourceRef("exam", pages, item_id=item["id"]),),
            item.get("max_points"),
            {
                "answer_format": item.get(
                    "answer_format", "Odpowiedź jako jeden tekst."
                ),
                "instructions": exam.get("instructions", ""),
                "syntax_notice": "Answer-format examples describe syntax, not correct answers.",
            },
            (
                "ready"
                if kind != "unknown" and item.get("max_points") is not None
                else "needs_review"
            ),
            (
                ()
                if kind != "unknown"
                else (
                    "Question type needs review; source item boundaries are preserved.",
                )
            ),
            item["id"],
        )
        tasks.append(task)
        keys.append(AnswerKey(task.id, max_points=task.max_points))
    if (
        exam.get("max_points") is not None
        and sum(t.max_points or 0 for t in tasks) != exam["max_points"]
    ):
        raise ValueError("Item points do not equal the declared exam total")
    dataset = Dataset(
        exam["exam_id"],
        tasks,
        sources,
        keys,
        {
            "importer": "structured-v1",
            "official_total_points": exam.get("max_points"),
            "grading_status": "manual placeholders only; no expected answers imported",
            "type_map_supplied": type_map is not None,
        },
        root,
    )
    dataset.save()
    return dataset
