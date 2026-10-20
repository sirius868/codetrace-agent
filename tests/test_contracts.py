import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from codetrace.contracts import Answer, Citation, Evidence


def test_documented_examples():
    examples = json.loads((Path(__file__).parents[1] / "docs/answer-examples.json").read_text(encoding="utf-8"))
    Answer.model_validate(examples["valid"])
    Answer.model_validate(examples["insufficient"])
    with pytest.raises(ValidationError):
        Answer.model_validate(examples["invalid"])


@pytest.mark.parametrize("patch", [{"start": True}, {"end": 0}, {"start": 4, "end": 2}, {"extra": 1}])
def test_strict_citations(patch):
    with pytest.raises(ValidationError):
        Citation.model_validate({"evidence_id": "r:1", "path": "a.py", "start": 1, "end": 2, **patch})


@pytest.mark.parametrize("data", [
    {"findings": [], "uncertainties": [], "evidence_status": "sufficient"},
    {"findings": [], "uncertainties": [], "evidence_status": "insufficient"},
    {"findings": [], "uncertainties": [" "], "evidence_status": "insufficient"},
])
def test_empty_answers_rejected(data):
    with pytest.raises(ValidationError):
        Answer.model_validate(data)


def test_evidence_lines_match_range():
    with pytest.raises(ValidationError):
        Evidence(evidence_id="r:1", path="a.py", start=1, end=2,
                 lines=[{"line": 2, "text": "x"}], sha256="a" * 64)
