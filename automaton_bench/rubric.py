from __future__ import annotations

from automaton_bench.models import ForensicEvidence, RubricBreakdown


def score_artifact_existence(e: ForensicEvidence) -> int:
    score = 0
    if e.python_files > 0:
        score += 12
    if e.dependency_files:
        score += 7
    if e.docs_present:
        score += 6
    return min(score, 25)


def score_architecture_modularity(e: ForensicEvidence) -> int:
    score = 0
    if e.package_count >= 2:
        score += 10
    elif e.package_count == 1:
        score += 5

    if e.class_count + e.function_count >= 8:
        score += 7
    elif e.class_count + e.function_count >= 3:
        score += 4

    if 0 < e.avg_lines_per_python_file <= 220:
        score += 4
    elif e.avg_lines_per_python_file <= 320:
        score += 2

    if e.type_hinted_function_ratio >= 0.6:
        score += 4
    elif e.type_hinted_function_ratio >= 0.3:
        score += 2

    return min(score, 25)


def score_test_quality(e: ForensicEvidence) -> int:
    if e.python_files == 0:
        return 0
    ratio = e.test_files / max(1, e.python_files)
    if ratio >= 0.5:
        return 20
    if ratio >= 0.25:
        return 14
    if ratio > 0:
        return 8
    return 0


def score_ci_governance(e: ForensicEvidence) -> int:
    score = 0
    if e.ci_present:
        score += 10
    if e.security_docs_present:
        score += 5
    return score


def score_documentation(e: ForensicEvidence) -> int:
    score = 0
    if e.docs_present:
        score += 10
    if any("Architecture" in finding for finding in e.findings):
        score += 2
    if e.dependency_files:
        score += 3
    return min(score, 15)


def score_forensic_rubric(evidence: ForensicEvidence) -> RubricBreakdown:
    return RubricBreakdown(
        artifact_existence=score_artifact_existence(evidence),
        architecture_modularity=score_architecture_modularity(evidence),
        test_quality=score_test_quality(evidence),
        ci_governance=score_ci_governance(evidence),
        documentation=score_documentation(evidence),
    )

