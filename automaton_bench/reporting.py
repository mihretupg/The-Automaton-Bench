from __future__ import annotations

import json
from pathlib import Path

from automaton_bench.models import AuditReport


def write_report_json(report: AuditReport, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


def build_markdown_report(report: AuditReport) -> str:
    ev = report.evidence
    fv = report.final_verdict
    lines = [
        "# Automaton Bench Audit Report",
        "",
        "## Final Verdict",
        f"- Label: `{fv.label.value}`",
        f"- Score: `{fv.score}/100`",
        f"- Confidence: `{fv.confidence}`",
        "",
        "## Forensic Snapshot",
        f"- Repository: `{ev.repository_path}`",
        f"- Repository URL: `{ev.repository_source_url or 'N/A'}`",
        f"- PDF report: `{ev.pdf_report_path or 'N/A'}`",
        f"- PDF pages: `{ev.pdf_page_count}`",
        f"- PDF extracted chars: `{ev.pdf_text_char_count}`",
        f"- Python files: `{ev.python_files}`",
        f"- Test files: `{ev.test_files}`",
        f"- Package count: `{ev.package_count}`",
        f"- Classes: `{ev.class_count}`",
        f"- Functions: `{ev.function_count}`",
        f"- Avg lines per Python file: `{ev.avg_lines_per_python_file}`",
        f"- Type-hinted function ratio: `{ev.type_hinted_function_ratio}`",
        f"- CI present: `{ev.ci_present}`",
        f"- Docs present: `{ev.docs_present}`",
        f"- Security docs present: `{ev.security_docs_present}`",
        "",
        "## PDF Excerpt",
        ev.pdf_excerpt or "_No extractable PDF text available._",
        "",
        "## Findings",
    ]
    if ev.findings:
        lines.extend([f"- {finding}" for finding in ev.findings])
    else:
        lines.append("- No critical forensic findings.")

    lines.extend(["", "## Detective Layer"])
    if ev.repo_investigator:
        repo = ev.repo_investigator
        lines.extend(
            [
                "### RepoInvestigator",
                f"- State Structure: `{repo.state_structure.passed}` - {repo.state_structure.summary}",
                f"- Graph Wiring: `{repo.graph_wiring.passed}` - {repo.graph_wiring.summary}",
                f"- Git Narrative: `{repo.git_narrative.passed}` - {repo.git_narrative.summary}",
                f"- Git commit count: `{repo.git_commit_count}`",
                f"- Git classification: `{repo.git_history_classification}`",
            ]
        )
    if ev.doc_analyst:
        doc = ev.doc_analyst
        lines.extend(
            [
                "### DocAnalyst",
                f"- Citation Check: `{doc.citation_check.passed}` - {doc.citation_check.summary}",
                f"- Concept Verification: `{doc.concept_verification.passed}` - {doc.concept_verification.summary}",
                f"- Concept depth: `{doc.concept_depth}`",
            ]
        )
    if ev.vision_inspector:
        vision = ev.vision_inspector
        lines.extend(
            [
                "### VisionInspector",
                f"- Flow Analysis: `{vision.flow_analysis.passed}` - {vision.flow_analysis.summary}",
                f"- Flow classification: `{vision.architecture_flow_classification}`",
            ]
        )

    lines.extend(["", "## Judge Opinions"])
    for opinion in report.judge_opinions:
        lines.append(f"### {opinion.judge_name}")
        lines.append(f"- Score: `{opinion.score.total}/100`")
        lines.append("- Rationale:")
        lines.extend([f"  - {note}" for note in opinion.rationale])
        lines.append("- Remediation:")
        lines.extend([f"  - {fix}" for fix in opinion.remediation])
        lines.append("")

    lines.extend(["## Unified Remediation Plan"])
    lines.extend([f"- {step}" for step in fv.remediation_plan])
    return "\n".join(lines).strip() + "\n"


def write_report_markdown(report: AuditReport, output_path: Path) -> None:
    output_path.write_text(build_markdown_report(report), encoding="utf-8")
