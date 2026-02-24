from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_constitution(path: str | None = None) -> dict[str, Any]:
    src = Path(path).resolve() if path else (Path(__file__).resolve().parent / "constitution.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("constitution.json must be an object")
    return data


def split_dimensions_by_target(constitution: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    dims = constitution.get("dimensions", [])
    out = {"github_repo": [], "pdf_report": [], "pdf_images": []}
    for dim in dims:
        target = dim.get("target_artifact")
        if target in out:
            out[target].append(dim)
    return out


def build_judicial_logic(constitution: dict[str, Any]) -> str:
    lines = []
    for dim in constitution.get("dimensions", []):
        lines.append(
            f"{dim.get('id')}: success='{dim.get('success_pattern')}' failure='{dim.get('failure_pattern')}'"
        )
    return "\n".join(lines)
