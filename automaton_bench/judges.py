from __future__ import annotations

from dataclasses import dataclass
from typing import List

from automaton_bench.models import (
    ForensicEvidence,
    JudicialCriterionOpinion,
    JudgeOpinion,
    RubricBreakdown,
)


@dataclass(frozen=True)
class JudgeProfile:
    name: str
    lens: str


JUDGE_PROFILES = [
    JudgeProfile(name="Prosecutor", lens="Critical Lens"),
    JudgeProfile(name="Defense", lens="Optimistic Lens"),
    JudgeProfile(name="TechLead", lens="Pragmatic Lens"),
]


CRITERION_TO_BUCKET = [
    ("Artifact Integrity", "artifact_existence", 25),
    ("LangGraph Architecture", "architecture_modularity", 25),
    ("Judicial Nuance", "test_quality", 20),
    ("Engineering Process", "ci_governance", 15),
    ("Cross-Evidence Fidelity", "documentation", 15),
]


def _quantize_score(raw: int) -> int:
    if raw <= 1:
        return 1
    if raw <= 3:
        return 3
    return 5


def _base_signals(e: ForensicEvidence) -> dict[str, bool]:
    return {
        "artifacts_present": e.python_files > 0 and bool(e.dependency_files),
        "parallel_graph": bool(e.repo_investigator and e.repo_investigator.graph_wiring.passed),
        "typed_state": bool(e.repo_investigator and e.repo_investigator.state_structure.passed),
        "git_atomic": bool(e.repo_investigator and e.repo_investigator.git_narrative.passed),
        "citation_clean": bool(e.doc_analyst and e.doc_analyst.citation_check.passed),
        "concept_explained": bool(e.doc_analyst and e.doc_analyst.concept_verification.passed),
        "diagram_parallel": bool(e.vision_inspector and e.vision_inspector.flow_analysis.passed),
        "has_tests": e.test_files > 0,
        "has_ci": e.ci_present,
    }


def _evaluate_criterion(
    e: ForensicEvidence,
    profile: JudgeProfile,
    criterion: str,
) -> tuple[int, str, list[str]]:
    s = _base_signals(e)
    missing: list[str] = []
    raw = 1
    reasoning = ""

    if criterion == "Artifact Integrity":
        if s["artifacts_present"] and e.docs_present:
            raw = 5
            reasoning = "Core artifacts and documentation are present."
        elif s["artifacts_present"]:
            raw = 3
            reasoning = "Core code artifacts exist, but supporting documentation is thin."
            missing.append("Comprehensive repository documentation")
        else:
            raw = 1
            reasoning = "Essential build/runtime artifacts are missing."
            missing.append("Python source and dependency manifest")

    elif criterion == "LangGraph Architecture":
        if s["parallel_graph"] and s["typed_state"]:
            raw = 5
            reasoning = "Graph shows AST-verifiable fan-out with typed state."
        elif s["parallel_graph"] or s["typed_state"]:
            raw = 3
            reasoning = "Graph has partial structure but misses full parallel architecture guarantees."
            if not s["parallel_graph"]:
                missing.append("AST-verifiable parallel fan-out edges")
            if not s["typed_state"]:
                missing.append("Typed state schema")
        else:
            raw = 1
            reasoning = "Graph architecture is linear or weakly specified."
            missing.extend(["Parallel fan-out architecture", "Typed state schema"])

    elif criterion == "Judicial Nuance":
        nuance_signals = sum([s["citation_clean"], s["concept_explained"], s["diagram_parallel"]])
        if nuance_signals >= 3:
            raw = 5
            reasoning = "Evidence supports thesis-antithesis-synthesis style reasoning."
        elif nuance_signals >= 1:
            raw = 3
            reasoning = "Some dialectical structure exists but lacks complete rigor."
            if not s["concept_explained"]:
                missing.append("Concrete explanation of dialectical synthesis execution")
            if not s["diagram_parallel"]:
                missing.append("Diagram that shows detective/judge parallelism")
        else:
            raw = 1
            reasoning = "Judicial reasoning appears generic and not dialectical."
            missing.append("Criterion-level dialectical reasoning outputs")

    elif criterion == "Engineering Process":
        if s["git_atomic"] and s["has_ci"]:
            raw = 5
            reasoning = "History is iterative and operationalized with CI."
        elif s["git_atomic"] or s["has_ci"]:
            raw = 3
            reasoning = "Process quality is mixed; either CI or iterative history is missing."
            if not s["git_atomic"]:
                missing.append("Atomic git narrative with iterative commits")
            if not s["has_ci"]:
                missing.append("Automated CI validation")
        else:
            raw = 1
            reasoning = "Workflow appears monolithic and lacks automation."
            missing.extend(["Atomic commit trail", "CI workflow"])

    elif criterion == "Cross-Evidence Fidelity":
        if s["citation_clean"] and e.pdf_text_char_count >= 120:
            raw = 5
            reasoning = "Document claims are consistent with repository artifacts."
        elif s["citation_clean"] or e.pdf_text_char_count >= 120:
            raw = 3
            reasoning = "Cross-evidence is partially consistent but still fragile."
            if not s["citation_clean"]:
                missing.append("Remove hallucinated file citations")
            if e.pdf_text_char_count < 120:
                missing.append("Readable PDF with extractable technical details")
        else:
            raw = 1
            reasoning = "Evidence trail is unreliable across code and report."
            missing.extend(["Citation consistency", "Readable PDF evidence"])

    if profile.name == "Prosecutor":
        raw -= 1
        if not missing:
            missing.append("Potential hidden risk not fully mitigated")
    elif profile.name == "Defense":
        if e.repo_investigator and e.repo_investigator.git_commit_count >= 3:
            raw += 1
        if s["concept_explained"]:
            raw += 1
    elif profile.name == "TechLead":
        if not s["has_tests"] and criterion in {"LangGraph Architecture", "Engineering Process"}:
            raw -= 1
            missing.append("Automated tests to validate architecture behavior")

    score = _quantize_score(raw)
    return score, reasoning, sorted(set(missing))


def _criterion_to_bucket_points(score_1_to_5: int, bucket_max: int) -> int:
    return round((score_1_to_5 / 5) * bucket_max)


def _build_rubric_breakdown(opinions: list[JudicialCriterionOpinion]) -> RubricBreakdown:
    lookup = {op.criterion: op.score_1_to_5 for op in opinions}
    bucket_values: dict[str, int] = {}
    for criterion, bucket, bucket_max in CRITERION_TO_BUCKET:
        score = lookup.get(criterion, 1)
        bucket_values[bucket] = _criterion_to_bucket_points(score, bucket_max)
    return RubricBreakdown(**bucket_values)


def _build_rationale(profile: JudgeProfile, criterion_opinions: list[JudicialCriterionOpinion]) -> list[str]:
    notes = [f"Lens: {profile.lens}"]
    for item in criterion_opinions:
        notes.append(f"{item.criterion}: {item.reasoning} (Score {item.score_1_to_5}/5)")
    return notes


def _build_remediation(criterion_opinions: list[JudicialCriterionOpinion]) -> list[str]:
    fixes: list[str] = []
    for item in criterion_opinions:
        for missing in item.missing_elements:
            if missing not in fixes:
                fixes.append(missing)
    if not fixes:
        fixes.append("No critical remediation required; focus on stress testing and maintainability.")
    return fixes


def generate_judge_opinion(evidence: ForensicEvidence, profile: JudgeProfile) -> JudgeOpinion:
    criterion_opinions: list[JudicialCriterionOpinion] = []
    for criterion, _, _ in CRITERION_TO_BUCKET:
        score, reasoning, missing = _evaluate_criterion(evidence, profile, criterion)
        criterion_opinions.append(
            JudicialCriterionOpinion(
                criterion=criterion,
                score_1_to_5=score,
                lens=profile.lens,
                reasoning=reasoning,
                missing_elements=missing,
            )
        )

    return JudgeOpinion(
        judge_name=profile.name,
        score=_build_rubric_breakdown(criterion_opinions),
        criterion_opinions=criterion_opinions,
        rationale=_build_rationale(profile, criterion_opinions),
        remediation=_build_remediation(criterion_opinions),
    )
