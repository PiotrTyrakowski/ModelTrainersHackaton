"""Complete closed answers from question metadata, never from marking keys."""

import json


CONTRACT = "typed_answer_v3"


def layout(question):
    structure = question.constraints.get("coverage", {}).get("answer_structure", {})
    if question.type not in {"choice", "chronology", "matching", "true_false"}:
        return None
    if structure.get("kind") not in {"choice", "multi_choice", "matching", "true_false"}:
        return None
    # Closed-plus-explanation tasks retain the full free-text contract.
    if "uzasadn" in question.prompt.casefold() or "wyjaśn" in question.prompt.casefold():
        return None
    slots, values = structure.get("slots"), structure.get("allowed_values")
    for items in (slots, values):
        if (not isinstance(items, list) or not items or
                any(not isinstance(x, str) or not x.strip() for x in items) or
                len(items) != len(set(items))):
            raise ValueError("Invalid closed-answer metadata")
    return structure


def schema(structure):
    return {
        "type": "object",
        "properties": {slot: {"type": "string", "enum": structure["allowed_values"]}
                       for slot in structure["slots"]},
        "required": structure["slots"],
        "additionalProperties": False,
    }


def render(value, structure):
    slots = structure["slots"]
    if not isinstance(value, dict) or set(value) != set(slots):
        raise ValueError("Missing or unexpected answer slots")
    if any(not isinstance(value[s], str) or value[s] not in structure["allowed_values"]
           for s in slots):
        raise ValueError("Answer is outside the allowed choices")
    if structure["kind"] == "choice" and len(slots) == 1:
        return value[slots[0]]
    return "\n".join(f"{slot}: {value[slot]}" for slot in slots)


def generate(question, context, base_prompt, structure):
    instruction = (
        "Zwróć tylko JSON. Każde wymagane pole oznacza osobną pozycję zadania. "
        "Wypełnij wszystkie pola wybraną etykietą; nie przepisuj treści opcji. "
        "Dozwolone etykiety nie wskazują poprawnych odpowiedzi. Schemat: "
        + json.dumps(schema(structure), ensure_ascii=False)
    )
    old_instruction = (
        "Zwróć tylko JSON z jednym polem answer zawierającym całą gotową odpowiedź. "
        "Nie przepisuj polecenia, nie dodawaj metadanych ani osobnej listy dowodów."
    )
    if old_instruction not in base_prompt:
        raise ValueError("Unknown base prompt")
    client = context["client"]
    previous = client.response_format
    client.response_format = {"type": "json_schema", "json_schema": {
        "name": "closed_answer", "strict": True, "schema": schema(structure)}}
    try:
        raw = client.generate(base_prompt.replace(old_instruction, instruction),
                              question, context["budget"], temperature=0)
    finally:
        client.response_format = previous
    return render(json.loads(raw), structure)
