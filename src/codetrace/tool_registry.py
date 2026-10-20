"""A task owns its tool definitions, execution whitelist and mutable index."""
import json

from codetrace.repository import TOOLS, RepositoryError


class ToolRegistry:
    def __init__(self, repository, retrieval="literal"):
        if retrieval not in {"literal", "indexed"}:
            raise ValueError("retrieval must be literal or indexed")
        self.repository, self.retrieval, self.indexed = repository, retrieval, None
        definitions, versions = list(TOOLS), {}
        if retrieval == "indexed":
            from codetrace.parsing import parser_versions
            from codetrace.indexed_tools import IndexedTools, INDEXED_TOOLS
            versions = parser_versions()
            self.indexed = IndexedTools(repository)
            definitions += INDEXED_TOOLS
        self._definitions = json.dumps(definitions, ensure_ascii=False)
        self.names = frozenset(t["function"]["name"] for t in definitions)
        self.setup = {"node": "retrieval_setup", "mode": retrieval, "parser_versions": versions,
                      "algorithm_version": 1 if self.indexed else None,
                      "index_config": self.indexed.index.config if self.indexed else None,
                      "tools": sorted(self.names)}

    @property
    def definitions(self):
        # A model adapter cannot mutate another request's contract.
        return json.loads(self._definitions)

    def deadline(self, value):
        if self.indexed:
            self.indexed.index.deadline = value

    def cancel(self):
        if self.indexed:
            self.indexed.index.cancelled.set()

    def execute(self, name, arguments):
        if name not in self.names:
            return {"ok": False, "error": "unknown_tool"}
        if not isinstance(arguments, dict):
            return {"ok": False, "error": "invalid_arguments"}
        if self.indexed and name in {"find_symbol", "find_related_symbols", "search_code_ranked"}:
            try:
                return {"ok": True, "data": getattr(self.indexed, name)(**arguments)}
            except RepositoryError as exc:
                return {"ok": False, "error": exc.code}
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid_arguments"}
            except OSError:
                return {"ok": False, "error": "file_access_error"}
        return self.repository.execute(name, arguments)


def semantic_result(value):
    if isinstance(value, dict):
        return {k: semantic_result(v) for k, v in value.items() if k != "diagnostics"}
    if isinstance(value, list):
        return [semantic_result(v) for v in value]
    return value
