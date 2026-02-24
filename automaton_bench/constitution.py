from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_rubric_dimensions(rubric_path: str | None = None) -> list[dict[str, Any]]:
    if rubric_path:
        path = Path(rubric_path).resolve()
    else:
        path = Path(__file__).resolve().parent / "rubric.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    dimensions = data.get("dimensions", [])
    if not isinstance(dimensions, list):
        raise ValueError("rubric.json is invalid: 'dimensions' must be a list")
    return dimensions


def load_conflict_rules(conflict_path: str | None = None) -> dict[str, Any]:
    if conflict_path:
        path = Path(conflict_path).resolve()
    else:
        path = Path(__file__).resolve().parent / "conflict_rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("conflict_rules.json is invalid: root must be an object")
    return data
