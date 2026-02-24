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
from automaton_bench.constitution import load_rubric_dimensions
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
from automaton_bench.state import AgentState, Evidence, JudicialOpinion
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
    rubric_dimensions: list[dict]
    evidence: ForensicEvidence
    judge_opinions: Annotated[list[JudgeOpinion], operator.add]
    final_report: AuditReport
    evidences: Annotated[dict[str, list[Evidence]], operator.ior]
    opinions: Annotated[list[JudicialOpinion], operator.add]


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


def evidence_aggregator_node(state: DetectiveState) -> DetectiveState:
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


def _detective_evidence_map(state: DetectiveState) -> dict[str, list[Evidence]]:
    repo = state["repo_investigator"]
    doc = state["doc_analyst"]
    vision = state["vision_inspector"]
    return {
        "RepoInvestigator": [
            Evidence(
                goal="State Structure",
                found=repo.state_structure.passed,
                content=repo.state_structure.summary,
                location="src/state.py|src/graph.py",
                rationale=repo.state_structure.summary,
                confidence=0.9 if repo.state_structure.passed else 0.5,
            ),
            Evidence(
                goal="Graph Wiring",
                found=repo.graph_wiring.passed,
                content=repo.graph_wiring.summary,
                location="graph AST",
                rationale=repo.graph_wiring.summary,
                confidence=0.9 if repo.graph_wiring.passed else 0.5,
            ),
            Evidence(
                goal="Git Narrative",
                found=repo.git_narrative.passed,
                content=repo.git_narrative.summary,
                location="git log",
                rationale=repo.git_narrative.summary,
                confidence=0.85 if repo.git_narrative.passed else 0.5,
            ),
        ],
        "DocAnalyst": [
            Evidence(
                goal="Citation Check",
                found=doc.citation_check.passed,
                content=doc.citation_check.summary,
                location="README.md|PDF",
                rationale=doc.citation_check.summary,
                confidence=0.85 if doc.citation_check.passed else 0.45,
            ),
            Evidence(
                goal="Concept Verification",
                found=doc.concept_verification.passed,
                content=doc.concept_verification.summary,
                location="README.md|PDF",
                rationale=doc.concept_verification.summary,
                confidence=0.8 if doc.concept_verification.passed else 0.4,
            ),
        ],
        "VisionInspector": [
            Evidence(
                goal="Flow Analysis",
                found=vision.flow_analysis.passed,
                content=vision.flow_analysis.summary,
                location="architecture diagrams",
                rationale=vision.flow_analysis.summary,
                confidence=0.8 if vision.flow_analysis.passed else 0.4,
            )
        ],
    }


def build_detective_graph():
    if StateGraph is None:
        return _FallbackDetectiveGraph()

    builder = StateGraph(DetectiveState)
    builder.add_node("base_forensics", base_forensics_node)
    builder.add_node("repo_investigator", repo_investigator_node)
    builder.add_node("doc_analyst", doc_analyst_node)
    builder.add_node("vision_inspector", vision_inspector_node)
    builder.add_node("evidence_aggregator", evidence_aggregator_node)

    builder.add_edge(START, "base_forensics")
    builder.add_edge("base_forensics", "repo_investigator")
    builder.add_edge("base_forensics", "doc_analyst")
    builder.add_edge("base_forensics", "vision_inspector")
    builder.add_edge("repo_investigator", "evidence_aggregator")
    builder.add_edge("doc_analyst", "evidence_aggregator")
    builder.add_edge("vision_inspector", "evidence_aggregator")
    builder.add_edge("evidence_aggregator", END)
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
    return {
        "evidence": detective_state["evidence"],
        "evidences": _detective_evidence_map(detective_state),
    }


def prosecutor_node(state: AuditState) -> AuditState:
    opinion = generate_judge_opinion(state["evidence"], JUDGE_PROFILES[0], state["rubric_dimensions"])
    judicial = [
        JudicialOpinion(
            judge="Prosecutor",
            criterion_id=item.criterion,
            score=item.score_1_to_5,
            argument=item.reasoning,
            cited_evidence=["RepoInvestigator", "DocAnalyst", "VisionInspector"],
        )
        for item in opinion.criterion_opinions
    ]
    return {"judge_opinions": [opinion], "opinions": judicial}


def defense_node(state: AuditState) -> AuditState:
    opinion = generate_judge_opinion(state["evidence"], JUDGE_PROFILES[1], state["rubric_dimensions"])
    judicial = [
        JudicialOpinion(
            judge="Defense",
            criterion_id=item.criterion,
            score=item.score_1_to_5,
            argument=item.reasoning,
            cited_evidence=["RepoInvestigator", "DocAnalyst", "VisionInspector"],
        )
        for item in opinion.criterion_opinions
    ]
    return {"judge_opinions": [opinion], "opinions": judicial}


def techlead_node(state: AuditState) -> AuditState:
    opinion = generate_judge_opinion(state["evidence"], JUDGE_PROFILES[2], state["rubric_dimensions"])
    judicial = [
        JudicialOpinion(
            judge="TechLead",
            criterion_id=item.criterion,
            score=item.score_1_to_5,
            argument=item.reasoning,
            cited_evidence=["RepoInvestigator", "DocAnalyst", "VisionInspector"],
        )
        for item in opinion.criterion_opinions
    ]
    return {"judge_opinions": [opinion], "opinions": judicial}


def chief_justice_node(state: AuditState) -> AuditState:
    verdict = synthesize_verdict(state["judge_opinions"], state["evidence"])
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
        next_state.update(evidence_aggregator_node(next_state))
        return next_state


class _FallbackAuditGraph:
    def invoke(self, state: AuditState) -> AuditState:
        next_state = dict(state)
        next_state.update(detective_layer_node(next_state))
        opinions: list[JudgeOpinion] = []
        judicial_stream: list[JudicialOpinion] = []
        prosecutor = prosecutor_node(next_state)
        defense = defense_node(next_state)
        techlead = techlead_node(next_state)
        opinions.extend(prosecutor["judge_opinions"])
        judicial_stream.extend(prosecutor["opinions"])
        opinions.extend(defense["judge_opinions"])
        judicial_stream.extend(defense["opinions"])
        opinions.extend(techlead["judge_opinions"])
        judicial_stream.extend(techlead["opinions"])
        next_state["judge_opinions"] = opinions
        next_state["opinions"] = judicial_stream
        next_state.update(chief_justice_node(next_state))
        return next_state


def run_audit(repository: str, pdf_report_path: str | None = None) -> AuditReport:
    app = build_graph()
    rubric_dimensions = load_rubric_dimensions()
    resolved = resolve_repository_input(repository)
    try:
        result: AuditState = app.invoke(
            {
                "repo_url": repository,
                "repo_path": resolved.repository_path,
                "repo_source_url": resolved.repository_source_url,
                "pdf_path": pdf_report_path or "",
                "pdf_report_path": pdf_report_path,
                "rubric_dimensions": rubric_dimensions,
            }
        )
        return result["final_report"]
    finally:
        if resolved.temp_dir is not None:
            resolved.temp_dir.cleanup()
