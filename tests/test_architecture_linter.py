import importlib.util
from pathlib import Path


def load_architecture_linter():
    linter_path = Path(__file__).parents[1] / ".linters" / "check_architecture.py"
    spec = importlib.util.spec_from_file_location("check_architecture", linter_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_code_metrics():
    metrics_path = Path(__file__).parents[1] / ".linters" / "code_metrics.py"
    spec = importlib.util.spec_from_file_location("code_metrics", metrics_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reports_application_importing_infrastructure(tmp_path):
    module = load_architecture_linter()
    source_root = tmp_path / "src"
    (source_root / "application").mkdir(parents=True)
    (source_root / "application" / "service.py").write_text(
        "from src.infrastructure.database import Repository\n",
        encoding="utf-8",
    )

    violations = module.find_violations(source_root)

    assert any("application cannot import infrastructure" in item for item in violations)


def test_reports_import_cycle(tmp_path):
    module = load_architecture_linter()
    source_root = tmp_path / "src"
    (source_root / "application").mkdir(parents=True)
    (source_root / "application" / "first.py").write_text(
        "from src.application.second import value\n",
        encoding="utf-8",
    )
    (source_root / "application" / "second.py").write_text(
        "from src.application.first import value\n",
        encoding="utf-8",
    )

    violations = module.find_violations(source_root)

    assert any("import cycle" in item for item in violations)


def test_reports_forbidden_relative_import(tmp_path):
    module = load_architecture_linter()
    source_root = tmp_path / "src"
    (source_root / "application").mkdir(parents=True)
    (source_root / "infrastructure").mkdir()
    (source_root / "application" / "service.py").write_text(
        "from ..infrastructure.database import Repository\n",
        encoding="utf-8",
    )
    (source_root / "infrastructure" / "database.py").write_text(
        "class Repository: pass\n",
        encoding="utf-8",
    )

    violations = module.find_violations(source_root)

    assert any("application cannot import infrastructure" in item for item in violations)


def test_reports_relative_import_cycle(tmp_path):
    module = load_architecture_linter()
    source_root = tmp_path / "src"
    (source_root / "application").mkdir(parents=True)
    (source_root / "application" / "first.py").write_text(
        "from .second import value\n",
        encoding="utf-8",
    )
    (source_root / "application" / "second.py").write_text(
        "from .first import value\n",
        encoding="utf-8",
    )

    violations = module.find_violations(source_root)

    assert any("import cycle" in item for item in violations)


def test_reports_forbidden_imported_layer_name(tmp_path):
    module = load_architecture_linter()
    source_root = tmp_path / "src"
    (source_root / "application").mkdir(parents=True)
    (source_root / "infrastructure").mkdir()
    (source_root / "application" / "service.py").write_text(
        "from src import infrastructure\n",
        encoding="utf-8",
    )
    (source_root / "infrastructure" / "__init__.py").write_text("", encoding="utf-8")

    violations = module.find_violations(source_root)

    assert any("application cannot import infrastructure" in item for item in violations)


def test_reports_cycle_imported_from_package(tmp_path):
    module = load_architecture_linter()
    source_root = tmp_path / "src"
    (source_root / "application").mkdir(parents=True)
    (source_root / "application" / "first.py").write_text(
        "from src.application import second\n",
        encoding="utf-8",
    )
    (source_root / "application" / "second.py").write_text(
        "from src.application import first\n",
        encoding="utf-8",
    )

    violations = module.find_violations(source_root)

    assert any("import cycle" in item for item in violations)


def test_code_metrics_reports_files_over_limit(tmp_path):
    module = load_code_metrics()
    source_root = tmp_path / "src"
    tests_root = tmp_path / "tests"
    source_root.mkdir()
    tests_root.mkdir()
    (source_root / "large.py").write_text("value = 1\n" * 301, encoding="utf-8")
    (tests_root / "test_large.py").write_text("def test_value():\n    pass\n", encoding="utf-8")

    metrics = module.collect_metrics(source_root, tests_root)

    assert metrics["source_files"] == 1
    assert metrics["test_files"] == 1
    assert metrics["files_over_300_lines"] == [{"path": "large.py", "lines": 301}]
