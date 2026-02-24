from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

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


def _classify_git_history(commits: list[GitCommitRecord]) -> str:
    commit_count = len(commits)
    if commit_count <= 1:
        return "MONOLITHIC"
    messages = [commit.message.lower() for commit in commits]
    unique_messages = len(set(messages))
    if commit_count >= 4 and unique_messages >= 3:
        return "ATOMIC"
    return "MIXED"


def analyze_graph_structure(path: str) -> dict[str, Any]:
    root = Path(path).resolve()
    state_targets = [root / "src" / "state.py", root / "src" / "graph.py", root / "automaton_bench" / "state.py"]
    state_files = [p for p in state_targets if p.exists()]

    typed_schema_locations: list[str] = []
    stategraph_instantiations: list[str] = []
    edges_by_source: dict[str, set[str]] = {}

    for py_file in _iter_python_files(root):
        src = _safe_read(py_file)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = [getattr(base, "id", getattr(base, "attr", "")) for base in node.bases]
                if "BaseModel" in base_names or "TypedDict" in base_names:
                    typed_schema_locations.append(f"{py_file.relative_to(root)}::{node.name}")

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "StateGraph":
                    stategraph_instantiations.append(str(py_file.relative_to(root)))
                elif isinstance(node.func, ast.Attribute) and node.func.attr == "StateGraph":
                    stategraph_instantiations.append(str(py_file.relative_to(root)))

                if isinstance(node.func, ast.Attribute) and node.func.attr == "add_edge":
                    parsed = _parse_edge_endpoints(node)
                    if not parsed:
                        continue
                    source, target = parsed
                    edges_by_source.setdefault(source, set()).add(target)

    fan_out_sources = sorted([source for source, targets in edges_by_source.items() if len(targets) >= 2])
    return {
        "state_files": [str(p.relative_to(root)) for p in state_files],
        "typed_schema_locations": sorted(set(typed_schema_locations)),
        "stategraph_instantiations": sorted(set(stategraph_instantiations)),
        "edges_by_source": {k: sorted(v) for k, v in edges_by_source.items()},
        "fan_out_sources": fan_out_sources,
        "is_parallel_wired": bool(fan_out_sources),
        "has_typed_state": bool(state_files and typed_schema_locations),
        "is_stategraph_instantiated": bool(stategraph_instantiations),
    }


def extract_git_history(path: str) -> dict[str, Any]:
    root = Path(path).resolve()
    commits: list[GitCommitRecord] = []
    error: str | None = None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--pretty=format:%H|%aI|%s", "--reverse"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            error = (result.stderr.strip() or result.stdout.strip() or "git log failed").strip()
        else:
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
    except OSError as exc:
        error = str(exc)

    classification = _classify_git_history(commits) if commits else "UNKNOWN"
    summary = "No git metadata available."
    if commits:
        summary = (
            f"{classification} history with {len(commits)} commits; "
            f"timeline {commits[0].authored_at} -> {commits[-1].authored_at}."
        )
    elif error:
        summary = f"Git history unavailable: {error}"
    return {
        "commits": commits,
        "classification": classification,
        "summary": summary,
        "error": error,
    }


def ingest_pdf(path: str, chunk_size: int = 1200, overlap: int = 120) -> dict[str, Any]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")
    if not path:
        return {"chunks": [], "page_count": 0, "query": lambda _: []}
    if PdfReader is None:
        return {"chunks": [], "page_count": 0, "query": lambda _: []}

    pdf_path = Path(path).resolve()
    if not pdf_path.exists():
        return {"chunks": [], "page_count": 0, "query": lambda _: []}

    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return {"chunks": [], "page_count": 0, "query": lambda _: []}

    full_text = []
    for page in reader.pages:
        try:
            full_text.append(page.extract_text() or "")
        except Exception:
            full_text.append("")
    text = "\n".join(full_text).strip()

    chunks: list[dict[str, Any]] = []
    if text:
        start = 0
        idx = 0
        stride = chunk_size - overlap
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk = text[start:end]
            chunks.append({"id": idx, "text": chunk})
            idx += 1
            start += stride

    def query(question: str, top_k: int = 3) -> list[dict[str, Any]]:
        tokens = [t for t in re.findall(r"[A-Za-z0-9_]+", question.lower()) if len(t) > 2]
        scored: list[tuple[int, dict[str, Any]]] = []
        for chunk in chunks:
            lowered = chunk["text"].lower()
            score = sum(lowered.count(token) for token in tokens)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    return {"chunks": chunks, "page_count": len(reader.pages), "query": query}


def extract_images_from_pdf(path: str, output_dir: str | None = None) -> list[str]:
    if PdfReader is None:
        return []
    pdf_path = Path(path).resolve()
    if not pdf_path.exists():
        return []
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return []

    out_base = Path(output_dir).resolve() if output_dir else (pdf_path.parent / f"{pdf_path.stem}_images")
    out_base.mkdir(parents=True, exist_ok=True)

    results: list[str] = []
    for page_index, page in enumerate(reader.pages):
        images = getattr(page, "images", [])
        for image_index, image_file in enumerate(images):
            raw = getattr(image_file, "data", None)
            if not raw:
                continue
            ext = Path(getattr(image_file, "name", f"p{page_index}_img{image_index}.bin")).suffix or ".bin"
            out_path = out_base / f"page_{page_index + 1}_image_{image_index + 1}{ext}"
            try:
                out_path.write_bytes(raw)
                results.append(str(out_path))
            except OSError:
                continue
    return results


def _read_pdf_text(pdf_report_path: str | None) -> str:
    if not pdf_report_path:
        return ""
    parsed = ingest_pdf(pdf_report_path)
    return "\n".join(chunk["text"] for chunk in parsed["chunks"])


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


def investigate_repository(repo_path: str) -> RepoInvestigatorEvidence:
    graph_analysis = analyze_graph_structure(repo_path)
    git_data = extract_git_history(repo_path)

    state_protocol = ProtocolResult(
        protocol="State Structure",
        passed=graph_analysis["has_typed_state"],
        summary=(
            f"Found typed state schemas: {', '.join(graph_analysis['typed_schema_locations'])}"
            if graph_analysis["has_typed_state"]
            else "Missing typed state schemas in src/state.py or src/graph.py."
        ),
    )
    graph_protocol = ProtocolResult(
        protocol="Graph Wiring",
        passed=graph_analysis["is_parallel_wired"],
        summary=(
            f"Detected fan-out from: {', '.join(graph_analysis['fan_out_sources'])}"
            if graph_analysis["is_parallel_wired"]
            else "No AST-verified fan-out edge pattern detected from add_edge calls."
        ),
    )
    git_protocol = ProtocolResult(
        protocol="Git Narrative",
        passed=git_data["classification"] == "ATOMIC",
        summary=git_data["summary"],
    )

    commits: list[GitCommitRecord] = git_data["commits"]
    return RepoInvestigatorEvidence(
        state_structure=state_protocol,
        graph_wiring=graph_protocol,
        git_narrative=git_protocol,
        fan_out_sources=graph_analysis["fan_out_sources"],
        typed_schema_locations=graph_analysis["typed_schema_locations"],
        git_commit_count=len(commits),
        git_history_classification=git_data["classification"],
        git_timeline=commits,
    )


def analyze_documentation(repo_path: str, pdf_report_path: str | None) -> DocAnalystEvidence:
    root = Path(repo_path).resolve()
    pdf_corpus = ingest_pdf(pdf_report_path or "")
    dialectical_chunks = pdf_corpus["query"]("What does the report say about Dialectical Synthesis?")
    combined_pdf = "\n".join(chunk["text"] for chunk in dialectical_chunks) if dialectical_chunks else _read_pdf_text(pdf_report_path)
    corpus = f"{_read_markdown_corpus(root)}\n{combined_pdf}"
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
    image_paths = extract_images_from_pdf(pdf_report_path or "")
    lowered = corpus.lower()

    has_detective = "detective" in lowered
    has_judge = "judge" in lowered
    has_aggregation = "aggregation" in lowered or "evidence aggregation" in lowered
    has_synthesis = "synthesis" in lowered
    has_parallel = "parallel" in lowered or "fan-out" in lowered

    if has_detective and has_judge and has_aggregation and has_synthesis and has_parallel:
        classification = "COURTROOM_PARALLEL"
        passed = True
    elif diagram_lines or image_paths:
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
        diagram_sources=(diagram_lines + image_paths)[:20],
    )
