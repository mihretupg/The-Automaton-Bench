from __future__ import annotations

import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - dependency/runtime compatibility guard
    END = "END"
    START = "START"
    StateGraph = None

from automaton_bench.detectives import analyze_documentation, inspect_diagrams, investigate_repository
from automaton_bench.forensics import collect_forensic_evidence
from automaton_bench.intake import resolve_repository_input
from automaton_bench.judges import JUDGE_PROFILES, generate_judge_opinion
from automaton_bench.models import (
    AuditReport,
    DocAnalystEvidence,
    ForensicEvidence,
    JudgeOpinion,
    RepoInvestigatorEvidence,
    VisionInspectorEvidence,
)
from automaton_bench.synthesis import synthesize_verdict


class DetectiveState(TypedDict, total=False):
    repo_path: str
    repo_source_url: str | None
    pdf_report_path: str | None
    evidence: ForensicEvidence
    repo_investigator: RepoInvestigatorEvidence
    doc_analyst: DocAnalystEvidence
    vision_inspector: VisionInspectorEvidence


class AuditState(TypedDict, total=False):
    repo_path: str
    repo_source_url: str | None
    pdf_report_path: str | None
    evidence: ForensicEvidence
    judge_opinions: Annotated[list[JudgeOpinion], operator.add]
    final_report: AuditReport


def base_forensics_node(state: DetectiveState) -> DetectiveState:
    return {
        "evidence": collect_forensic_evidence(
            state["repo_path"],
            repository_source_url=state.get("repo_source_url"),
            pdf_report_path=state.get("pdf_report_path"),
        )
    }


def repo_investigator_node(state: DetectiveState) -> DetectiveState:
    return {"repo_investigator": investigate_repository(state["repo_path"])}


def doc_analyst_node(state: DetectiveState) -> DetectiveState:
    return {
        "doc_analyst": analyze_documentation(
            state["repo_path"],
            pdf_report_path=state.get("pdf_report_path"),
        )
    }


def vision_inspector_node(state: DetectiveState) -> DetectiveState:
    return {
        "vision_inspector": inspect_diagrams(
            state["repo_path"],
            pdf_report_path=state.get("pdf_report_path"),
        )
    }


def detective_aggregation_node(state: DetectiveState) -> DetectiveState:
    evidence = state["evidence"]
    repo = state["repo_investigator"]
    doc = state["doc_analyst"]
    vision = state["vision_inspector"]
    evidence.repo_investigator = repo
    evidence.doc_analyst = doc
    evidence.vision_inspector = vision

    protocol_checks = [
        repo.state_structure,
        repo.graph_wiring,
        repo.git_narrative,
        doc.citation_check,
        doc.concept_verification,
        vision.flow_analysis,
    ]
    for check in protocol_checks:
        if not check.passed:
            evidence.findings.append(f"{check.protocol}: {check.summary}")
    return {"evidence": evidence}


def build_detective_graph():
    if StateGraph is None:
        return _FallbackDetectiveGraph()

    builder = StateGraph(DetectiveState)
    builder.add_node("base_forensics", base_forensics_node)
    builder.add_node("repo_investigator", repo_investigator_node)
    builder.add_node("doc_analyst", doc_analyst_node)
    builder.add_node("vision_inspector", vision_inspector_node)
    builder.add_node("detective_aggregation", detective_aggregation_node)

    builder.add_edge(START, "base_forensics")
    builder.add_edge("base_forensics", "repo_investigator")
    builder.add_edge("base_forensics", "doc_analyst")
    builder.add_edge("base_forensics", "vision_inspector")
    builder.add_edge("repo_investigator", "detective_aggregation")
    builder.add_edge("doc_analyst", "detective_aggregation")
    builder.add_edge("vision_inspector", "detective_aggregation")
    builder.add_edge("detective_aggregation", END)
    return builder.compile()


def detective_layer_node(state: AuditState) -> AuditState:
    app = build_detective_graph()
    detective_state: DetectiveState = app.invoke(
        {
            "repo_path": state["repo_path"],
            "repo_source_url": state.get("repo_source_url"),
            "pdf_report_path": state.get("pdf_report_path"),
        }
    )
    return {"evidence": detective_state["evidence"]}


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
        return _FallbackAuditGraph()

    builder = StateGraph(AuditState)
    builder.add_node("detective_layer", detective_layer_node)
    builder.add_node("prosecutor", prosecutor_node)
    builder.add_node("defense", defense_node)
    builder.add_node("techlead", techlead_node)
    builder.add_node("chief_justice", chief_justice_node)

    builder.add_edge(START, "detective_layer")
    builder.add_edge("detective_layer", "prosecutor")
    builder.add_edge("detective_layer", "defense")
    builder.add_edge("detective_layer", "techlead")
    builder.add_edge("prosecutor", "chief_justice")
    builder.add_edge("defense", "chief_justice")
    builder.add_edge("techlead", "chief_justice")
    builder.add_edge("chief_justice", END)
    return builder.compile()


class _FallbackDetectiveGraph:
    def invoke(self, state: DetectiveState) -> DetectiveState:
        next_state = dict(state)
        next_state.update(base_forensics_node(next_state))
        next_state.update(repo_investigator_node(next_state))
        next_state.update(doc_analyst_node(next_state))
        next_state.update(vision_inspector_node(next_state))
        next_state.update(detective_aggregation_node(next_state))
        return next_state


class _FallbackAuditGraph:
    def invoke(self, state: AuditState) -> AuditState:
        next_state = dict(state)
        next_state.update(detective_layer_node(next_state))
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
