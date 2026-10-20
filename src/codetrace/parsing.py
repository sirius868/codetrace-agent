"""Optional syntax frontends. Importing CodeTrace never requires Tree-sitter."""
import ast
from importlib import import_module, metadata


def java_parser():
    try:
        ts = import_module("tree_sitter")
        java = import_module("tree_sitter_java")
    except ImportError:
        raise ValueError("indexed requires Java parser dependencies: pip install '.[indexed]'") from None
    return ts.Parser(ts.Language(java.language()))


def parser_versions():
    java_parser()  # Fail at configuration time, before any model request.
    return {name: metadata.version(name) for name in ("tree-sitter", "tree-sitter-java")}


def parse_source(path, text):
    """Return (status, tree). Invalid files expose text only, never partial symbols."""
    if path.endswith(".java"):
        tree = java_parser().parse(text.encode("utf-8"))
        return ("parse_error", None) if tree.root_node.has_error else ("parsed", tree)
    if path.endswith(".py"):
        try:
            return "parsed", ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            return "parse_error", None
    return "text_only", None
