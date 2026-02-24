from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from automaton_bench.forensics import collect_forensic_evidence
from automaton_bench.judges import JUDGE_PROFILES, generate_judge_opinion
from automaton_bench.models import AuditReport, ForensicEvidence, JudgeOpinion
from automaton_bench.synthesis import synthesize_verdict


class AuditState(TypedDict, total=False):
    repo_path: str
    evidence: ForensicEvidence
    judge_opinions: Annotated[list[JudgeOpinion], operator.add]
    final_report: AuditReport


def forensic_node(state: AuditState) -> AuditState:
    return {"evidence": collect_forensic_evidence(state["repo_path"])}


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


def run_audit(repo_path: str) -> AuditReport:
    app = build_graph()
    result: AuditState = app.invoke({"repo_path": repo_path, "judge_opinions": []})
    return result["final_report"]

