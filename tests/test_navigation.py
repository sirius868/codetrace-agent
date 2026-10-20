import json

import pytest

from codetrace.evidence import validate_answer
from codetrace.models import final_response
from codetrace.repository import Repository
from codetrace.tool_registry import ToolRegistry


def source(root, path, text):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(text.encode("utf-8"))


def test_java_definitions_lines_and_overloads(tmp_path):
    source(tmp_path, "Demo.java", "package demo;\r\nimport java.util.List;\r\n// 中文\r\n@Deprecated\r\npublic class Demo implements Api {\r\n Demo() {}\r\n void run() {}\r\n void run(\r\n String s) {}\r\n class Inner {}\r\n}\r\ninterface Api {}\r\nrecord Item(String name) {}\r\nenum Mode { A }\r\n")
    registry = ToolRegistry(Repository(tmp_path), "indexed")
    run = registry.execute("find_symbol", {"name": "run"})["data"]["matches"]
    assert len(run) == 2 and run[0]["start"] == 7 and run[1]["start"] == 8 and run[1]["end"] == 9
    assert run[0]["symbol_id"] != run[1]["symbol_id"]
    assert run[0]["qualified_name"] == "demo.Demo.run"
    assert run[0]["imports"] == ["java.util.List"]
    cls = registry.execute("find_symbol", {"name": "Demo", "kind": "class"})["data"]["matches"][0]
    assert cls["start"] == 4 and cls["end"] == 11 and cls["annotations"] == ["@Deprecated"]
    for name, kind in [("Demo", "constructor"), ("Inner", "class"), ("Item", "record"), ("Mode", "enum"), ("Api", "interface")]:
        matches = registry.execute("find_symbol", {"name": name, "kind": kind})["data"]["matches"]
        assert len(matches) == 1
    assert registry.execute("find_symbol", {"name": "demo.Demo.Inner"})["data"]["matches"]
    forged = final_response([{**cls, "evidence_id": cls["symbol_id"]}])["message"]["content"]
    assert validate_answer(forged, [])[1]


def test_python_scopes_decorators_and_syntax_fallback(tmp_path):
    source(tmp_path, "pkg/service.py", "import os\nclass Service:\n @staticmethod\n async def run(x: str):\n  def nested():\n   pass\n  return x\ndef run():\n pass\n")
    source(tmp_path, "broken.py", "def broken(:")
    source(tmp_path, "Bad.java", "class Bad { invalid !!! }")
    repo = Repository(tmp_path)
    registry = ToolRegistry(repo, "indexed")
    matches = registry.execute("find_symbol", {"name": "run", "language": "python"})["data"]["matches"]
    assert len(matches) == 2
    method = next(m for m in matches if m["kind"] == "method")
    assert method["start"] == 3 and method["end"] == 7 and method["signature"].startswith("async def")
    assert method["annotations"] == ["staticmethod"]
    assert repo.read_file(method["path"], method["start"], method["end"])["end"] == 7
    assert registry.execute("find_symbol", {"name": "pkg.service.Service.run.nested"})["data"]["matches"]
    assert not registry.execute("find_symbol", {"name": "Bad"})["data"]["matches"]
    assert registry.execute("search_code_ranked", {"query": "broken"})["data"]["matches"]


def test_java_relations_ambiguity_and_external(tmp_path):
    for path, code in {
        "p/Api.java": "package p; public interface Api {}",
        "p/A.java": "package p; class A implements Api {}",
        "q/B.java": "package q; import p.Api; class B implements Api {}",
        "q/C.java": "package q; import p.*; class C implements Api {}",
        "q/D.java": "package q; class D extends external.Base {}",
        "p/E.java": "package p; import external.Api; class E implements Api {}",
        "q/F.java": "package q; class F extends p.A {}",
    }.items():
        source(tmp_path, path, code)
    registry = ToolRegistry(Repository(tmp_path), "indexed")
    def related(name, relation):
        symbol = registry.execute("find_symbol", {"name": name})["data"]["matches"][0]
        return registry.execute("find_related_symbols", {"symbol_id": symbol["symbol_id"], "relation": relation})["data"]["matches"]
    assert len(related("Api", "implemented_by")) == 3
    assert related("B", "implements")[0]["status"] == "resolved"
    assert related("C", "implements")[0]["status"] == "ambiguous"
    assert related("D", "extends")[0]["status"] == "unresolved"
    assert related("E", "implements")[0]["status"] == "unresolved"
    assert related("A", "extended_by")[0]["path"] == "q/F.java"


def test_python_imports_relative_dynamic_and_duplicate(tmp_path):
    source(tmp_path, "pkg/base.py", "class Base: pass\nclass Base: pass\n")
    source(tmp_path, "pkg/child.py", "from .base import Base as B\nclass Child(B): pass\nclass Dynamic(factory()): pass\n")
    registry = ToolRegistry(Repository(tmp_path), "indexed")
    for name, status in [("Child", "ambiguous"), ("Dynamic", "unresolved")]:
        symbol = registry.execute("find_symbol", {"name": name})["data"]["matches"][0]
        edges = registry.execute("find_related_symbols", {"symbol_id": symbol["symbol_id"], "relation": "extends"})["data"]["matches"]
        assert edges[0]["status"] == status


def test_filters_limits_prefix_and_stale(tmp_path):
    source(tmp_path, "a.py", "\n".join(f"def run{i}(): pass" for i in range(25)) + "\ndef run(): pass\n")
    source(tmp_path, "sub/b.py", "def run(): pass\n")
    registry = ToolRegistry(Repository(tmp_path), "indexed")
    data = registry.execute("find_symbol", {"name": "run", "limit": 20})["data"]
    assert data["truncated"] and len(data["matches"]) == 20 and data["matches"][0]["match"] == "exact"
    assert data["matches"][2]["match"] == "prefix"
    assert len(registry.execute("find_symbol", {"name": "run", "path": "sub"})["data"]["matches"]) == 1
    for args in [{"name": "run", "limit": 21}, {"name": ""}, {"name": "run", "kind": "bogus"}, {"name": "run", "path": "../"}]:
        assert not registry.execute("find_symbol", args)["ok"]
    assert registry.execute("find_related_symbols", {"symbol_id": "unknown", "relation": "extends"})["error"] == "unknown_symbol"
    source(tmp_path, "sub/b.py", "\n\ndef run(): pass\n")
    assert registry.execute("find_symbol", {"name": "run", "path": "sub"})["error"] == "index_stale"
    assert registry.execute("find_symbol", {"name": "run", "path": "sub"})["data"]["matches"][0]["start"] == 3


def test_long_signature_and_hints(tmp_path):
    code = "\n".join(f"import package{i}.Type{i};" for i in range(12)) + "\nclass Long { void run(" + ",".join(f"String argument{i}" for i in range(40)) + ") {} }"
    source(tmp_path, "Long.java", code)
    data = ToolRegistry(Repository(tmp_path), "indexed").execute("find_symbol", {"name": "run"})["data"]["matches"][0]
    assert data["truncated"] and len(data["signature"]) == 300 and len(data["imports"]) == 10
    assert "_imports" not in json.dumps(data)


def test_python_src_layout_imports(tmp_path):
    source(tmp_path, "src/pkg/base.py", "class Base: pass\n")
    source(tmp_path, "src/pkg/child.py", "from pkg.base import Base\nclass Child(Base): pass\n")
    registry = ToolRegistry(Repository(tmp_path), "indexed")
    symbol = registry.execute("find_symbol", {"name": "Child"})["data"]["matches"][0]
    edges = registry.execute("find_related_symbols", {"symbol_id": symbol["symbol_id"], "relation": "extends"})["data"]["matches"]
    assert edges[0]["status"] == "resolved" and edges[0]["targets"][0]["qualified_name"] == "pkg.base.Base"
