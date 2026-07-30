"""Mechanical checks for MaxSupport layer boundaries and import cycles."""

import ast
import sys
from pathlib import Path

FORBIDDEN_LAYER_IMPORTS = {
    "domain": {"application", "infrastructure", "interface"},
    "application": {"infrastructure", "interface"},
    "infrastructure": {"interface"},
    "interface": {"infrastructure"},
}


def _module_name(source_root: Path, file_path: Path) -> str:
    relative = file_path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(["src", *parts])


def _imported_modules(tree: ast.AST, current_module: str, is_package: bool) -> set[str]:
    modules: set[str] = set()
    package_parts = current_module.split(".") if is_package else current_module.split(".")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names if alias.name.startswith("src."))
        elif isinstance(node, ast.ImportFrom):
            if (
                node.level == 0
                and node.module
                and (node.module == "src" or node.module.startswith("src."))
            ):
                modules.add(node.module)
                modules.update(
                    f"{node.module}.{alias.name}" for alias in node.names if alias.name != "*"
                )
            elif node.level > 0:
                parent_count = node.level - 1
                if parent_count > len(package_parts):
                    continue
                base_parts = package_parts[: len(package_parts) - parent_count]
                if node.module:
                    imported_module = ".".join([*base_parts, *node.module.split(".")])
                    modules.add(imported_module)
                    modules.update(
                        f"{imported_module}.{alias.name}"
                        for alias in node.names
                        if alias.name != "*"
                    )
                else:
                    modules.update(".".join([*base_parts, alias.name]) for alias in node.names)
    return modules


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()

    def visit(module: str) -> list[str] | None:
        if module in active_set:
            start = active.index(module)
            return [*active[start:], module]
        if module in visited:
            return None

        visited.add(module)
        active.append(module)
        active_set.add(module)
        for dependency in sorted(graph.get(module, set())):
            cycle = visit(dependency)
            if cycle:
                return cycle
        active.pop()
        active_set.remove(module)
        return None

    for module in sorted(graph):
        cycle = visit(module)
        if cycle:
            return cycle
    return None


def find_violations(source_root: Path) -> list[str]:
    violations: list[str] = []
    graph: dict[str, set[str]] = {}
    files = sorted(source_root.rglob("*.py"))
    known_modules = {_module_name(source_root, file_path) for file_path in files}

    for file_path in files:
        module = _module_name(source_root, file_path)
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except SyntaxError as error:
            violations.append(f"{file_path}: invalid Python syntax: {error.msg}")
            continue

        imports = _imported_modules(tree, module, file_path.name == "__init__.py")
        graph[module] = {dependency for dependency in imports if dependency in known_modules}

        relative = file_path.relative_to(source_root)
        source_layer = relative.parts[0] if len(relative.parts) > 1 else None
        forbidden = FORBIDDEN_LAYER_IMPORTS.get(source_layer or "", set())
        for dependency in sorted(imports):
            parts = dependency.split(".")
            target_layer = parts[1] if len(parts) > 1 else None
            if target_layer in forbidden:
                violations.append(
                    f"{relative}: {source_layer} cannot import {target_layer} "
                    f"({dependency}). See docs/architecture.md#dependency-rules."
                )

    cycle = _find_cycle(graph)
    if cycle:
        violations.append(f"import cycle: {' -> '.join(cycle)}")
    return violations


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    violations = find_violations(project_root / "src")
    if violations:
        for violation in violations:
            print(f"ERROR: {violation}")
        return 1
    print("Architecture checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
