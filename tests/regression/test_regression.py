from __future__ import annotations

from pathlib import Path

from harness.regression import load_regression_prompts

ROOT = Path(__file__).resolve().parents[2]


def test_regression_prompt_suite_has_ten_unique_prompts() -> None:
    prompt_set, _ = load_regression_prompts(ROOT / "tests/regression/prompts.yaml")
    ids = [item.id for item in prompt_set.prompts]

    assert len(ids) == 10
    assert len(set(ids)) == len(ids)
    assert all(item.subject for item in prompt_set.prompts)
