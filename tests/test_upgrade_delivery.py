import json
from pathlib import Path

from codetrace.contracts import Result
from codetrace.evidence import validate_answer

ROOT = Path(__file__).parents[1]


def test_live_mvp_records_remain_unreviewed_and_valid():
    base = ROOT / "docs/verification/live-mvp"
    files = [base / f"smoke-{s}.json" for s in ("entry", "cross-file", "config", "no-answer")]
    report = json.loads(next((base / "ten-case").glob("*/report.json")).read_text(encoding="utf-8"))
    assert len(report["cases"]) == 10 and report["mode"] == "live"
    assert report["summary"]["reviewed"] == 0 and report["summary"]["live_success_rate"] is None
    records = [json.loads(p.read_text(encoding="utf-8")) for p in files] + [r["result"] for r in report["cases"]]
    for record in records:
        Result.model_validate(record)
        assert record["mode"] == "live" and record["usage"] is not None
        if record["stop_reason"] in {"completed", "insufficient_evidence"}:
            _, errors = validate_answer(json.dumps({k: record[k] for k in ("findings", "uncertainties", "evidence_status")}), record["evidence"])
            assert not errors
    draft = json.loads((base / "ten-case-assistant-draft.json").read_text(encoding="utf-8"))
    assert draft["review_source"] == "assistant_draft"
    assert next(r for r in draft["reviews"] if r["id"] == "python-exception")["semantic_correct"] is False
