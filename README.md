# The Automaton Bench

The Automaton Bench is a multi-agent LangGraph auditor designed for Week 2 MinMax optimization:

- Forensic analysis to verify code artifacts objectively.
- Nuanced scoring through a strict rubric.
- Constructive remediation output, not only pass/fail.

## Architecture

1. `Forensics` agent gathers AST and repository evidence.
2. `Judges` (Prosecutor, Defense, TechLead) score independently with courtroom personas.
3. `Chief Justice` synthesizes a deterministic final verdict.

The graph is fan-out (three judges in parallel) then fan-in (single synthesis).

## Quick Start

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
```

Run an audit:

```bash
automaton-bench "https://github.com/org/repo" --pdf-report "C:\path\to\peer-report.pdf" --output-dir audit_output
```

Outputs:

- `audit_output/audit_report.json`
- `audit_output/audit_report.md`

## Scoring Rubric (100 points)

- Artifact existence: 25
- Architecture modularity: 25
- Test quality: 20
- CI and governance: 15
- Documentation quality: 15

## MinMax Loop (Week 2)

1. Audit peer repositories with this auditor.
2. Receive peer auditor reports on your repository.
3. Fix implementation gaps in your Week 2 project.
4. Refine this auditor to catch misses and reduce false positives.

Repeat until both your project quality and your auditor quality converge upward.

## Inputs

- One GitHub repository URL (or local path for offline testing)
- One PDF report used as documentary evidence
