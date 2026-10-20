import json
from pathlib import Path

import yaml

from codetrace.evaluation import DEFAULT_DATASET, load_dataset

ROOT = Path(__file__).parents[1]


def test_ci_has_two_platforms_and_no_live_commands():
    workflow = yaml.safe_load((ROOT / ".github/workflows/offline.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["verify"]
    assert set(job["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "windows-latest"}
    commands = [step["run"] for step in job["steps"] if "run" in step]
    assert not any("--live" in command for command in commands)
    assert "python -m pytest -q -rs" in commands
    assert "python -m pip check" in commands
    assert all("--offline" in cmd for cmd in commands if "--repo" in cmd)


def test_committed_report_matches_dataset_and_raw_records():
    _, digest = load_dataset(DEFAULT_DATASET)
    reports = list((ROOT / "docs/evaluation-example").glob("*/report.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    assert report["dataset_sha256"] == digest
    assert report["mode"] == "offline" and report["live_status"] == "not_run"
    assert len(report["cases"]) == 10 and report["summary"]["reviewed"] == 0
    for row in report["cases"]:
        record = json.loads((reports[0].parent / f"{row['run_id']}.json").read_text(encoding="utf-8"))
        assert record == row["result"]
