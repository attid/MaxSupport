"""Emit deterministic repository health metrics as JSON."""

import json
from pathlib import Path
from typing import TypedDict


class FileMetric(TypedDict):
    path: str
    lines: int


class CodeMetrics(TypedDict):
    source_files: int
    source_lines: int
    test_files: int
    test_lines: int
    files_over_300_lines: list[FileMetric]


def _line_count(file_path: Path) -> int:
    return len(file_path.read_text(encoding="utf-8").splitlines())


def collect_metrics(source_root: Path, tests_root: Path) -> CodeMetrics:
    source_files = sorted(source_root.rglob("*.py"))
    test_files = sorted(tests_root.rglob("*.py"))
    source_counts = {file_path: _line_count(file_path) for file_path in source_files}
    test_counts = {file_path: _line_count(file_path) for file_path in test_files}
    files_over_limit = [
        {
            "path": str(file_path.relative_to(source_root)),
            "lines": line_count,
        }
        for file_path, line_count in source_counts.items()
        if line_count > 300
    ]
    return {
        "source_files": len(source_files),
        "source_lines": sum(source_counts.values()),
        "test_files": len(test_files),
        "test_lines": sum(test_counts.values()),
        "files_over_300_lines": files_over_limit,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    metrics = collect_metrics(project_root / "src", project_root / "tests")
    print(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
