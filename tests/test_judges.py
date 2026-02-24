from automaton_bench.constitution import load_rubric_dimensions
from automaton_bench.judges import JUDGE_PROFILES, generate_judge_opinion
from automaton_bench.models import ForensicEvidence, ProtocolResult, RepoInvestigatorEvidence


def test_judges_emit_criterion_level_opinions() -> None:
    evidence = ForensicEvidence(
        repository_path="repo",
        python_files=5,
        test_files=1,
        docs_present=True,
        ci_present=False,
        dependency_files=["pyproject.toml"],
        repo_investigator=RepoInvestigatorEvidence(
            state_structure=ProtocolResult(protocol="State Structure", passed=True, summary="ok"),
            graph_wiring=ProtocolResult(protocol="Graph Wiring", passed=False, summary="linear"),
            git_narrative=ProtocolResult(protocol="Git Narrative", passed=False, summary="single commit"),
            git_commit_count=1,
            git_history_classification="MONOLITHIC",
        ),
    )
    rubric = load_rubric_dimensions()
    opinions = [generate_judge_opinion(evidence, profile, rubric) for profile in JUDGE_PROFILES]
    assert len(opinions) == 3
    assert all(len(op.criterion_opinions) == 5 for op in opinions)
    assert {op.judge_name for op in opinions} == {"Prosecutor", "Defense", "TechLead"}
