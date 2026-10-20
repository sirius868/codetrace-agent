"""Bounded v2 paired runs. Annotations never enter the inference adapter."""
import argparse
import asyncio
import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Literal
from uuid import uuid4
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

from codetrace.benchmark import load_benchmark, verify_checkouts, digest
from codetrace.evaluation import Strict
from codetrace.graph import analyse, SYSTEM, INDEXED_HINT
from codetrace.models import DemoModel, OpenAICompatibleModel
from codetrace.records import write_json, write_text
from codetrace.reporting import outside_repository
from codetrace.repository import Repository
from codetrace.tool_registry import ToolRegistry

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "benchmarks/repository-analysis-v2.json"
BUDGETS = {"max_rounds": 8, "max_tools": 16, "timeout": 180, "model_timeout": 90, "max_context_chars": 60000}
SUCCESS_STOPS = {"completed", "insufficient_evidence"}


def configuration(dataset_sha, roots, live, budgets):
    source = Path(__file__).parent
    code = {p.name: digest(p.read_bytes().hex()) for p in sorted(source.glob("*.py"))}
    tools = {mode: ToolRegistry(Repository(next(iter(roots.values()), source)), mode).definitions for mode in ("literal", "indexed")}
    url = urlsplit(os.getenv("CODETRACE_BASE_URL", ""))
    if live and (url.username or url.password or url.query or url.fragment):
        raise ValueError("Model base URL must not contain credentials/query/fragment")
    public_url = urlunsplit((url.scheme, url.netloc, url.path, "", ""))
    return {"dataset_sha256": dataset_sha, "code": code, "prompt_sha256": digest([SYSTEM, INDEXED_HINT]),
            "tools_sha256": digest(tools), "algorithm_version": 1,
            "parser_versions": ToolRegistry(Repository(source), "indexed").setup["parser_versions"],
            "budgets": budgets, "mode": "live" if live else "offline",
            "model": os.getenv("CODETRACE_MODEL", "") if live else "DemoModel",
            "base_url": public_url if live else None,
            "max_tokens": 2048, "sdk_max_retries": 1}


async def infer(question, root, variant, *, live, budgets, model_factory=None):
    """Intentionally accepts no case, expected paths, facts, reviews or gold query."""
    model = None
    try:
        model = model_factory() if model_factory else (OpenAICompatibleModel() if live else
                DemoModel(steps=[("repository_overview", {})], insufficient=True))
        return await analyse(model, Repository(root), question, retrieval=variant,
                             mode="live" if live else "offline", **budgets)
    finally:
        if model is not None and hasattr(model, "close"):
            await model.close()


def case_metrics(case, result):
    citations = [c for f in result["findings"] for c in f["citations"]]
    evidence = {e["evidence_id"]: e for e in result["evidence"]}
    valid = [c for c in citations if (e := evidence.get(c["evidence_id"])) and
             e["path"] == c["path"] and e["start"] <= c["start"] <= c["end"] <= e["end"]]
    file_hits = sum(any(c["path"] == option.path for option in group for c in valid) for group in case.evidence_groups)
    range_hits = sum(any(c["path"] == option.path and c["start"] <= option.start and c["end"] >= option.end
                         for option in group for c in valid) for group in case.evidence_groups)
    n = len(case.evidence_groups)
    return {"file_group_coverage": file_hits/n if n else None, "evidence_group_coverage": range_hits/n if n else None,
            "valid_citations": len(valid), "citation_count": len(citations),
            "citation_validity": len(valid)/len(citations) if citations else None,
            "model_attempts": result["model_attempts"], "tool_count": result["tool_count"],
            "elapsed_ms": result["elapsed_ms"], "usage": result["usage"], "cost": None}


class ManualReview(Strict):
    report_id: str
    dataset_sha256: str
    case_id: str
    variant: Literal["literal", "indexed"]
    run_id: str
    reviewer: str
    review_source: Literal["human", "assistant_draft"]
    semantic_correct: bool
    omitted_facts: list[str]
    reasonable_refusal: bool | None
    failure_category: Literal["none", "retrieval_miss", "explanation_error", "insufficient", "model_error", "budget_stop"]
    notes: str


def import_reviews(report, raw):
    reviews = [ManualReview.model_validate(item) for item in raw]
    pairs = {(r["case_id"], r["variant"]): r for r in report["rows"]}
    seen = set()
    for review in reviews:
        key = (review.case_id, review.variant)
        if key in seen or key not in pairs or review.report_id != report["report_id"] or review.dataset_sha256 != report["dataset_sha256"]:
            raise ValueError("Review identity mismatch")
        if not review.reviewer.strip() or not pairs[key]["attempts"] or pairs[key]["attempts"][-1].get("run_id") != review.run_id:
            raise ValueError("Review run/reviewer mismatch")
        seen.add(key)
    for review in reviews:
        pairs[(review.case_id, review.variant)]["attempts"][-1]["review"] = review.model_dump()
    report["summary"] = summarize(report)
    return report


def semantic_success(row):
    if not row["attempts"]:
        return None
    attempt = row["attempts"][-1]
    review = attempt.get("review")
    if not review or review["review_source"] != "human":
        return None
    if row["answerable"]:
        return attempt["status"] == "completed" and review["semantic_correct"] and not review["omitted_facts"]
    return attempt["status"] == "insufficient_evidence" and review["semantic_correct"] and not review["omitted_facts"] and review["reasonable_refusal"] is True


def summarize(report):
    summary = {"planned": len(report["rows"]), "ran": 0, "reviewed": 0, "cost": None, "modes": {}, "pairs": []}
    for mode in ("literal", "indexed"):
        rows = [r for r in report["rows"] if r["variant"] == mode]
        ran = [r for r in rows if r["attempts"]]
        reviews = [r for r in rows if semantic_success(r) is not None]
        held = [r for r in rows if r["split"] == "held-out"]
        successes = sum(semantic_success(r) is True for r in rows)
        all_reviewed = len(reviews) == len(rows) and len(ran) == len(rows) and bool(rows)
        times = [r["attempts"][-1]["metrics"]["elapsed_ms"] for r in ran if r["attempts"][-1].get("metrics")]
        summary["modes"][mode] = {"planned": len(rows), "ran": len(ran), "reviewed": len(reviews), "successes": successes,
            "success_rate": successes/len(rows) if all_reviewed and report["mode"] == "live" else None,
            "held_out_planned": len(held), "held_out_successes": sum(semantic_success(r) is True for r in held),
            "held_out_rate": sum(semantic_success(r) is True for r in held)/len(held) if held and all(semantic_success(r) is not None for r in held) and report["mode"] == "live" else None,
            "failures": sum(r["attempts"][-1]["status"] not in SUCCESS_STOPS for r in ran),
            "not_run": len(rows)-len(ran), "elapsed_ms_median": median(times) if times else None, "elapsed_ms_max": max(times) if times else None}
        summary["ran"] += len(ran)
        summary["reviewed"] += len(reviews)
    by_case = {}
    for row in report["rows"]:
        by_case.setdefault(row["case_id"], {})[row["variant"]] = row
    for case_id, pair in by_case.items():
        a, b = pair["literal"], pair["indexed"]
        def metric(row, name):
            return (row["attempts"][-1].get("metrics") or {}).get(name) if row["attempts"] else None
        delta = {}
        for name in ("file_group_coverage", "evidence_group_coverage", "elapsed_ms", "model_attempts", "tool_count"):
            left, right = metric(a, name), metric(b, name)
            delta[name] = right-left if left is not None and right is not None else None
        summary["pairs"].append({"case_id": case_id, "literal_success": semantic_success(a), "indexed_success": semantic_success(b), "indexed_minus_literal": delta})
    a, b = summary["modes"]["literal"], summary["modes"]["indexed"]
    summary["analysis_ready_for_programming"] = bool(report["mode"] == "live" and summary["reviewed"] == summary["planned"]
        and summary["ran"] == summary["planned"] and b["success_rate"] is not None and b["success_rate"] >= .75
        and b["held_out_rate"] is not None and b["held_out_rate"] >= .75 and b["successes"] >= a["successes"]
        and report.get("boundary_regression_check") == "passed")
    return summary


def save(report, target):
    report["summary"] = summarize(report)
    write_json(target, report)
    lines = ["# CodeTrace 成对评测 v2", "", f"模式: {report['mode']}; report_id: {report['report_id']}",
             "", "离线只验证控制链路。人工未确认保持未知。两模式是整体方案比较，不是BM25因果实验。费用未知。", "",
             "| Case | Variant | Status | Attempts | Human semantic success |", "|---|---|---|---|---|"]
    for row in report["rows"]:
        status = row["attempts"][-1]["status"] if row["attempts"] else "not_run"
        lines.append(f"| {row['case_id']} | {row['variant']} | {status} | {len(row['attempts'])} | {semantic_success(row)} |")
    lines.extend(["", "```json", json.dumps(report["summary"], ensure_ascii=False, indent=2), "```", ""])
    write_text(Path(target).with_suffix(".md"), "\n".join(lines))


async def evaluate(dataset_path, mapping, output, *, live=False, max_runs=4, case_ids=None, variant="both",
                   resume=None, retry_failed=False, budgets=None, model_factory=None, freeze=None):
    if type(max_runs) is not int or max_runs < 1 or variant not in {"both", "literal", "indexed"}:
        raise ValueError("Invalid batch configuration")
    budgets = budgets or dict(BUDGETS)
    dataset, dataset_sha = load_benchmark(dataset_path)
    if case_ids and not set(case_ids) <= {c.id for c in dataset.cases}:
        raise ValueError("Unknown case ID")
    roots, statuses = verify_checkouts(dataset, mapping)
    for root in roots.values():
        outside_repository(output, root)
        outside_repository(Path(output).with_suffix('.md'), root)
    config = configuration(dataset_sha, roots, live, budgets)
    config_sha = digest(config)
    frozen = json.loads(Path(freeze).read_text(encoding="utf-8")) if freeze else None
    if frozen and (frozen.get("configuration_sha256") != config_sha or frozen.get("dataset_sha256") != dataset_sha
                   or not frozen.get("code_commit") or not frozen.get("frozen_at")
                   or frozen.get("held_out_used_for_tuning") is not False):
        raise ValueError("Freeze configuration mismatch")
    if resume:
        report = json.loads(Path(resume).read_text(encoding="utf-8"))
        if report.get("configuration_sha256") != config_sha or report.get("dataset_sha256") != dataset_sha:
            raise ValueError("Resume configuration mismatch")
        expected = {(c.id, mode) for c in dataset.cases for mode in ("literal", "indexed")}
        actual = [(r["case_id"], r["variant"]) for r in report.get("rows", [])]
        if set(actual) != expected or len(actual) != len(expected) or digest(report.get("configuration")) != config_sha:
            raise ValueError("Resume plan/configuration mismatch")
        by_id = {c.id: c for c in dataset.cases}
        repos = {r.id: r for r in dataset.repositories}
        for row in report["rows"]:
            case = by_id[row["case_id"]]
            if (row["question"], row["repo_id"], row["answerable"], row["split"]) != (case.question, case.repo_id, case.answerable, repos[case.repo_id].split):
                raise ValueError("Resume case mismatch")
        report = copy.deepcopy(report)
    else:
        repos = {r.id: r for r in dataset.repositories}
        report = {"schema_version": 2, "result_schema_version": 1, "dataset_version": dataset.dataset_version,
                  "report_id": uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": dataset_sha,
                  "mode": "live" if live else "offline", "configuration": config, "configuration_sha256": config_sha,
                  "boundary_regression_check": "not_confirmed", "rows": [
                      {"case_id": c.id, "repo_id": c.repo_id, "split": repos[c.repo_id].split, "variant": mode,
                       "answerable": c.answerable, "question": c.question, "attempts": [], "not_run_reason": None}
                      for c in dataset.cases for mode in ("literal", "indexed")]}
    report["checkout_status"] = statuses
    report["freeze"] = frozen
    cases = {c.id: c for c in dataset.cases}
    count = 0
    save(report, output)
    for row in report["rows"]:
        if case_ids and row["case_id"] not in case_ids or variant != "both" and row["variant"] != variant:
            continue
        if row["attempts"] and (not retry_failed or row["attempts"][-1]["status"] in SUCCESS_STOPS):
            continue
        reason = statuses.get(row["repo_id"])
        if reason == "verified":
            reason = None
        if live and not model_factory and not all(os.getenv(k) for k in ("CODETRACE_API_KEY", "CODETRACE_BASE_URL", "CODETRACE_MODEL")):
            reason = "missing_model_configuration"
        if live and row["split"] == "held-out" and not frozen:
            reason = "freeze_required"
        row["not_run_reason"] = reason
        if count >= max_runs and not reason:
            row["not_run_reason"] = "batch_limit"
        if reason or count >= max_runs:
            continue
        count += 1
        attempt = {"attempt_id": uuid4().hex, "review": None, "metrics": None, "run_id": uuid4().hex,
                   "started_at": datetime.now(timezone.utc).isoformat()}
        try:
            result = await infer(row["question"], roots[row["repo_id"]], row["variant"], live=live, budgets=budgets, model_factory=model_factory)
            attempt.update(status=result["stop_reason"], result=result, run_id=result["run_id"], metrics=case_metrics(cases[row["case_id"]], result))
        except Exception as exc:
            attempt.update(status="case_error", error_type=type(exc).__name__)
        row["attempts"].append(attempt)
        save(report, output)
    save(report, output)
    return report


def main():
    parser = argparse.ArgumentParser(description="v2 paired evaluation; offline by default")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--repo-map", type=Path)
    parser.add_argument("--output", type=Path, default=Path("runs/paired/report.json"))
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-runs", type=int, default=4)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--variant", choices=["literal", "indexed", "both"], default="both")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    try:
        if args.review:
            if not args.resume or args.live:
                raise ValueError("Reviews require --resume without --live")
            report = import_reviews(json.loads(args.resume.read_text(encoding="utf-8")), json.loads(args.review.read_text(encoding="utf-8")))
            # Review import performs no inference but still respects saved target roots.
            for row in report["rows"]:
                for attempt in row["attempts"]:
                    if attempt.get("result"):
                        outside_repository(args.output, attempt["result"]["repository"])
                        outside_repository(args.output.with_suffix('.md'), attempt["result"]["repository"])
            save(report, args.output)
        else:
            if args.live:
                load_dotenv(Path.cwd() / ".env", override=False)
            mapping = json.loads(args.repo_map.read_text(encoding="utf-8-sig")) if args.repo_map else {}
            report = asyncio.run(evaluate(args.dataset, mapping, args.output, live=args.live, max_runs=args.max_runs,
                case_ids=args.case_id, variant=args.variant, resume=args.resume, retry_failed=args.retry_failed, freeze=args.freeze))
        print(json.dumps({"report": str(args.output), "planned": report["summary"]["planned"], "ran": report["summary"]["ran"], "reviewed": report["summary"]["reviewed"]}))
        return 0
    except (ValueError, OSError):
        parser.exit(2, "Evaluation configuration, source identity or review validation failed. No comparable score generated.\n")


if __name__ == "__main__":
    raise SystemExit(main())
