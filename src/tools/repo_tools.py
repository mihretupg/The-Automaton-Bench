from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse


def is_github_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() != "github.com":
        return False
    parts = [p for p in parsed.path.split("/") if p]
    return len(parts) >= 2


def clone_repo_sandboxed(repo_url: str) -> tuple[str, TemporaryDirectory[str]]:
    temp_dir = TemporaryDirectory(prefix="automaton-bench-src-")
    target = Path(temp_dir.name) / "repo"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        temp_dir.cleanup()
        err = result.stderr.strip() or result.stdout.strip() or "Unknown git clone error"
        raise RuntimeError(f"Sandboxed clone failed: {err}")
    return str(target), temp_dir


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if ".git" not in path.parts:
            yield path


def analyze_graph_structure(path: str) -> dict:
    root = Path(path).resolve()
    edges: dict[str, set[str]] = {}
    typed_state: list[str] = []
    stategraph_inits: list[str] = []
    graph_block_snippet = ""

    for py_file in _iter_python_files(root):
        source = py_file.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = [getattr(base, "id", getattr(base, "attr", "")) for base in node.bases]
                if "BaseModel" in base_names or "TypedDict" in base_names:
                    typed_state.append(f"{py_file.relative_to(root)}::{node.name}")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "StateGraph":
                    stategraph_inits.append(str(py_file.relative_to(root)))
                if isinstance(node.func, ast.Attribute) and node.func.attr == "add_edge" and len(node.args) >= 2:
                    if not graph_block_snippet and "add_edge" in source:
                        lines = source.splitlines()
                        idx = next((i for i, line in enumerate(lines) if "add_edge" in line), 0)
                        start = max(0, idx - 2)
                        end = min(len(lines), idx + 6)
                        graph_block_snippet = "\n".join(lines[start:end])
                    src, dst = node.args[0], node.args[1]
                    if (
                        isinstance(src, ast.Constant)
                        and isinstance(src.value, str)
                        and isinstance(dst, ast.Constant)
                        and isinstance(dst.value, str)
                    ):
                        edges.setdefault(src.value, set()).add(dst.value)

    fan_out = sorted([k for k, v in edges.items() if len(v) >= 2])
    return {
        "typed_state_locations": sorted(set(typed_state)),
        "stategraph_instantiations": sorted(set(stategraph_inits)),
        "fan_out_sources": fan_out,
        "edges": {k: sorted(v) for k, v in edges.items()},
        "parallel_wired": bool(fan_out),
        "graph_block_snippet": graph_block_snippet,
    }


def extract_git_history(path: str) -> dict:
    root = Path(path).resolve()
    result = subprocess.run(
        ["git", "-C", str(root), "log", "--pretty=format:%H|%aI|%s", "--reverse"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        return {"commits": [], "classification": "UNKNOWN", "error": err}

    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({"hash": parts[0], "timestamp": parts[1], "message": parts[2]})

    if len(commits) <= 1:
        classification = "MONOLITHIC"
    elif len(set(c["message"] for c in commits)) >= 3:
        classification = "ATOMIC"
    else:
        classification = "MIXED"
    progression_keywords = ["env", "setup", "tool", "graph", "orchestration", "judge", "detective"]
    progression_detected = any(
        any(keyword in commit["message"].lower() for keyword in progression_keywords) for commit in commits
    )
    return {
        "commits": commits,
        "classification": classification,
        "progression_detected": progression_detected,
        "error": None,
    }


def extract_agent_state_snippet(path: str) -> str:
    root = Path(path).resolve()
    candidates = [root / "src" / "state.py", root / "src" / "graph.py"]
    for candidate in candidates:
        if not candidate.exists():
            continue
        source = candidate.read_text(encoding="utf-8", errors="ignore")
        lines = source.splitlines()
        for idx, line in enumerate(lines):
            if "class AgentState" in line:
                return "\n".join(lines[idx : min(len(lines), idx + 20)])
    return ""


def scan_tool_safety(path: str) -> dict:
    root = Path(path).resolve()
    tools_dir = root / "src" / "tools"
    has_tempdir = False
    unsafe_calls: list[str] = []
    clone_function_snippet = ""
    if not tools_dir.exists():
        return {"has_tempdir": False, "unsafe_calls": [], "clone_function_snippet": ""}

    for py_file in tools_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8", errors="ignore")
        if "TemporaryDirectory(" in source:
            has_tempdir = True
        if "git clone" in source and not clone_function_snippet:
            lines = source.splitlines()
            idx = next((i for i, line in enumerate(lines) if "git clone" in line), 0)
            clone_function_snippet = "\n".join(lines[max(0, idx - 6) : min(len(lines), idx + 10)])

        for match in re.finditer(r"os\.system\((.+)\)", source):
            expr = match.group(1)
            if "shlex.quote" not in expr:
                unsafe_calls.append(f"{py_file.relative_to(root)}:{expr.strip()}")
    return {
        "has_tempdir": has_tempdir,
        "unsafe_calls": unsafe_calls,
        "clone_function_snippet": clone_function_snippet,
    }


def scan_judge_structured_output(path: str) -> dict:
    root = Path(path).resolve()
    judges_file = root / "src" / "nodes" / "judges.py"
    if not judges_file.exists():
        return {
            "structured_enforced": False,
            "has_pydantic_schema": False,
            "uses_with_structured_output": False,
            "uses_bind_tools": False,
            "snippet": "",
        }
    source = judges_file.read_text(encoding="utf-8", errors="ignore")
    has_schema = "BaseModel" in source and "class" in source and "score" in source and "citations" in source
    uses_with_structured_output = ".with_structured_output(" in source
    uses_bind_tools = ".bind_tools(" in source
    structured_enforced = has_schema and (uses_with_structured_output or uses_bind_tools)
    lines = source.splitlines()
    idx = next(
        (i for i, line in enumerate(lines) if ".with_structured_output(" in line or ".bind_tools(" in line),
        0,
    )
    snippet = "\n".join(lines[max(0, idx - 6) : min(len(lines), idx + 10)])
    return {
        "structured_enforced": structured_enforced,
        "has_pydantic_schema": has_schema,
        "uses_with_structured_output": uses_with_structured_output,
        "uses_bind_tools": uses_bind_tools,
        "snippet": snippet,
    }


def scan_synthesis_strategy(path: str) -> dict:
    root = Path(path).resolve()
    justice_file = root / "src" / "nodes" / "justice.py"
    if not justice_file.exists():
        return {"deterministic_rules": False, "llm_synthesis": False, "snippet": ""}
    source = justice_file.read_text(encoding="utf-8", errors="ignore")
    deterministic = "def " in source and ("_security_override" in source or "_fact_supremacy" in source)
    llm_synthesis = ("ChatOpenAI" in source) or ("with_structured_output" in source and "justice" in source.lower())
    lines = source.splitlines()
    idx = next((i for i, line in enumerate(lines) if "_security_override" in line or "ChatOpenAI" in line), 0)
    snippet = "\n".join(lines[max(0, idx - 6) : min(len(lines), idx + 12)])
    return {"deterministic_rules": deterministic, "llm_synthesis": llm_synthesis, "snippet": snippet}


def detect_ast_sophistication(path: str) -> dict:
    root = Path(path).resolve()
    tools_dir = root / "src" / "tools"
    if not tools_dir.exists():
        return {"advanced_ast_logic": False, "snippet": ""}
    best_snippet = ""
    advanced = False
    for py_file in tools_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8", errors="ignore")
        if "ast.parse" in source and ("ast.walk" in source or "isinstance(node, ast." in source):
            advanced = True
            lines = source.splitlines()
            idx = next((i for i, line in enumerate(lines) if "ast.parse" in line), 0)
            best_snippet = "\n".join(lines[max(0, idx - 6) : min(len(lines), idx + 14)])
            break
    return {"advanced_ast_logic": advanced, "snippet": best_snippet}
