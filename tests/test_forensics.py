from pathlib import Path

from automaton_bench.forensics import collect_forensic_evidence


def test_collect_forensic_evidence_detects_basic_artifacts(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "core.py").write_text(
        "def run(x: int) -> int:\n    return x + 1\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_core.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    evidence = collect_forensic_evidence(str(tmp_path))
    assert evidence.python_files >= 2
    assert evidence.test_files >= 1
    assert evidence.docs_present is True
    assert evidence.ci_present is True
    assert evidence.function_count >= 1

