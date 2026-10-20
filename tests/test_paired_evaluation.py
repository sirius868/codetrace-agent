import copy
import json
from pathlib import Path

import pytest

from codetrace.benchmark import load_benchmark
from codetrace.models import DemoModel, final_response
from codetrace.paired_evaluation import evaluate, import_reviews, summarize, case_metrics, configuration
from test_benchmark import corpus


async def test_batch_resume_missing_offline_and_no_gold(corpus,tmp_path,monkeypatch):
    path,mapping,_=corpus
    def forbidden(): raise AssertionError("network client constructed")
    monkeypatch.setattr("codetrace.paired_evaluation.OpenAICompatibleModel",forbidden)
    output=tmp_path/"out/report.json"
    report=await evaluate(path,mapping,output)
    assert report["summary"]["planned"]==48 and report["summary"]["ran"]==4
    assert report["summary"]["modes"]["indexed"]["success_rate"] is None
    assert not report["summary"]["analysis_ready_for_programming"]
    first=[r["attempts"] for r in report["rows"][:4]]
    continued=await evaluate(path,mapping,output,resume=output)
    assert continued["summary"]["ran"]==8 and [r["attempts"] for r in continued["rows"][:4]]==first
    for row in continued["rows"]:
        for attempt in row["attempts"]:
            assert "SENTINEL" not in json.dumps(attempt["result"]["messages"])
    missing=await evaluate(path,{},tmp_path/"missing.json")
    assert missing["summary"]["planned"]==48 and missing["summary"]["ran"]==0


async def test_live_inference_sentinel_and_freeze(corpus,tmp_path):
    path,mapping,_=corpus
    class Inspect(DemoModel):
        async def respond(self,messages,tools,**kwargs):
            assert "SENTINEL" not in json.dumps([messages,tools])
            return final_response([],insufficient=True)
    report=await evaluate(path,mapping,tmp_path/"live.json",live=True,model_factory=Inspect,max_runs=48)
    assert report["summary"]["ran"]==32
    assert all(r["not_run_reason"]=="freeze_required" for r in report["rows"] if r["split"]=="held-out")


async def test_resume_configuration_rejection(corpus,tmp_path,monkeypatch):
    path,mapping,_=corpus
    output=tmp_path/"report.json"
    await evaluate(path,mapping,output)
    from codetrace.paired_evaluation import BUDGETS
    with pytest.raises(ValueError,match="Resume"):
        await evaluate(path,mapping,output,resume=output,budgets={**BUDGETS,"max_tools":17})
    with pytest.raises(ValueError,match="Resume"):
        await evaluate(path,mapping,output,resume=output,live=True)


async def test_failures_isolated_retry_history_atomic_and_output_boundary(corpus,tmp_path):
    path,mapping,_=corpus
    output=tmp_path/"report.json"
    def broken(): raise RuntimeError("secret-provider-error")
    report=await evaluate(path,mapping,output,model_factory=broken)
    assert report["summary"]["ran"]==4 and "secret-provider-error" not in json.dumps(report)
    assert all(r["attempts"][0]["status"]=="case_error" for r in report["rows"][:4])
    retried=await evaluate(path,mapping,output,resume=output,retry_failed=True,max_runs=1)
    assert len(retried["rows"][0]["attempts"])==2
    assert retried["rows"][0]["attempts"][0]==report["rows"][0]["attempts"][0]
    assert json.loads(output.read_text(encoding="utf-8"))["summary"]==retried["summary"]
    with pytest.raises(ValueError,match="outside"):
        await evaluate(path,mapping,Path(mapping["repo-0"])/"out.json")


async def test_review_binding_draft_unknown_and_negative(corpus,tmp_path):
    path,mapping,_=corpus
    report=await evaluate(path,mapping,tmp_path/"report.json")
    row=report["rows"][0]
    review=dict(report_id=report["report_id"],dataset_sha256=report["dataset_sha256"],case_id=row["case_id"],variant=row["variant"],run_id=row["attempts"][-1]["run_id"],reviewer="assistant",review_source="assistant_draft",semantic_correct=True,omitted_facts=[],reasonable_refusal=True,failure_category="none",notes="draft")
    import_reviews(report,[review])
    assert report["summary"]["reviewed"]==0
    review.update(review_source="human",reviewer="fixture reviewer",semantic_correct=False,failure_category="explanation_error")
    import_reviews(report,[review])
    assert report["summary"]["reviewed"]==1 and report["summary"]["modes"]["literal"]["successes"]==0
    for key,value in [("run_id","wrong"),("variant","indexed"),("dataset_sha256","wrong"),("report_id","wrong")]:
        with pytest.raises(ValueError): import_reviews(report,[{**review,key:value}])
    assert report["summary"]["modes"]["literal"]["success_rate"] is None


def test_equivalent_evidence_unknown_usage_and_semantic_independence(corpus):
    path,_,_=corpus
    dataset,_=load_benchmark(path)
    case=copy.deepcopy(dataset.cases[0])
    case.evidence_groups[0].append(dataset.cases[1].evidence_groups[0][0])
    alternative=case.evidence_groups[0][1]
    citation=dict(evidence_id="ev",path=alternative.path,start=1,end=1)
    result=dict(findings=[dict(citations=[citation])],evidence=[citation],model_attempts=2,tool_count=1,elapsed_ms=12,usage=None)
    metrics=case_metrics(case,result)
    assert metrics["file_group_coverage"]==1 and metrics["evidence_group_coverage"]==1 and metrics["citation_validity"]==1
    assert metrics["cost"] is None and metrics["usage"] is None
    result["findings"]=[]
    assert case_metrics(case,result)["citation_validity"] is None


def test_full_denominator_gate_and_negative_comparison():
    rows=[]
    for i in range(24):
        for variant in ["literal", "indexed"]:
            rows.append(dict(case_id=str(i),variant=variant,split="held-out" if i>=16 else "development",answerable=True,
                attempts=[dict(status="completed",metrics={"elapsed_ms":10},review=dict(review_source="human",semantic_correct=i%4!=0,omitted_facts=[],reasonable_refusal=None))]))
    report=dict(mode="live",rows=rows,boundary_regression_check="passed")
    summary=summarize(report)
    assert summary["planned"]==48 and summary["reviewed"]==48
    assert summary["modes"]["indexed"]["success_rate"]==.75 and summary["modes"]["indexed"]["held_out_rate"]==.75
    assert summary["analysis_ready_for_programming"]
    rows[3]["attempts"][0]["review"]["semantic_correct"]=False
    assert not summarize(report)["analysis_ready_for_programming"]
    rows[3]["attempts"]=[]
    assert summarize(report)["modes"]["indexed"]["success_rate"] is None
    assert summarize(report)["modes"]["indexed"]["planned"]==24


async def test_freeze_identity_and_all_attempts(corpus,tmp_path):
    from codetrace.benchmark import digest
    path,mapping,_=corpus
    model=lambda: DemoModel(steps=[],insufficient=True)
    output=tmp_path/"report.json"
    report=await evaluate(path,mapping,output,live=True,model_factory=model,max_runs=1)
    frozen=dict(configuration_sha256=report["configuration_sha256"],dataset_sha256=report["dataset_sha256"],code_commit="test-commit",frozen_at="test-time",held_out_used_for_tuning=False)
    freeze=tmp_path/"freeze.json"
    freeze.write_text(json.dumps(frozen),encoding="utf-8")
    report=await evaluate(path,mapping,output,live=True,model_factory=model,resume=output,freeze=freeze,max_runs=48)
    assert report["summary"]["ran"]==48 and report["summary"]["reviewed"]==0
    assert report["summary"]["modes"]["indexed"]["success_rate"] is None
    frozen["held_out_used_for_tuning"]=True
    freeze.write_text(json.dumps(frozen),encoding="utf-8")
    with pytest.raises(ValueError,match="Freeze"):
        await evaluate(path,mapping,output,live=True,model_factory=model,resume=output,freeze=freeze)
