import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from codetrace.indexing import SourceIndex
from codetrace.repository import Repository, RepositoryError


def put(root, path, data=b"pass\n"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def test_stable_manifest_and_task_isolation(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    put(left, "service.py")
    put(right, "service.py", b"x = 2\n")
    with ThreadPoolExecutor() as pool:
        a, b = list(pool.map(lambda p: SourceIndex(Repository(p)).ensure(), [left, right]))
    again = SourceIndex(Repository(left)).ensure()
    assert a.digest == again.digest != b.digest
    assert a.index_id != again.index_id != b.index_id
    assert a.manifest == again.manifest
    assert a.diagnostics()["parse_states"] == {"parsed": 1}
    assert a.read_bytes == 5 and a.build_ms >= 0


@pytest.mark.parametrize("limit,expected", [(5, 0), (6, 1), (10, 1), (11, 2)])
def test_total_budget_never_indexes_incomplete_file(tmp_path, limit, expected):
    put(tmp_path, "a.py")
    put(tmp_path, "b.py")
    idx = SourceIndex(Repository(tmp_path), max_total_bytes=limit).ensure()
    assert len(idx.files) == expected
    assert idx.read_bytes <= limit
    assert idx.diagnostics()["partial"] == (expected < 2)


def test_file_size_decode_and_exclusions(tmp_path):
    put(tmp_path, "a.py", b"x" * 11)
    put(tmp_path, "b.py", b"\xff\xff")
    put(tmp_path, "c.py", b"\0")
    put(tmp_path, "d.py", b"pass #1234")  # Exactly ten bytes.
    put(tmp_path, "bad.py", b"def :")
    for path in [".env", "credentials.json", "secret.pem", "target/a.py", ".venv-verify/a.py"]:
        put(tmp_path, path)
    idx = SourceIndex(Repository(tmp_path, max_bytes=10)).ensure()
    assert set(idx.files) == {"d.py", "bad.py"}
    assert idx.files["bad.py"]["parse_status"] == "parse_error"
    assert idx.read_bytes == 29
    assert idx.skipped == {"file_too_large": 1, "unsupported_encoding": 1, "binary_file": 1}


@pytest.mark.parametrize("kwargs,reason,expected", [({"max_files": 2}, "file_budget", 2), ({"max_entries": 2}, "entry_budget", 2)])
def test_scan_limits(tmp_path, kwargs, reason, expected):
    for n in range(4):
        put(tmp_path, f"{n}.py")
    idx = SourceIndex(Repository(tmp_path, **kwargs)).ensure()
    assert len(idx.files) == expected
    assert reason in idx.diagnostics()["truncation_reasons"]
    assert idx.diagnostics()["partial"]


def test_default_limits():
    # Exact defaults are part of the public resource contract.
    from pathlib import Path
    idx = SourceIndex(Repository(Path.cwd()))
    assert idx.config == {"max_files": 2000, "max_entries": 10000, "max_file_bytes": 256000, "max_total_bytes": 16777216}


def test_changed_same_mtime_deleted_and_new_file(tmp_path):
    path = put(tmp_path, "a.py")
    repo = Repository(tmp_path)
    idx = SourceIndex(repo).ensure()
    old_read = repo.read_file("a.py")
    stamp = path.stat().st_mtime_ns
    path.write_bytes(b"x = 1\npass\n")
    os.utime(path, ns=(stamp, stamp))
    with pytest.raises(RepositoryError, match="index_stale"):
        idx.verify(["a.py", "a.py"])
    idx.ensure()
    assert idx.files["a.py"]["sha256"] != old_read["sha256"]
    assert old_read["lines"] == [{"line": 1, "text": "pass"}]
    put(tmp_path, "new.py")
    assert "new.py" not in idx.ensure().files
    path.unlink()
    with pytest.raises(RepositoryError, match="index_stale"):
        idx.verify(["a.py"])
    assert "a.py" not in idx.ensure().files
    assert "new.py" in SourceIndex(repo).ensure().files


def test_permission_and_relinked_candidate(tmp_path, monkeypatch):
    put(tmp_path, "a.py")
    repo = Repository(tmp_path)
    idx = SourceIndex(repo).ensure()
    def denied(*_):
        raise PermissionError("private system detail")
    monkeypatch.setattr(repo, "_raw", denied)
    with pytest.raises(RepositoryError, match="index_stale"):
        idx.verify(["a.py"])
    assert not idx.ensure().files
    assert idx.skipped["file_access_error"] == 1
    # _raw delegates link/reparse rejection to the existing shared path guard.
    def linked(*_):
        raise RepositoryError("linked_path")
    monkeypatch.setattr(repo, "_path", linked)
    monkeypatch.undo()
    original = repo._path
    monkeypatch.setattr(repo, "_path", linked)
    with pytest.raises(RepositoryError, match="linked_path"):
        repo._raw("a.py", 10)
    monkeypatch.setattr(repo, "_path", original)


def test_deadline_and_cancel_stop_scheduling(tmp_path, monkeypatch):
    put(tmp_path, "a.py")
    put(tmp_path, "b.py")
    now, calls = [0], []
    repo = Repository(tmp_path)
    original = repo._raw
    def slow(path, limit):
        calls.append(path)
        now[0] = 2
        return original(path, limit)
    monkeypatch.setattr(repo, "_raw", slow)
    idx = SourceIndex(repo, deadline=1, clock=lambda: now[0])
    with pytest.raises(RepositoryError, match="task_timeout"):
        idx.ensure()
    assert calls == ["a.py"] and idx.read_bytes == 5
    with pytest.raises(RepositoryError, match="task_timeout"):
        idx.ensure()
    assert calls == ["a.py"]


@pytest.mark.parametrize("path", ["../secret.py", "C:/secret.py", ".env", "a\\b"])
def test_index_shared_read_rejects_unsafe_paths(tmp_path, path):
    with pytest.raises(RepositoryError):
        SourceIndex(Repository(tmp_path))._read(path)
