from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Iterable

from automaton_bench.models import (
    CitationFinding,
    DocAnalystEvidence,
    GitCommitRecord,
    ProtocolResult,
    RepoInvestigatorEvidence,
    VisionInspectorEvidence,
)

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency guard
    PdfReader = None


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if ".git" not in path.parts:
            yield path


def _parse_edge_endpoints(call: ast.Call) -> tuple[str, str] | None:
    if len(call.args) < 2:
        return None
    source, target = call.args[0], call.args[1]
    if not isinstance(source, ast.Constant) or not isinstance(source.value, str):
        return None
    if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
        return None
    return source.value, target.value


def investigate_repository(repo_path: str) -> RepoInvestigatorEvidence:
    root = Path(repo_path).resolve()

    state_targets = [root / "src" / "state.py", root / "src" / "graph.py"]
    state_files = [path for path in state_targets if path.exists()]
    typed_schema_locations: list[str] = []
    for file_path in state_files:
        src = _safe_read(file_path)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = [getattr(base, "id", getattr(base, "attr", "")) for base in node.bases]
                if "BaseModel" in base_names or "TypedDict" in base_names:
                    typed_schema_locations.append(f"{file_path.relative_to(root)}::{node.name}")

    state_protocol = ProtocolResult(
        protocol="State Structure",
        passed=bool(state_files and typed_schema_locations),
        summary=(
            f"Found typed state schemas: {', '.join(typed_schema_locations)}"
            if typed_schema_locations
            else "Missing typed state schemas in src/state.py or src/graph.py."
        ),
    )

    edges_by_source: dict[str, set[str]] = {}
    for py_file in _iter_python_files(root):
        src = _safe_read(py_file)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_edge":
                parsed = _parse_edge_endpoints(node)
                if not parsed:
                    continue
                source, target = parsed
                edges_by_source.setdefault(source, set()).add(target)

    fan_out_sources = sorted([source for source, targets in edges_by_source.items() if len(targets) >= 2])
    graph_protocol = ProtocolResult(
        protocol="Graph Wiring",
        passed=bool(fan_out_sources),
        summary=(
            f"Detected fan-out from: {', '.join(fan_out_sources)}"
            if fan_out_sources
            else "No AST-verified fan-out edge pattern detected from add_edge calls."
        ),
    )

    commits: list[GitCommitRecord] = []
    git_classification = "UNKNOWN"
    git_summary = "No git metadata available."
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--pretty=format:%H|%aI|%s", "--reverse"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split("|", 2)
                if len(parts) != 3:
                    continue
                commits.append(
                    GitCommitRecord(
                        commit_hash=parts[0],
                        authored_at=parts[1],
                        message=parts[2],
                    )
                )
    except OSError:
        commits = []

    commit_count = len(commits)
    if commit_count <= 1:
        git_classification = "MONOLITHIC"
    else:
        messages = [commit.message.lower() for commit in commits]
        unique_messages = len(set(messages))
        if commit_count >= 4 and unique_messages >= 3:
            git_classification = "ATOMIC"
        else:
            git_classification = "MIXED"

    if commits:
        git_summary = (
            f"{git_classification} history with {commit_count} commits; "
            f"timeline {commits[0].authored_at} -> {commits[-1].authored_at}."
        )

    git_protocol = ProtocolResult(
        protocol="Git Narrative",
        passed=git_classification == "ATOMIC",
        summary=git_summary,
    )

    return RepoInvestigatorEvidence(
        state_structure=state_protocol,
        graph_wiring=graph_protocol,
        git_narrative=git_protocol,
        fan_out_sources=fan_out_sources,
        typed_schema_locations=typed_schema_locations,
        git_commit_count=commit_count,
        git_history_classification=git_classification,
        git_timeline=commits,
    )


def _read_pdf_text(pdf_report_path: str | None) -> str:
    if not pdf_report_path or PdfReader is None:
        return ""
    pdf_path = Path(pdf_report_path).resolve()
    if not pdf_path.exists():
        return ""
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return ""
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts)


def _read_markdown_corpus(root: Path) -> str:
    parts: list[str] = []
    readme = root / "README.md"
    if readme.exists():
        parts.append(_safe_read(readme))
    docs_dir = root / "docs"
    if docs_dir.exists():
        for path in docs_dir.rglob("*.md"):
            parts.append(_safe_read(path))
    return "\n".join(parts)


_CITED_PATH_PATTERN = re.compile(
    r"([A-Za-z0-9_\-./\\]+\.(?:py|md|txt|json|ya?ml|toml|tsx?|jsx?|png|jpg|jpeg|svg))"
)


def analyze_documentation(repo_path: str, pdf_report_path: str | None) -> DocAnalystEvidence:
    root = Path(repo_path).resolve()
    corpus = f"{_read_markdown_corpus(root)}\n{_read_pdf_text(pdf_report_path)}"
    cited_paths = sorted(set(match.group(1).replace("\\", "/") for match in _CITED_PATH_PATTERN.finditer(corpus)))

    findings: list[CitationFinding] = []
    hallucinations = 0
    for rel_path in cited_paths[:50]:
        exists = (root / rel_path).exists()
        status = "OK" if exists else "HALLUCINATION"
        if not exists:
            hallucinations += 1
        findings.append(CitationFinding(cited_path=rel_path, exists_in_repo=exists, status=status))

    citation_protocol = ProtocolResult(
        protocol="Citation Check",
        passed=hallucinations == 0,
        summary=(
            "All cited file paths were verified in repository."
            if hallucinations == 0
            else f"Detected {hallucinations} cited paths that do not exist in repository."
        ),
    )

    lowered = corpus.lower()
    has_dialectical = "dialectical synthesis" in lowered
    has_metacognition = "metacognition" in lowered
    explanation_markers = ["because", "therefore", "means", "implemented", "executes", "via", "by"]
    depth = "MISSING"
    passed = False
    if has_dialectical or has_metacognition:
        marker_hits = sum(1 for marker in explanation_markers if marker in lowered)
        if marker_hits >= 2:
            depth = "EXPLAINED"
            passed = True
        else:
            depth = "KEYWORD_DROP"
    concept_protocol = ProtocolResult(
        protocol="Concept Verification",
        passed=passed,
        summary=(
            f"Concept depth classified as {depth}."
            if has_dialectical or has_metacognition
            else "Neither 'Dialectical Synthesis' nor 'Metacognition' found in provided documents."
        ),
    )

    return DocAnalystEvidence(
        citation_check=citation_protocol,
        concept_verification=concept_protocol,
        cited_paths=findings,
        concept_depth=depth,
    )


def inspect_diagrams(repo_path: str, pdf_report_path: str | None) -> VisionInspectorEvidence:
    root = Path(repo_path).resolve()
    corpus = f"{_read_markdown_corpus(root)}\n{_read_pdf_text(pdf_report_path)}"
    lines = [line.strip() for line in corpus.splitlines() if line.strip()]
    diagram_lines = [line for line in lines if "->" in line or "flowchart" in line.lower() or "mermaid" in line.lower()]
    lowered = corpus.lower()

    has_detective = "detective" in lowered
    has_judge = "judge" in lowered
    has_aggregation = "aggregation" in lowered or "evidence aggregation" in lowered
    has_synthesis = "synthesis" in lowered
    has_parallel = "parallel" in lowered or "fan-out" in lowered

    if has_detective and has_judge and has_aggregation and has_synthesis and has_parallel:
        classification = "COURTROOM_PARALLEL"
        passed = True
    elif diagram_lines:
        classification = "LINEAR_OR_INCOMPLETE"
        passed = False
    else:
        classification = "NO_DIAGRAM_EVIDENCE"
        passed = False

    flow_protocol = ProtocolResult(
        protocol="Flow Analysis",
        passed=passed,
        summary=f"Diagram flow classified as {classification}.",
    )
    return VisionInspectorEvidence(
        flow_analysis=flow_protocol,
        architecture_flow_classification=classification,
        diagram_sources=diagram_lines[:20],
    )
