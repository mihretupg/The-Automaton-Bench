from pathlib import Path

import pytest

from automaton_bench.intake import is_github_url, resolve_repository_input


def test_is_github_url() -> None:
    assert is_github_url("https://github.com/openai/openai-python") is True
    assert is_github_url("http://github.com/openai/openai-python") is True
    assert is_github_url("https://gitlab.com/group/repo") is False
    assert is_github_url(r"C:\repos\project") is False


def test_resolve_repository_input_local_path(tmp_path: Path) -> None:
    resolved = resolve_repository_input(str(tmp_path))
    assert resolved.repository_path == str(tmp_path.resolve())
    assert resolved.repository_source_url is None
    assert resolved.temp_dir is None


def test_resolve_repository_input_missing_path() -> None:
    with pytest.raises(FileNotFoundError):
        resolve_repository_input("./definitely-missing-folder")
