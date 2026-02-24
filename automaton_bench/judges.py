from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

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


class StructuredJudgeResponse(BaseModel):
    score: int = Field(ge=1, le=5)
    reasoning: str
    citations: list[str] = Field(default_factory=list)


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


def _evaluate_criterion_heuristic(
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


def _llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _invoke_structured_judge_llm(
    profile: JudgeProfile,
    criterion: dict[str, Any],
    evidence: ForensicEvidence,
    max_retries: int = 2,
) -> StructuredJudgeResponse | None:
    if not _llm_enabled():
        return None
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        return None

    system_prompt = (
        "You are a Digital Courtroom judge. "
        f"Persona: {profile.name} ({profile.lens}). "
        "Return strictly structured output with score (1-5), reasoning, and citations."
    )
    evidence_payload = {
        "repo_path": evidence.repository_path,
        "findings": evidence.findings,
        "repo_investigator": evidence.repo_investigator.model_dump(mode="json") if evidence.repo_investigator else {},
        "doc_analyst": evidence.doc_analyst.model_dump(mode="json") if evidence.doc_analyst else {},
        "vision_inspector": evidence.vision_inspector.model_dump(mode="json") if evidence.vision_inspector else {},
    }
    human_prompt = (
        "Evaluate one rubric criterion.\n"
        f"Criterion: {criterion['name']} ({criterion['id']})\n"
        f"Description: {criterion.get('description', '')}\n"
        f"Evidence JSON: {json.dumps(evidence_payload)}"
    )

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    structured_llm = llm.with_structured_output(StructuredJudgeResponse)
    attempt = 0
    while attempt <= max_retries:
        try:
            return structured_llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt},
                ]
            )
        except Exception as exc:
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(
                    f"Structured parser error for judge={profile.name}, criterion={criterion['id']}: {exc}"
                ) from exc
    return None


def _criterion_to_bucket_points(score_1_to_5: int, bucket_max: int) -> int:
    return round((score_1_to_5 / 5) * bucket_max)


def _build_rubric_breakdown(
    opinions: list[JudicialCriterionOpinion],
    rubric_dimensions: list[dict[str, Any]],
) -> RubricBreakdown:
    by_name = {item.criterion: item.score_1_to_5 for item in opinions}
    bucket_values = {
        "artifact_existence": 0,
        "architecture_modularity": 0,
        "test_quality": 0,
        "ci_governance": 0,
        "documentation": 0,
    }
    for dimension in rubric_dimensions:
        score = by_name.get(dimension["name"], 1)
        bucket = dimension.get("bucket", "documentation")
        bucket_max = int(dimension.get("max_points", 15))
        if bucket in bucket_values:
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


def generate_judge_opinion(
    evidence: ForensicEvidence,
    profile: JudgeProfile,
    rubric_dimensions: list[dict[str, Any]],
) -> JudgeOpinion:
    criterion_opinions: list[JudicialCriterionOpinion] = []
    for dimension in rubric_dimensions:
        criterion_name = dimension["name"]
        heuristic_score, heuristic_reasoning, heuristic_missing = _evaluate_criterion_heuristic(
            evidence, profile, criterion_name
        )

        llm_result = None
        try:
            llm_result = _invoke_structured_judge_llm(profile, dimension, evidence)
        except RuntimeError:
            llm_result = None

        if llm_result is not None:
            score = llm_result.score
            reasoning = llm_result.reasoning
            citations = llm_result.citations
            missing = list(sorted(set(heuristic_missing + [f"Citations: {', '.join(citations)}"])))
        else:
            score = heuristic_score
            reasoning = heuristic_reasoning
            missing = heuristic_missing

        criterion_opinions.append(
            JudicialCriterionOpinion(
                criterion=criterion_name,
                score_1_to_5=score,
                lens=profile.lens,
                reasoning=reasoning,
                missing_elements=missing,
            )
        )

    return JudgeOpinion(
        judge_name=profile.name,
        score=_build_rubric_breakdown(criterion_opinions, rubric_dimensions),
        criterion_opinions=criterion_opinions,
        rationale=_build_rationale(profile, criterion_opinions),
        remediation=_build_remediation(criterion_opinions),
    )
