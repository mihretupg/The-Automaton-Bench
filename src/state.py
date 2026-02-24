from __future__ import annotations

import operator
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Evidence(BaseModel):
    goal: str = Field()
    found: bool = Field(description="Whether the artifact exists")
    content: Optional[str] = Field(default=None)
    location: str = Field(description="File path or commit hash")
    rationale: str = Field(
        description="Rationale for confidence on the evidence gathered for this goal"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class JudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(ge=1, le=5)
    argument: str
    cited_evidence: List[str] = Field(default_factory=list)


class CriterionResult(BaseModel):
    dimension_id: str
    dimension_name: str
    final_score: int = Field(ge=1, le=5)
    judge_opinions: List[JudicialOpinion]
    dissent_summary: Optional[str] = Field(default=None)
    remediation: str


class AuditReport(BaseModel):
    repo_url: str
    executive_summary: str
    overall_score: float
    criteria: List[CriterionResult]
    remediation_plan: str


class AgentState(TypedDict, total=False):
    repo_url: str
    repo_path: str
    pdf_path: str
    constitution: Dict
    rubric_dimensions: List[Dict]
    repo_dimensions: List[Dict]
    pdf_dimensions: List[Dict]
    image_dimensions: List[Dict]
    judicial_logic: str
    synthesis_rules: Dict
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior]
    opinions: Annotated[List[JudicialOpinion], operator.add]
    criterion_results: Annotated[List[CriterionResult], operator.add]
    errors: Annotated[List[str], operator.add]
    final_report: AuditReport
