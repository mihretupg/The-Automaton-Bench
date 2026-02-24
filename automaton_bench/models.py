from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class VerdictLabel(str, Enum):
    exceptional = "EXCEPTIONAL"
    pass_label = "PASS"
    needs_work = "NEEDS_WORK"
    fail = "FAIL"


class ProtocolResult(BaseModel):
    protocol: str
    passed: bool
    summary: str


class GitCommitRecord(BaseModel):
    commit_hash: str
    authored_at: str
    message: str


class RepoInvestigatorEvidence(BaseModel):
    state_structure: ProtocolResult
    graph_wiring: ProtocolResult
    git_narrative: ProtocolResult
    fan_out_sources: List[str] = Field(default_factory=list)
    typed_schema_locations: List[str] = Field(default_factory=list)
    git_commit_count: int = 0
    git_history_classification: str = "UNKNOWN"
    git_timeline: List[GitCommitRecord] = Field(default_factory=list)


class CitationFinding(BaseModel):
    cited_path: str
    exists_in_repo: bool
    status: str


class DocAnalystEvidence(BaseModel):
    citation_check: ProtocolResult
    concept_verification: ProtocolResult
    cited_paths: List[CitationFinding] = Field(default_factory=list)
    concept_depth: str = "UNKNOWN"


class VisionInspectorEvidence(BaseModel):
    flow_analysis: ProtocolResult
    architecture_flow_classification: str = "UNKNOWN"
    diagram_sources: List[str] = Field(default_factory=list)


class ForensicEvidence(BaseModel):
    repository_path: str
    repository_source_url: str | None = None
    pdf_report_path: str | None = None
    pdf_page_count: int = 0
    pdf_text_char_count: int = 0
    pdf_excerpt: str = ""
    python_files: int = 0
    test_files: int = 0
    docs_present: bool = False
    ci_present: bool = False
    security_docs_present: bool = False
    package_count: int = 0
    class_count: int = 0
    function_count: int = 0
    avg_lines_per_python_file: float = 0.0
    type_hinted_function_ratio: float = 0.0
    dependency_files: List[str] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)
    repo_investigator: RepoInvestigatorEvidence | None = None
    doc_analyst: DocAnalystEvidence | None = None
    vision_inspector: VisionInspectorEvidence | None = None


class RubricBreakdown(BaseModel):
    artifact_existence: int
    architecture_modularity: int
    test_quality: int
    ci_governance: int
    documentation: int

    @property
    def total(self) -> int:
        return (
            self.artifact_existence
            + self.architecture_modularity
            + self.test_quality
            + self.ci_governance
            + self.documentation
        )


class JudicialCriterionOpinion(BaseModel):
    criterion: str
    score_1_to_5: int = Field(ge=1, le=5)
    lens: str
    reasoning: str
    missing_elements: List[str] = Field(default_factory=list)


class JudgeOpinion(BaseModel):
    judge_name: str
    score: RubricBreakdown
    criterion_opinions: List[JudicialCriterionOpinion] = Field(default_factory=list)
    rationale: List[str]
    remediation: List[str]


class CriterionVerdict(BaseModel):
    criterion: str
    final_score_1_to_5: int = Field(ge=1, le=5)
    ruling: str


class DissentNote(BaseModel):
    criterion: str
    summary: str


class RemediationAction(BaseModel):
    file_path: str
    instruction: str


class FinalVerdict(BaseModel):
    label: VerdictLabel
    score: int
    confidence: float = Field(ge=0.0, le=1.0)
    consensus_summary: List[str]
    criterion_verdicts: List[CriterionVerdict] = Field(default_factory=list)
    dissents: List[DissentNote] = Field(default_factory=list)
    remediation_plan: List[RemediationAction] = Field(default_factory=list)


class AuditReport(BaseModel):
    evidence: ForensicEvidence
    judge_opinions: List[JudgeOpinion]
    final_verdict: FinalVerdict
