from pathlib import Path
from types import SimpleNamespace

import pytest

from codetrace.repository import Repository, TOOLS


def test_overview_and_scoped_search(tmp_path):
    for name, text in {"z.py": "first\nneedle\nlast", "a.java": "needle", "README.md": "read", "pom.xml": "build"}.items():
        (tmp_path / name).write_text(text)
    repo = Repository(tmp_path)
    overview = repo.repository_overview()
    assert overview["file_count"] == 4
    assert overview["by_suffix"][".java"] == 1
    assert overview["candidate_paths"] == ["README.md", "pom.xml"]
    assert repo.list_files()["files"] == sorted(repo.list_files()["files"])
    assert [m["path"] for m in repo.search_code("needle", suffixes=[".java"])["matches"]] == ["a.java"]
    hit = repo.search_code("needle", path="z.py", context=1)["matches"][0]
    assert [line["line"] for line in hit["context"]] == [1, 2, 3]
    assert repo.search_code("needle", limit=1)["truncation_reasons"] == ["match_budget"]
    assert Repository(tmp_path, max_files=1).repository_overview()["counts_scope"] == "partial"
    assert not repo.execute("search_code", {"query": "x", "context": True})["ok"]
    assert not repo.execute("list_files", {"suffixes": "py"})["ok"]


def test_read_pages_and_hash(tmp_path):
    p = tmp_path / "a.py"
    p.write_text("x\n" * 200)
    repo = Repository(tmp_path)
    first = repo.read_file("a.py")
    assert first["next_start"] == 81
    assert repo.read_file("a.py", start=121)["end"] == 200
    assert repo.read_file("a.py", start=121)["eof"]
    assert len(repo.read_file("a.py", end=120)["lines"]) == 120
    p.write_text("x" * 7000 + "\n" + "y" * 7000)
    limited = repo.read_file("a.py")
    assert limited["truncated"] and limited["next_start"] == 2
    assert limited["sha256"] != first["sha256"]
    p.write_text("")
    assert repo.read_file("a.py")["lines"] == []
    p.write_text("x" * 12001)
    assert repo.execute("read_file", {"path": "a.py"})["error"] == "line_too_long"


@pytest.mark.parametrize("mode,attributes", [(0o120777, 0), (0o100644, 0x400)])
def test_link_attributes_rejected_without_privileges(tmp_path, monkeypatch, mode, attributes):
    p = tmp_path / "linked.py"
    p.write_text("do not return")
    repo = Repository(tmp_path)
    original = Path.lstat
    monkeypatch.setattr(Path, "lstat", lambda self, *a, **kw: SimpleNamespace(st_mode=mode, st_file_attributes=attributes) if self == p else original(self, *a, **kw))
    for name, args in [("read_file", {"path": "linked.py"}), ("search_code", {"query": "do", "path": "linked.py"}), ("repository_overview", {"path": "linked.py"}), ("list_files", {"path": "linked.py"})]:
        assert repo.execute(name, args) == {"ok": False, "error": "linked_path"}


def test_permission_and_skip_reporting(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_bytes(b"\xff")
    (tmp_path / ".env").write_text("key")
    repo = Repository(tmp_path)
    result = repo.search_code("nothing")
    assert result["matches"] == []
    assert result["skip_reasons"]["unsupported_encoding"] == 1
    import os
    monkeypatch.setattr(os, "scandir", lambda p: (_ for _ in ()).throw(PermissionError()))
    assert repo.list_files()["skip_reasons"]["file_access_error"] == 1


def test_schema_defaults():
    tools = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}
    assert tools["list_files"]["properties"]["limit"]["default"] == 100
    assert tools["search_code"]["properties"]["context"]["default"] == 0
