"""Retrieve a complete stored essay; this module never generates or rewrites text."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Protocol, Sequence
import unicodedata


def _text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold().replace("ł", "l"))
    return " ".join(
        re.sub(
            r"[^\w\s]", " ", "".join(c for c in value if not unicodedata.combining(c))
        ).split()
    )


def _strings(values: Sequence[str], name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or any(
        not isinstance(v, str) or not v.strip() for v in values
    ):
        raise ValueError(f"{name} must contain nonempty strings")
    return tuple(values)


@dataclass(frozen=True)
class EssayScope:
    start_year: int | None = None
    end_year: int | None = None
    entities: tuple[str, ...] = ()
    aspects: tuple[str, ...] = ()
    intent: str | None = None

    def __post_init__(self) -> None:
        if (self.start_year is None) != (self.end_year is None):
            raise ValueError("Declare both period endpoints or neither")
        if self.start_year is not None:
            if any(
                type(v) is not int or v == 0 for v in (self.start_year, self.end_year)
            ):
                raise ValueError(
                    "Years must be nonzero integers; negative values denote BCE"
                )
            if self.start_year > self.end_year:
                raise ValueError("Period endpoints are reversed")
        object.__setattr__(self, "entities", _strings(self.entities, "entities"))
        object.__setattr__(self, "aspects", _strings(self.aspects, "aspects"))
        if self.intent is not None and (
            not isinstance(self.intent, str) or not self.intent.strip()
        ):
            raise ValueError("intent must be a nonempty string")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EssayScope:
        if not isinstance(value, dict) or set(value) - set(cls.__dataclass_fields__):
            raise ValueError("Invalid essay scope fields")
        return cls(**value)


@dataclass(frozen=True)
class EssayRecord:
    id: str
    question: str
    essay: str
    scope: EssayScope = field(default_factory=EssayScope)
    sources: tuple[str, ...] = ()
    preparation: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("id", "question", "essay"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if not isinstance(self.scope, EssayScope):
            raise ValueError("scope must be an EssayScope")
        object.__setattr__(self, "sources", _strings(self.sources, "sources"))
        if not isinstance(self.preparation, dict):
            raise ValueError("preparation must be an object")
        json.dumps(self.preparation, allow_nan=False)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EssayRecord:
        if not isinstance(value, dict) or set(value) - set(cls.__dataclass_fields__):
            raise ValueError("Invalid essay record fields")
        try:
            return cls(
                **{**value, "scope": EssayScope.from_dict(value.get("scope", {}))}
            )
        except TypeError as error:
            raise ValueError("Essay record requires id, question and essay") from error


@dataclass(frozen=True)
class EssayQuery:
    question: str
    scope: EssayScope = field(default_factory=EssayScope)
    min_words: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise ValueError("Question must be nonempty")
        if (
            not isinstance(self.scope, EssayScope)
            or type(self.min_words) is not int
            or self.min_words < 0
        ):
            raise ValueError("Invalid essay requirements")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EssayQuery:
        if not isinstance(value, dict) or set(value) - set(cls.__dataclass_fields__):
            raise ValueError("Invalid essay query fields")
        try:
            return cls(
                **{**value, "scope": EssayScope.from_dict(value.get("scope", {}))}
            )
        except TypeError as error:
            raise ValueError("Essay query requires question") from error


class Embedder(Protocol):
    identity: str

    def embed(self, texts: Sequence[str], *, role: str) -> list[list[float]]: ...


def _unit(vector: Sequence[float]) -> tuple[float, ...]:
    if not isinstance(vector, (list, tuple)) or not vector:
        raise ValueError("An embedding must be a nonempty vector")
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in vector
    ):
        raise ValueError("Embedding values must be finite numbers")
    norm = math.hypot(*vector)
    if norm == 0 or not math.isfinite(norm):
        raise ValueError("Embedding norm must be finite and nonzero")
    return tuple(v / norm for v in vector)


def _question_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EmbeddingIndex:
    encoder_id: str
    question_hashes: dict[str, str]
    vectors: dict[str, tuple[float, ...]]

    def __post_init__(self) -> None:
        if not isinstance(self.encoder_id, str) or not self.encoder_id.strip():
            raise ValueError("Index requires an encoder identity")
        if (
            not isinstance(self.question_hashes, dict)
            or not isinstance(self.vectors, dict)
            or not self.vectors
            or set(self.vectors) != set(self.question_hashes)
        ):
            raise ValueError(
                "Index vectors and question hashes must have the same nonempty IDs"
            )
        if any(not isinstance(k, str) or not k for k in self.vectors):
            raise ValueError("Invalid index ID")
        if any(
            not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)
            for v in self.question_hashes.values()
        ):
            raise ValueError("Invalid question hash")
        normalized = {key: _unit(vector) for key, vector in self.vectors.items()}
        if len({len(v) for v in normalized.values()}) != 1:
            raise ValueError("Embedding dimensions differ")
        object.__setattr__(self, "vectors", normalized)
        object.__setattr__(self, "question_hashes", dict(self.question_hashes))

    def write(self, path: str | Path) -> None:
        _write_json(path, {"schema_version": 1, **asdict(self)})

    @classmethod
    def read(cls, path: str | Path) -> EmbeddingIndex:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or set(value)
            != {"schema_version", "encoder_id", "question_hashes", "vectors"}
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
        ):
            raise ValueError("Unsupported embedding index")
        return cls(value["encoder_id"], value["question_hashes"], value["vectors"])


@dataclass(frozen=True)
class Candidate:
    record_id: str
    score: float | None
    exclusions: tuple[str, ...] = ()


@dataclass(frozen=True)
class MatchResult:
    status: str
    method: str
    reason: str
    record_id: str | None = None
    essay: str | None = None
    score: float | None = None
    candidates: tuple[Candidate, ...] = ()
    generation_calls: int = 0
    embedding_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_essay(self, path: str | Path) -> None:
        """Write the exact UTF-8 essay bytes, without prefixes or an added newline."""
        if self.status != "matched" or self.essay is None:
            raise ValueError("No selected essay to write")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.essay.encode("utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _features(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for word in _text(text).split():
        counts["w:" + word] += 1
        if len(word) >= 3:
            padded = "^" + word + "$"
            for n in (3, 4):
                for offset in range(len(padded) - n + 1):
                    counts["c:" + padded[offset : offset + n]] += 1
    return counts


def _exclusions(record: EssayRecord, query: EssayQuery) -> tuple[str, ...]:
    missing = []
    required, offered = query.scope, record.scope
    if required.start_year is not None and (required.start_year, required.end_year) != (
        offered.start_year,
        offered.end_year,
    ):
        missing.append("period_mismatch_or_unknown")
    if required.intent is not None and (
        offered.intent is None or _text(required.intent) != _text(offered.intent)
    ):
        missing.append("intent_mismatch_or_unknown")
    for field_name in ("entities", "aspects"):
        if {_text(x) for x in getattr(required, field_name)} - {
            _text(x) for x in getattr(offered, field_name)
        }:
            missing.append("missing_" + field_name)
    if len(record.essay.split()) < query.min_words:
        missing.append("too_short")
    return tuple(missing)


class EssayBank:
    def __init__(self, records: Sequence[EssayRecord]):
        self.records = tuple(records)
        if any(not isinstance(record, EssayRecord) for record in self.records):
            raise ValueError("Bank entries must be EssayRecord instances")
        if len({record.id for record in self.records}) != len(self.records):
            raise ValueError("Essay IDs must be unique")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> EssayBank:
        records = []
        for number, line in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                records.append(EssayRecord.from_dict(json.loads(line)))
            except (ValueError, TypeError) as error:
                raise ValueError(f"Invalid essay record on line {number}") from error
        return cls(records)

    def write_jsonl(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "".join(
                json.dumps(asdict(r), ensure_ascii=False, allow_nan=False) + "\n"
                for r in self.records
            ),
            encoding="utf-8",
        )

    def build_index(self, embedder: Embedder) -> EmbeddingIndex:
        if not self.records:
            raise ValueError("Cannot embed an empty bank")
        vectors = embedder.embed([r.question for r in self.records], role="document")
        if len(vectors) != len(self.records):
            raise ValueError("Embedding count does not match the bank")
        return EmbeddingIndex(
            embedder.identity,
            {r.id: _question_hash(r.question) for r in self.records},
            {r.id: v for r, v in zip(self.records, vectors)},
        )

    def _lexical_scores(self, question: str) -> dict[str, float]:
        documents = {r.id: _features(r.question) for r in self.records}
        frequency: Counter[str] = Counter()
        for terms in documents.values():
            frequency.update(terms.keys())

        def vector(terms: Counter[str]) -> dict[str, float]:
            values = {
                term: (1 + math.log(count))
                * (1 + math.log((len(documents) + 1) / (frequency[term] + 1)))
                * (0.25 if term.startswith("c:") else 1)
                for term, count in terms.items()
            }
            norm = math.hypot(*values.values())
            return {k: v / norm for k, v in values.items()} if norm else {}

        q = vector(_features(question))
        return {
            key: max(
                0.0,
                min(
                    1.0,
                    sum(
                        q.get(term, 0) * weight
                        for term, weight in vector(terms).items()
                    ),
                ),
            )
            for key, terms in documents.items()
        }

    def match(
        self,
        query: EssayQuery,
        *,
        method: str = "lexical",
        min_score: float | None = None,
        min_margin: float = 0.03,
        index: EmbeddingIndex | None = None,
        embedder: Embedder | None = None,
        query_vector: Sequence[float] | None = None,
        encoder_id: str | None = None,
    ) -> MatchResult:
        if not isinstance(query, EssayQuery) or method not in {"lexical", "dense"}:
            raise ValueError("Use an EssayQuery and lexical or dense matching")
        if min_score is None:
            min_score = 0.3 if method == "lexical" else 0.7
        if (
            isinstance(min_score, bool)
            or not isinstance(min_score, (int, float))
            or not math.isfinite(min_score)
            or not 0 <= min_score <= 1
        ):
            raise ValueError("min_score must be between zero and one")
        if (
            isinstance(min_margin, bool)
            or not isinstance(min_margin, (int, float))
            or not math.isfinite(min_margin)
            or not 0 <= min_margin <= 2
        ):
            raise ValueError("min_margin must be between zero and two")
        if method == "lexical" and any(
            value is not None for value in (index, embedder, query_vector, encoder_id)
        ):
            raise ValueError("Lexical matching does not accept model inputs")
        exclusions = {r.id: _exclusions(r, query) for r in self.records}
        rejected = tuple(
            Candidate(r.id, None, exclusions[r.id])
            for r in self.records
            if exclusions[r.id]
        )
        if not self.records:
            return MatchResult("no_match", method, "empty_bank")
        if len(rejected) == len(self.records):
            return MatchResult(
                "no_match", method, "requirements_not_met", candidates=rejected
            )
        calls = 0
        if method == "dense":
            if index is None or index.question_hashes != {
                r.id: _question_hash(r.question) for r in self.records
            }:
                raise ValueError(
                    "Embedding index is missing, stale or belongs to another bank"
                )
            if (embedder is None) == (query_vector is None):
                raise ValueError(
                    "Provide exactly one embedder or precomputed query vector"
                )
            identity = embedder.identity if embedder is not None else encoder_id
            if identity != index.encoder_id:
                raise ValueError("Query encoder identity differs from the index")
            if embedder is not None:
                vectors = embedder.embed([query.question], role="query")
                if len(vectors) != 1:
                    raise ValueError("Expected one query embedding")
                query_vector = vectors[0]
                calls = 1
            q_vector = _unit(query_vector)
            if len(q_vector) != len(next(iter(index.vectors.values()))):
                raise ValueError("Query embedding dimension differs from the index")
            scores = {
                key: max(-1.0, min(1.0, sum(a * b for a, b in zip(q_vector, vector))))
                for key, vector in index.vectors.items()
            }
        else:
            scores = self._lexical_scores(query.question)
        ranked = sorted(
            (
                Candidate(r.id, scores[r.id])
                for r in self.records
                if not exclusions[r.id]
            ),
            key=lambda c: (-c.score, c.record_id),
        )
        best = ranked[0]
        common = {
            "method": method,
            "score": best.score,
            "candidates": tuple(ranked) + rejected,
            "embedding_calls": calls,
        }
        if best.score <= 0 or best.score < min_score:
            return MatchResult("no_match", reason="below_threshold", **common)
        if len(ranked) > 1 and (
            best.score - ranked[1].score <= 1e-12
            or best.score - ranked[1].score < min_margin
        ):
            return MatchResult("no_match", reason="ambiguous", **common)
        record = next(r for r in self.records if r.id == best.record_id)
        return MatchResult(
            "matched",
            reason="selected_stored_essay",
            record_id=record.id,
            essay=record.essay,
            **common,
        )
