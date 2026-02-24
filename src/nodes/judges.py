from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field

from src.state import AgentState, JudicialOpinion


class JudgeStructuredOutput(BaseModel):
    score: int = Field(ge=1, le=5)
    reasoning: str
    citations: list[str] = Field(default_factory=list)


JUDGE_PROMPTS = {
    "Prosecutor": (
        "Trust no one. Scrutinize risks, missing controls, and brittle architecture. "
        "Cite Protocol A forensic standards explicitly in your reasoning."
    ),
    "Defense": (
        "Reward effort and engineering intent, even if implementation is imperfect. "
        "Still cite Protocol A standards and evidence captures."
    ),
    "TechLead": (
        "Assess practical viability, maintainability, and technical debt objectively. "
        "Anchor arguments to Protocol A standards and captured evidence."
    ),
}


def _collect_evidence_strings(state: AgentState) -> list[str]:
    out: list[str] = []
    for source, items in state.get("evidences", {}).items():
        for item in items:
            out.append(f"{source}:{item.goal}:found={item.found}:{item.content}:{item.rationale}")
    return out


def _heuristic_judge(judge: str, criterion: dict[str, Any], state: AgentState) -> JudgeStructuredOutput:
    evidence_strings = " ".join(_collect_evidence_strings(state)).lower()
    cid = criterion["id"]
    score = 3
    reasoning = f"{judge} assessment for {cid} using Protocol B precedents."
    citations = ["RepoInvestigator", "DocAnalyst", "VisionInspector"]

    has_parallel = "graph orchestration (phase 1):found=true" in evidence_strings
    structured_output_enforced = "structured output (phase 3):found=true" in evidence_strings
    has_tempdir_safe = "safe tool engineering (phase 2):found=true" in evidence_strings
    has_unsafe_os_system = "unsafe os.system calls=" in evidence_strings and ":found=false" in evidence_strings
    ast_sophisticated = "ast detective sophistication:found=true" in evidence_strings
    synthesis_deterministic = "synthesis strategy:found=true" in evidence_strings

    if judge == "Prosecutor":
        if cid == "langgraph_architecture" and not has_parallel:
            score = 1
            reasoning = "Orchestration Fraud: linear flow detected, no fan-out orchestration."
        elif cid == "judicial_nuance" and not structured_output_enforced:
            score = min(score, 2)
            reasoning = "Hallucination Liability: judge outputs lack enforced structured schema."
        else:
            score = 3

    elif judge == "TechLead":
        if cid in {"langgraph_architecture", "forensic_accuracy"}:
            if "typed state verification:found=true" in evidence_strings and "state management rigor (phase 0):found=true" in evidence_strings:
                score = 4 if has_parallel else 3
            else:
                score = 3
                reasoning = "Technical Debt: dict-style brittle state handling suspected."
        if cid == "forensic_accuracy" and (has_unsafe_os_system or not has_tempdir_safe):
            score = 1
            reasoning = "Security Negligence: cloning/tooling not safely sandboxed."

    elif judge == "Defense":
        score = 4 if ("git forensic analysis:found=true" in evidence_strings or "dialectical" in evidence_strings) else 3
        if cid == "forensic_accuracy" and not has_parallel and ast_sophisticated:
            score = max(score, 3)
            reasoning = "Mitigation: deep AST comprehension detected despite orchestration compile/syntax issues."
        if cid == "judicial_nuance" and not synthesis_deterministic:
            score = max(score, 3)
            score = min(score, 4)
            reasoning = (
                "Mitigation: role-separated judicial disagreement provides dialectical tension despite "
                "non-deterministic synthesis style."
            )

    return JudgeStructuredOutput(
        score=score,
        reasoning=reasoning,
        citations=citations,
    )


def _llm_structured_judge(
    judge: str,
    criterion: dict[str, Any],
    state: AgentState,
    max_retries: int = 2,
) -> JudgeStructuredOutput | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        return None

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    structured_llm = llm.with_structured_output(JudgeStructuredOutput)

    evidence_summary = "\n".join(_collect_evidence_strings(state))
    system = (
        f"You are {judge}. {JUDGE_PROMPTS[judge]} Return structured output only.\n"
        f"Judicial sentencing guidelines:\n{state.get('judicial_logic', '')}"
    )
    user = (
        f"Criterion: {criterion['id']} ({criterion['name']})\n"
        f"Description: {criterion.get('description', '')}\n"
        f"Evidence:\n{evidence_summary}"
    )
    for attempt in range(max_retries + 1):
        try:
            return structured_llm.invoke(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
            )
        except Exception:
            if attempt == max_retries:
                raise RuntimeError(f"Parser error for judge={judge}, criterion={criterion['id']}.")
    return None


def _judge_node(state: AgentState, judge: str) -> AgentState:
    opinions: list[JudicialOpinion] = []
    errors: list[str] = []
    for criterion in state.get("rubric_dimensions", []):
        try:
            parsed = _llm_structured_judge(judge, criterion, state)
        except RuntimeError as exc:
            errors.append(str(exc))
            parsed = None

        if parsed is None:
            parsed = _heuristic_judge(judge, criterion, state)

        opinions.append(
            JudicialOpinion(
                judge=judge,  # type: ignore[arg-type]
                criterion_id=criterion["id"],
                score=parsed.score,
                argument=parsed.reasoning,
                cited_evidence=parsed.citations,
            )
        )
    payload: AgentState = {"opinions": opinions}
    if errors:
        payload["errors"] = errors
    return payload


def prosecutor_node(state: AgentState) -> AgentState:
    return _judge_node(state, "Prosecutor")


def defense_node(state: AgentState) -> AgentState:
    return _judge_node(state, "Defense")


def techlead_node(state: AgentState) -> AgentState:
    return _judge_node(state, "TechLead")
