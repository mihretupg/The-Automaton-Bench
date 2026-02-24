from __future__ import annotations

import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - dependency/runtime compatibility guard
    END = "END"
    START = "START"
    StateGraph = None

from automaton_bench.forensics import collect_forensic_evidence
from automaton_bench.intake import resolve_repository_input
from automaton_bench.judges import JUDGE_PROFILES, generate_judge_opinion
from automaton_bench.models import AuditReport, ForensicEvidence, JudgeOpinion
from automaton_bench.synthesis import synthesize_verdict


class AuditState(TypedDict, total=False):
    repo_path: str
    repo_source_url: str | None
    pdf_report_path: str | None
    evidence: ForensicEvidence
    judge_opinions: Annotated[list[JudgeOpinion], operator.add]
    final_report: AuditReport


def forensic_node(state: AuditState) -> AuditState:
    return {
        "evidence": collect_forensic_evidence(
            state["repo_path"],
            repository_source_url=state.get("repo_source_url"),
            pdf_report_path=state.get("pdf_report_path"),
        )
    }


def prosecutor_node(state: AuditState) -> AuditState:
    return {"judge_opinions": [generate_judge_opinion(state["evidence"], JUDGE_PROFILES[0])]}


def defense_node(state: AuditState) -> AuditState:
    return {"judge_opinions": [generate_judge_opinion(state["evidence"], JUDGE_PROFILES[1])]}


def techlead_node(state: AuditState) -> AuditState:
    return {"judge_opinions": [generate_judge_opinion(state["evidence"], JUDGE_PROFILES[2])]}


def chief_justice_node(state: AuditState) -> AuditState:
    verdict = synthesize_verdict(state["judge_opinions"])
    return {
        "final_report": AuditReport(
            evidence=state["evidence"],
            judge_opinions=state["judge_opinions"],
            final_verdict=verdict,
        )
    }


def build_graph():
    if StateGraph is None:
        return _FallbackGraph()

    builder = StateGraph(AuditState)
    builder.add_node("forensics", forensic_node)
    builder.add_node("prosecutor", prosecutor_node)
    builder.add_node("defense", defense_node)
    builder.add_node("techlead", techlead_node)
    builder.add_node("chief_justice", chief_justice_node)

    builder.add_edge(START, "forensics")
    builder.add_edge("forensics", "prosecutor")
    builder.add_edge("forensics", "defense")
    builder.add_edge("forensics", "techlead")
    builder.add_edge("prosecutor", "chief_justice")
    builder.add_edge("defense", "chief_justice")
    builder.add_edge("techlead", "chief_justice")
    builder.add_edge("chief_justice", END)

    return builder.compile()


class _FallbackGraph:
    """Minimal in-process fallback when LangGraph is unavailable."""

    def invoke(self, state: AuditState) -> AuditState:
        next_state = dict(state)
        next_state.update(forensic_node(next_state))
        opinions: list[JudgeOpinion] = []
        opinions.extend(prosecutor_node(next_state)["judge_opinions"])
        opinions.extend(defense_node(next_state)["judge_opinions"])
        opinions.extend(techlead_node(next_state)["judge_opinions"])
        next_state["judge_opinions"] = opinions
        next_state.update(chief_justice_node(next_state))
        return next_state


def run_audit(repository: str, pdf_report_path: str | None = None) -> AuditReport:
    app = build_graph()
    resolved = resolve_repository_input(repository)
    try:
        result: AuditState = app.invoke(
            {
                "repo_path": resolved.repository_path,
                "repo_source_url": resolved.repository_source_url,
                "pdf_report_path": pdf_report_path,
                "judge_opinions": [],
            }
        )
        return result["final_report"]
    finally:
        if resolved.temp_dir is not None:
            resolved.temp_dir.cleanup()
