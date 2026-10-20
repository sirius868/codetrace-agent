import pytest
from codetrace import parsing
from codetrace.repository import Repository


def test_minimal_parsers():
    status, tree = parsing.parse_source("Main.java", "class Main { void run() {} }")
    assert status == "parsed" and tree.root_node.named_children[0].type == "class_declaration"
    assert parsing.parse_source("main.py", "async def run():\n    pass\n")[0] == "parsed"
    assert parsing.parse_source("bad.java", "class {") == ("parse_error", None)
    assert parsing.parse_source("bad.py", "def :") == ("parse_error", None)
    assert parsing.parse_source("config.xml", "<config/>") == ("text_only", None)
    assert parsing.parser_versions() == {"tree-sitter": "0.25.2", "tree-sitter-java": "0.23.5"}


def test_missing_optional_dependency_leaves_literal_usable(monkeypatch, tmp_path):
    def missing(_):
        raise ImportError("not installed")
    monkeypatch.setattr(parsing, "import_module", missing)
    with pytest.raises(ValueError, match=r"pip install.*indexed"):
        parsing.java_parser()
    (tmp_path / "main.py").write_text("def main(): pass", encoding="utf-8")
    assert Repository(tmp_path).execute("search_code", {"query": "main"})["ok"]
    assert parsing.parse_source("main.py", "pass")[0] == "parsed"
