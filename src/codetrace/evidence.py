"""Snapshot registration, structural validation and deterministic rendering."""
import json

from pydantic import ValidationError

from codetrace.contracts import Answer, Evidence


def register(evidence: list[dict], data: dict, run_id: str):
    if not data["lines"]:
        return evidence, None
    for item in evidence:
        if all(item[key] == data[key] for key in ("path", "sha256", "start", "end", "lines")):
            return evidence, item["evidence_id"]
    item = Evidence(evidence_id=f"{run_id}:{len(evidence)+1}",
                    **{k: data[k] for k in ("path", "start", "end", "lines", "sha256")}).model_dump()
    return evidence + [item], item["evidence_id"]


def parse_answer(text: str) -> Answer:
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    elif text.startswith("```\n") and text.endswith("\n```"):
        text = text[4:-4]
    return Answer.model_validate(json.loads(text))


def validate_answer(text: str, evidence: list[dict]):
    try:
        answer = parse_answer(text)
    except (ValidationError, ValueError, TypeError):
        return None, ["invalid_answer_structure"]
    indexed = {e["evidence_id"]: e for e in evidence}
    errors = []
    for finding in answer.findings:
        for citation in finding.citations:
            e = indexed.get(citation.evidence_id)
            if not e or e["path"] != citation.path or not e["start"] <= citation.start <= citation.end <= e["end"]:
                errors.append(f"unsupported_citation:{citation.evidence_id}:{citation.path}:{citation.start}-{citation.end}")
    return answer, errors


def render(answer: Answer) -> str:
    lines = []
    for finding in answer.findings:
        refs = " ".join(f"[[{c.path}:L{c.start}-L{c.end}]]" for c in finding.citations)
        lines.append(f"- {finding.text} {refs}")
    if answer.uncertainties:
        lines.append("未确认事项：")
        lines.extend(f"- {text}" for text in answer.uncertainties)
    return "\n".join(lines)
