"""Lexical definitions and explicit inheritance candidates, not a type checker."""
import ast
import hashlib
import re
from pathlib import PurePosixPath

from codetrace.repository import json_bytes

TYPES = {"class", "interface", "enum", "record"}


def _symbol(path, sha, name, qualified, kind, start, end, signature, imports, annotations, bases, language, package):
    identity = [path, qualified, kind, signature, start, end]
    return {"symbol_id": "sym_" + hashlib.sha256(json_bytes(identity)).hexdigest()[:24],
            "path": path, "sha256": sha, "name": name, "qualified_name": qualified, "kind": kind,
            "start": start, "end": end, "signature": signature[:300], "language": language,
            "imports": [i[:300] for i in imports[:10]], "annotations": [a[:300] for a in annotations[:10]],
            "truncated": len(signature) > 300 or len(imports) > 10 or len(annotations) > 10
                or any(len(v) > 300 for v in imports + annotations),
            "_imports": imports, "_package": package, "_bases": bases}


def public(symbol):
    return {k: v for k, v in symbol.items() if not k.startswith("_")}


def extract(file):
    if file["parse_status"] != "parsed":
        return []
    return _python(file) if file["path"].endswith(".py") else _java(file)


def _java(file):
    raw = file["text"].encode("utf-8")
    root = file["tree"].root_node
    def text(node):
        return raw[node.start_byte:node.end_byte].decode("utf-8") if node else ""
    package, imports = "", []
    for child in root.named_children:
        if child.type == "package_declaration":
            package = text(child).removeprefix("package").strip().rstrip(";").strip()
        elif child.type == "import_declaration":
            imports.append(text(child).removeprefix("import").strip().rstrip(";").strip())
    result = []
    kinds = {"class_declaration": "class", "interface_declaration": "interface", "enum_declaration": "enum",
             "record_declaration": "record", "method_declaration": "method", "constructor_declaration": "constructor",
             "compact_constructor_declaration": "constructor"}
    def walk(node, parents):
        kind = kinds.get(node.type)
        nested = parents
        if kind:
            name = text(node.child_by_field_name("name"))
            qualified = ".".join(filter(None, [package, *parents, name]))
            body = node.child_by_field_name("body")
            signature = raw[node.start_byte:body.start_byte if body else node.end_byte].decode("utf-8").strip()
            modifiers = next((c for c in node.named_children if c.type == "modifiers"), None)
            annotations = [text(c) for c in modifiers.named_children if "annotation" in c.type] if modifiers else []
            bases = []
            for child in node.named_children:
                if child.type not in {"superclass", "super_interfaces", "extends_interfaces"}:
                    continue
                relation = "implements" if child.type == "super_interfaces" else "extends"
                nodes = child.named_children
                if nodes and nodes[0].type == "type_list":
                    nodes = nodes[0].named_children
                for base in nodes:
                    bases.append({"relation": relation, "expression": text(base),
                                  "start": base.start_point.row + 1, "end": base.end_point.row + 1})
            result.append(_symbol(file["path"], file["sha256"], name, qualified, kind,
                                  node.start_point.row + 1, node.end_point.row + 1, signature,
                                  imports, annotations, bases, "java", package))
            nested = parents + [name]
        for child in node.named_children:
            walk(child, nested)
    walk(root, [])
    return result


def _python(file):
    text, root = file["text"], file["tree"]
    module = ".".join(PurePosixPath(file["path"]).with_suffix("").parts)
    if module.endswith(".__init__"):
        module = module[:-9]
    imports = []
    # Module-level import bindings only; local/dynamic bindings are not inferred.
    for node in root.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.get_source_segment(text, node) or ast.unparse(node))
    result = []
    def walk(node, parents, parent_kind="module"):
        nested, nested_kind = parents, parent_kind
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else ("method" if parent_kind == "class" else "function")
            annotations = [ast.get_source_segment(text, n) or ast.unparse(n) for n in node.decorator_list]
            start = min([node.lineno] + [n.lineno for n in node.decorator_list])
            # Reconstruct only the declaration; never include the function body.
            if kind == "class":
                signature = f"class {node.name}({', '.join(ast.unparse(b) for b in node.bases)})"
            else:
                signature = ("async " if isinstance(node, ast.AsyncFunctionDef) else "") + f"def {node.name}({ast.unparse(node.args)})"
                if node.returns:
                    signature += " -> " + ast.unparse(node.returns)
            bases = [{"relation": "extends", "expression": ast.get_source_segment(text, b) or ast.unparse(b),
                      "start": b.lineno, "end": b.end_lineno,
                      "resolvable": isinstance(b, (ast.Name, ast.Attribute))} for b in node.bases] if kind == "class" else []
            result.append(_symbol(file["path"], file["sha256"], node.name, ".".join([module, *parents, node.name]),
                                  kind, start, node.end_lineno, signature, imports, annotations, bases, "python", module))
            nested, nested_kind = parents + [node.name], kind
        for child in ast.iter_child_nodes(node):
            walk(child, nested, nested_kind)
    walk(root, [])
    return result


def _resolve(source, base, types):
    expression = base["expression"]
    if not base.get("resolvable", True):
        return [], "unresolved"
    name = re.sub(r"<.*>", "", expression).strip() if source["language"] == "java" else expression
    pool = [s for s in types if s["language"] == source["language"]]
    def matching(names):
        return [s for s in pool if s["qualified_name"] in names]
    if source["language"] == "java":
        candidates = matching([name]) if "." in name else []
        if not candidates:
            explicit = [i for i in source["_imports"] if not i.startswith("static ") and i.rsplit(".", 1)[-1] == name]
            candidates = matching(explicit)
            # An explicit external import must not resolve to a same-package namesake.
            if explicit and not candidates:
                return [], "unresolved"
        if not candidates:
            candidates = matching([".".join(filter(None, [source["_package"], name]))])
        wildcard = False
        if not candidates:
            wild = [i[:-1] + name for i in source["_imports"] if i.endswith(".*") and not i.startswith("static ")]
            candidates, wildcard = matching(wild), bool(wild)
        return candidates, "ambiguous" if candidates and (wildcard or len(candidates) > 1) else ("resolved" if candidates else "unresolved")
    names = []
    first, _, tail = name.partition(".")
    bound = False
    for code in source["_imports"]:
        node = ast.parse(code).body[0]
        for alias in node.names:
            if isinstance(node, ast.Import):
                local = alias.asname or alias.name.split(".")[0]
                target = alias.name if alias.asname else local
            else:
                local = alias.asname or alias.name
                prefix = node.module or ""
                if node.level:
                    parts = source["_package"].split(".")
                    # __init__ uses its own package, regular modules use their parent.
                    if not source["path"].endswith("/__init__.py"):
                        parts = parts[:-1]
                    parts = parts[:len(parts) - node.level + 1]
                    prefix = ".".join(filter(None, [*parts, prefix]))
                target = ".".join(filter(None, [prefix, alias.name]))
            if local == first:
                bound = True
                names.append(target + ("." + tail if tail else ""))
    if not bound:
        names = [source["_package"] + "." + name]
    candidates = matching(names)
    return candidates, "ambiguous" if len(candidates) > 1 else ("resolved" if candidates else "unresolved")


def relations(symbols):
    types = [s for s in symbols if s["kind"] in TYPES]
    edges = []
    for source in types:
        for base in source["_bases"]:
            targets, status = _resolve(source, base, types)
            edges.append({"source": source["symbol_id"], "path": source["path"], "sha256": source["sha256"],
                          "relation": base["relation"], "expression": base["expression"][:300],
                          "start": base["start"], "end": base["end"], "status": status,
                          "targets": [public(s) for s in targets]})
    return edges
