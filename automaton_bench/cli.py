from __future__ import annotations

import argparse
from pathlib import Path

from automaton_bench.graph import run_audit
from automaton_bench.reporting import write_report_json, write_report_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automaton Bench repository auditor.")
    parser.add_argument("repo_path", help="Path to the repository to audit.")
    parser.add_argument(
        "--output-dir",
        default="audit_output",
        help="Directory where JSON and Markdown reports will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_audit(args.repo_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "audit_report.json"
    md_path = out_dir / "audit_report.md"
    write_report_json(report, json_path)
    write_report_markdown(report, md_path)

    print(f"Audit complete: {report.final_verdict.label.value} ({report.final_verdict.score}/100)")
    print(f"JSON report: {json_path.resolve()}")
    print(f"Markdown report: {md_path.resolve()}")


if __name__ == "__main__":
    main()

