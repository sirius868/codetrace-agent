"""Bounded indexed tool contracts, shared by model schemas and execution."""
from pathlib import PurePosixPath
from time import perf_counter

from codetrace.indexing import SourceIndex
from codetrace.repository import RepositoryError, SUFFIXES, tool_schema
from codetrace.retrieval import ALGORITHM_VERSION, rank
from codetrace.symbols import extract, public, relations

KINDS = ["class", "interface", "enum", "record", "constructor", "method", "function"]
RELATIONS = ["extends", "implements", "extended_by", "implemented_by"]
BOUND = {"type": "integer", "minimum": 1, "maximum": 20, "default": 10}
PATH = {"type": "string", "default": "."}
INDEXED_TOOLS = [
    tool_schema("find_symbol", "Locate definitions; prefix matches are marked. Read source before citing; symbol_id is not evidence.",
                {"name": {"type": "string", "minLength": 1, "maxLength": 200}, "kind": {"type": "string", "enum": KINDS},
                 "language": {"type": "string", "enum": ["java", "python"]}, "path": PATH, "limit": BOUND}, ["name"]),
    tool_schema("find_related_symbols", "Explicit inheritance candidates, not runtime binding. Ambiguous/unresolved declarations remain uncertain.",
                {"symbol_id": {"type": "string"}, "relation": {"type": "string", "enum": RELATIONS}, "limit": BOUND}, ["symbol_id", "relation"]),
    tool_schema("search_code_ranked", "BM25 lexical candidates with identifier splitting; no semantic translation. Read source before citing.",
                {"query": {"type": "string", "minLength": 1, "maxLength": 200}, "path": PATH,
                 "suffixes": {"type": "array", "items": {"type": "string"}}, "top_k": {**BOUND, "default": 5}}, ["query"]),
]


class IndexedTools:
    def __init__(self, repository):
        self.repository = repository
        self.index = SourceIndex(repository)

    def _symbols(self):
        self.index.ensure()
        result = []
        for file in self.index.files.values():
            self.index.check()
            result.extend(extract(file))
        return result

    def _scope(self, path):
        target = self.repository._path(path)
        relative = target.relative_to(self.repository.root).as_posix()
        return lambda name: relative == "." or name == relative or name.startswith(relative + "/")

    @staticmethod
    def _query(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise RepositoryError("invalid_query")

    def _output(self, matches, total, started, **extra):
        return {"matches": matches, "truncated": total > len(matches), **extra,
                "diagnostics": {**self.index.diagnostics(), "query_ms": round((perf_counter()-started)*1000, 2)}}

    def find_symbol(self, name, kind=None, language=None, path=".", limit=10):
        self._query(name)
        self.repository._integer(limit, 1, 20)
        if kind is not None and kind not in KINDS or language is not None and language not in {"java", "python"}:
            raise RepositoryError("invalid_filter")
        scoped, started = self._scope(path), perf_counter()
        results = []
        for symbol in self._symbols():
            if not scoped(symbol["path"]) or kind and symbol["kind"] != kind or language and symbol["language"] != language:
                continue
            names = (symbol["name"], symbol["qualified_name"])
            if any(n.startswith(name) for n in names):
                results.append(public(symbol) | {"match": "exact" if name in names else "prefix"})
        results.sort(key=lambda s: (s["match"] != "exact", s["path"], s["start"], s["symbol_id"]))
        selected = results[:limit]
        self.index.verify(s["path"] for s in selected)
        return self._output(selected, len(results), started)

    def find_related_symbols(self, symbol_id, relation, limit=10):
        self.repository._integer(limit, 1, 20)
        if not isinstance(symbol_id, str) or relation not in RELATIONS:
            raise RepositoryError("invalid_relation")
        started, symbols = perf_counter(), self._symbols()
        source = next((s for s in symbols if s["symbol_id"] == symbol_id), None)
        if not source:
            raise RepositoryError("unknown_symbol")
        edges = relations(symbols)
        if relation in {"extends", "implements"}:
            matches = [e for e in edges if e["source"] == symbol_id and e["relation"] == relation]
        else:
            forward = {"extended_by": "extends", "implemented_by": "implements"}[relation]
            matches = [e for e in edges if e["relation"] == forward and any(t["symbol_id"] == symbol_id for t in e["targets"])]
        matches.sort(key=lambda e: (e["path"], e["start"], e["expression"]))
        selected = matches[:limit]
        # Each edge is also bounded; preserve ambiguity if not all targets fit.
        bounded, remaining = [], 20
        for edge in selected:
            targets = edge["targets"][:remaining]
            bounded.append({**edge, "targets": targets, "targets_truncated": len(edge["targets"]) > len(targets)})
            remaining -= len(targets)
        selected = bounded
        paths = [source["path"]] + [e["path"] for e in selected] + [t["path"] for e in selected for t in e["targets"]]
        self.index.verify(paths)
        return self._output(selected, len(matches), started, declaration_only=True)

    def search_code_ranked(self, query, path=".", suffixes=None, top_k=5):
        self._query(query)
        self.repository._integer(top_k, 1, 20)
        if suffixes is not None and (not isinstance(suffixes, list) or len(suffixes) > 20
                                    or any(not isinstance(s, str) or s not in SUFFIXES for s in suffixes)):
            raise RepositoryError("invalid_suffixes")
        scoped, started = self._scope(path), perf_counter()
        symbols = self._symbols()
        files = {p: f for p, f in self.index.files.items() if scoped(p) and (suffixes is None or PurePosixPath(p).suffix.lower() in suffixes)}
        results, skipped = rank(files, symbols, query, check=self.index.check)
        selected = results[:top_k]
        self.index.verify(r["path"] for r in selected)
        remaining = 4000
        for item in selected:
            snippet = item.pop("text")
            item["snippet"] = snippet[:min(400, remaining)]
            item["snippet_truncated"] = len(item["snippet"]) < len(snippet)
            remaining -= len(item["snippet"])
        return self._output(selected, len(results), started, algorithm_version=ALGORITHM_VERSION, skipped_long_lines=skipped)
