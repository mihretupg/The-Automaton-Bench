from pathlib import Path

from automaton_bench.detectives import analyze_documentation, inspect_diagrams, investigate_repository


def test_repo_investigator_detects_state_and_fanout(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "state.py").write_text(
        "from typing import TypedDict\n\nclass AuditState(TypedDict):\n    x: int\n",
        encoding="utf-8",
    )
    (src / "graph.py").write_text(
        "def build(builder):\n"
        "    builder.add_edge('forensics', 'prosecutor')\n"
        "    builder.add_edge('forensics', 'defense')\n",
        encoding="utf-8",
    )

    evidence = investigate_repository(str(tmp_path))
    assert evidence.state_structure.passed is True
    assert evidence.graph_wiring.passed is True
    assert "forensics" in evidence.fan_out_sources


def test_doc_analyst_flags_hallucinated_citation(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "We implemented judges in src/nodes/judges.py with dialectical synthesis.\n",
        encoding="utf-8",
    )
    doc = analyze_documentation(str(tmp_path), pdf_report_path=None)
    assert doc.citation_check.passed is False
    assert any(item.status == "HALLUCINATION" for item in doc.cited_paths)


def test_vision_inspector_classifies_parallel_flow(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Detectives run in parallel -> Evidence Aggregation -> Judges in parallel -> Synthesis.\n",
        encoding="utf-8",
    )
    vision = inspect_diagrams(str(tmp_path), pdf_report_path=None)
    assert vision.flow_analysis.passed is True
    assert vision.architecture_flow_classification == "COURTROOM_PARALLEL"
