from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class VerdictLabel(str, Enum):
    exceptional = "EXCEPTIONAL"
    pass_label = "PASS"
    needs_work = "NEEDS_WORK"
    fail = "FAIL"


class ForensicEvidence(BaseModel):
    repository_path: str
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


class JudgeOpinion(BaseModel):
    judge_name: str
    score: RubricBreakdown
    rationale: List[str]
    remediation: List[str]


class FinalVerdict(BaseModel):
    label: VerdictLabel
    score: int
    confidence: float = Field(ge=0.0, le=1.0)
    consensus_summary: List[str]
    remediation_plan: List[str]


class AuditReport(BaseModel):
    evidence: ForensicEvidence
    judge_opinions: List[JudgeOpinion]
    final_verdict: FinalVerdict

