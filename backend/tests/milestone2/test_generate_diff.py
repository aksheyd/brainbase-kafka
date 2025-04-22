import itertools
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, ".")

from agent.agent import MAX_ITER


class PatchError(Exception):
    pass


def test_generate_based_diff_success(agent, monkeypatch):
    """Test successful diff generation on the first attempt."""
    # Arrange
    current_code = "old code"
    prompt = "add a feature"
    expected_diff_str = "diff-ok"
    expected_new_code = "new code"

    mock_llm_response = MagicMock()
    mock_llm_response.content = expected_diff_str
    agent.llm.invoke.return_value = mock_llm_response

    # Mock preprocess_diff and apply_patch
    monkeypatch.setattr(agent, "preprocess_diff", lambda diff: diff)
    monkeypatch.setattr(
        "agent.agent.apply_patch", lambda code, patch: expected_new_code
    )
    # Mock validate_code to succeed
    monkeypatch.setattr(
        agent,
        "validate_code",
        lambda code: {"status": "success", "converted_code": code},
    )

    # Act
    result = agent.generate_based_diff(current_code, prompt)

    # Assert: Check the dictionary return value
    assert result["diff"] == expected_diff_str
    assert result["new_code"] == expected_new_code
    assert result["old_code"] == current_code


def test_generate_based_diff_iterates_on_patch_error(agent, monkeypatch):
    """Test diff generation iterating due to patch application failure."""
    # Arrange
    current_code = "old code"
    prompt = "fix bug"
    bad_diff_str = "bad-diff"
    good_diff_str = "good-diff"
    patched_code = "patched code"

    outputs = itertools.chain(
        [bad_diff_str, good_diff_str], itertools.repeat(good_diff_str)
    )

    def fake_invoke(msgs):
        return type("Resp", (), {"content": next(outputs)})()

    agent.llm.invoke.side_effect = fake_invoke

    monkeypatch.setattr(agent, "preprocess_diff", lambda diff: diff)  # Mock preprocess

    patch_exception = PatchError("bad format")

    def fake_patch(code, patch):
        if patch == bad_diff_str:
            raise patch_exception
        return patched_code

    # Patch apply_patch in the correct module where it's called
    monkeypatch.setattr("agent.agent.apply_patch", fake_patch)

    # Mock validate_code to succeed
    monkeypatch.setattr(
        agent,
        "validate_code",
        lambda code: {"status": "success", "converted_code": code},
    )

    # Act
    result = agent.generate_based_diff(current_code, prompt)

    # Assert
    assert result["diff"] == good_diff_str
    assert result["new_code"] == patched_code
    assert result["old_code"] == current_code
    assert agent.llm.invoke.call_count == 2  # Ensure it iterated


def test_generate_based_diff_iterates_on_validation_error(agent, monkeypatch):
    """Test diff generation iterating due to validation failure."""
    # Arrange
    current_code = "old code"
    prompt = "improve"
    diff1_str = "diff1"
    diff2_str = "diff2"
    patched_code1 = "patched-diff1"
    patched_code2 = "patched-diff2"

    outputs = itertools.chain([diff1_str, diff2_str], itertools.repeat(diff2_str))

    def fake_invoke(msgs):
        return type("Resp", (), {"content": next(outputs)})()

    agent.llm.invoke.side_effect = fake_invoke

    monkeypatch.setattr(agent, "preprocess_diff", lambda diff: diff)  # Mock preprocess
    # Mock apply_patch based on the diff string
    monkeypatch.setattr(
        "agent.agent.apply_patch", lambda code, patch: f"patched-{patch}"
    )

    def fake_validate(code):
        if code == patched_code1:
            return {"status": "fail", "error": "bad validation"}
        elif code == patched_code2:
            return {"status": "success", "converted_code": code}
        pytest.fail(f"Unexpected code to validate: {code}")

    monkeypatch.setattr(agent, "validate_code", fake_validate)

    # Act
    result = agent.generate_based_diff(current_code, prompt)

    # Assert
    assert result["diff"] == diff2_str
    assert result["new_code"] == patched_code2
    assert result["old_code"] == current_code
    assert agent.llm.invoke.call_count == 2  # Ensure it iterated


def test_generate_based_diff_max_iterations(agent, monkeypatch):
    """Test diff generation failing after MAX_ITER attempts (due to validation)."""
    # Arrange
    current_code = "old code"
    prompt = "fail always"
    last_diff_str = f"diff{MAX_ITER - 1}"
    last_patched_code = f"patched-{last_diff_str}"

    # Generate MAX_ITER distinct diff strings
    outputs = itertools.chain(
        (f"diff{i}" for i in range(MAX_ITER)), itertools.repeat(last_diff_str)
    )

    def fake_invoke(msgs):
        return type("Resp", (), {"content": next(outputs)})()

    agent.llm.invoke.side_effect = fake_invoke

    monkeypatch.setattr(agent, "preprocess_diff", lambda diff: diff)  # Mock preprocess
    # Mock apply_patch to return predictable patched code
    monkeypatch.setattr(
        "agent.agent.apply_patch", lambda code, patch: f"patched-{patch}"
    )
    # Mock validate_code to always fail
    monkeypatch.setattr(
        agent, "validate_code", lambda code: {"status": "fail", "error": "always bad"}
    )

    # Act
    result = agent.generate_based_diff(current_code, prompt)

    # Assert
    assert result["diff"] == last_diff_str
    # new_code should be the result of applying the *last* diff, even though validation failed
    assert result["new_code"] == last_patched_code
    assert result["old_code"] == current_code
    assert (
        agent.llm.invoke.call_count == MAX_ITER
    )  # Ensure LLM was called MAX_ITER times
