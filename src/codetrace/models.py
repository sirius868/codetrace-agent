"""Model adapters. Offline mode does not create a client or need credentials."""

import json
import os
from typing import Protocol


class Model(Protocol):
    async def respond(self, messages: list[dict], tools: list[dict]) -> dict: ...


class OpenAICompatibleModel:
    def __init__(self):
        from openai import AsyncOpenAI

        key = os.getenv("CODETRACE_API_KEY", "")
        self.model = os.getenv("CODETRACE_MODEL", "")
        url = os.getenv("CODETRACE_BASE_URL", "")
        if not all((key, self.model, url)):
            raise ValueError("Set CODETRACE_API_KEY, CODETRACE_MODEL and CODETRACE_BASE_URL in .env")
        self.client = AsyncOpenAI(api_key=key, base_url=url, timeout=45, max_retries=1)

    async def respond(self, messages, tools):
        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools, tool_choice="auto", max_tokens=2048,
        )
        if not response.choices:
            raise ValueError("Model returned no choices")
        message = response.choices[0].message
        return {"message": {"role": "assistant", "content": message.content or "",
                            **({"tool_calls": [c.model_dump() for c in message.tool_calls]} if message.tool_calls else {})},
                "usage": response.usage.model_dump() if response.usage else {}}

    async def close(self):
        await self.client.close()


class DemoModel:
    """A fixed repository exercise, not a reasoning model or general question-answerer."""

    async def respond(self, messages, tools):
        observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        count = len(observations)
        if count and not observations[-1]["ok"]:
            return {"message": {"role": "assistant", "content": "离线演示工具失败，无法确认入口。"}}
        if count == 0:
            name, args = "list_files", {}
        elif count == 1:
            name, args = "search_code", {"query": "def main("}
        elif count == 2:
            hits = observations[-1]["data"]["matches"]
            if not hits:
                return {"message": {"role": "assistant", "content": "未找到 def main(；离线演示仅识别这一固定入口。"}}
            hit = hits[0]
            name, args = "read_file", {"path": hit["path"], "start": hit["line"], "end": hit["line"] + 8}
        else:
            evidence = observations[-1]["data"]
            ref = f"[[{evidence['path']}:L{evidence['start']}-L{evidence['end']}]]"
            return {"message": {"role": "assistant", "content": f"离线演示已定位 main 函数并读取源码：{ref}\n这是固定模拟响应，未使用真实模型推理。"}}
        return {"message": {"role": "assistant", "content": "",
                "tool_calls": [{"id": f"demo_{count}", "type": "function", "function": {
                    "name": name, "arguments": json.dumps(args)}}]}}
