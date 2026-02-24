from __future__ import annotations

from statistics import mean, pstdev
from typing import Iterable, List

from automaton_bench.models import FinalVerdict, JudgeOpinion, VerdictLabel


def _label_from_score(score: int) -> VerdictLabel:
    if score >= 85:
        return VerdictLabel.exceptional
    if score >= 70:
        return VerdictLabel.pass_label
    if score >= 50:
        return VerdictLabel.needs_work
    return VerdictLabel.fail


def synthesize_verdict(opinions: Iterable[JudgeOpinion]) -> FinalVerdict:
    opinion_list = list(opinions)
    totals = [op.score.total for op in opinion_list]
    score = round(mean(totals)) if totals else 0
    dispersion = pstdev(totals) if len(totals) > 1 else 0.0
    confidence = round(max(0.2, min(1.0, 1 - (dispersion / 25))), 2)

    summary: List[str] = [f"Consensus score from {len(opinion_list)} judges: {score}/100."]
    if dispersion > 8:
        summary.append("High disagreement between judges; manual review advised.")
    else:
        summary.append("Judge consensus is tight and stable.")

    remediation: List[str] = []
    for opinion in opinion_list:
        for fix in opinion.remediation:
            if fix not in remediation:
                remediation.append(fix)

    return FinalVerdict(
        label=_label_from_score(score),
        score=score,
        confidence=confidence,
        consensus_summary=summary,
        remediation_plan=remediation,
    )

