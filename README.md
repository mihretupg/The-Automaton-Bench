# The Automation Bench

Deliverable-focused implementation of the Digital Courtroom architecture for Week 2.

## Deliverable Map
- `src/state.py`: Pydantic + TypedDict state definitions with reducers (`operator.add`, `operator.ior`)
- `src/tools/repo_tools.py`: sandboxed clone, git history extraction, AST graph analysis
- `src/tools/doc_tools.py`: PDF ingestion + chunked RAG-lite querying
- `src/nodes/detectives.py`: RepoInvestigator, DocAnalyst, VisionInspector, EvidenceAggregator
- `src/nodes/judges.py`: Prosecutor, Defense, TechLead with `.with_structured_output()` path
- `src/nodes/justice.py`: deterministic ChiefJustice conflict resolution and audit synthesis
- `src/graph.py`: full fan-out/fan-in graph with conditional error handling
- `src/constitution.json`: central machine-readable constitution (dimensions + synthesis rules)
- `src/constitution.py`: ContextBuilder helpers to dispatch forensic instructions by `target_artifact`
- `automaton_bench/rubric.json`: constitutional scoring dimensions
- `automaton_bench/conflict_rules.json`: deterministic conflict feedback rules
- `reports/interim_report.pdf`, `reports/final_report.pdf`
- `audit/report_onself_generated/`, `audit/report_onpeer_generated/`, `audit/report_bypeer_received/`

## Setup (uv)
```bash
uv venv
uv sync
copy .env.example .env
```

Set required keys in `.env`:
- `LANGCHAIN_API_KEY` (LangSmith tracing)
- `OPENAI_API_KEY` (structured judge outputs)
- optional: `GITHUB_TOKEN`

## Run Detective Graph (Phase 2)
```bash
uv run python -c "from src.graph import run_detective_graph; run_detective_graph('https://github.com/org/repo', 'reports/final_report.pdf')"
```

## Run Full Swarm (Detectives + Judges + Chief Justice)
```bash
uv run python -c "from src.graph import run_full_graph; run_full_graph('https://github.com/org/repo', 'reports/final_report.pdf', output_markdown='audit/report_onself_generated/audit_report.md')"
```

## Output Contract
Generated Markdown reports follow:
1. Executive Summary
2. Criterion Breakdown
3. Remediation Plan

The `ContextBuilder` in `src/graph.py` dispatches:
- `forensic_instruction` to detectives by `target_artifact` (`github_repo`, `pdf_report`, `pdf_images`)
- aggregated judicial standards into judge prompts
- `synthesis_rules` into `ChiefJusticeNode`

## API/Frontend (optional)
```bash
uv run automaton-bench-api
cd frontend
npm install
npm run dev
```

## Docker (optional)
```bash
docker build -t automaton-bench .
docker run --rm -p 8000:8000 --env-file .env automaton-bench
```
