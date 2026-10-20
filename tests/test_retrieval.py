import pytest

from codetrace.repository import Repository
from codetrace.retrieval import chunks, tokenize
from codetrace.tool_registry import ToolRegistry


def test_tokenization_and_chunk_limits():
    terms = tokenize("getUserName read_file HTTPServer 中文检索 单")
    assert {"getusername", "get", "user", "name", "read_file", "read", "file", "http", "server", "中文", "文检", "检索", "单"} <= set(terms)
    assert tokenize("!?;") == []
    pieces, skipped = chunks("a.py", "\n".join(str(i) for i in range(141)))
    assert [(p["start"], p["end"]) for p in pieces] == [(1, 80), (61, 140), (121, 141)]
    pieces, skipped = chunks("a.py", "x" * 8001 + "\n" + "a\n" * 85)
    assert skipped == [1] and all(len(p["text"]) <= 8000 and p["end"]-p["start"] < 80 for p in pieces)
    assert len({(p["path"], p["start"], p["end"]) for p in pieces}) == len(pieces)


def test_ranking_scopes_ties_stale_and_snippets(tmp_path):
    (tmp_path / "a.py").write_text("def fetchUser():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("# fetchUser\n", encoding="utf-8")
    (tmp_path / "c.xml").write_text("<fetchUser/>\n", encoding="utf-8")
    registry = ToolRegistry(Repository(tmp_path), "indexed")
    data = registry.execute("search_code_ranked", {"query": "fetchUser"})["data"]
    assert data["matches"][0]["path"] == "a.py"
    assert data["matches"][0]["contributions"]["symbol"] == 3
    xml = registry.execute("search_code_ranked", {"query": "fetchUser", "suffixes": [".xml"]})["data"]["matches"]
    assert len(xml) == 1 and xml[0]["path"] == "c.xml"
    assert not registry.execute("search_code_ranked", {"query": "不存在的中文概念"})["data"]["matches"]
    assert registry.execute("search_code_ranked", {"query": "fetchUser", "path": "b.py"})["data"]["matches"][0]["path"] == "b.py"
    (tmp_path / "a.py").write_text("# changed", encoding="utf-8")
    assert registry.execute("search_code_ranked", {"query": "fetchUser"})["error"] == "index_stale"
    assert all(m["path"] != "a.py" for m in registry.execute("search_code_ranked", {"query": "fetchUser"})["data"]["matches"])
    for args in [{"query": "x", "top_k": 21}, {"query": ""}, {"query": "x", "suffixes": [".key"]}]:
        assert not registry.execute("search_code_ranked", args)["ok"]


def test_stable_order_and_total_snippet_budget(tmp_path):
    for i in range(22):
        (tmp_path / f"{i:02}.txt").write_text("match " * 100, encoding="utf-8")
    registry = ToolRegistry(Repository(tmp_path), "indexed")
    data = registry.execute("search_code_ranked", {"query": "match", "top_k": 20})["data"]
    assert data["truncated"] and len(data["matches"]) == 20
    assert [m["path"] for m in data["matches"]] == [f"{i:02}.txt" for i in range(20)]
    assert sum(len(m["snippet"]) for m in data["matches"]) == 4000
    assert all(m["snippet_truncated"] for m in data["matches"])


def test_component_recall_at_five_same_corpus(tmp_path):
    # Original fixture; both methods see exactly these files. No live-agent claims.
    files = {"app.py": "def main():\n    greet()", "service.py": "def greet(): pass",
             "test_service.py": "# test greet", "settings.properties": "TIMEOUT_SECONDS=30",
             "README.md": "A tiny example"}
    for path, text in files.items():
        (tmp_path / path).write_text(text, encoding="utf-8")
    repo, recalls = Repository(tmp_path), {"literal": [], "indexed": []}
    registry = ToolRegistry(repo, "indexed")
    for query, gold in [("greet", {"service.py"}), ("TIMEOUT_SECONDS", {"settings.properties"}), ("中文不存在", set())]:
        literal = repo.search_code(query)["matches"]
        ranked = registry.execute("search_code_ranked", {"query": query})["data"]["matches"]
        for name, rows in [("literal", literal), ("indexed", ranked)]:
            found = list(dict.fromkeys(r["path"] for r in rows))[:5]
            if gold:
                recalls[name].append(len(set(found) & gold)/len(gold))
            else:
                assert not found  # Negative query is not assigned fictitious recall=1.
    assert recalls == {"literal": [1.0, 1.0], "indexed": [1.0, 1.0]}
