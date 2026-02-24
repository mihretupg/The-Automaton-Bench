from __future__ import annotations

from dataclasses import dataclass
from typing import List

from automaton_bench.models import ForensicEvidence, JudgeOpinion
from automaton_bench.rubric import score_forensic_rubric


@dataclass(frozen=True)
class JudgeProfile:
    name: str
    focus: str
    adjustment: int


JUDGE_PROFILES = [
    JudgeProfile(name="Prosecutor", focus="risk and missing controls", adjustment=-3),
    JudgeProfile(name="Defense", focus="implementation intent and progress", adjustment=2),
    JudgeProfile(name="TechLead", focus="engineering pragmatism and maintainability", adjustment=0),
]


def _bound(value: int, min_v: int, max_v: int) -> int:
    return max(min_v, min(max_v, value))


def _build_rationale(e: ForensicEvidence, focus: str) -> List[str]:
    notes = [f"Focus: {focus}"]
    if e.repository_source_url:
        notes.append(f"Evidence sourced from GitHub URL: {e.repository_source_url}")
    if e.python_files == 0:
        notes.append("Repository does not contain executable Python artifacts.")
    if e.test_files > 0:
        notes.append(f"Detected {e.test_files} test files.")
    else:
        notes.append("No automated tests detected.")
    if e.ci_present:
        notes.append("CI workflow exists.")
    else:
        notes.append("CI workflow missing.")
    if e.type_hinted_function_ratio >= 0.5:
        notes.append("Type annotation coverage is moderate to high.")
    if e.pdf_report_path:
        notes.append(
            f"Reviewed PDF report ({e.pdf_page_count} pages, {e.pdf_text_char_count} extracted chars)."
        )
    else:
        notes.append("No PDF report context available to corroborate repository findings.")
    if e.repo_investigator:
        notes.append(f"RepoInvestigator git narrative: {e.repo_investigator.git_history_classification}.")
    if e.doc_analyst and not e.doc_analyst.citation_check.passed:
        notes.append("DocAnalyst flagged report-to-repo citation hallucinations.")
    if e.vision_inspector:
        notes.append(f"VisionInspector flow classification: {e.vision_inspector.architecture_flow_classification}.")
    return notes


def _build_remediation(e: ForensicEvidence) -> List[str]:
    fixes: List[str] = []
    if e.test_files == 0:
        fixes.append("Add smoke tests and core-path unit tests.")
    if not e.ci_present:
        fixes.append("Create CI workflow that runs linting and tests.")
    if not e.security_docs_present:
        fixes.append("Add SECURITY.md and dependency scanning in CI.")
    if e.type_hinted_function_ratio < 0.4:
        fixes.append("Increase type hints on public functions and critical flows.")
    if not e.pdf_report_path:
        fixes.append("Attach the latest PDF report so judges can cross-check documented claims.")
    elif e.pdf_text_char_count < 120:
        fixes.append("Provide a text-readable PDF report with explicit findings and evidence.")
    if e.repo_investigator and not e.repo_investigator.graph_wiring.passed:
        fixes.append("Refactor graph edges to explicit AST-verifiable fan-out for parallel sub-agents.")
    if e.doc_analyst and not e.doc_analyst.citation_check.passed:
        fixes.append("Fix hallucinated document citations so all claimed files exist in the repository.")
    if e.vision_inspector and not e.vision_inspector.flow_analysis.passed:
        fixes.append("Update architecture diagram to show Detectives->Aggregation->Judges->Synthesis flow.")
    if not fixes:
        fixes.append("No critical remediation required; refine edge-case coverage.")
    return fixes


def generate_judge_opinion(evidence: ForensicEvidence, profile: JudgeProfile) -> JudgeOpinion:
    base = score_forensic_rubric(evidence)
    return JudgeOpinion(
        judge_name=profile.name,
        score=base.model_copy(
            update={
                "artifact_existence": _bound(base.artifact_existence + profile.adjustment, 0, 25),
                "architecture_modularity": _bound(base.architecture_modularity + profile.adjustment, 0, 25),
                "test_quality": _bound(base.test_quality + profile.adjustment, 0, 20),
                "ci_governance": _bound(base.ci_governance + profile.adjustment, 0, 15),
                "documentation": _bound(base.documentation + profile.adjustment, 0, 15),
            }
        ),
        rationale=_build_rationale(evidence, profile.focus),
        remediation=_build_remediation(evidence),
    )
