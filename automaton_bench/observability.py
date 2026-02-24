from __future__ import annotations

import os

from dotenv import load_dotenv


def bootstrap_runtime() -> None:
    load_dotenv()
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "automaton-bench")
