import json
import os
from pathlib import Path
import subprocess
import sys
import socket

import pytest

from codetrace.records import write_json
from codetrace.graph import analyse
from codetrace.models import DemoModel
from codetrace.repository import Repository

ROOT = Path(__file__).parents[1]
REPO = ROOT / "examples/demo_repo"


@pytest.mark.parametrize("scenario", ["entry", "cross-file", "config", "no-answer"])
async def test_offline_without_network(monkeypatch, scenario):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline mode attempted network access")
    with monkeypatch.context() as scoped:
        scoped.setattr(socket.socket, "connect", forbidden)
        scoped.setattr(socket.socket, "connect_ex", forbidden)
        scoped.setattr(socket, "getaddrinfo", forbidden)
        result = await analyse(DemoModel(scenario), Repository(REPO), "offline check", mode="offline")
    assert result["stop_reason"] in {"completed", "insufficient_evidence"}


def cli(*args, cwd=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CODETRACE_", "LANGSMITH_", "LANGCHAIN_"))}
    env["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, "-m", "codetrace", "--repo", str(REPO), *args],
                          cwd=cwd or ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)


@pytest.mark.parametrize("scenario", ["entry", "cross-file", "config", "no-answer"])
def test_cli_scenarios_and_records(tmp_path, scenario):
    result = cli("--offline", "--scenario", scenario, "--trace-dir", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "固定模拟" in result.stdout
    record = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert record["schema_version"] == 1 and record["mode"] == "offline"
    assert record["usage"] is None
    assert record["stop_reason"] == ("insufficient_evidence" if scenario == "no-answer" else "completed")
    if scenario == "cross-file":
        assert {e["path"] for e in record["evidence"]} == {"app.py", "service.py"}
    assert all("arguments" in e for e in record["trace"] if e["node"] == "tools")


def test_cli_errors_and_budget(tmp_path):
    assert cli("--offline", "--max-rounds", "0").returncode == 2
    assert cli("--offline", "--max-rounds", "1").returncode == 1
    assert cli(cwd=tmp_path).returncode == 2
    occupied = tmp_path / "occupied"
    occupied.write_text("file")
    failed = cli("--offline", "--trace-dir", str(occupied))
    assert failed.returncode == 2 and "未保存" in failed.stdout
    assert "执行记录：" not in failed.stdout


def test_target_env_is_not_loaded(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    (repo / ".env").write_text("CODETRACE_API_KEY=test\nCODETRACE_MODEL=test\nCODETRACE_BASE_URL=http://127.0.0.1:1\n")
    result = cli("--repo", str(repo), cwd=tmp_path)
    assert result.returncode == 2
    assert "Set CODETRACE_API_KEY" in result.stderr


def test_atomic_record_failure(tmp_path, monkeypatch):
    target = tmp_path / "record.json"
    target.write_text('{"old":true}')
    monkeypatch.setattr(os, "replace", lambda *a: (_ for _ in ()).throw(PermissionError()))
    with pytest.raises(PermissionError):
        write_json(target, {"new": True})
    assert json.loads(target.read_text()) == {"old": True}
    assert not list(tmp_path.glob("*.tmp"))
