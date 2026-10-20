"""Model adapters. Offline mode does not create a client or need credentials."""

import json
import os
from typing import Protocol


class Model(Protocol):
    async def respond(self, messages: list[dict], tools: list[dict], *, allow_tools: bool = True) -> dict: ...


class OpenAICompatibleModel:
    def __init__(self):
        from openai import AsyncOpenAI

        key = os.getenv("CODETRACE_API_KEY", "")
        self.model = os.getenv("CODETRACE_MODEL", "")
        url = os.getenv("CODETRACE_BASE_URL", "")
        if not all((key, self.model, url)):
            raise ValueError("Set CODETRACE_API_KEY, CODETRACE_MODEL and CODETRACE_BASE_URL in .env")
        self.client = AsyncOpenAI(api_key=key, base_url=url, timeout=45, max_retries=1)

    async def respond(self, messages, tools, *, allow_tools=True):
        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools, tool_choice="auto" if allow_tools else "none", max_tokens=2048,
        )
        if not response.choices:
            raise ValueError("Model returned no choices")
        message = response.choices[0].message
        if message.role != "assistant" or (message.content is not None and not isinstance(message.content, str)):
            raise ValueError("Invalid assistant response")
        if not allow_tools and message.tool_calls:
            raise ValueError("Repair must not request tools")
        return {"message": {"role": "assistant", "content": message.content or "",
                            **({"tool_calls": [c.model_dump() for c in message.tool_calls]} if message.tool_calls else {})},
                "usage": response.usage.model_dump() if response.usage else {}}

    async def close(self):
        await self.client.close()


def final_response(evidence, *, insufficient=False, explanation="已检查可访问范围，证据仍不足。"):
    findings = [{"text": "离线演示读取了该源码片段（不是模型语义推理）。", "citations": [
        {k: e[k] for k in ("evidence_id", "path", "start", "end")}
    ]} for e in evidence if e.get("evidence_id")]
    return {"message": {"role": "assistant", "content": json.dumps({
        "findings": findings, "uncertainties": [explanation] if insufficient else [],
        "evidence_status": "insufficient" if insufficient else "sufficient",
    }, ensure_ascii=False)}}


class DemoModel:
    """Deterministic exercise; scenarios do not interpret arbitrary questions."""
    def __init__(self, scenario="entry", *, steps=None, insufficient=False):
        self.scenario = scenario
        self.steps = steps
        self.insufficient = insufficient

    async def respond(self, messages, tools, *, allow_tools=True):
        observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        evidence = [o["data"] for o in observations if o["ok"] and o.get("data", {}).get("evidence_id")]
        count = len(observations)
        if not allow_tools:
            return final_response([], insufficient=True, explanation="模拟模型不能进行真实回答修正。")
        if count and not observations[-1]["ok"]:
            return final_response(evidence, insufficient=True, explanation="离线场景工具失败，无法确认预设结论。")
        if self.steps is not None:
            if count >= len(self.steps):
                return final_response(evidence, insufficient=self.insufficient or not evidence)
            name, args = self.steps[count]
        elif count == 0:
            name, args = "repository_overview", {}
        elif count == 1:
            name, args = "search_code", {"query": "TIMEOUT_SECONDS" if self.scenario == "config" else ("missing_feature_123" if self.scenario == "no-answer" else "def main(")}
        elif count == 2:
            hits = observations[-1]["data"]["matches"]
            if not hits:
                return final_response(evidence, insufficient=True, explanation="预设搜索未命中；不能据此证明功能不存在。")
            hit = hits[0]
            name, args = "read_file", {"path": hit["path"], "start": hit["line"], "end": hit["line"]+8}
        elif self.scenario == "cross-file" and count == 3:
            name, args = "read_file", {"path": "service.py"}
        else:
            return final_response(evidence, insufficient=not evidence)
        return {"message": {"role": "assistant", "content": "", "tool_calls": [
            {"id": f"demo_{count}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
        ]}}
