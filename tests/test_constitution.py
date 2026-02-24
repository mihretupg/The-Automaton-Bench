from automaton_bench.constitution import load_rubric_dimensions


def test_load_rubric_dimensions() -> None:
    dimensions = load_rubric_dimensions()
    assert len(dimensions) >= 5
    assert {"id", "name", "max_points", "bucket"}.issubset(set(dimensions[0].keys()))
