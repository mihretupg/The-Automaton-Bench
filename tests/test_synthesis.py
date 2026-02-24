from automaton_bench.models import (
    ForensicEvidence,
    JudgeOpinion,
    JudicialCriterionOpinion,
    ProtocolResult,
    RepoInvestigatorEvidence,
    RubricBreakdown,
)
from automaton_bench.synthesis import synthesize_verdict


CRITERIA = [
    "Artifact Integrity",
    "LangGraph Architecture",
    "Judicial Nuance",
    "Engineering Process",
    "Cross-Evidence Fidelity",
]


def _opinion(name: str, scores: dict[str, int]) -> JudgeOpinion:
    return JudgeOpinion(
        judge_name=name,
        score=RubricBreakdown(
            artifact_existence=20,
            architecture_modularity=20,
            test_quality=15,
            ci_governance=12,
            documentation=12,
        ),
        criterion_opinions=[
            JudicialCriterionOpinion(
                criterion=criterion,
                score_1_to_5=scores.get(criterion, 3),
                lens=f"{name} Lens",
                reasoning="test",
                missing_elements=[],
            )
            for criterion in CRITERIA
        ],
        rationale=[],
        remediation=["Create CI workflow that runs linting and tests."],
    )


def test_security_rule_caps_scores() -> None:
    evidence = ForensicEvidence(
        repository_path="repo",
        findings=["Security vulnerability: os.system with unsanitized input in app.py"],
    )
    opinions = [
        _opinion("Prosecutor", {c: 5 for c in CRITERIA}),
        _opinion("Defense", {c: 5 for c in CRITERIA}),
        _opinion("TechLead", {c: 5 for c in CRITERIA}),
    ]
    verdict = synthesize_verdict(opinions, evidence)
    assert all(item.final_score_1_to_5 <= 3 for item in verdict.criterion_verdicts)


def test_evidence_rule_overrules_defense_metacognition_claim() -> None:
    evidence = ForensicEvidence(repository_path="repo", pdf_report_path=None, pdf_text_char_count=0)
    opinions = [
        _opinion("Prosecutor", {"Judicial Nuance": 1}),
        _opinion("Defense", {"Judicial Nuance": 5}),
        _opinion("TechLead", {"Judicial Nuance": 1}),
    ]
    verdict = synthesize_verdict(opinions, evidence)
    nuance = next(item for item in verdict.criterion_verdicts if item.criterion == "Judicial Nuance")
    assert nuance.final_score_1_to_5 == 1
    assert any("Defense claim of deep metacognition overruled" in d.summary for d in verdict.dissents)


def test_functionality_rule_weights_techlead_for_architecture() -> None:
    evidence = ForensicEvidence(
        repository_path="repo",
        repo_investigator=RepoInvestigatorEvidence(
            state_structure=ProtocolResult(protocol="State Structure", passed=True, summary="typed"),
            graph_wiring=ProtocolResult(protocol="Graph Wiring", passed=False, summary="partial"),
            git_narrative=ProtocolResult(protocol="Git Narrative", passed=False, summary="n/a"),
        ),
    )
    opinions = [
        _opinion("Prosecutor", {"LangGraph Architecture": 1}),
        _opinion("Defense", {"LangGraph Architecture": 1}),
        _opinion("TechLead", {"LangGraph Architecture": 5}),
    ]
    verdict = synthesize_verdict(opinions, evidence)
    architecture = next(item for item in verdict.criterion_verdicts if item.criterion == "LangGraph Architecture")
    assert architecture.final_score_1_to_5 == 3
    assert any(
        ("Tech Lead carried higher weight" in d.summary) or ("re-evaluated with constitution rules" in d.summary)
        for d in verdict.dissents
    )


def test_conflict_variance_triggers_constitution_re_evaluation() -> None:
    evidence = ForensicEvidence(
        repository_path="repo",
        python_files=0,
        dependency_files=[],
        docs_present=False,
    )
    opinions = [
        _opinion("Prosecutor", {"Artifact Integrity": 1}),
        _opinion("Defense", {"Artifact Integrity": 5}),
        _opinion("TechLead", {"Artifact Integrity": 5}),
    ]
    verdict = synthesize_verdict(opinions, evidence)
    artifact = next(item for item in verdict.criterion_verdicts if item.criterion == "Artifact Integrity")
    assert artifact.final_score_1_to_5 == 1
    assert any("re-evaluated with constitution rules" in d.summary for d in verdict.dissents)
