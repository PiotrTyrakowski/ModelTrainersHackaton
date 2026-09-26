"""Matura task inputs, separate grading records, and source provenance."""

from .models import Task, SourceRecord, SourceRef, PageSpan, AnswerKey
from .dataset import Dataset
from .essay_bank import (
    EssayBank,
    EssayRecord,
    EssayQuery,
    EssayScope,
    EmbeddingIndex,
    MatchResult,
)

__all__ = [
    "Task",
    "SourceRecord",
    "SourceRef",
    "PageSpan",
    "AnswerKey",
    "Dataset",
    "EssayBank",
    "EssayRecord",
    "EssayQuery",
    "EssayScope",
    "EmbeddingIndex",
    "MatchResult",
]
