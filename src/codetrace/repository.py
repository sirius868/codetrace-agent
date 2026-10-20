"""Bounded, read-only tools for a trusted local checkout.

Symlinks and Windows reparse points are rejected. This is not an OS sandbox:
do not analyse a directory that another process is maliciously changing.
"""

import hashlib
import os
import stat
from collections import Counter
from pathlib import Path


EXCLUDED = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "runs", ".aws", ".ssh"}
SUFFIXES = {".py", ".java", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".c", ".h", ".cpp", ".cs", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".xml", ".sql", ".properties", ".html", ".css", ".sh", ".gradle", ".kts"}
BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "Dockerfile"}


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

    def _raw(self, path: str, limit: int) -> bytes:
        target = self._path(path)
        if not target.is_file():
            raise RepositoryError("not_a_file")
        with target.open("rb") as stream:
            return stream.read(limit)

    def _text(self, path: str) -> tuple[str, str]:
        raw = self._raw(path, self.max_bytes + 1)
        return self._decode(raw)

    def _decode(self, raw: bytes) -> tuple[str, str]:
        if len(raw) > self.max_bytes:
            raise RepositoryError("file_too_large")
        if b"\0" in raw:
            raise RepositoryError("binary_file")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise RepositoryError("unsupported_encoding") from None
        return text, hashlib.sha256(raw).hexdigest()

    def _walk(self, path=".", limit=500, suffixes=None, *, check=None, excluded=None):
        if suffixes is not None and (not isinstance(suffixes, list) or len(suffixes) > 20
                                    or any(not isinstance(s, str) or s not in SUFFIXES for s in suffixes)):
            raise RepositoryError("invalid_suffixes")
        base = self._path(path)
        skipped = Counter()
        reasons = []
        found, pending, visited = [], [base], 0

        def accept(candidate):
            return ((candidate.suffix.lower() in SUFFIXES or candidate.name in BUILD_FILES)
                    and (suffixes is None or candidate.suffix.lower() in suffixes))

        if base.is_file():
            return {"files": [base.relative_to(self.root).as_posix()] if accept(base) else [],
                    "truncated": False, "truncation_reasons": [], "scanned_entries": 1,
                    "skipped_entries": 0 if accept(base) else 1, "skip_reasons": {} if accept(base) else {"suffix": 1}}
        while pending:
            if check:
                check()
            directory = pending.pop()
            try:
                self._path(directory.relative_to(self.root).as_posix())
                batch = []
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if check:
                            check()
                        if visited >= self.max_entries:
                            reasons.append("entry_budget")
                            break
                        visited += 1
                        batch.append(entry.name)
                subdirs = []
                for name in sorted(batch):
                    if check:
                        check()
                    if excluded and excluded(name):
                        skipped["index_excluded"] += 1
                        continue
                    rel = (directory / name).relative_to(self.root).as_posix()
                    try:
                        candidate = self._path(rel)
                        if candidate.is_dir():
                            subdirs.append(candidate)
                        elif candidate.is_file() and accept(candidate):
                            if len(found) >= min(limit, self.max_files):
                                reasons.append("file_budget")
                                break
                            found.append(rel)
                        else:
                            skipped["suffix_or_type"] += 1
                    except RepositoryError as exc:
                        skipped[exc.code] += 1
                    except OSError:
                        skipped["file_access_error"] += 1
                pending.extend(reversed(subdirs))
            except RepositoryError as exc:
                skipped[exc.code] += 1
            except OSError:
                skipped["file_access_error"] += 1
            if reasons:
                break
        return {"files": sorted(found), "truncated": bool(reasons), "truncation_reasons": sorted(set(reasons)),
                "scanned_entries": visited, "skipped_entries": sum(skipped.values()), "skip_reasons": dict(skipped)}

    def list_files(self, path=".", limit=100, suffixes=None):
        self._integer(limit, 1, 500)
        if not self._path(path).is_dir():
            raise RepositoryError("not_a_directory")
        return self._walk(path, limit, suffixes)

    def repository_overview(self, path="."):
        listing = self.list_files(path, limit=500)
        files = listing.pop("files")
        return {**listing, "file_count": len(files),
                "counts_scope": "partial" if listing["truncated"] or listing["skip_reasons"].get("file_access_error") else "accessible_files",
                "by_suffix": dict(sorted(Counter(Path(f).suffix.lower() or "[none]" for f in files).items())),
                "directories": sorted({str(Path(f).parent).replace('\\', '/') for f in files}),
                "candidate_paths": [f for f in files if Path(f).name.lower().startswith("readme") or Path(f).name in BUILD_FILES]}

    def fingerprint(self):
        """Bounded content fingerprint for repeat detection, not a persistent index."""
        listing = self._walk(limit=self.max_files)
        digest = hashlib.sha256(json_bytes(listing))
        for path in listing["files"]:
            try:
                _, sha = self._text(path)
                digest.update(json_bytes([path, sha]))
            except (RepositoryError, OSError) as exc:
                digest.update(json_bytes([path, type(exc).__name__]))
        return digest.hexdigest()

    @staticmethod
    def _integer(value, low, high):
        if type(value) is not int or not low <= value <= high:
            raise RepositoryError("invalid_range")

    def search_code(self, query, path=".", limit=30, suffixes=None, context=0):
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise RepositoryError("invalid_query")
        self._integer(limit, 1, 100)
        self._integer(context, 0, 3)
        listing = self._walk(path, limit=min(self.max_files, 500), suffixes=suffixes)
        hits, skipped = [], Counter(listing["skip_reasons"])
        for filename in listing["files"]:
            try:
                text, _ = self._text(filename)
            except RepositoryError as exc:
                skipped[exc.code] += 1
                continue
            except OSError:
                skipped["file_access_error"] += 1
                continue
            lines = text.splitlines()
            for number, line in enumerate(lines, 1):
                if query in line:
                    if len(hits) >= limit:
                        return {"matches": hits, "truncated": True, "truncation_reasons": listing["truncation_reasons"] + ["match_budget"], "skipped_files": sum(skipped.values()), "skip_reasons": dict(skipped)}
                    hits.append({"path": filename, "line": number, "text": line[:500], "line_truncated": len(line) > 500,
                                 "context": [{"line": n, "text": lines[n-1][:500], "line_truncated": len(lines[n-1]) > 500}
                                             for n in range(max(1, number-context), min(len(lines), number+context)+1)]})
        return {"matches": hits, "truncated": listing["truncated"], "truncation_reasons": listing["truncation_reasons"], "skipped_files": sum(skipped.values()), "skip_reasons": dict(skipped)}

    def read_file(self, path, start=1, end=None):
        self._integer(start, 1, 10_000_000)
        end = start + 79 if end is None else end
        self._integer(end, start, start + 119)
        text, digest = self._text(path)
        lines = text.splitlines()
        if not lines and start == 1:
            return {"path": self._path(path).relative_to(self.root).as_posix(), "start": None, "end": None,
                    "lines": [], "sha256": digest, "truncated": False, "next_start": None, "eof": True}
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
                "truncated": output[-1]["line"] < actual_end,
                "next_start": output[-1]["line"] + 1 if output[-1]["line"] < len(lines) else None,
                "eof": output[-1]["line"] == len(lines)}

    def execute(self, name: str, arguments: dict) -> dict:
        methods = {"list_files": self.list_files, "search_code": self.search_code, "read_file": self.read_file, "repository_overview": self.repository_overview}
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


def json_bytes(value):
    import json
    return json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")


TOOLS = [
    tool_schema("repository_overview", "Bounded file statistics and README/build-file candidates, not a call graph.", {"path": {"type": "string", "default": "."}}, []),
    tool_schema("list_files", "List source files under a relative directory; exclusions and limits apply.",
                {"path": {"type": "string", "default": "."}, "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100}, "suffixes": {"type": "array", "items": {"type": "string"}}}, []),
    tool_schema("search_code", "Case-sensitive literal search in source files. Read matched files before citing them.",
                {"query": {"type": "string"}, "path": {"type": "string", "default": "."}, "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30}, "suffixes": {"type": "array", "items": {"type": "string"}}, "context": {"type": "integer", "minimum": 0, "maximum": 3, "default": 0}}, ["query"]),
    tool_schema("read_file", "Read UTF-8 source lines. Use forward-slash relative paths; at most 120 lines per call.",
                {"path": {"type": "string"}, "start": {"type": "integer", "minimum": 1, "default": 1}, "end": {"type": "integer", "minimum": 1, "description": "Omit for start+79; at most start+119."}}, ["path"]),
]
