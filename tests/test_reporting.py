from automaton_bench.models import (
    AuditReport,
    CriterionVerdict,
    FinalVerdict,
    ForensicEvidence,
    RemediationAction,
    VerdictLabel,
)
from automaton_bench.reporting import build_markdown_report


def test_markdown_top_level_structure_order() -> None:
    report = AuditReport(
        evidence=ForensicEvidence(repository_path="repo"),
        judge_opinions=[],
        final_verdict=FinalVerdict(
            label=VerdictLabel.pass_label,
            score=75,
            confidence=0.8,
            consensus_summary=["summary"],
            criterion_verdicts=[CriterionVerdict(criterion="Artifact Integrity", final_score_1_to_5=3, ruling="r")],
            dissents=[],
            remediation_plan=[RemediationAction(file_path="README.md", instruction="fix docs")],
        ),
    )
    md = build_markdown_report(report)
    exec_idx = md.find("## Executive Summary")
    crit_idx = md.find("## Criterion Breakdown")
    rem_idx = md.find("## Remediation Plan")
    assert -1 not in (exec_idx, crit_idx, rem_idx)
    assert exec_idx < crit_idx < rem_idx
