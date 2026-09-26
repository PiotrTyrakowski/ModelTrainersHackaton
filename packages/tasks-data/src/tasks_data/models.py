from dataclasses import asdict, dataclass, field, fields
import math
from pathlib import PurePosixPath

TASK_TYPES = {
    "unknown",
    "choice",
    "true_false",
    "matching",
    "identification",
    "chronology",
    "genealogy",
    "data_table",
    "comparison",
    "explanation",
    "map",
    "art",
    "cartoon",
    "essay",
}
GRADING_KEYS = {
    "expected",
    "accepted",
    "gold",
    "gold_answer",
    "answer_key",
    "rubric",
    "rubric_and_examples",
    "correct_answer",
    "solution",
}


def no_grading_fields(value):
    if isinstance(value, dict):
        if GRADING_KEYS.intersection(value):
            raise ValueError("Grading fields cannot appear in task inputs")
        for child in value.values():
            no_grading_fields(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            no_grading_fields(child)


def safe_relative(value):
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts or "\\" in value:
        raise ValueError("Asset paths must be safe dataset-relative paths")
    return value


def record(cls, value):
    extra = set(value) - {f.name for f in fields(cls)}
    if extra:
        raise ValueError(f"Unexpected {cls.__name__} fields: {sorted(extra)}")
    return cls(**value)


def positive_points(value, optional=False):
    if optional and value is None:
        return
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError("Points must be finite and positive")


@dataclass(frozen=True)
class PageSpan:
    page: int
    start: int
    end: int

    def __post_init__(self):
        if (
            any(type(v) is not int for v in (self.page, self.start, self.end))
            or self.page < 1
            or not 0 <= self.start < self.end
        ):
            raise ValueError("Invalid 1-based PDF page / character span")


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    pages: tuple[int, ...] = ()
    spans: tuple[PageSpan, ...] = ()
    item_id: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "pages", tuple(self.pages))
        object.__setattr__(
            self,
            "spans",
            tuple(
                record(PageSpan, s) if isinstance(s, dict) else s for s in self.spans
            ),
        )
        if (
            not self.source_id
            or any(type(p) is not int or p < 1 for p in self.pages)
            or len(set(self.pages)) != len(self.pages)
        ):
            raise ValueError("Invalid source reference")
        if any(s.page not in self.pages for s in self.spans):
            raise ValueError("Span page absent from reference pages")


@dataclass(frozen=True)
class SourceRecord:
    id: str
    title: str
    kind: str
    uri: str
    sha256: str
    local_path: str
    rights: str = "Redistribution status not assessed; preserve source attribution."
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if (
            not self.id
            or not self.title
            or self.kind
            not in {"structured_exam", "exam_pdf", "grading_pdf", "reference", "image"}
        ):
            raise ValueError("Invalid source identity/kind")
        if len(self.sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.sha256
        ):
            raise ValueError("Invalid SHA-256")
        safe_relative(self.local_path)


@dataclass(frozen=True)
class Task:
    id: str
    exam_id: str
    prompt: str
    question_type: str = "unknown"
    source_text: str = ""
    image_paths: tuple[str, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()
    max_points: float | None = None
    constraints: dict = field(default_factory=dict)
    review_status: str = "needs_review"
    review_notes: tuple[str, ...] = ()
    original_id: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "image_paths", tuple(self.image_paths))
        object.__setattr__(
            self,
            "source_refs",
            tuple(
                record(SourceRef, r) if isinstance(r, dict) else r
                for r in self.source_refs
            ),
        )
        object.__setattr__(self, "review_notes", tuple(self.review_notes))
        if not all(
            isinstance(x, str) and x.strip()
            for x in [self.id, self.exam_id, self.prompt]
        ):
            raise ValueError("Task needs nonempty id, exam_id and prompt")
        if self.question_type not in TASK_TYPES:
            raise ValueError("Unsupported task type")
        if self.review_status not in {"ready", "needs_review"}:
            raise ValueError("Invalid review status")
        positive_points(self.max_points, optional=True)
        if self.review_status == "ready" and (
            self.question_type == "unknown" or self.max_points is None
        ):
            raise ValueError("Ready task needs a reviewed type and point value")
        for path in self.image_paths:
            safe_relative(path)
        no_grading_fields(self.constraints)

    @classmethod
    def from_dict(cls, value):
        no_grading_fields(value)
        return record(cls, value)

    def to_dict(self):
        return asdict(self)

    def solver_input(self, root):
        """Legacy matura-lab-compatible inputs; grading metadata never enters."""
        if self.review_status != "ready":
            raise ValueError(f"Task {self.id} needs review before solver export")
        from pathlib import Path

        root = Path(root).resolve()
        paths = []
        for p in self.image_paths:
            path = (root / p).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("Image missing or outside dataset")
            paths.append(str(path))
        return {
            "id": self.id,
            "type": self.question_type,
            "prompt": self.prompt,
            "source_text": self.source_text,
            "images": paths,
            "constraints": self.constraints,
            "max_points": self.max_points,
        }


@dataclass(frozen=True)
class AnswerKey:
    task_id: str
    kind: str = "manual"
    expected: object = None
    rubric: str | None = None
    max_points: float | None = None
    source_refs: tuple[SourceRef, ...] = ()
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(
            self,
            "source_refs",
            tuple(
                record(SourceRef, r) if isinstance(r, dict) else r
                for r in self.source_refs
            ),
        )
        if not self.task_id or self.kind not in {
            "manual",
            "exact",
            "choice",
            "aliases",
            "components",
            "labelled_components",
        }:
            raise ValueError("Invalid answer key")
        positive_points(self.max_points, optional=True)
        if self.kind == "manual" and self.expected is not None:
            raise ValueError("Manual placeholder cannot claim an expected answer")
        if self.kind != "manual" and self.expected is None:
            raise ValueError("Automatic key needs an expected answer")
