from dataclasses import asdict
from pathlib import Path
import hashlib
import json
from .models import Task, SourceRecord, AnswerKey, record


def read_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Dataset:
    def __init__(self, exam_id, tasks, sources, keys=(), metadata=None, root=None):
        self.exam_id = exam_id
        self.tasks = list(tasks)
        self.sources = list(sources)
        self.keys = list(keys)
        self.metadata = metadata or {}
        self.root = Path(root) if root else None

    def validate(self, check_files=True):
        if not isinstance(self.exam_id, str) or not self.exam_id:
            raise ValueError("Dataset needs exam_id")
        ids = [t.id for t in self.tasks]
        sids = [s.id for s in self.sources]
        kids = [k.task_id for k in self.keys]
        if (
            len(ids) != len(set(ids))
            or len(sids) != len(set(sids))
            or len(kids) != len(set(kids))
        ):
            raise ValueError("Duplicate task/source/key IDs")
        source_map = {s.id: s for s in self.sources}
        task_map = {t.id: t for t in self.tasks}
        registered_images = {s.local_path for s in self.sources if s.kind == "image"}
        if set(kids) - set(ids):
            raise ValueError("Key references unknown task")
        for t in self.tasks:
            if t.exam_id != self.exam_id:
                raise ValueError("Task belongs to another exam")
            if set(t.image_paths) - registered_images:
                raise ValueError(
                    "Every task image needs a checksum-bearing image source record"
                )
            for ref in t.source_refs:
                if ref.source_id not in source_map:
                    raise ValueError("Task references missing source")
                if source_map[ref.source_id].kind == "grading_pdf":
                    raise ValueError("Task input cannot reference a grading source")
                count = source_map[ref.source_id].metadata.get("pdf_pages")
                if count is not None and any(p > count for p in ref.pages):
                    raise ValueError("Task references a page outside the PDF")
        for key in self.keys:
            task = task_map[key.task_id]
            if key.max_points is not None and key.max_points != task.max_points:
                raise ValueError("Key points disagree with task")
            if any(ref.source_id not in source_map for ref in key.source_refs):
                raise ValueError("Key references missing source")
        if check_files:
            if self.root is None:
                raise ValueError("Dataset root is required to verify files")
            root = self.root.resolve()
            for source in self.sources:
                p = (root / source.local_path).resolve()
                if not p.is_relative_to(root) or not p.is_file():
                    raise ValueError("Source missing or escapes dataset")
                if sha256_file(p) != source.sha256:
                    raise ValueError("Source checksum mismatch")
            page_texts = {}
            for source in self.sources:
                if extracted_id := source.metadata.get("extracted_pages_source_id"):
                    if extracted_id not in source_map:
                        raise ValueError("PDF page text source is missing")
                    rows = read_jsonl(root / source_map[extracted_id].local_path)
                    if [r["page"] for r in rows] != list(
                        range(1, source.metadata["pdf_pages"] + 1)
                    ):
                        raise ValueError("Extracted page sequence is incomplete")
                    page_texts[source.id] = {r["page"]: r["text"] for r in rows}
            for task in self.tasks:
                for ref in task.source_refs:
                    if ref.spans and ref.source_id not in page_texts:
                        raise ValueError("Character spans need archived page texts")
                    for span in ref.spans:
                        if span.end > len(page_texts[ref.source_id][span.page]):
                            raise ValueError(
                                "Character span extends beyond its source page"
                            )
                for image in task.image_paths:
                    p = (root / image).resolve()
                    if not p.is_relative_to(root) or not p.is_file():
                        raise ValueError("Task image missing or escapes dataset")
        ready = sum(t.review_status == "ready" for t in self.tasks)
        return {
            "exam_id": self.exam_id,
            "tasks": len(self.tasks),
            "ready": ready,
            "needs_review": len(self.tasks) - ready,
            "known_points": sum(t.max_points or 0 for t in self.tasks),
            "unknown_points": sum(t.max_points is None for t in self.tasks),
            "keys": len(self.keys),
            "automatic_keys": sum(k.kind != "manual" for k in self.keys),
            "sources": len(self.sources),
            "empty_dataset": not self.tasks,
        }

    def save(self, root=None):
        self.root = Path(root) if root else self.root
        if self.root is None:
            raise ValueError("Provide output directory")
        self.root.mkdir(parents=True, exist_ok=True)
        stats = self.validate()
        write_jsonl(self.root / "tasks.jsonl", [asdict(t) for t in self.tasks])
        write_jsonl(self.root / "sources.jsonl", [asdict(s) for s in self.sources])
        write_jsonl(self.root / "grading/keys.jsonl", [asdict(k) for k in self.keys])
        write_json(
            self.root / "manifest.json",
            {
                "schema_version": 1,
                "exam_id": self.exam_id,
                "metadata": self.metadata,
                "summary": stats,
                "files": {
                    name: sha256_file(self.root / name)
                    for name in ["tasks.jsonl", "sources.jsonl", "grading/keys.jsonl"]
                },
            },
        )
        return stats

    @classmethod
    def load(cls, root, check_files=True):
        root = Path(root)
        manifest = json.loads((root / "manifest.json").read_text())
        if manifest.get("schema_version") != 1:
            raise ValueError("Unsupported dataset schema")
        for name in ["tasks.jsonl", "sources.jsonl", "grading/keys.jsonl"]:
            if manifest["files"].get(name) != sha256_file(root / name):
                raise ValueError("Dataset file changed since manifest creation")
        result = cls(
            manifest["exam_id"],
            [Task.from_dict(t) for t in read_jsonl(root / "tasks.jsonl")],
            [record(SourceRecord, s) for s in read_jsonl(root / "sources.jsonl")],
            [record(AnswerKey, k) for k in read_jsonl(root / "grading/keys.jsonl")],
            manifest.get("metadata"),
            root,
        )
        result.validate(check_files=check_files)
        return result

    def export_solver_inputs(self, path):
        self.validate()
        if not self.tasks:
            raise ValueError("Empty datasets cannot be exported for evaluation")
        # Build all rows before writing: mixed ready/draft datasets fail closed.
        rows = [task.solver_input(self.root) for task in self.tasks]
        write_jsonl(path, rows)
        return len(rows)
