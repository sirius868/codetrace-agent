import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from codetrace.graph import analyse
from codetrace.models import DemoModel, OpenAICompatibleModel
from codetrace.repository import Repository
from codetrace.records import write_json, write_text
from codetrace.reporting import outside_repository, render_report

QUESTIONS = {"entry": "main 函数入口在哪里？请给出源码依据。", "cross-file": "main 如何调用 greet？请读取两个文件。",
             "config": "超时配置在哪里定义与使用？", "no-answer": "仓库实现了 missing_feature_123 吗？",
             "navigation": "定位 main 定义。", "ranking": "定位 TIMEOUT_SECONDS 配置。"}


async def run(args):
    repository = Repository(args.repo)
    for output in (args.trace_dir, args.report):
        if output:
            outside_repository(output, repository.root)
    if not args.offline:
        # Explicit caller working directory, never the repository being analysed.
        load_dotenv(Path.cwd() / ".env", override=False)
    if args.scenario in {"navigation", "ranking"} and args.retrieval != "indexed":
        raise ValueError("navigation/ranking demo requires --retrieval indexed")
    steps = None
    if args.scenario == "navigation":
        steps = [("find_symbol", {"name": "main"}), ("read_file", {"path": "app.py"})]
    elif args.scenario == "ranking":
        steps = [("search_code_ranked", {"query": "TIMEOUT_SECONDS"}), ("read_file", {"path": "config.py"})]
    model = DemoModel(args.scenario, steps=steps) if args.offline else OpenAICompatibleModel()
    try:
        state = await analyse(model, repository, args.question or QUESTIONS[args.scenario], max_rounds=args.max_rounds,
                              max_tools=args.max_tools, timeout=args.timeout, max_context_chars=args.max_context_chars,
                              mode="offline" if args.offline else "live", retrieval=args.retrieval)
    finally:
        if isinstance(model, OpenAICompatibleModel):
            await model.close()
    if args.offline:
        print(f"[离线演示：固定模拟响应，场景 {args.scenario}，不理解任意问题]")
    if state["validation_errors"]:
        print("[引用校验失败：以下答案不可作为已验证结论]")
    print(state["answer"])
    print(f"\n停止原因：{state['stop_reason']}；模型轮数：{state['rounds']}；工具调用：{state['tool_count']}")
    if args.trace_dir:
        directory = Path(args.trace_dir)
        try:
            target = write_json(directory / f"{state['run_id']}.json", state)
        except OSError:
            print("执行记录未保存：请检查输出目录权限。")
            return 2
        print(f"执行记录：{target}")
    if args.report:
        try:
            target = write_text(outside_repository(args.report, repository.root), render_report(state))
        except (OSError, ValueError):
            print("分析报告未保存：请检查输出路径与权限。")
            return 2
        print(f"分析报告：{target}")
    return 0 if state["stop_reason"] in {"completed", "insufficient_evidence"} else 1


def main():
    parser = argparse.ArgumentParser(description="知码 CodeTrace — LangGraph 只读仓库分析助手")
    parser.add_argument("--repo", required=True, help="待分析仓库路径")
    parser.add_argument("--question")
    parser.add_argument("--scenario", choices=list(QUESTIONS), default="entry", help="固定离线演示场景")
    parser.add_argument("--retrieval", choices=["literal", "indexed"], default="literal")
    parser.add_argument("--offline", action="store_true", help="固定离线演示，不调用模型 API")
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--max-tools", type=int, default=16)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--max-context-chars", type=int, default=60000)
    parser.add_argument("--trace-dir", help="可选：保存包含源码片段的 JSON 执行记录")
    parser.add_argument("--report", help="可选：导出 Markdown 报告；必须位于目标仓库外")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"启动失败：{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
