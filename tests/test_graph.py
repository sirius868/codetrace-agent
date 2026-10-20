import asyncio
import json
import pytest

from codetrace.graph import analyse, check_citations
from codetrace.models import DemoModel
from codetrace.repository import Repository


def call(name="list_files", arguments="{}", ident="call_1"):
    return {"id": ident, "type": "function", "function": {"name": name, "arguments": arguments}}


class FixedModel:
    def __init__(self, responses):
        self.responses = iter(responses)

    async def respond(self, messages, tools):
        return {"message": {"role": "assistant", **next(self.responses)}}


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app.py").write_text("def main():\n    return 1\n")
    return Repository(tmp_path)


async def test_real_graph_offline_roundtrip(repo):
    result = await analyse(DemoModel(), repo, "入口？")
    assert result["stop_reason"] == "completed"
    assert result["rounds"] == 4 and result["tool_count"] == 3
    assert result["citation_errors"] == []
    assert "[[app.py:L1-L2]]" in result["answer"]
    assert [t["tool"] for t in result["trace"] if t["node"] == "tools"] == ["list_files", "search_code", "read_file"]


async def test_round_budget_and_tool_budget(repo):
    model = FixedModel([{"tool_calls": [call()]}] * 3)
    result = await analyse(model, repo, "q", max_rounds=2)
    assert result["stop_reason"] == "max_rounds" and result["tool_count"] == 2
    model = FixedModel([{"tool_calls": [call(ident="a"), call(ident="b")]}])
    result = await analyse(model, repo, "q", max_tools=1)
    assert result["stop_reason"] == "max_tools" and result["tool_count"] == 0


@pytest.mark.parametrize("tool,error", [(call(arguments="{"), "invalid_json"), (call(arguments="[]"), "invalid_arguments"), (call("shell"), "unknown_tool")])
async def test_tool_errors_return_to_model(repo, tool, error):
    model = FixedModel([{"tool_calls": [tool]}, {"content": "无法继续，工具失败。"}])
    result = await analyse(model, repo, "q")
    assert result["stop_reason"] == "completed"
    observation = next(m for m in result["messages"] if m["role"] == "tool")
    assert json.loads(observation["content"])["error"] == error


async def test_invalid_citation_is_not_success(repo):
    model = FixedModel([{"content": "答案 [[app.py:L1-L2]]"}])
    result = await analyse(model, repo, "q")
    assert result["stop_reason"] == "invalid_citations"
    assert result["citation_errors"] == ["app.py:L1-L2"]


async def test_model_failure_and_timeout(repo):
    class Broken:
        async def respond(self, messages, tools):
            raise RuntimeError("secret must not appear in trace")
    result = await analyse(Broken(), repo, "q")
    assert result["stop_reason"] == "model_error"
    assert "secret" not in json.dumps(result)
    class Slow:
        async def respond(self, messages, tools):
            await asyncio.sleep(1)
    result = await analyse(Slow(), repo, "q", model_timeout=0.01)
    assert result["stop_reason"] == "model_error"


async def test_tasks_do_not_share_state(repo):
    results = await asyncio.gather(*(analyse(DemoModel(), repo, f"q{i}") for i in range(2)))
    assert all(r["tool_count"] == 3 for r in results)
    assert results[0]["messages"][1]["content"] == "q0"
    assert results[1]["messages"][1]["content"] == "q1"


def test_citation_ranges():
    evidence = [{"path": "a.py", "start": 2, "end": 5}]
    assert check_citations("[[a.py:L2-L4]]", evidence) == []
    assert check_citations("[[a.py:L1-L4]] [[bad]]", evidence) == ["a.py:L1-L4", "bad"]


@pytest.mark.parametrize("response,reason", [({"content": ""}, "empty_response"), ({"tool_calls": [call(ident="a"), call(ident="a")]}, "model_error")])
async def test_bad_model_responses(repo, response, reason):
    result = await analyse(FixedModel([response]), repo, "q")
    assert result["stop_reason"] == reason


async def test_multiple_tool_responses_precede_next_model_turn(repo):
    class BatchModel:
        async def respond(self, messages, tools):
            if messages[-1]["role"] == "user":
                return {"message": {"role": "assistant", "tool_calls": [call(ident="a"), call(ident="b")]}}
            assert [m["tool_call_id"] for m in messages[-2:]] == ["a", "b"]
            return {"message": {"role": "assistant", "content": "已列出文件，尚未读取内容。"}}
    assert (await analyse(BatchModel(), repo, "q"))["stop_reason"] == "completed"
