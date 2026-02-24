from pathlib import Path

from automaton_bench.graph import run_audit


def test_run_audit_returns_report(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("def f() -> int:\n    return 1\n", encoding="utf-8")

    report = run_audit(str(tmp_path))

    assert report.final_verdict.score >= 0
    assert len(report.judge_opinions) == 3
    assert report.evidence.python_files >= 1
    assert all(len(op.criterion_opinions) == 5 for op in report.judge_opinions)
