import sys
from unittest.mock import MagicMock, patch  # Import ANY

import pytest

sys.path.insert(0, ".")

from agent.agent import BASED_GUIDE, MAX_ITER, STRICT_INSTRUCTION


def test_classify_intent_create(agent):
    """Test intent classification correctly identifies CREATE_FILE."""
    # Arrange
    mock_response = MagicMock()
    mock_response.content = (
        '{"intent": "CREATE_FILE", "description": "test description"}'
    )
    agent.llm.invoke.return_value = mock_response
    prompt = "create a new agent"
    file_list = []

    # Act
    result = agent.classify_prompt_intent(prompt, None, None, file_list)

    # Assert
    assert result == {"intent": "CREATE_FILE", "description": "test description"}
    agent.llm.invoke.assert_called_once()
    call_args = agent.llm.invoke.call_args
    assert "CREATE_FILE" in call_args[0][0][0].content  # Check SystemMessage
    assert (
        f"User prompt: '{prompt}'" in call_args[0][0][1].content
    )  # Check HumanMessage


def test_classify_intent_edit(agent):
    """Test intent classification correctly identifies EDIT_FILE."""
    # Arrange
    mock_response = MagicMock()
    mock_response.content = '{"intent": "EDIT_FILE"}'
    agent.llm.invoke.return_value = mock_response
    prompt = "change the state"
    file_list = ["existing.based"]

    # Act
    result = agent.classify_prompt_intent(prompt, None, None, file_list)

    # Assert
    assert result == {"intent": "EDIT_FILE"}
    agent.llm.invoke.assert_called_once()
    call_args = agent.llm.invoke.call_args
    assert "EDIT_FILE" in call_args[0][0][0].content  # Check SystemMessage
    assert f"User prompt: '{prompt}'" in call_args[0][0][1].content
    assert "Existing files:\nexisting.based" in call_args[0][0][1].content


def test_classify_intent_default_on_error(agent):
    """Test intent classification defaults to EDIT_FILE on LLM error."""
    # Arrange
    agent.llm.invoke.side_effect = Exception("LLM failed")
    prompt = "some prompt"

    # Act
    result = agent.classify_prompt_intent(prompt, None, None, [])

    # Assert
    assert result == {"intent": "EDIT_FILE"}


def test_classify_intent_default_on_invalid_json(agent):
    """Test intent classification defaults to EDIT_FILE on invalid JSON response."""
    # Arrange
    mock_response = MagicMock()
    mock_response.content = "this is not json"
    agent.llm.invoke.return_value = mock_response
    prompt = "some prompt"

    # Act
    result = agent.classify_prompt_intent(prompt, None, None, [])

    # Assert
    assert result == {"intent": "EDIT_FILE"}


# --- Tests for generate_filename ---


def test_generate_filename_success(agent):
    """Test successful filename generation."""
    # Arrange
    mock_response = MagicMock()
    mock_response.content = "test-agent.based"
    agent.llm.invoke.return_value = mock_response
    description = "a test agent"

    # Act
    filename = agent.generate_filename(description)

    # Assert
    assert filename == "test-agent.based"
    agent.llm.invoke.assert_called_once()
    call_args = agent.llm.invoke.call_args
    assert f"Description: '{description}'" in call_args[0][0][1].content


def test_generate_filename_fallback_invalid_llm_output(agent):
    """Test fallback filename generation when LLM output is invalid."""
    # Arrange
    mock_response = MagicMock()
    mock_response.content = "invalid filename"  # Missing .based, contains space
    agent.llm.invoke.return_value = mock_response
    description = "a test agent"

    # Act
    filename = agent.generate_filename(description)

    # Assert
    assert filename == "a-test-agent.based"  # Check fallback logic
    agent.llm.invoke.assert_called_once()


def test_generate_filename_fallback_llm_error(agent):
    """Test fallback filename generation on LLM error."""
    # Arrange
    agent.llm.invoke.side_effect = Exception("LLM failed")
    description = "another test agent"

    # Act
    filename = agent.generate_filename(description)

    # Assert
    assert filename == "another-test-agent.based"  # Check fallback logic


# --- Tests for generate_based_code ---


def test_generate_based_code_success(agent, monkeypatch):
    """Test successful code generation on the first attempt."""
    # Arrange
    mock_llm_response = MagicMock()
    mock_llm_response.content = "state = {}"
    agent.llm.invoke.return_value = mock_llm_response
    monkeypatch.setattr(
        agent,
        "validate_code",
        lambda code: {"status": "success", "converted_code": code},
    )

    # Act
    code = agent.generate_based_code("test prompt")

    # Assert
    assert code == "state = {}"
    agent.llm.invoke.assert_called_once()
    call_args = agent.llm.invoke.call_args
    assert (
        call_args[0][0][0].content == BASED_GUIDE + STRICT_INSTRUCTION
    )  # Check SystemMessage
    assert (
        "User Request: test prompt" in call_args[0][0][1].content
    )  # Check HumanMessage


def test_generate_based_code_iterates(agent, monkeypatch):
    """Test code generation succeeding after one failed validation attempt."""
    # Arrange
    mock_response_bad = MagicMock()
    mock_response_bad.content = "bad code"
    mock_response_good = MagicMock()
    mock_response_good.content = "state = {}"
    agent.llm.invoke.side_effect = [mock_response_bad, mock_response_good]

    def mock_validate(code):
        if code == "bad code":
            return {"status": "fail", "error": "Syntax error"}
        elif code == "state = {}":
            return {"status": "success", "converted_code": code}
        pytest.fail(f"Unexpected code passed to validate_code: {code}")

    monkeypatch.setattr(agent, "validate_code", mock_validate)

    # Act
    code = agent.generate_based_code("test prompt")

    # Assert
    assert code == "state = {}"
    assert agent.llm.invoke.call_count == 2
    # Check that the second call included error feedback
    second_call_args = agent.llm.invoke.call_args_list[1]
    assert (
        "failed validation with this error:\nSyntax error"
        in second_call_args[0][0][1].content
    )


def test_generate_based_code_max_iterations(agent, monkeypatch):
    """Test code generation failing after MAX_ITER attempts."""
    # Arrange
    mock_response_bad = MagicMock()
    mock_response_bad.content = "bad code"
    agent.llm.invoke.return_value = mock_response_bad
    monkeypatch.setattr(
        agent, "validate_code", lambda code: {"status": "fail", "error": "Syntax error"}
    )

    # Act
    code = agent.generate_based_code("test prompt")

    # Assert
    assert code == "bad code"
    assert agent.llm.invoke.call_count == MAX_ITER
    last_call_args = agent.llm.invoke.call_args
    assert (
        "failed validation with this error:\nSyntax error"
        in last_call_args[0][0][1].content
    )


def test_generate_based_code_with_context_history(agent, monkeypatch):
    """Test that context and history are included in the LLM prompt."""
    # Arrange
    mock_llm_response = MagicMock()
    mock_llm_response.content = "state = {}"
    agent.llm.invoke.return_value = mock_llm_response
    monkeypatch.setattr(
        agent,
        "validate_code",
        lambda code: {"status": "success", "converted_code": code},
    )

    prompt = "test prompt"
    context = ["context item 1", {"key": "value"}]
    history = [
        {"role": "user", "prompt": "previous prompt"},
        {"role": "agent", "filename": "f.based", "code": "old code"},
    ]

    # Act
    agent.generate_based_code(prompt, context=context, history=history)

    # Assert
    agent.llm.invoke.assert_called_once()
    call_args = agent.llm.invoke.call_args
    human_message_content = call_args[0][0][1].content
    assert "Conversation history:" in human_message_content
    assert "User: previous prompt" in human_message_content
    assert "Agent: [Generated initial code] for file f.based" in human_message_content
    assert "Context:" in human_message_content
    assert "context item 1" in human_message_content
    assert "{'key': 'value'}" in human_message_content
    assert f"User Request: {prompt}" in human_message_content


# --- Tests for preprocess_diff ---


@pytest.mark.parametrize(
    "raw_diff, expected_clean_diff",
    [
        # Basic case
        ("@@ -1,1 +1,1 @@\n-a\n+b", "@@ -1,1 +1,1 @@\n-a\n+b"),
        # With markdown
        ("```diff\n@@ -1,1 +1,1 @@\n-a\n+b\n```", "@@ -1,1 +1,1 @@\n-a\n+b"),
        # With file headers
        (
            "--- a/file.txt\n+++ b/file.txt\n@@ -1,1 +1,1 @@\n-a\n+b",
            "@@ -1,1 +1,1 @@\n-a\n+b",
        ),
        # With /dev/null headers
        ("--- /dev/null\n+++ b/file.txt\n@@ -0,0 +1,1 @@\n+a", "@@ -0,0 +1,1 @@\n+a"),
        # With indented headers
        ("  @@ -1,1 +1,1 @@\n-a\n+b", "@@ -1,1 +1,1 @@\n-a\n+b"),
        # Mixed
        (
            "```\n--- a/f.txt\n+++ b/f.txt\n  @@ -1,2 +1,2 @@\n- line1\n+ line one\n  line2\n```",
            "@@ -1,2 +1,2 @@\n- line1\n+ line one\n  line2",
        ),
    ],
)
def test_preprocess_diff(agent, raw_diff, expected_clean_diff):
    """Test diff preprocessing for various LLM outputs."""
    clean_diff = agent.preprocess_diff(raw_diff)
    assert clean_diff == expected_clean_diff


# --- Tests for generate_based_diff ---


def test_generate_based_diff_success(agent, monkeypatch):
    """Test successful diff generation on the first attempt."""
    # Arrange
    current_code = "state = {'a': 1}"
    prompt = "change a to 2"
    expected_diff = "@@ -1,1 +1,1 @@\n-state = {'a': 1}\n+state = {'a': 2}"
    expected_new_code = "state = {'a': 2}"

    mock_llm_response = MagicMock()
    mock_llm_response.content = expected_diff
    agent.llm.invoke.return_value = mock_llm_response

    # Mock preprocess_diff to return the raw diff for simplicity here
    # Mock validate_code to succeed
    monkeypatch.setattr(
        agent,
        "validate_code",
        lambda code: {"status": "success", "converted_code": code},
    )

    # Act
    result = agent.generate_based_diff(current_code, prompt)

    # Assert
    assert result["diff"] == expected_diff
    assert result["new_code"] == expected_new_code
    assert result["old_code"] == current_code
    agent.llm.invoke.assert_called_once()
    call_args = agent.llm.invoke.call_args
    # Adjust assertion to match the actual prompt format
    assert f"implement this user request: '{prompt}'" in call_args[0][0][1].content


def test_generate_based_diff_iterates_on_validation_error(agent, monkeypatch):
    """Test diff generation iterating due to validation failure."""
    # Arrange
    current_code = "state = {'a': 1}"
    prompt = "change a to 2"
    bad_diff = "@@ -1,1 +1,1 @@\n-state = {'a': 1}\n+state = {'a': 2"  # Invalid syntax
    good_diff = "@@ -1,1 +1,1 @@\n-state = {'a': 1}\n+state = {'a': 2}"
    bad_new_code = "state = {'a': 2"
    good_new_code = "state = {'a': 2}"

    mock_response_bad = MagicMock()
    mock_response_bad.content = bad_diff
    mock_response_good = MagicMock()
    mock_response_good.content = good_diff
    agent.llm.invoke.side_effect = [mock_response_bad, mock_response_good]

    monkeypatch.setattr(agent, "preprocess_diff", lambda diff: diff)  # Mock preprocess

    def mock_validate(code):
        if code == bad_new_code:
            return {"status": "fail", "error": "Syntax error"}
        elif code == good_new_code:
            return {"status": "success", "converted_code": code}
        pytest.fail(f"Unexpected code to validate: {code}")

    monkeypatch.setattr(agent, "validate_code", mock_validate)

    # Act
    result = agent.generate_based_diff(current_code, prompt)

    # Assert
    assert result["diff"] == good_diff
    assert result["new_code"] == good_new_code
    assert result["old_code"] == current_code
    assert agent.llm.invoke.call_count == 2
    # Check second call includes validation error feedback
    second_call_args = agent.llm.invoke.call_args_list[1]
    assert (
        "failed validation with this error:\nSyntax error"
        in second_call_args[0][0][1].content
    )


@patch("agent.agent.apply_patch")  # Mock apply_patch directly
def test_generate_based_diff_iterates_on_patch_error(
    mock_apply_patch, agent, monkeypatch
):
    """Test diff generation iterating due to patch application failure."""
    # Arrange
    current_code = "state = {'a': 1}"
    prompt = "change a to 2"
    bad_diff = (
        "@@ -5,1 +5,1 @@\n-state = {'a': 1}\n+state = {'a': 2}"  # Bad line numbers
    )
    good_diff = "@@ -1,1 +1,1 @@\n-state = {'a': 1}\n+state = {'a': 2}"
    good_new_code = "state = {'a': 2}"

    mock_response_bad = MagicMock()
    mock_response_bad.content = bad_diff
    mock_response_good = MagicMock()
    mock_response_good.content = good_diff
    agent.llm.invoke.side_effect = [mock_response_bad, mock_response_good]

    # Make apply_patch fail on the bad diff, succeed on the good one
    patch_exception = Exception("Bad patch line")
    mock_apply_patch.side_effect = [patch_exception, good_new_code]

    # Mock validate_code to succeed when called with good code
    monkeypatch.setattr(
        agent,
        "validate_code",
        lambda code: {"status": "success", "converted_code": code}
        if code == good_new_code
        else {"status": "fail"},
    )

    # Act
    result = agent.generate_based_diff(current_code, prompt)

    # Assert
    assert result["diff"] == good_diff
    assert result["new_code"] == good_new_code
    assert result["old_code"] == current_code
    assert agent.llm.invoke.call_count == 2
    assert mock_apply_patch.call_count == 2
    # Check second call includes patch error feedback
    second_call_args = agent.llm.invoke.call_args_list[1]
    # Adjust assertion to match the actual prompt format for patch errors
    assert (
        "The previous diff attempt failed to apply with this error:\n"
        in second_call_args[0][0][1].content
    )
    assert (
        f"User Request: '{prompt}'" in second_call_args[0][0][1].content
    )  # Check prompt is still there
    assert (
        f"Current Based code:\n```based\n{current_code}\n```"
        in second_call_args[0][0][1].content
    )  # Check code is still there


def test_generate_based_diff_max_iterations(agent, monkeypatch):
    """Test diff generation failing after MAX_ITER attempts."""
    # Arrange
    current_code = "state = {'a': 1}"
    prompt = "change a to 2"
    bad_diff = "@@ -1,1 +1,1 @@\n-state = {'a': 1}\n+state = {'a': 2"  # Invalid syntax
    bad_new_code = "state = {'a': 2"  # Expected result from applying the bad diff

    mock_response_bad = MagicMock()
    mock_response_bad.content = bad_diff
    agent.llm.invoke.return_value = mock_response_bad  # Always return bad diff

    monkeypatch.setattr(agent, "preprocess_diff", lambda diff: diff)
    monkeypatch.setattr(
        agent, "validate_code", lambda code: {"status": "fail", "error": "Syntax error"}
    )

    # Mock apply_patch to return the expected bad code when the bad diff is applied
    # This is needed because the function returns the result of the last *successful* patch apply
    with patch(
        "agent.agent.apply_patch", return_value=bad_new_code
    ) as mock_apply_patch:
        # Act: Call generate_based_diff ONCE
        result = agent.generate_based_diff(current_code, prompt)

        # Assert
        assert result["diff"] == bad_diff
        # new_code should be the result of applying the last bad diff
        assert result["new_code"] == bad_new_code
        assert result["old_code"] == current_code
        # Check that apply_patch was called MAX_ITER times (once per loop iteration)
        assert mock_apply_patch.call_count == MAX_ITER
        # Check that the LLM was called MAX_ITER times
        assert agent.llm.invoke.call_count == MAX_ITER

    # Check the content of the last LLM call's prompt
    last_call_args = agent.llm.invoke.call_args
    assert (
        "failed validation with this error:\nSyntax error"
        in last_call_args[0][0][1].content
    )
