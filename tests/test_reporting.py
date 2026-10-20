import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from codetrace.graph import analyse
from codetrace.models import DemoModel
from codetrace.records import write_text
from codetrace.reporting import outside_repository, render_report
from codetrace.repository import Repository
from test_cli import cli, REPO


@pytest.mark.parametrize("scenario,budget,status", [("entry", 8, "completed"), ("no-answer", 8, "insufficient_evidence"), ("entry", 1, "max_rounds")])
async def test_pure_report_status_citations_and_unknown_usage(scenario, budget, status):
    result = await analyse(DemoModel(scenario), Repository(REPO), "question <script>", max_rounds=budget)
    before = json.dumps(result)
    text = render_report(result)
    assert status in text and "usage: 未知" in text and "&lt;script&gt;" in text
    for finding in result["findings"]:
        for c in finding["citations"]:
            assert f"{c['path']}:L{c['start']}-L{c['end']}" in text
    assert json.dumps(result) == before


def test_output_inside_target_rejected_before_analysis(tmp_path):
    before = Repository(REPO).fingerprint()
    for option in ("--report", "--trace-dir"):
        result = cli("--offline", option, str(REPO / "forbidden"))
        assert result.returncode == 2 and "outside" in result.stderr
        assert "停止原因" not in result.stdout
    assert Repository(REPO).fingerprint() == before


def test_atomic_report_failure_preserves_old_file(tmp_path, monkeypatch):
    file = tmp_path / "report.md"
    file.write_text("old report", encoding="utf-8")
    monkeypatch.setattr(os, "replace", lambda *a: (_ for _ in ()).throw(PermissionError()))
    with pytest.raises(PermissionError):
        write_text(file, "new report")
    assert file.read_text() == "old report" and not list(tmp_path.glob("*.tmp"))


def test_reparse_parent_output_rejected(tmp_path, monkeypatch):
    parent = tmp_path / "alias"
    parent.mkdir()
    original = Path.lstat
    info = original(parent)
    monkeypatch.setattr(Path, "lstat", lambda self, *a, **kw: SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400) if self == parent else original(self, *a, **kw))
    with pytest.raises(ValueError, match="reparse"):
        outside_repository(parent / "report.md", REPO)


@pytest.mark.parametrize("scenario", ["navigation", "ranking"])
def test_documented_indexed_export(tmp_path, scenario):
    before = Repository(REPO).fingerprint()
    report = tmp_path / "analysis.md"
    result = cli("--offline", "--retrieval", "indexed", "--scenario", scenario,
                 "--trace-dir", str(tmp_path / "records"), "--report", str(report))
    assert result.returncode == 0, result.stderr
    record = json.loads(next((tmp_path / "records").glob("*.json")).read_text(encoding="utf-8"))
    assert report.read_text(encoding="utf-8") == render_report(record)
    assert "检索模式: indexed" in report.read_text(encoding="utf-8")
    assert record["model_attempts"] == 3
    assert Repository(REPO).fingerprint() == before
