from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - runtime compatibility guard
    END = "END"
    START = "START"
    StateGraph = None

from src.constitution import build_judicial_logic, load_constitution, split_dimensions_by_target
from src.nodes.detectives import (
    doc_analyst_node,
    evidence_aggregator_node,
    repo_investigator_node,
    vision_inspector_node,
)
from src.nodes.judges import defense_node, prosecutor_node, techlead_node
from src.nodes.justice import chief_justice_node
from src.state import AgentState
from src.tools.repo_tools import clone_repo_sandboxed, is_github_url


def _resolve_repo(repo_url_or_path: str) -> tuple[str, TemporaryDirectory[str] | None]:
    if is_github_url(repo_url_or_path):
        repo_path, temp_dir = clone_repo_sandboxed(repo_url_or_path)
        return repo_path, temp_dir
    return str(Path(repo_url_or_path).resolve()), None


def _has_errors(state: AgentState) -> str:
    return "error" if state.get("errors") else "ok"


def context_builder_node(state: AgentState) -> AgentState:
    constitution = load_constitution()
    split = split_dimensions_by_target(constitution)
    return {
        "constitution": constitution,
        "rubric_dimensions": constitution.get("dimensions", []),
        "repo_dimensions": split["github_repo"],
        "pdf_dimensions": split["pdf_report"],
        "image_dimensions": split["pdf_images"],
        "judicial_logic": build_judicial_logic(constitution),
        "synthesis_rules": constitution.get("synthesis_rules", {}),
    }


def build_detective_graph():
    if StateGraph is None:
        return _FallbackDetectiveGraph()
    builder = StateGraph(AgentState)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("repo_investigator", repo_investigator_node)
    builder.add_node("doc_analyst", doc_analyst_node)
    builder.add_node("vision_inspector", vision_inspector_node)
    builder.add_node("evidence_aggregator", evidence_aggregator_node)

    builder.add_edge(START, "context_builder")
    builder.add_edge("context_builder", "repo_investigator")
    builder.add_edge("context_builder", "doc_analyst")
    builder.add_edge("context_builder", "vision_inspector")
    builder.add_edge("repo_investigator", "evidence_aggregator")
    builder.add_edge("doc_analyst", "evidence_aggregator")
    builder.add_edge("vision_inspector", "evidence_aggregator")
    builder.add_edge("evidence_aggregator", END)
    return builder.compile()


def build_full_graph():
    if StateGraph is None:
        return _FallbackFullGraph()
    builder = StateGraph(AgentState)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("repo_investigator", repo_investigator_node)
    builder.add_node("doc_analyst", doc_analyst_node)
    builder.add_node("vision_inspector", vision_inspector_node)
    builder.add_node("evidence_aggregator", evidence_aggregator_node)
    builder.add_node("prosecutor", prosecutor_node)
    builder.add_node("defense", defense_node)
    builder.add_node("techlead", techlead_node)
    builder.add_node("chief_justice", chief_justice_node)

    builder.add_edge(START, "context_builder")
    builder.add_edge("context_builder", "repo_investigator")
    builder.add_edge("context_builder", "doc_analyst")
    builder.add_edge("context_builder", "vision_inspector")
    builder.add_edge("repo_investigator", "evidence_aggregator")
    builder.add_edge("doc_analyst", "evidence_aggregator")
    builder.add_edge("vision_inspector", "evidence_aggregator")

    builder.add_conditional_edges(
        "evidence_aggregator",
        _has_errors,
        {"error": END, "ok": "prosecutor"},
    )
    builder.add_edge("evidence_aggregator", "defense")
    builder.add_edge("evidence_aggregator", "techlead")

    builder.add_edge("prosecutor", "chief_justice")
    builder.add_edge("defense", "chief_justice")
    builder.add_edge("techlead", "chief_justice")
    builder.add_conditional_edges(
        "chief_justice",
        _has_errors,
        {"error": END, "ok": END},
    )
    return builder.compile()


def render_markdown_report(state: AgentState) -> str:
    report = state["final_report"]
    lines = [
        "# Audit Report",
        "",
        "## Executive Summary",
        f"- Repo: `{report.repo_url}`",
        f"- Overall Score: `{report.overall_score}/5`",
        f"- {report.executive_summary}",
        "",
        "## Criterion Breakdown",
    ]
    for criterion in report.criteria:
        lines.append(f"### {criterion.dimension_name} ({criterion.final_score}/5)")
        for op in criterion.judge_opinions:
            lines.append(f"- {op.judge}: {op.score}/5 - {op.argument}")
            if op.cited_evidence:
                lines.append(f"  - Cited evidence: {', '.join(op.cited_evidence)}")
        if criterion.dissent_summary:
            lines.append(f"- Dissent: {criterion.dissent_summary}")
        lines.append(f"- Remediation: {criterion.remediation}")
        lines.append("")

    lines.extend(["## Remediation Plan", report.remediation_plan, ""])
    return "\n".join(lines)


def run_detective_graph(repo_url_or_path: str, pdf_path: str) -> AgentState:
    repo_path, temp_dir = _resolve_repo(repo_url_or_path)
    graph = build_detective_graph()
    try:
        return graph.invoke(
            {
                "repo_url": repo_url_or_path,
                "repo_path": repo_path,
                "pdf_path": pdf_path,
                "constitution": {},
                "rubric_dimensions": [],
                "repo_dimensions": [],
                "pdf_dimensions": [],
                "image_dimensions": [],
                "judicial_logic": "",
                "synthesis_rules": {},
                "evidences": {},
                "opinions": [],
                "criterion_results": [],
                "errors": [],
            }
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def run_full_graph(repo_url_or_path: str, pdf_path: str, output_markdown: str | None = None) -> AgentState:
    repo_path, temp_dir = _resolve_repo(repo_url_or_path)
    graph = build_full_graph()
    try:
        state: AgentState = graph.invoke(
            {
                "repo_url": repo_url_or_path,
                "repo_path": repo_path,
                "pdf_path": pdf_path,
                "constitution": {},
                "rubric_dimensions": [],
                "repo_dimensions": [],
                "pdf_dimensions": [],
                "image_dimensions": [],
                "judicial_logic": "",
                "synthesis_rules": {},
                "evidences": {},
                "opinions": [],
                "criterion_results": [],
                "errors": [],
            }
        )
        if output_markdown and state.get("final_report"):
            out = Path(output_markdown).resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_markdown_report(state), encoding="utf-8")
        return state
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


class _FallbackDetectiveGraph:
    def invoke(self, state: AgentState) -> AgentState:
        next_state = dict(state)
        next_state.update(context_builder_node(next_state))
        next_state.update(repo_investigator_node(next_state))
        next_state.update(doc_analyst_node(next_state))
        next_state.update(vision_inspector_node(next_state))
        next_state.update(evidence_aggregator_node(next_state))
        return next_state


class _FallbackFullGraph:
    def invoke(self, state: AgentState) -> AgentState:
        next_state = dict(state)
        next_state.update(context_builder_node(next_state))
        next_state.update(repo_investigator_node(next_state))
        next_state.update(doc_analyst_node(next_state))
        next_state.update(vision_inspector_node(next_state))
        next_state.update(evidence_aggregator_node(next_state))
        if next_state.get("errors"):
            return next_state
        opinions = []
        errors = list(next_state.get("errors", []))
        for node_fn in (prosecutor_node, defense_node, techlead_node):
            node_out = node_fn(next_state)
            opinions.extend(node_out.get("opinions", []))
            errors.extend(node_out.get("errors", []))
        next_state["opinions"] = opinions
        if errors:
            next_state["errors"] = errors
        next_state.update(chief_justice_node(next_state))
        return next_state
