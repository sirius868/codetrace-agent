"""Bounded, read-only tools for a trusted local checkout.

Symlinks and Windows reparse points are rejected. This is not an OS sandbox:
do not analyse a directory that another process is maliciously changing.
"""

import hashlib
import os
import stat
from pathlib import Path


EXCLUDED = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "runs", ".aws", ".ssh"}
SUFFIXES = {".py", ".java", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".c", ".h", ".cpp", ".cs", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".xml", ".sql", ".properties", ".html", ".css", ".sh"}


class RepositoryError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Repository:
    def __init__(self, root: str | Path, *, max_bytes=256_000, max_files=2000, max_entries=10000):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Repository root must be a directory")
        self.max_bytes = max_bytes
        self.max_files = max_files
        self.max_entries = max_entries

    @staticmethod
    def _blocked(part: str) -> bool:
        name = part.lower()
        return (name in EXCLUDED or name.startswith(".env") or name.startswith("id_rsa")
                or name.startswith("id_ed25519") or name.endswith((".pem", ".key", ".p12", ".pfx"))
                or name in {"credentials", "credentials.json", "secrets.json", "secrets.yaml"})

    def _path(self, value: str) -> Path:
        if not isinstance(value, str) or not value or "\\" in value or ":" in value:
            raise RepositoryError("invalid_path")
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise RepositoryError("path_outside_repository")
        current = self.root
        for part in relative.parts:
            if self._blocked(part):
                raise RepositoryError("excluded_path")
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                raise RepositoryError("not_found") from None
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise RepositoryError("linked_path")
        if not current.resolve().is_relative_to(self.root):
            raise RepositoryError("path_outside_repository")
        return current

    def _text(self, path: str) -> tuple[str, str]:
        target = self._path(path)
        if not target.is_file():
            raise RepositoryError("not_a_file")
        with target.open("rb") as stream:
            raw = stream.read(self.max_bytes + 1)
        if len(raw) > self.max_bytes:
            raise RepositoryError("file_too_large")
        if b"\0" in raw:
            raise RepositoryError("binary_file")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise RepositoryError("unsupported_encoding") from None
        return text, hashlib.sha256(raw).hexdigest()

    def list_files(self, path=".", limit=100):
        self._integer(limit, 1, 500)
        base = self._path(path)
        if not base.is_dir():
            raise RepositoryError("not_a_directory")
        found, pending, visited = [], [base], 0
        # Bound directory entries as well as returned files, including excluded entries.
        while pending:
            directory = pending.pop()
            self._path(directory.relative_to(self.root).as_posix())
            with os.scandir(directory) as entries:
                for entry in entries:
                    visited += 1
                    if visited > self.max_entries:
                        return {"files": sorted(found), "truncated": True}
                    rel = Path(entry.path).relative_to(self.root).as_posix()
                    try:
                        candidate = self._path(rel)
                        if candidate.is_dir():
                            pending.append(candidate)
                        elif candidate.is_file() and (candidate.suffix.lower() in SUFFIXES or candidate.name == "Dockerfile"):
                            if len(found) >= min(limit, self.max_files):
                                return {"files": sorted(found), "truncated": True}
                            found.append(rel)
                    except (RepositoryError, OSError):
                        continue
        return {"files": sorted(found), "truncated": False}

    @staticmethod
    def _integer(value, low, high):
        if type(value) is not int or not low <= value <= high:
            raise RepositoryError("invalid_range")

    def search_code(self, query, path=".", limit=30):
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise RepositoryError("invalid_query")
        self._integer(limit, 1, 100)
        listing = self.list_files(path, limit=min(self.max_files, 500))
        hits, skipped = [], 0
        for filename in listing["files"]:
            try:
                text, _ = self._text(filename)
            except (RepositoryError, OSError):
                skipped += 1
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if query in line:
                    if len(hits) >= limit:
                        return {"matches": hits, "truncated": True, "skipped_files": skipped}
                    hits.append({"path": filename, "line": number, "text": line[:500], "line_truncated": len(line) > 500})
        return {"matches": hits, "truncated": listing["truncated"], "skipped_files": skipped}

    def read_file(self, path, start=1, end=80):
        self._integer(start, 1, 10_000_000)
        self._integer(end, start, start + 119)
        text, digest = self._text(path)
        lines = text.splitlines()
        if start > len(lines):
            raise RepositoryError("line_out_of_range")
        actual_end = min(end, len(lines))
        output, size = [], 0
        for number in range(start, actual_end + 1):
            line = lines[number - 1]
            if size + len(line) > 12000:
                break
            output.append({"line": number, "text": line})
            size += len(line)
        if not output:
            raise RepositoryError("line_too_long")
        return {"path": self._path(path).relative_to(self.root).as_posix(), "start": start,
                "end": output[-1]["line"], "lines": output, "sha256": digest,
                "truncated": output[-1]["line"] < actual_end}

    def execute(self, name: str, arguments: dict) -> dict:
        methods = {"list_files": self.list_files, "search_code": self.search_code, "read_file": self.read_file}
        if name not in methods:
            return {"ok": False, "error": "unknown_tool"}
        if not isinstance(arguments, dict):
            return {"ok": False, "error": "invalid_arguments"}
        try:
            return {"ok": True, "data": methods[name](**arguments)}
        except RepositoryError as exc:
            return {"ok": False, "error": exc.code}
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_arguments"}
        except OSError:
            return {"ok": False, "error": "file_access_error"}


def tool_schema(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}}}


TOOLS = [
    tool_schema("list_files", "List source files under a relative directory; exclusions and limits apply.",
                {"path": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 500}}, []),
    tool_schema("search_code", "Case-sensitive literal search in source files. Read matched files before citing them.",
                {"query": {"type": "string"}, "path": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, ["query"]),
    tool_schema("read_file", "Read UTF-8 source lines. Use forward-slash relative paths; at most 120 lines per call.",
                {"path": {"type": "string"}, "start": {"type": "integer", "minimum": 1}, "end": {"type": "integer", "minimum": 1}}, ["path"]),
]
