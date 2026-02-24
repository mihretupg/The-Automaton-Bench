# The Automaton Bench

The Automaton Bench is a multi-agent LangGraph auditor designed for Week 2 MinMax optimization:

- Forensic analysis to verify code artifacts objectively.
- Nuanced scoring through a strict rubric.
- Constructive remediation output, not only pass/fail.

## Architecture

1. Detective Layer (Hierarchical subgraph):
   - `RepoInvestigator`: AST/state schema checks, graph fan-out wiring checks, and git narrative timeline extraction.
   - `DocAnalyst`: citation cross-reference and concept-depth verification.
   - `VisionInspector`: architecture flow analysis for parallel detective/judge topology.
   - Phase 2 tool primitives:
     - `analyze_graph_structure(path: str)`
     - `extract_git_history(path: str)`
     - `ingest_pdf(path: str)` with chunked RAG-lite query support
     - `extract_images_from_pdf(path: str)` for multimodal inspection hooks
2. Judge Layer:
   - `Prosecutor`, `Defense`, and `TechLead` evaluate identical evidence in parallel.
   - Each judge emits criterion-by-criterion `JudicialCriterionOpinion` objects for:
     - Artifact Integrity
     - LangGraph Architecture
     - Judicial Nuance
     - Engineering Process
     - Cross-Evidence Fidelity
   - Structured output enforcement:
     - Judges use `.with_structured_output()` when `OPENAI_API_KEY` is available.
     - Parser errors trigger retry attempts before fallback logic is used.
3. Chief Justice Layer:
   - synthesizes the final verdict and unified remediation plan.
   - applies hardcoded Supreme Court rules:
     - Security Rule: confirmed security vulnerabilities cap criterion scores at 3.
     - Evidence Rule: Defense claims of deep metacognition are overruled without valid PDF evidence.
     - Functionality Rule: Tech Lead carries highest weight on architecture viability.

The graph is fan-out (three judges in parallel) then fan-in (single synthesis).

## Quick Start

```bash
uv venv
uv sync
```

Create environment file:

```bash
copy .env.example .env
```

Set `LANGCHAIN_API_KEY` in `.env` for LangSmith traces. Runtime bootstraps `.env` automatically and enables `LANGCHAIN_TRACING_V2=true`.

Run backend API:

```bash
uv run automaton-bench-api
```

Run frontend:

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173` and submit a repository + PDF report.

Run a CLI audit:

```bash
uv run automaton-bench "https://github.com/org/repo" --pdf-report "C:\path\to\peer-report.pdf" --output-dir audit_output
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

## Constitution

- Scoring dimensions are dynamically loaded from [automaton_bench/rubric.json](automaton_bench/rubric.json).
- Update that file to change courtroom rubric behavior without changing code paths.

## Inputs

- One GitHub repository URL (or local path for offline testing)
- One PDF report used as documentary evidence
