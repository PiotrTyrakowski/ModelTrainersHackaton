"""Conservative, offline routing to unchanged, prepared essay text."""

import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

PACKAGE = Path(__file__).resolve().parents[2] / "packages/tasks-data/src"


def normalized(text):
    # Preserve negation, punctuation and numbers; tolerate only case/whitespace.
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def route(question, settings):
    if str(PACKAGE) not in sys.path:
        sys.path.insert(0, str(PACKAGE))
    from tasks_data.essay_bank import EssayBank, EssayQuery, EssayScope
    if settings.get("version") != "reviewed_essay_v1":
        raise ValueError("Unknown essay routing version")
    if question.type != "essay":
        raise ValueError("Essay router received a different question type")
    if question.images or question.source_text.strip():
        return None, {"status": "no_match", "reason": "task_specific_sources"}
    structure = question.constraints.get("coverage", {}).get("answer_structure", {})
    expected = structure.get("topic_options")
    matches = list(re.finditer(r"(?m)^\s*(\d+)\.\s+", question.prompt))
    labels = [m.group(1) for m in matches]
    if not expected or labels != expected or len(labels) != len(set(labels)):
        return None, {"status": "no_match", "reason": "unknown_topic_structure"}
    minimum = max(question.constraints.get("min_words", 0), structure.get("min_words", 0))
    if type(minimum) is not int or minimum <= 0:
        return None, {"status": "no_match", "reason": "unknown_length_requirement"}
    catalog = json.loads(Path(settings["catalog"]).read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1:
        raise ValueError("Unknown scope catalog")
    introduction = normalized(question.prompt[:matches[0].start()])
    if introduction not in {normalized(t) for t in catalog.get("introductions", [])}:
        return None, {"status": "no_match", "reason": "global_requirements_not_reviewed"}
    reviewed = {normalized(t["question"]): t for t in catalog["topics"]}
    if len(reviewed) != len(catalog["topics"]):
        raise ValueError("Duplicate reviewed topic")
    bank = EssayBank.from_jsonl(settings["bank"])
    attempts = []
    for i, match in enumerate(matches):
        topic = question.prompt[match.end():matches[i+1].start() if i+1 < len(matches) else None].strip()
        spec = reviewed.get(normalized(topic))
        if spec is None:
            attempts.append({"topic": labels[i], "status": "no_match", "reason": "scope_not_reviewed"})
            continue
        result = bank.match(EssayQuery(topic, EssayScope.from_dict(spec["scope"]), minimum),
                            method="lexical", min_score=settings.get("min_score", 0.3),
                            min_margin=settings.get("min_margin", 0.03))
        attempts.append({"topic": labels[i], **result.to_dict()})
        # Avoid duplicating the full essay in the routing trace.
        attempts[-1].pop("essay", None)
        if result.status == "matched":
            return f"Temat {labels[i]}.\n\n" + result.essay, {
                "status": "matched", "method": "reviewed_scope_then_lexical",
                "record_id": result.record_id, "topic": labels[i], "attempts": attempts,
                "essay_sha256": hashlib.sha256(result.essay.encode("utf-8")).hexdigest(),
                "essay_words": len(result.essay.split()), "generation_calls": 0,
                "embedding_calls": 0, "body_returned_unchanged": True,
            }
    return None, {"status": "no_match", "reason": "no_compatible_essay", "attempts": attempts}
