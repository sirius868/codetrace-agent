"""Pure result rendering and explicit output boundary validation."""
import json
import stat
from pathlib import Path

from codetrace.contracts import Result


def outside_repository(target, root):
    path, root = Path(target).absolute(), Path(root).resolve(strict=True)
    if path.resolve().is_relative_to(root):
        raise ValueError("Output must be outside the analysed repository")
    for part in [path, *path.parents]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            # Avoid writing through mutable aliases even if they currently point outside.
            raise ValueError("Output path must not traverse a link/reparse point")
    return path


def _safe(text):
    # Render source/model text as text, not active HTML or Markdown instructions.
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("`", "\\`").replace("[", "\\[").replace("]", "\\]").replace("*", "\\*").replace("#", "\\#")


def render_report(data):
    result = Result.model_validate(data)
    lines = ["# CodeTrace 分析报告", "", "本报告展示程序结果和引用校验，不代表人工确认语义正确。", "",
             "## 问题", "", _safe(result.question), "", "## 状态", "",
             f"- run_id: {result.run_id}", f"- 停止原因: {result.stop_reason}",
             f"- 证据状态: {result.evidence_status}", f"- 运行模式: {result.mode}", "", "## 事实与引用", ""]
    for finding in result.findings:
        lines.append("- " + _safe(finding.text))
        for citation in finding.citations:
            lines.append(f"  - {_safe(citation.path)}:L{citation.start}-L{citation.end} ({citation.evidence_id})")
    if not result.findings:
        lines.append("没有已验证引用的事实。")
    lines.extend(["", "## 未确认事项", ""] + ["- " + _safe(u) for u in result.uncertainties])
    if not result.uncertainties:
        lines.append("本次输出未列出额外事项；这不证明分析覆盖完整。")
    lines.extend(["", "## 证据快照", ""])
    for evidence in result.evidence:
        lines.append(f"- {_safe(evidence.path)}:L{evidence.start}-L{evidence.end}; SHA-256 {evidence.sha256}; {evidence.evidence_id}")
    setup = next((t for t in result.trace if t.get("node") == "retrieval_setup"), {})
    coverage = [t["retrieval"]["diagnostics"] for t in result.trace if t.get("retrieval")]
    lines.extend(["", "## 索引覆盖", "", f"检索模式: {setup.get('mode', '未记录（旧记录）')}"])
    if coverage:
        last = coverage[-1]
        lines.extend([f"文件数: {last['file_count']}; partial: {last['partial']}; 累计构建读取字节: {last['read_bytes']}",
                      f"清单摘要: {last['manifest_sha256']}", "", _safe(json.dumps(last, ensure_ascii=False, sort_keys=True))])
    else:
        lines.append("未构建索引或没有成功的索引工具记录；不能据此声称全仓库覆盖。")
    lines.extend(["", "## 执行统计", "", f"- 模型: {_safe(result.model)}", f"- 模型请求: {result.model_attempts}",
                  f"- 工具执行: {result.tool_count}", f"- 修正次数: {result.repair_count}", f"- 总耗时毫秒: {result.elapsed_ms}",
                  "- usage: " + (_safe(json.dumps(result.usage, ensure_ascii=False)) if result.usage is not None else "未知"),
                  "- 费用: 未知（未配置可核实的供应商价格）", ""])
    return "\n".join(lines)
