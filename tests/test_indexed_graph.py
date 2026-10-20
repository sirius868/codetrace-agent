import asyncio
import json
import time

import pytest

from codetrace.graph import analyse
from codetrace.models import DemoModel, final_response
from codetrace.repository import Repository, TOOLS
from codetrace.tool_registry import ToolRegistry


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app.py").write_text("def main():\n    pass\n", encoding="utf-8")
    return Repository(tmp_path)


async def test_indexed_roundtrip_and_same_repo_concurrent_isolation(repo):
    steps = [("find_symbol", {"name": "main"}), ("search_code_ranked", {"query": "main"}), ("read_file", {"path": "app.py"})]
    a, b = await asyncio.gather(*(analyse(DemoModel(steps=steps), repo, "question", retrieval="indexed") for _ in range(2)))
    for result in (a, b):
        assert result["schema_version"] == 1 and result["stop_reason"] == "completed"
        assert result["tool_count"] == 3 and result["model_attempts"] == 4 and result["usage"] is None
        assert result["trace"][0]["mode"] == "indexed"
        events = [t for t in result["trace"] if t.get("retrieval")]
        assert len(events) == 2
        assert events[0]["retrieval"]["diagnostics"]["read_bytes"] == events[1]["retrieval"]["diagnostics"]["read_bytes"]
    def ident(result):
        return next(t["retrieval"]["diagnostics"]["index_id"] for t in result["trace"] if t.get("retrieval"))
    assert ident(a) != ident(b)


def test_registry_whitelist_and_immutable_definitions(repo):
    registry = ToolRegistry(repo)
    assert registry.definitions == TOOLS
    definitions = registry.definitions
    definitions.clear()
    assert registry.definitions == TOOLS
    assert registry.execute("find_symbol", {"name": "main"})["error"] == "unknown_tool"


async def test_same_tools_for_repair_and_context(repo):
    class Capture:
        def __init__(self):
            self.calls = []
        async def respond(self, messages, tools, *, allow_tools=True):
            self.calls.append((json.loads(json.dumps(tools)), allow_tools, len(json.dumps({"messages": messages, "tools": tools}, ensure_ascii=False))))
            tools.clear()
            if allow_tools:
                return {"message": {"role": "assistant", "content": "invalid"}}
            return final_response([], insufficient=True)
    model = Capture()
    result = await analyse(model, repo, "q", retrieval="indexed")
    assert model.calls[0][0] == model.calls[1][0] and len(model.calls[0][0]) == 7
    assert [c[1] for c in model.calls] == [True, False]
    assert [t["context_chars"] for t in result["trace"] if "context_chars" in t] == [c[2] for c in model.calls]


async def test_repeat_diagnostics_dont_bypass_guard(repo):
    step = ("find_symbol", {"name": "main"})
    result = await analyse(DemoModel(steps=[step] * 3), repo, "q", retrieval="indexed")
    assert result["stop_reason"] == "repeated_calls" and result["tool_count"] == 2
    observations = [json.loads(m["content"]) for m in result["messages"] if m["role"] == "tool"]
    assert "warning" in observations[1] and observations[2]["error"] == "skipped"


async def test_changed_version_allows_next_call(repo):
    class Changing(DemoModel):
        async def respond(self, messages, tools, **kwargs):
            count = sum(m["role"] == "tool" for m in messages)
            if count == 2:
                (repo.root / "app.py").write_text("\ndef main(): pass\n", encoding="utf-8")
            if count == 3:
                # Explicitly retry after index_stale instead of DemoModel's early refusal.
                return await DemoModel(steps=[("find_symbol", {"name": "main"})]).respond(messages[:2], tools, **kwargs)
            return await super().respond(messages, tools, **kwargs)
    result = await analyse(Changing(steps=[("find_symbol", {"name": "main"})]*4), repo, "q", retrieval="indexed")
    observations = [json.loads(m["content"]) for m in result["messages"] if m["role"] == "tool"]
    assert observations[2]["error"] == "index_stale" and observations[3]["data"]["matches"][0]["start"] == 2


async def test_missing_dependency_before_model(repo, monkeypatch):
    from codetrace import parsing
    monkeypatch.setattr(parsing, "import_module", lambda _: (_ for _ in ()).throw(ImportError()))
    with pytest.raises(ValueError, match="indexed"):
        await analyse(DemoModel(), repo, "q", retrieval="indexed")
    assert (await analyse(DemoModel(), repo, "q"))["stop_reason"] == "completed"


async def test_index_deadline_no_further_reads_or_model_calls(repo, monkeypatch):
    original, reads = repo._raw, []
    def slow(path, limit):
        reads.append(path)
        time.sleep(.1)
        return original(path, limit)
    monkeypatch.setattr(repo, "_raw", slow)
    result = await analyse(DemoModel(steps=[("find_symbol", {"name": "main"})]), repo, "q", retrieval="indexed", timeout=.04)
    assert result["stop_reason"] == "task_timeout" and result["model_attempts"] == 1
    await asyncio.sleep(.15)
    assert len(reads) == 1


async def test_indexed_budgets_and_batch_pairing(repo):
    class Batch:
        async def respond(self, *args, **kwargs):
            return {"message": {"role": "assistant", "content": "", "tool_calls": [
                {"id": str(i), "type": "function", "function": {"name": "find_symbol", "arguments": '{"name":"main"}'}} for i in range(2)]}}
    result = await analyse(Batch(), repo, "q", retrieval="indexed", max_tools=1)
    assert result["stop_reason"] == "max_tools" and result["tool_count"] == 0
    assert [m["tool_call_id"] for m in result["messages"] if m["role"] == "tool"] == ["0", "1"]
    result = await analyse(DemoModel(), repo, "q", retrieval="indexed", max_context_chars=1)
    assert result["stop_reason"] == "context_budget" and result["model_attempts"] == 0
