import copy
import json
from pathlib import Path
import shutil
import socket

import pytest

from codetrace import evaluation as ev


def copy_dataset(tmp_path):
    for folder in ("eval_python", "eval_java"):
        shutil.copytree(ev.DEFAULT_DATASET.parent / folder, tmp_path / folder)
    target = tmp_path / "evaluation.json"
    shutil.copyfile(ev.DEFAULT_DATASET, target)
    return target


@pytest.mark.parametrize("damage", ["duplicate", "hash", "snippet", "file", "category", "language", "version"])
def test_dataset_rejects_incomparable_data(tmp_path, damage):
    path = copy_dataset(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    case = raw["cases"][0]
    if damage == "duplicate":
        raw["cases"][1]["id"] = case["id"]
    elif damage == "hash":
        (tmp_path / "eval_python/app.py").write_text("changed")
    elif damage == "snippet":
        case["snippets"][0]["text"] = "invented"
    elif damage == "file":
        case["expected_files"] = ["../outside.py"]
    elif damage in {"category", "language"}:
        case[damage] = "unsupported"
    else:
        raw["schema_version"] = 2
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        ev.load_dataset(path)


def test_manifest_portable_but_sensitive_to_content(tmp_path):
    path = tmp_path / "app.py"
    path.write_bytes(b"a\nb\n")
    digest = ev.manifest(tmp_path)
    path.write_bytes(b"a\r\nb\r\n")
    assert ev.manifest(tmp_path) == digest
    path.write_bytes(b"different\n")
    assert ev.manifest(tmp_path) != digest


async def test_offline_full_dataset_no_network_reports_unknowns(tmp_path, monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("offline must not create a client or connect")
    monkeypatch.setattr(ev, "OpenAICompatibleModel", forbidden)
    with monkeypatch.context() as scoped:
        scoped.setattr(socket.socket, "connect", forbidden)
        scoped.setattr(socket, "getaddrinfo", forbidden)
        report = await ev.evaluate(ev.DEFAULT_DATASET)
    assert report["mode"] == "offline" and report["live_status"] == "not_run"
    assert report["summary"]["statuses"] == {"completed": 8, "insufficient_evidence": 2}
    assert report["summary"]["reviewed"] == 0
    assert report["summary"]["live_success_rate"] is None
    assert report["summary"]["citation_validity"] == {"numerator": 14, "denominator": 14, "value": 1.0}
    assert report["summary"]["file_coverage"] == {"numerator": 14, "denominator": 14, "value": 1.0}
    for row in report["cases"]:
        assert row["metrics"]["usage"] is None and row["review"] is None
        if not row["answerable"]:
            assert row["metrics"]["citation_validity"] is None
        if row["category"] == "cross-file":
            assert len({e["path"] for e in row["result"]["evidence"]}) == 2
    path = ev.save_report(report, tmp_path)
    assert path.with_suffix(".md").exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    for row in saved["cases"]:
        record = json.loads((path.parent / f"{row['run_id']}.json").read_text(encoding="utf-8"))
        assert record == row["result"]


async def test_missing_live_credentials_does_not_create_client(monkeypatch):
    for key in ("CODETRACE_API_KEY", "CODETRACE_MODEL", "CODETRACE_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(ev, "OpenAICompatibleModel", lambda: pytest.fail("must not create client"))
    report = await ev.evaluate(ev.DEFAULT_DATASET, live=True)
    assert report["status"] == "not_run" and not report["cases"]
    assert report["summary"]["live_success_rate"] is None


async def test_case_failure_isolated_and_sanitized():
    def factory(case):
        if case.id == "python-entry":
            raise RuntimeError("secret-provider-key")
        return ev.DemoModel(steps=[], insufficient=True)
    report = await ev.evaluate(ev.DEFAULT_DATASET, model_factory=factory)
    assert len(report["cases"]) == 10
    assert report["summary"]["case_errors"] == 1
    assert report["summary"]["measured"] == 9
    assert "secret-provider-key" not in json.dumps(report)
    assert report["summary"]["citation_validity"]["value"] is None


async def test_review_identity_and_valid_citation_wrong_semantics():
    report = await ev.evaluate(ev.DEFAULT_DATASET)
    row = report["cases"][0]
    raw = {"report_id": report["report_id"], "dataset_sha256": report["dataset_sha256"], "reviews": [
        {"id": row["id"], "run_id": row["run_id"], "semantic_correct": False,
         "omitted_facts": ["missing entry behavior"], "reasonable_refusal": None, "notes": "Only says it read code."}]}
    ev.import_reviews(report, raw)
    assert row["metrics"]["citation_validity"] == 1
    assert report["summary"]["semantic_review"] == {"numerator": 0, "denominator": 1, "value": 0}
    assert report["summary"]["live_success_rate"] is None
    for key in ("report_id", "dataset_sha256"):
        bad = copy.deepcopy(raw)
        bad[key] = "different"
        with pytest.raises(ValueError):
            ev.import_reviews(report, bad)
    bad = copy.deepcopy(raw)
    bad["reviews"][0]["run_id"] = "wrong-run"
    with pytest.raises(ValueError):
        ev.import_reviews(report, bad)


def test_insufficient_answer_not_success_and_partial_review_denominator():
    rows = [{"id": "answerable", "answerable": True, "status": "insufficient_evidence", "metrics": None,
             "review": {"semantic_correct": True, "omitted_facts": [], "reasonable_refusal": True}},
            {"id": "absent", "answerable": False, "status": "insufficient_evidence", "metrics": None,
             "review": {"semantic_correct": True, "omitted_facts": [], "reasonable_refusal": True}}]
    report = {"mode": "live", "cases": rows}
    assert ev.summarize(report)["live_success_rate"] == 0.5
    rows[0]["review"] = None
    summary = ev.summarize(report)
    assert summary["live_success_rate"] is None
    assert summary["semantic_review"]["denominator"] == 1


def test_metrics_invalid_and_zero_citations():
    dataset, _ = ev.load_dataset(ev.DEFAULT_DATASET)
    result = {"findings": [{"citations": [{"evidence_id": "unknown", "path": "app.py", "start": 1, "end": 2}]}],
              "evidence": [], "rounds": 1, "model_attempts": 1, "tool_count": 0, "elapsed_ms": 1, "usage": None}
    m = ev.metrics(dataset.cases[0], result)
    assert m["citation_validity"] == 0 and m["file_coverage"] == 0
    result["findings"] = []
    assert ev.metrics(dataset.cases[0], result)["citation_validity"] is None


def test_evaluation_cli_offline_and_invalid_dataset(tmp_path):
    import os
    import subprocess
    import sys
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CODETRACE_", "LANGCHAIN_", "LANGSMITH_"))}
    command = [sys.executable, "-m", "codetrace.evaluation", "--output", str(tmp_path)]
    result = subprocess.run(command, env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(command + ["--dataset", str(tmp_path / "missing")], env=env, capture_output=True, timeout=30)
    assert result.returncode == 2
