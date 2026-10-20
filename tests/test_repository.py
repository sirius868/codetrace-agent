import pytest

from codetrace.repository import Repository


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app.py").write_text("def main():\n    return 42\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=hidden")
    return Repository(tmp_path)


def test_search_and_read(repo):
    hit = repo.execute("search_code", {"query": "main"})["data"]["matches"][0]
    assert hit["path"] == "app.py" and hit["line"] == 1
    data = repo.execute("read_file", {"path": "app.py", "start": 1, "end": 2})["data"]
    assert data["lines"][1]["text"] == "    return 42"
    assert len(data["sha256"]) == 64
    assert repo.execute("search_code", {"query": "missing"})["data"]["matches"] == []


@pytest.mark.parametrize("path", ["../outside.py", "/etc/passwd", "C:/Windows/a", ".env", ".git/config", "dir/../app.py", "a\\b", "app.py:stream"])
def test_blocked_paths(repo, path):
    assert not repo.execute("read_file", {"path": path})["ok"]


def test_limits_and_invalid_arguments(repo):
    (repo.root / "other.py").write_text("x\n")
    assert repo.execute("list_files", {"limit": 1})["data"]["truncated"]
    assert ".env" not in repo.execute("list_files", {})["data"]["files"]
    for args in ({"path": "app.py", "start": 0}, {"path": "app.py", "end": 500}, {"path": "app.py", "start": True}):
        assert not repo.execute("read_file", args)["ok"]
    assert not repo.execute("read_file", {"path": "missing.py"})["ok"]
    assert repo.execute("shell", {})["error"] == "unknown_tool"
    assert not repo.execute("read_file", [])["ok"]
    assert not repo.execute("read_file", {"path": "bad\0.py"})["ok"]


def test_large_binary_and_encoding(repo):
    for name, data, error in [("large.py", b"x" * 256001, "file_too_large"), ("bin.py", b"a\0b", "binary_file"), ("encoding.py", b"\xff", "unsupported_encoding")]:
        (repo.root / name).write_bytes(data)
        assert repo.execute("read_file", {"path": name})["error"] == error


def test_symlink_escape(repo, tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}_outside.py"
    outside.write_text("secret")
    try:
        (repo.root / "link.py").symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks needs Windows developer mode or privileges")
    assert repo.execute("read_file", {"path": "link.py"})["error"] == "linked_path"


def test_entry_budget(tmp_path):
    for n in range(5):
        (tmp_path / f"{n}.bin").write_bytes(b"x")
    result = Repository(tmp_path, max_entries=2).list_files()
    assert result["truncated"] and result["files"] == []
