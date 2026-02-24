from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from automaton_bench.models import ForensicEvidence


def _is_test_file(path: Path) -> bool:
    name = path.name.lower()
    return name.startswith("test_") or name.endswith("_test.py") or "tests" in path.parts


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _iter_python_files(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.py")


def collect_forensic_evidence(repo_path: str) -> ForensicEvidence:
    root = Path(repo_path).resolve()
    evidence = ForensicEvidence(repository_path=str(root))

    python_files = [p for p in _iter_python_files(root) if ".git" not in p.parts]
    evidence.python_files = len(python_files)
    evidence.test_files = len([p for p in python_files if _is_test_file(p)])
    evidence.docs_present = (root / "README.md").exists() or (root / "docs").exists()
    evidence.ci_present = (root / ".github" / "workflows").exists() or (root / ".gitlab-ci.yml").exists()
    evidence.security_docs_present = (root / "SECURITY.md").exists() or (root / ".snyk").exists()
    evidence.package_count = len([p for p in root.rglob("__init__.py") if ".git" not in p.parts])
    evidence.dependency_files = [
        candidate
        for candidate in ["pyproject.toml", "requirements.txt", "Pipfile", "poetry.lock", "package.json"]
        if (root / candidate).exists()
    ]

    total_lines = 0
    hinted = 0
    total_functions = 0

    for path in python_files:
        src = _safe_read(path)
        total_lines += len(src.splitlines())
        try:
            tree = ast.parse(src)
        except SyntaxError:
            evidence.findings.append(f"Syntax error in {path.relative_to(root)}")
            continue

        class_count = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
        function_nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        hinted_here = 0
        for fn in function_nodes:
            has_return = fn.returns is not None
            has_any_arg_hint = any(arg.annotation is not None for arg in fn.args.args)
            if has_return or has_any_arg_hint:
                hinted_here += 1

        total_functions += len(function_nodes)
        hinted += hinted_here
        evidence.class_count += class_count
        evidence.function_count += len(function_nodes)

    if evidence.python_files:
        evidence.avg_lines_per_python_file = round(total_lines / evidence.python_files, 2)
    if total_functions:
        evidence.type_hinted_function_ratio = round(hinted / total_functions, 2)

    if evidence.python_files == 0:
        evidence.findings.append("No Python source files detected.")
    if evidence.test_files == 0:
        evidence.findings.append("No automated tests detected.")
    if not evidence.ci_present:
        evidence.findings.append("No CI workflow detected.")
    if not evidence.dependency_files:
        evidence.findings.append("No dependency management file detected.")

    return evidence

