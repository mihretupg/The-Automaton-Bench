from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Iterable

from automaton_bench.constitution import load_conflict_rules
from automaton_bench.models import (
    CriterionVerdict,
    DissentNote,
    FinalVerdict,
    ForensicEvidence,
    JudgeOpinion,
    RemediationAction,
    VerdictLabel,
)


def _label_from_score(score: int) -> VerdictLabel:
    if score >= 85:
        return VerdictLabel.exceptional
    if score >= 70:
        return VerdictLabel.pass_label
    if score >= 50:
        return VerdictLabel.needs_work
    return VerdictLabel.fail


def _has_confirmed_security_vulnerability(evidence: ForensicEvidence) -> bool:
    lowered = " ".join(evidence.findings).lower()
    return "security vulnerability" in lowered or "unsanitized" in lowered


def _score_lookup(opinions: list[JudgeOpinion], criterion: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for opinion in opinions:
        for item in opinion.criterion_opinions:
            if item.criterion == criterion:
                scores[opinion.judge_name] = item.score_1_to_5
                break
    return scores


def _resolve_bool_expr(evidence: ForensicEvidence, expr: str) -> bool:
    if expr.endswith("_non_empty"):
        field_name = expr.replace("_non_empty", "")
        value = getattr(evidence, field_name, [])
        return bool(value)
    if ">=" in expr:
        field, raw = expr.split(">=", 1)
        value = getattr(evidence, field, 0)
        return float(value) >= float(raw)
    if ">" in expr:
        field, raw = expr.split(">", 1)
        value = getattr(evidence, field, 0)
        return float(value) > float(raw)
    parts = expr.split(".")
    current: Any = evidence
    for part in parts:
        current = getattr(current, part, None)
        if current is None:
            return False
    return bool(current)


def _conflict_re_evaluate(
    evidence: ForensicEvidence,
    criterion: str,
    conflict_rules: dict[str, Any],
) -> tuple[int, str] | None:
    criteria_cfg = conflict_rules.get("criteria", {})
    if criterion not in criteria_cfg:
        return None
    cfg = criteria_cfg[criterion]
    checks: list[str] = cfg.get("checks", [])
    if not checks:
        return None
    results = [_resolve_bool_expr(evidence, check) for check in checks]
    if all(results):
        score = int(cfg.get("score_if_all_true", 5))
    elif any(results):
        score = int(cfg.get("score_if_any_true", 3))
    else:
        score = int(cfg.get("score_if_none_true", 1))
    rationale = str(cfg.get("rationale", "Conflict re-evaluation applied."))
    return max(1, min(5, score)), rationale


def _rule_based_criterion_score(
    evidence: ForensicEvidence,
    criterion: str,
    scores: dict[str, int],
    conflict_rules: dict[str, Any],
) -> tuple[int, list[str]]:
    prosecutor = scores.get("Prosecutor", 1)
    defense = scores.get("Defense", 1)
    techlead = scores.get("TechLead", 1)
    dissents: list[str] = []

    if criterion == "LangGraph Architecture" and techlead >= 3:
        final = round((prosecutor * 0.2) + (defense * 0.2) + (techlead * 0.6))
        dissents.append("Tech Lead carried higher weight due to modular/workable architecture assessment.")
    else:
        final = round(mean([prosecutor, defense, techlead]))

    variance = max(scores.values(), default=1) - min(scores.values(), default=1)
    threshold = int(conflict_rules.get("variance_threshold", 2))
    if variance > threshold:
        re_eval = _conflict_re_evaluate(evidence, criterion, conflict_rules)
        if re_eval is not None:
            final, rationale = re_eval
            dissents.append(
                f"Conflict variance {variance} exceeded threshold {threshold}; re-evaluated with constitution rules. {rationale}"
            )

    if criterion == "Judicial Nuance":
        defense_claims_deep = defense >= 5
        no_pdf_evidence = not evidence.pdf_report_path or evidence.pdf_text_char_count < 120
        if defense_claims_deep and no_pdf_evidence:
            final = round(mean([prosecutor, techlead]))
            dissents.append(
                "Defense claim of deep metacognition overruled: no sufficient PDF evidence provided."
            )

    if _has_confirmed_security_vulnerability(evidence):
        if final > 3:
            final = 3
        dissents.append("Security Rule applied: confirmed vulnerability caps criterion score at 3.")

    final = max(1, min(5, final))
    return final, dissents


def _criterion_to_100(score_1_to_5: int) -> int:
    return round((score_1_to_5 / 5) * 100)


def _build_file_level_remediation(opinions: list[JudgeOpinion]) -> list[RemediationAction]:
    actions: list[RemediationAction] = []
    seen: set[tuple[str, str]] = set()
    for opinion in opinions:
        for item in opinion.remediation:
            text = item.lower()
            file_path = "README.md"
            if "ci" in text or "workflow" in text:
                file_path = ".github/workflows/ci.yml"
            elif "security" in text or "dependency scanning" in text:
                file_path = "SECURITY.md"
            elif "type hint" in text or "typed state" in text:
                file_path = "src/state.py"
            elif "parallel fan-out" in text or "graph" in text:
                file_path = "src/graph.py"
            elif "test" in text:
                file_path = "tests/test_graph.py"
            elif "citation" in text or "hallucinated" in text:
                file_path = "README.md"
            key = (file_path, item)
            if key not in seen:
                actions.append(RemediationAction(file_path=file_path, instruction=item))
                seen.add(key)
    if not actions:
        actions.append(
            RemediationAction(
                file_path="README.md",
                instruction="No critical remediation required; add regression checks for stability.",
            )
        )
    return actions


def synthesize_verdict(opinions: Iterable[JudgeOpinion], evidence: ForensicEvidence) -> FinalVerdict:
    conflict_rules = load_conflict_rules()
    opinion_list = list(opinions)
    criteria = sorted({item.criterion for opinion in opinion_list for item in opinion.criterion_opinions})

    criterion_verdicts: list[CriterionVerdict] = []
    dissent_notes: list[DissentNote] = []
    criterion_scores: list[int] = []
    for criterion in criteria:
        scores = _score_lookup(opinion_list, criterion)
        final_score, dissent = _rule_based_criterion_score(evidence, criterion, scores, conflict_rules)
        criterion_scores.append(final_score)
        ruling = (
            f"Prosecutor={scores.get('Prosecutor', 1)}, "
            f"Defense={scores.get('Defense', 1)}, "
            f"TechLead={scores.get('TechLead', 1)}."
        )
        criterion_verdicts.append(
            CriterionVerdict(
                criterion=criterion,
                final_score_1_to_5=final_score,
                ruling=ruling,
            )
        )
        if dissent:
            dissent_notes.append(DissentNote(criterion=criterion, summary=" ".join(dissent)))

    score_100 = round(mean([_criterion_to_100(s) for s in criterion_scores])) if criterion_scores else 0
    dispersion = pstdev([_criterion_to_100(s) for s in criterion_scores]) if len(criterion_scores) > 1 else 0.0
    confidence = round(max(0.2, min(1.0, 1 - (dispersion / 50))), 2)

    summary = [
        f"Supreme Court synthesized {len(criteria)} criterion rulings from 3 judicial personas.",
        "Deterministic conflict resolution rules were applied when judicial variance exceeded constitutional threshold.",
    ]

    return FinalVerdict(
        label=_label_from_score(score_100),
        score=score_100,
        confidence=confidence,
        consensus_summary=summary,
        criterion_verdicts=criterion_verdicts,
        dissents=dissent_notes,
        remediation_plan=_build_file_level_remediation(opinion_list),
    )
