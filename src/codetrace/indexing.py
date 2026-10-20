"""Task-local, bounded snapshots. Navigation is not citation evidence."""
import hashlib
from collections import Counter
from threading import Event
from time import perf_counter
from uuid import uuid4

from codetrace.parsing import parse_source
from codetrace.repository import RepositoryError, json_bytes


def index_excluded(name):
    lower = name.lower()
    return lower == "target" or lower.startswith((".venv", "venv-", "venv_")) or lower in {"env", ".envs", "envs"}


class SourceIndex:
    def __init__(self, repository, *, max_total_bytes=16 * 1024 * 1024, deadline=None, clock=perf_counter):
        self.repository = repository
        self.max_total_bytes = max_total_bytes
        self.deadline, self.clock = deadline, clock
        self.cancelled = Event()
        self.index_id = uuid4().hex
        self.files = {}
        self.invalid = set()
        self.built = False
        self.read_bytes = 0
        self.validation_bytes = 0
        self.skipped = Counter()
        self.listing = {}
        self.build_ms = 0

    def check(self):
        if self.cancelled.is_set() or (self.deadline is not None and self.clock() >= self.deadline):
            self.cancelled.set()
            raise RepositoryError("task_timeout")

    def _read(self, path):
        self.check()
        remaining = self.max_total_bytes - self.read_bytes
        if remaining <= 0:
            raise RepositoryError("total_byte_budget")
        limit = min(self.repository.max_bytes + 1, remaining)
        raw = self.repository._raw(path, limit)
        self.read_bytes += len(raw)  # Failed decoding counts too.
        self.check()
        if len(raw) == limit and limit <= self.repository.max_bytes:
            # Cannot establish EOF without exceeding the remaining budget.
            raise RepositoryError("total_byte_budget")
        text, sha = self.repository._decode(raw)
        status, tree = parse_source(path, text)
        self.check()
        return {"path": path, "sha256": sha, "text": text, "parse_status": status, "tree": tree}

    def ensure(self):
        self.check()
        if not self.built:
            started = self.clock()
            self.listing = self.repository._walk(limit=self.repository.max_files, check=self.check, excluded=index_excluded)
            for path in self.listing["files"]:
                self._refresh(path)
                if self.read_bytes >= self.max_total_bytes:
                    break
            self.built = True
            self.build_ms = round((self.clock() - started) * 1000, 2)
        else:
            for path in sorted(self.invalid):
                self._refresh(path)
            self.invalid.clear()
        self.check()
        return self

    def _refresh(self, path):
        self.files.pop(path, None)
        try:
            self.files[path] = self._read(path)
        except RepositoryError as exc:
            if exc.code == "task_timeout":
                raise
            self.skipped[exc.code] += 1
        except OSError:
            self.skipped["file_access_error"] += 1

    @property
    def config(self):
        return {"max_files": self.repository.max_files, "max_entries": self.repository.max_entries,
                "max_file_bytes": self.repository.max_bytes, "max_total_bytes": self.max_total_bytes}

    @property
    def manifest(self):
        return [{"path": p, "sha256": f["sha256"], "parse_status": f["parse_status"]}
                for p, f in sorted(self.files.items())]

    @property
    def digest(self):
        return hashlib.sha256(json_bytes({"config": self.config, "files": self.manifest})).hexdigest()

    def diagnostics(self):
        skips = Counter(self.listing.get("skip_reasons", {})) + self.skipped
        return {"index_id": self.index_id, "config": self.config, "manifest_sha256": self.digest,
                "file_count": len(self.files), "read_bytes": self.read_bytes, "validation_bytes": self.validation_bytes,
                "build_ms": self.build_ms, "scanned_entries": self.listing.get("scanned_entries", 0),
                "partial": bool(self.skipped or self.listing.get("truncated") or skips.get("file_access_error")),
                "truncation_reasons": self.listing.get("truncation_reasons", []), "skip_reasons": dict(skips),
                "parse_states": dict(Counter(f["parse_status"] for f in self.files.values())),
                "scope": "initial manifest; new files require a new task"}

    def verify(self, paths):
        """Revalidate each selected file once per query; never return stale candidates."""
        stale = []
        for path in sorted(set(paths)):
            self.check()
            try:
                raw = self.repository._raw(path, self.repository.max_bytes + 1)
                self.validation_bytes += len(raw)
                self.check()
                _, digest = self.repository._decode(raw)
                if digest != self.files[path]["sha256"]:
                    stale.append(path)
            except RepositoryError as exc:
                if exc.code == "task_timeout":
                    raise
                stale.append(path)
            except OSError:
                stale.append(path)
        if stale:
            self.invalid.update(stale)
            raise RepositoryError("index_stale")
