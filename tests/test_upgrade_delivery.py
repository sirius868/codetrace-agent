import json
import copy
from pathlib import Path

from codetrace.contracts import Result
from codetrace.evidence import validate_answer
from codetrace.benchmark import digest
from codetrace.paired_evaluation import import_reviews, summarize

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


def test_model_switch_records_keep_partial_runs_separate():
    directory = ROOT / "docs/verification"
    switch = json.loads((directory / "model-switch.json").read_text(encoding="utf-8"))
    previous = json.loads((directory / "qwen-interrupted.json").read_text(encoding="utf-8"))
    assert switch["status"] == "ok" and switch["returned_model"] == "deepseek-v4.1-flash"
    assert previous["model"] == "qwen3.8-27b"
    assert previous["completed_combinations"] == len(previous["rows"]) == 15
    assert previous["interrupted_attempt_usage"].startswith("unknown")


def test_pro_switch_preserves_flash_permission_failures():
    directory = ROOT / "docs/verification"
    switch = json.loads((directory / "pro-model-switch.json").read_text(encoding="utf-8"))
    previous = json.loads((directory / "flash-development-summary.json").read_text(encoding="utf-8"))
    assert switch["status"] == "ok" and switch["returned_model"] == "deepseek-v4-pro-0813"
    assert previous["completed_combinations"] == len(previous["rows"]) == 32
    assert sum("PermissionDeniedError" in r["errors"] for r in previous["rows"]) == 10
    current = json.loads((directory / "qwen-max-model-switch.json").read_text(encoding="utf-8"))
    assert current["status"] == "ok" and current["returned_model"] == "qwen3.8-max"
    smoke = json.loads((directory / "qwen-max-smoke.json").read_text(encoding="utf-8"))
    Result.model_validate(smoke)
    assert smoke["mode"] == "live" and smoke["stop_reason"] == "completed"
    assert {e["path"] for e in smoke["evidence"]} >= {"app.py", "service.py"}
    _, errors = validate_answer(json.dumps({k: smoke[k] for k in ("findings", "uncertainties", "evidence_status")}), smoke["evidence"])
    assert not errors


def test_pro_paired_delivery_preserves_provider_block_and_review_identity():
    directory = ROOT / "docs/verification/pro-paired"
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    drafts = json.loads((directory / "assistant-review.json").read_text(encoding="utf-8"))
    assert report["configuration"]["model"] == "deepseek-v4-pro-0813"
    assert digest(report["configuration"]) == report["configuration_sha256"]
    assert report["freeze"] is None
    assert report["summary"] == summarize(report)
    assert report["summary"]["planned"] == len(report["rows"]) == 48
    assert report["summary"]["ran"] == 32
    assert all(len(row["attempts"]) == (1 if row["split"] == "development" else 0) for row in report["rows"])
    held = [row for row in report["rows"] if row["split"] == "held-out"]
    assert len(held) == 16
    assert all(not row["attempts"] for row in held)
    assert len(drafts) == 32 and all(d["review_source"] == "assistant_draft" for d in drafts)
    recheck = json.loads((directory.parent / "pro-connectivity-recheck.json").read_text(encoding="utf-8"))
    assert recheck["http_status"] == 403 and recheck["provider_code"] == "AllocationQuota.FreeTierOnly"
    checked = import_reviews(copy.deepcopy(report), drafts)
    assert checked["summary"]["reviewed"] == 0
    assert checked["summary"]["analysis_ready_for_programming"] is False
    assert all(m["success_rate"] is None for m in checked["summary"]["modes"].values())
    for row in report["rows"]:
        if not row["attempts"]:
            continue
        attempt = row["attempts"][0]
        if "result" not in attempt:
            assert attempt["status"] == "case_error"
            continue
        result = attempt["result"]
        Result.model_validate(result)
        assert result["run_id"] == attempt["run_id"] and result["stop_reason"] == attempt["status"]
        if attempt["status"] in {"completed", "insufficient_evidence"}:
            _, errors = validate_answer(json.dumps({k: result[k] for k in ("findings", "uncertainties", "evidence_status")}), result["evidence"])
            assert not errors
