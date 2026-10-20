"""Versioned public result types. Strict validation is not semantic verification."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
PathText = Annotated[str, StringConstraints(min_length=1, max_length=1024)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Citation(StrictModel):
    evidence_id: Text
    path: PathText
    start: int = Field(ge=1)
    end: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("reversed_range")
        return self


class Finding(StrictModel):
    text: Text
    citations: list[Citation] = Field(min_length=1, max_length=8)


class Answer(StrictModel):
    findings: list[Finding] = Field(max_length=20)
    uncertainties: list[Text] = Field(max_length=20)
    evidence_status: Literal["sufficient", "insufficient"]

    @model_validator(mode="after")
    def meaningful(self):
        if self.evidence_status == "sufficient" and not self.findings:
            raise ValueError("sufficient_requires_findings")
        if self.evidence_status == "insufficient" and not self.uncertainties:
            raise ValueError("insufficient_requires_explanation")
        return self


class SourceLine(StrictModel):
    line: int = Field(ge=1)
    text: str


class Evidence(StrictModel):
    evidence_id: Text
    path: PathText
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    lines: list[SourceLine] = Field(min_length=1, max_length=120)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def continuous(self):
        if [line.line for line in self.lines] != list(range(self.start, self.end + 1)):
            raise ValueError("evidence_lines_must_match_range")
        return self


StopReason = Literal["completed", "insufficient_evidence", "invalid_answer", "model_error",
                     "task_timeout", "max_rounds", "max_tools", "context_budget", "repeated_calls"]


class Result(StrictModel):
    schema_version: Literal[1] = 1
    run_id: Text
    mode: Literal["offline", "live", "test"]
    question: Text
    repository: PathText
    model: Text
    budgets: dict
    stop_reason: StopReason
    answer: str
    findings: list[Finding]
    uncertainties: list[Text]
    evidence_status: Literal["sufficient", "insufficient", "unverified"]
    evidence: list[Evidence]
    trace: list[dict]
    messages: list[dict]
    rounds: int = Field(ge=0)
    model_attempts: int = Field(ge=0)
    tool_count: int = Field(ge=0)
    repair_count: int = Field(ge=0, le=1)
    validation_errors: list[str]
    elapsed_ms: float = Field(ge=0)
    usage: dict | None
