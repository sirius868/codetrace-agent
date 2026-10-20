"""Version 2 independent repository manifests and annotation validation."""
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from codetrace.evaluation import Strict, CATEGORIES
from codetrace.indexing import SourceIndex
from codetrace.repository import Repository, json_bytes


class ManifestFile(Strict):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    lines: int = Field(ge=0)


class BenchmarkRepo(Strict):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    url: str = Field(pattern=r"^https://github.com/[^/]+/[^/]+$")
    revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    language: Literal["java", "python"]
    split: Literal["development", "held-out"]
    license: str
    license_path: str
    license_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_manifest: list[ManifestFile]
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class EvidenceRange(Strict):
    path: str
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class BenchmarkCase(Strict):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    repo_id: str
    category: Literal["entry", "cross-file", "config", "exception", "no-answer"]
    question: str = Field(min_length=1, max_length=8000)
    expected_facts: list[str]
    evidence_groups: list[list[EvidenceRange]]
    answerable: bool
    acceptable_uncertainties: list[str]
    ambiguity: bool = False
    reference_query: str | None = None
    annotation_source: Literal["assistant_draft", "human"] = "assistant_draft"


class Benchmark(Strict):
    schema_version: Literal[2]
    dataset_version: str
    repositories: list[BenchmarkRepo]
    cases: list[BenchmarkCase]

    @model_validator(mode="after")
    def validate_corpus(self):
        repos = {r.id: r for r in self.repositories}
        if len(repos) != len(self.repositories) or len(repos) < 3:
            raise ValueError("Need three unique repositories")
        if len({r.url.removesuffix('.git').lower() for r in self.repositories}) != len(repos):
            raise ValueError("Duplicate upstream identity")
        languages = Counter(r.language for r in self.repositories)
        if languages["java"] < 2 or languages["python"] < 1:
            raise ValueError("Need two Java and one Python repositories")
        if not any(r.language == "java" and r.split == "held-out" for r in self.repositories):
            raise ValueError("Need held-out Java repository")
        if len({c.id for c in self.cases}) != len(self.cases) or len(self.cases) < 24:
            raise ValueError("Need 24 unique cases")
        categories = Counter(c.category for c in self.cases)
        counts = Counter(c.repo_id for c in self.cases)
        if any(categories[c] < 3 for c in CATEGORIES) or not any(c.ambiguity for c in self.cases):
            raise ValueError("Insufficient category/ambiguity coverage")
        for repo in self.repositories:
            files = {f.path: f for f in repo.source_manifest}
            if len(files) != len(repo.source_manifest) or counts[repo.id] < 8:
                raise ValueError("Duplicate files or insufficient repository cases")
            if sum(p.endswith('.java' if repo.language == 'java' else '.py') for p in files) < 20:
                raise ValueError("Need twenty readable source files per repository")
            for path in files:
                safe_relative(path)
            safe_relative(repo.license_path)
            if digest([f.model_dump() for f in repo.source_manifest]) != repo.manifest_sha256:
                raise ValueError("Manifest digest mismatch")
        for case in self.cases:
            if case.repo_id not in repos:
                raise ValueError("Unknown repository")
            files = {f.path: f for f in repos[case.repo_id].source_manifest}
            if case.answerable and (not case.expected_facts or not case.evidence_groups):
                raise ValueError("Answerable case needs facts/evidence")
            if not case.answerable and not case.acceptable_uncertainties:
                raise ValueError("Unanswerable case needs refusal guidance")
            for group in case.evidence_groups:
                if not group:
                    raise ValueError("Empty evidence group")
                for item in group:
                    if item.path not in files or not item.start <= item.end <= files[item.path].lines:
                        raise ValueError("Invalid annotation range")
        return self


def safe_relative(path):
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts or "\\" in path or ":" in path:
        raise ValueError("Unsafe manifest path")
    if any(Repository._blocked(part) for part in p.parts):
        raise ValueError("Excluded manifest path")


def digest(data):
    return hashlib.sha256(json_bytes(data)).hexdigest()


def source_manifest(root):
    index = SourceIndex(Repository(root)).ensure()
    # Oversized/binary/non-UTF8 files are outside the readable-source contract.
    # Scan truncation, cumulative budget and access failures are incomplete manifests.
    if index.listing.get("truncated") or any(k not in {"file_too_large", "binary_file", "unsupported_encoding"} for k in index.skipped):
        raise ValueError("Benchmark source scope is partial")
    return [{"path": p, "sha256": f["sha256"], "lines": len(f["text"].splitlines())} for p, f in sorted(index.files.items())]


def git(root, *args):
    # Fixed argument lists, no hooks, builds, shell interpolation or target code.
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", timeout=30)
    if result.returncode:
        raise ValueError("Cannot verify Git identity")
    return result.stdout.strip()


def load_benchmark(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    data = Benchmark.model_validate(raw)
    return data, digest(data.model_dump())


def verify_checkouts(dataset, mapping):
    roots, statuses = {}, {}
    for repo in dataset.repositories:
        configured = mapping.get(repo.id)
        if not configured or not Path(configured).is_dir():
            statuses[repo.id] = "missing_checkout"
            continue
        root = Path(configured).resolve(strict=True)
        if any(root == other or root.is_relative_to(other) or other.is_relative_to(root) for other in roots.values()):
            raise ValueError("Aliased or overlapping benchmark roots")
        roots[repo.id] = root
        if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise ValueError("Mapping must name repository root")
        if git(root, "rev-parse", "HEAD") != repo.revision:
            raise ValueError("Benchmark revision mismatch: " + repo.id)
        if git(root, "remote", "get-url", "origin").removesuffix(".git").lower() != repo.url.removesuffix(".git").lower():
            raise ValueError("Benchmark upstream mismatch: " + repo.id)
        current = source_manifest(root)
        if current != [f.model_dump() for f in repo.source_manifest]:
            raise ValueError("Benchmark source manifest mismatch: " + repo.id)
        # Verify license independently; LICENSE without suffix is outside the source index.
        raw = Repository(root)._raw(repo.license_path, 256001)
        if hashlib.sha256(raw).hexdigest() != repo.license_sha256:
            raise ValueError("Benchmark license mismatch")
        reader = Repository(root)
        for case in dataset.cases:
            if case.repo_id != repo.id:
                continue
            for group in case.evidence_groups:
                for item in group:
                    text, _ = reader._text(item.path)
                    content = "\n".join(text.splitlines()[item.start-1:item.end])
                    if hashlib.sha256(content.encode()).hexdigest() != item.content_sha256:
                        raise ValueError("Annotated content mismatch")
        statuses[repo.id] = "verified"
    return roots, statuses
