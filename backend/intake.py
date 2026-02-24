from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse


@dataclass
class ResolvedRepository:
    repository_path: str
    repository_source_url: str | None
    temp_dir: TemporaryDirectory[str] | None


def is_github_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() != "github.com":
        return False
    segments = [part for part in parsed.path.split("/") if part]
    return len(segments) >= 2


def _clone_github_repository(url: str) -> ResolvedRepository:
    temp_dir = TemporaryDirectory(prefix="automaton-bench-")
    clone_dir = Path(temp_dir.name) / "repo"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, str(clone_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        temp_dir.cleanup()
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Failed to clone repository: {stderr}")

    return ResolvedRepository(
        repository_path=str(clone_dir),
        repository_source_url=url,
        temp_dir=temp_dir,
    )


def resolve_repository_input(repository: str) -> ResolvedRepository:
    if is_github_url(repository):
        return _clone_github_repository(repository)

    local_path = Path(repository).resolve()
    if not local_path.exists():
        raise FileNotFoundError(f"Repository path not found: {local_path}")
    if not local_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {local_path}")

    return ResolvedRepository(
        repository_path=str(local_path),
        repository_source_url=None,
        temp_dir=None,
    )
