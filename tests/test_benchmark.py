import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from codetrace.benchmark import Benchmark, digest, load_benchmark, source_manifest, verify_checkouts
from codetrace.evaluation import load_dataset


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def corpus(tmp_path):
    repositories, cases, mapping = [], [], {}
    for n, language in enumerate(["java", "python", "java"]):
        ident = f"repo-{n}"
        root = tmp_path / ident
        root.mkdir()
        suffix = ".java" if language == "java" else ".py"
        for i in range(20):
            (root / f"file{i}{suffix}").write_text(f"class Type{i} {{}}\n" if language == "java" else f"class Type{i}: pass\n", encoding="utf-8")
        (root / "LICENSE").write_text("Original test fixture", encoding="utf-8")
        git(root, "init")
        git(root, "config", "core.autocrlf", "false")
        git(root, "add", ".")
        git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
        url = f"https://github.com/fixture/{ident}"
        git(root, "remote", "add", "origin", url)
        manifest = source_manifest(root)
        repositories.append(dict(id=ident,url=url,revision=git(root,"rev-parse","HEAD"),language=language,split="held-out" if n==2 else "development",license="fixture",license_path="LICENSE",license_sha256=hashlib.sha256((root/"LICENSE").read_bytes()).hexdigest(),source_manifest=manifest,manifest_sha256=digest(manifest)))
        mapping[ident] = str(root)
        for i, category in enumerate(["entry","cross-file","cross-file","config","exception","exception","no-answer","no-answer"]):
            path=f"file{i}{suffix}"
            snippet=(root/path).read_text().strip()
            cases.append(dict(id=f"{ident}-case-{i}",repo_id=ident,category=category,question=f"Locate Type{i}",expected_facts=["GOLD_FACT_SENTINEL"],evidence_groups=[[dict(path=path,start=1,end=1,content_sha256=hashlib.sha256(snippet.encode()).hexdigest())]],answerable=category!="no-answer",acceptable_uncertainties=["GOLD_REVIEW_SENTINEL"],ambiguity=i==2,reference_query="GOLD_QUERY_SENTINEL"))
    raw=dict(schema_version=2,dataset_version="fixture.1",repositories=repositories,cases=cases)
    dataset=tmp_path/"dataset.json"
    dataset.write_text(json.dumps(raw),encoding="utf-8")
    return dataset,mapping,raw


def test_fixture_identity_and_v1_v2_loading(corpus):
    path,mapping,raw=corpus
    data,sha=load_benchmark(path)
    roots,status=verify_checkouts(data,mapping)
    assert set(status.values())=={"verified"} and len(roots)==3
    assert load_dataset(path)[1]==sha
    assert load_dataset(Path(__file__).parents[1]/"examples/evaluation.json")[0].schema_version==1
    assert verify_checkouts(data,{})[1]=={r.id:"missing_checkout" for r in data.repositories}


@pytest.mark.parametrize("change", ["duplicate", "range", "manifest", "unsafe", "count"])
def test_bad_metadata(corpus,change):
    _,_,raw=corpus
    raw=copy.deepcopy(raw)
    if change=="duplicate": raw["repositories"][1]["url"]=raw["repositories"][0]["url"]
    if change=="range": raw["cases"][0]["evidence_groups"][0][0]["end"]=999
    if change=="manifest": raw["repositories"][0]["source_manifest"].pop()
    if change=="unsafe":
        repo=raw["repositories"][0]
        repo["source_manifest"][0]["path"]="../secret.py"
        repo["manifest_sha256"]=digest(repo["source_manifest"])
    if change=="count": raw["cases"]=raw["cases"][:-1]
    with pytest.raises(ValueError): Benchmark.model_validate(raw)


def test_dirty_source_wrong_revision_alias_and_annotation(corpus):
    path,mapping,raw=corpus
    data,_=load_benchmark(path)
    wrong=copy.deepcopy(data)
    wrong.repositories[0].revision="0"*40
    with pytest.raises(ValueError,match="revision"): verify_checkouts(wrong,mapping)
    alias={**mapping,"repo-1":mapping["repo-0"]+"/."}
    with pytest.raises(ValueError,match="Aliased"): verify_checkouts(data,alias)
    wrong=copy.deepcopy(data)
    wrong.cases[0].evidence_groups[0][0].content_sha256="0"*64
    with pytest.raises(ValueError,match="Annotated"): verify_checkouts(wrong,mapping)
    file=Path(mapping["repo-0"])/"file0.java"
    file.write_text("class Changed {}",encoding="utf-8")
    with pytest.raises(ValueError,match="manifest"): verify_checkouts(data,mapping)


def test_public_metadata_without_external_checkouts():
    path=Path(__file__).parents[1]/"benchmarks/repository-analysis-v2.json"
    data,_=load_benchmark(path)
    assert len(data.cases)==24 and len(data.repositories)==3
    assert all(v=="missing_checkout" for v in verify_checkouts(data,{})[1].values())
