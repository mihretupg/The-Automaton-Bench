from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Iterable

from src.state import AgentState, AuditReport, CriterionResult, JudicialOpinion


def _security_override(opinions: list[JudicialOpinion], evidences: dict) -> list[JudicialOpinion]:
    merged = " ".join(str(item.content) for items in evidences.values() for item in items).lower()
    if "unsanitized" not in merged and "security vulnerability" not in merged:
        return opinions
    fixed: list[JudicialOpinion] = []
    for op in opinions:
        fixed.append(op.model_copy(update={"score": min(op.score, 3)}))
    return fixed


def _fact_supremacy(opinions: list[JudicialOpinion], evidences: dict) -> list[JudicialOpinion]:
    has_pdf_signal = any(
        "dialectical" in (item.content or "").lower()
        for items in evidences.values()
        for item in items
    )
    if has_pdf_signal:
        return opinions
    fixed: list[JudicialOpinion] = []
    for op in opinions:
        if op.judge == "Defense" and op.criterion_id in {"judicial_nuance", "cross_evidence_fidelity"}:
            fixed.append(op.model_copy(update={"score": min(op.score, 3)}))
        else:
            fixed.append(op)
    return fixed


def _build_criterion_results(opinions: Iterable[JudicialOpinion], synthesis_rules: dict) -> list[CriterionResult]:
    grouped: dict[str, list[JudicialOpinion]] = defaultdict(list)
    for opinion in opinions:
        grouped[opinion.criterion_id].append(opinion)

    results: list[CriterionResult] = []
    for criterion_id, items in grouped.items():
        scores = [item.score for item in items]
        variance = max(scores) - min(scores) if scores else 0
        dissent = None
        if variance > 2:
            dissent = (
                synthesis_rules.get(
                    "dissent_requirement",
                    "High variance detected (>2). Re-evaluated evidence to enforce deterministic ruling.",
                )
            )
        final_score = round(mean(scores)) if scores else 1
        remediation = "Update related source files and tests for this criterion."
        results.append(
            CriterionResult(
                dimension_id=criterion_id,
                dimension_name=criterion_id.replace("_", " ").title(),
                final_score=max(1, min(5, final_score)),
                judge_opinions=items,
                dissent_summary=dissent,
                remediation=remediation,
            )
        )
    return sorted(results, key=lambda item: item.dimension_id)


def chief_justice_node(state: AgentState) -> AgentState:
    synthesis_rules = state.get("synthesis_rules", {})
    opinions = state.get("opinions", [])
    opinions = _security_override(opinions, state.get("evidences", {}))
    opinions = _fact_supremacy(opinions, state.get("evidences", {}))
    criteria = _build_criterion_results(opinions, synthesis_rules)
    overall = round(mean([c.final_score for c in criteria]), 2) if criteria else 1.0
    report = AuditReport(
        repo_url=state.get("repo_url", ""),
        executive_summary=(
            "Deterministic Supreme Court synthesis completed with conflict resolution rules applied."
        ),
        overall_score=overall,
        criteria=criteria,
        remediation_plan="Apply criterion remediation in priority order, then rerun the graph.",
    )
    return {"final_report": report}
