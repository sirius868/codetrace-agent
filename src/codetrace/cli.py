import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from codetrace.graph import analyse
from codetrace.models import DemoModel, OpenAICompatibleModel
from codetrace.repository import Repository


async def run(args):
    repository = Repository(args.repo)
    if not args.offline:
        # Explicit caller working directory, never the repository being analysed.
        load_dotenv(Path.cwd() / ".env", override=False)
    model = DemoModel() if args.offline else OpenAICompatibleModel()
    try:
        state = await analyse(model, repository, args.question, max_rounds=args.max_rounds, max_tools=args.max_tools)
    finally:
        if isinstance(model, OpenAICompatibleModel):
            await model.close()
    if args.offline:
        print("[离线演示：固定模型响应，仅演示 main 函数定位]")
    if state["citation_errors"]:
        print("[引用校验失败：以下答案不可作为已验证结论]")
    print(state["answer"])
    print(f"\n停止原因：{state['stop_reason']}；模型轮数：{state['rounds']}；工具调用：{state['tool_count']}")
    if args.trace_dir:
        directory = Path(args.trace_dir)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{uuid4().hex}.json"
        target.write_text(json.dumps({"repository": str(repository.root), **state}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"执行记录：{target.resolve()}")
    return 0 if state["stop_reason"] == "completed" else 1


def main():
    parser = argparse.ArgumentParser(description="知码 CodeTrace — LangGraph 只读仓库分析助手")
    parser.add_argument("--repo", required=True, help="待分析仓库路径")
    parser.add_argument("--question", default="main 函数入口在哪里？请给出源码依据。")
    parser.add_argument("--offline", action="store_true", help="固定离线演示，不调用模型 API")
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--max-tools", type=int, default=16)
    parser.add_argument("--trace-dir", help="可选：保存包含源码片段的 JSON 执行记录")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"启动失败：{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
