from __future__ import annotations

from pathlib import Path

from src.state import AgentState, Evidence
from src.tools.doc_tools import (
    extract_images_from_pdf,
    extract_keyword_contexts,
    extract_paths_from_text,
    ingest_pdf,
    query_dialectical_synthesis,
    verify_paths,
)
from src.tools.repo_tools import (
    analyze_graph_structure,
    detect_ast_sophistication,
    extract_agent_state_snippet,
    extract_git_history,
    scan_judge_structured_output,
    scan_synthesis_strategy,
    scan_tool_safety,
)


def repo_investigator_node(state: AgentState) -> AgentState:
    applicable = {d["id"]: d for d in state.get("repo_dimensions", [])}
    graph_info = analyze_graph_structure(state["repo_path"])
    git_info = extract_git_history(state["repo_path"])
    agent_state_snippet = extract_agent_state_snippet(state["repo_path"])
    safety = scan_tool_safety(state["repo_path"])
    judge_output_scan = scan_judge_structured_output(state["repo_path"])
    synthesis_scan = scan_synthesis_strategy(state["repo_path"])
    ast_depth = detect_ast_sophistication(state["repo_path"])

    commit_capture = "\n".join(
        [f"{c['timestamp']} | {c['message']}" for c in git_info["commits"][:20]]
    ) or "No git history found."
    evidence_items: list[Evidence] = []
    if "git_forensic_analysis" in applicable:
        evidence_items.append(Evidence(
                goal="Git Forensic Analysis",
                found=len(git_info["commits"]) > 0,
                content=commit_capture,
                location="git log --oneline --reverse",
                rationale=(
                    f"{applicable['git_forensic_analysis']['forensic_instruction']} | "
                    f"Commit classification={git_info['classification']}, "
                    f"progression_detected={git_info.get('progression_detected', False)}."
                ),
                confidence=0.9 if git_info["commits"] else 0.3,
            ))
    if "state_management_rigor" in applicable:
        evidence_items.append(Evidence(
                goal="State Management Rigor (Phase 0)",
                found=bool(graph_info["typed_state_locations"]) and bool(agent_state_snippet),
                content=agent_state_snippet,
                location="src/state.py or src/graph.py",
                rationale=(
                    f"{applicable['state_management_rigor']['forensic_instruction']} | "
                    "AST scan for BaseModel/TypedDict + AgentState evidence/opinion collections."
                ),
                confidence=0.9 if agent_state_snippet else 0.45,
            ))
    if "graph_orchestration" in applicable:
        evidence_items.append(Evidence(
                goal="Graph Orchestration (Phase 1)",
                found=graph_info["parallel_wired"],
                content=graph_info["graph_block_snippet"],
                location="StateGraph node/edge definition block",
                rationale=(
                    f"{applicable['graph_orchestration']['forensic_instruction']} | "
                    "AST-verified add_edge fan-out/fan-in pattern capture."
                ),
                confidence=0.9 if graph_info["parallel_wired"] else 0.5,
            ))
    if "safe_tool_engineering" in applicable:
        evidence_items.append(Evidence(
                goal="Safe Tool Engineering (Phase 2)",
                found=safety["has_tempdir"] and not safety["unsafe_calls"],
                content=safety["clone_function_snippet"],
                location="src/tools/* cloning logic",
                rationale=(
                    f"{applicable['safe_tool_engineering']['forensic_instruction']} | "
                    f"TemporaryDirectory used={safety['has_tempdir']}; "
                    f"unsafe os.system calls={len(safety['unsafe_calls'])}."
                ),
                confidence=0.9 if safety["has_tempdir"] and not safety["unsafe_calls"] else 0.4,
            ))
    if "structured_output_enforcement" in applicable:
        evidence_items.append(Evidence(
                goal="Structured Output (Phase 3)",
                found=judge_output_scan["structured_enforced"],
                content=judge_output_scan["snippet"],
                location="src/nodes/judges.py",
                rationale=(
                    f"{applicable['structured_output_enforcement']['forensic_instruction']} | "
                    f"with_structured_output={judge_output_scan['uses_with_structured_output']}, "
                    f"bind_tools={judge_output_scan['uses_bind_tools']}, "
                    f"pydantic_schema={judge_output_scan['has_pydantic_schema']}."
                ),
                confidence=0.9 if judge_output_scan["structured_enforced"] else 0.35,
            ))
    if "chief_justice_synthesis" in applicable:
        evidence_items.append(Evidence(
                goal="Synthesis Strategy",
                found=synthesis_scan["deterministic_rules"],
                content=synthesis_scan["snippet"],
                location="src/nodes/justice.py",
                rationale=(
                    f"{applicable['chief_justice_synthesis']['forensic_instruction']} | "
                    f"deterministic_rules={synthesis_scan['deterministic_rules']}, "
                    f"llm_synthesis={synthesis_scan['llm_synthesis']}."
                ),
                confidence=0.85 if synthesis_scan["deterministic_rules"] else 0.4,
            ))
    if "judicial_nuance" in applicable:
        evidence_items.append(Evidence(
                goal="AST Detective Sophistication",
                found=ast_depth["advanced_ast_logic"],
                content=ast_depth["snippet"],
                location="src/tools/*",
                rationale=(
                    f"{applicable['judicial_nuance']['forensic_instruction']} | "
                    "Checks whether AST parsing logic goes beyond regex-like matching."
                ),
                confidence=0.85 if ast_depth["advanced_ast_logic"] else 0.3,
            ))
    evidences = {"RepoInvestigator": evidence_items}
    return {"evidences": evidences}


def doc_analyst_node(state: AgentState) -> AgentState:
    applicable = {d["id"]: d for d in state.get("pdf_dimensions", [])}
    ingested = ingest_pdf(state["pdf_path"])
    dialectical_chunks = query_dialectical_synthesis(ingested)
    keyword_contexts = extract_keyword_contexts(ingested)
    all_text = "\n".join(chunk["text"] for chunk in ingested.get("chunks", []))
    cited_paths = extract_paths_from_text(all_text)
    cross_ref = verify_paths(cited_paths, state["repo_path"])
    theory_found = any(keyword_contexts.get(key) for key in keyword_contexts)
    evidence_items: list[Evidence] = []
    if "theoretical_depth" in applicable:
        evidence_items.append(Evidence(
                goal="Theoretical Depth",
                found=theory_found,
                content="\n".join(chunk["text"][:220] for chunk in dialectical_chunks),
                location=state["pdf_path"],
                rationale=(
                    f"{applicable['theoretical_depth']['forensic_instruction']} | "
                    "Keyword context capture for Dialectical Synthesis, Fan-In/Fan-Out, "
                    "Metacognition, and State Synchronization."
                ),
                confidence=0.8 if theory_found else 0.35,
            ))
    if "report_accuracy" in applicable:
        evidence_items.append(Evidence(
                goal="Host Analysis Accuracy",
                found=len(cross_ref["hallucinated"]) == 0,
                content=(
                    f"Verified Paths: {cross_ref['verified']}\n"
                    f"Hallucinated Paths: {cross_ref['hallucinated']}"
                ),
                location="PDF cited paths cross-reference",
                rationale=(
                    f"{applicable['report_accuracy']['forensic_instruction']} | "
                    "Doc paths validated against repository filesystem."
                ),
                confidence=0.9 if len(cross_ref["hallucinated"]) == 0 else 0.45,
            ))
    evidences = {"DocAnalyst": evidence_items}
    return {"evidences": evidences}


def vision_inspector_node(state: AgentState) -> AgentState:
    applicable = {d["id"]: d for d in state.get("image_dimensions", [])}
    image_paths = extract_images_from_pdf(
        state["pdf_path"],
        output_dir=str(Path(state["repo_path"]).resolve() / "audit" / "vision_extracts"),
    )
    flow_hint = (
        "Critical flow appears present"
        if any("diagram" in p.lower() or "flow" in p.lower() for p in image_paths)
        else "Unable to confirm critical split from extracted images"
    )
    evidence_items: list[Evidence] = []
    if "swarm_visual" in applicable:
        evidence_items.extend([
            Evidence(
                goal="Swarm Visual Classification",
                found=len(image_paths) > 0,
                content=f"classification=STATEGRAPH_OR_GENERIC_UNKNOWN; images={image_paths[:8]}",
                location=state["pdf_path"],
                rationale=(
                    f"{applicable['swarm_visual']['forensic_instruction']} | "
                    "Image extraction pipeline is implemented; multimodal inference execution is optional."
                ),
                confidence=0.4 if image_paths else 0.2,
            ),
            Evidence(
                goal="Critical Flow Check",
                found="present" in flow_hint.lower(),
                content=flow_hint,
                location="Extracted diagram images",
                rationale=(
                    "Expected flow: Evidence Aggregation -> (Prosecutor || Defense || TechLead) -> Chief Justice."
                ),
                confidence=0.35 if image_paths else 0.15,
            )
        ])
    evidences = {"VisionInspector": evidence_items}
    return {"evidences": evidences}


def evidence_aggregator_node(state: AgentState) -> AgentState:
    if not state.get("evidences"):
        return {"errors": ["EvidenceAggregator received empty evidence payload."]}
    return {}
