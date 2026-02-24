from pathlib import Path

import subprocess

from automaton_bench.detectives import (
    analyze_documentation,
    analyze_graph_structure,
    extract_git_history,
    extract_images_from_pdf,
    ingest_pdf,
    inspect_diagrams,
    investigate_repository,
)


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


def test_analyze_graph_structure_detects_stategraph_instantiation(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "state.py").write_text(
        "from typing import TypedDict\nclass S(TypedDict):\n    x: int\n",
        encoding="utf-8",
    )
    (src / "graph.py").write_text(
        "from langgraph.graph import StateGraph\n"
        "def build():\n"
        "    b = StateGraph(dict)\n"
        "    b.add_edge('a', 'b')\n"
        "    b.add_edge('a', 'c')\n",
        encoding="utf-8",
    )
    result = analyze_graph_structure(str(tmp_path))
    assert result["is_stategraph_instantiated"] is True
    assert result["is_parallel_wired"] is True


def test_extract_git_history_handles_repository(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(tmp_path), check=True, capture_output=True)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    history = extract_git_history(str(tmp_path))
    assert history["classification"] in {"MONOLITHIC", "MIXED", "ATOMIC"}
    assert len(history["commits"]) >= 1


def test_pdf_tools_handle_missing_file() -> None:
    parsed = ingest_pdf("missing-file.pdf")
    assert parsed["chunks"] == []
    assert extract_images_from_pdf("missing-file.pdf") == []
