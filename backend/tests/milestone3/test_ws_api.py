from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_initial_state():
    """Test server sends initial state upon connection."""
    # Use TestClient's websocket context manager
    with client.websocket_connect("/ws") as ws:
        response = ws.receive_json()  # Use receive_json() for convenience
        assert response["action"] == "initial_state"
        assert response["status"] == "success"
        assert "files" in response
        assert "activeFile" in response


@pytest.mark.asyncio
@patch("main.agent", new_callable=MagicMock)
# Remove unused 'agent' fixture injection
async def test_prompt_intent_create_file(mock_main_agent):
    """Test 'prompt' action resulting in CREATE_FILE intent."""
    # Arrange
    mock_main_agent.classify_prompt_intent.return_value = {
        "intent": "CREATE_FILE",
        "description": "test agent",
    }
    mock_main_agent.generate_filename.return_value = "test-agent.based"
    # Mock the actual method that will be called by the patched agent
    generated_code = 'print("Hello Agent")'
    mock_main_agent.generate_based_code.return_value = generated_code

    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Act
        ws.send_json({"action": "prompt", "prompt": "Create a test agent"})
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "success"
        assert response["action"] == "file_created"
        assert response["filename"] == "test-agent.based"
        # Check the content returned matches the mock
        assert response["content"] == generated_code
        assert "test-agent.based" in response["files"]


@pytest.mark.asyncio
@patch("main.agent", new_callable=MagicMock)
# Remove unused 'agent' fixture injection
async def test_prompt_intent_edit_file_success(mock_main_agent):
    """Test 'prompt' action resulting in EDIT_FILE intent (success)."""
    # Arrange
    mock_main_agent.classify_prompt_intent.return_value = {"intent": "EDIT_FILE"}
    initial_content = "line1"
    new_content = "line1\nline2"
    diff_content = "+line2"  # Simplified diff for mock
    mock_main_agent.generate_based_diff.return_value = {
        "diff": diff_content,
        "new_code": new_content,
        "old_code": initial_content,
    }
    filename = "edit-me.based"

    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Setup: Upload initial file
        ws.send_json(
            {"action": "upload_file", "filename": filename, "content": initial_content}
        )
        ws.receive_json()  # upload confirmation

        # Act: Send prompt with activeFile
        ws.send_json(
            {"action": "prompt", "prompt": "Add line2", "activeFile": filename}
        )
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "success"
        assert response["action"] == "diff_generated"
        assert response["filename"] == filename
        assert response["diff"] == diff_content
        assert response["new_code"] == new_content
        assert response["old_code"] == initial_content


@pytest.mark.asyncio
@patch("main.agent", new_callable=MagicMock)
# Remove unused 'agent' fixture injection
async def test_prompt_intent_edit_no_active_file_error(mock_main_agent):
    """Test EDIT_FILE intent fails if no activeFile provided when files exist."""
    # Arrange
    mock_main_agent.classify_prompt_intent.return_value = {"intent": "EDIT_FILE"}
    filename = "existing.based"
    initial_content = "some code"

    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Setup: Upload a file
        ws.send_json(
            {"action": "upload_file", "filename": filename, "content": initial_content}
        )
        ws.receive_json()  # upload confirmation

        # Act: Send prompt without activeFile
        ws.send_json({"action": "prompt", "prompt": "Edit the code"})
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "error"
        assert response["action"] == "edit_error"
        assert (
            response["error"]
            == "Please select a file to edit. Active file 'None' not found or invalid."
        )

        # Assert Agent Calls
        mock_main_agent.classify_prompt_intent.assert_called_once()
        mock_main_agent.generate_based_diff.assert_not_called()


@pytest.mark.asyncio
@patch("main.agent", new_callable=MagicMock)
# Remove unused 'agent' fixture injection
async def test_prompt_intent_edit_invalid_active_file_error(mock_main_agent):
    """Test EDIT_FILE intent fails if activeFile doesn't exist."""
    # Arrange
    mock_main_agent.classify_prompt_intent.return_value = {"intent": "EDIT_FILE"}
    active_file = "nonexistent.based"
    initial_content = "real code"

    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Setup: Upload a different file
        ws.send_json(
            {
                "action": "upload_file",
                "filename": "real.based",
                "content": initial_content,
            }
        )
        ws.receive_json()  # upload confirmation

        # Act: Send prompt with non-existent activeFile
        ws.send_json(
            {"action": "prompt", "prompt": "Edit the code", "activeFile": active_file}
        )
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "error"
        assert response["action"] == "edit_error"
        assert (
            response["error"]
            == f"Please select a file to edit. Active file '{active_file}' not found or invalid."
        )

        # Assert Agent Calls
        mock_main_agent.classify_prompt_intent.assert_called_once_with(
            prompt="Edit the code", context=[], history=ANY, file_list=["real.based"]
        )
        mock_main_agent.generate_based_diff.assert_not_called()


@pytest.mark.asyncio
@patch("main.agent", new_callable=MagicMock)
# Remove unused 'agent' fixture injection
async def test_prompt_intent_edit_implicit_create_when_no_files(mock_main_agent):
    """Test EDIT_FILE intent triggers implicit CREATE when no files exist."""
    # Arrange
    mock_main_agent.classify_prompt_intent.return_value = {"intent": "EDIT_FILE"}
    expected_filename = "implicit-agent.based"
    mock_main_agent.generate_filename.return_value = expected_filename
    generated_code = 'print("Implicit creation")'
    mock_main_agent.generate_based_code.return_value = generated_code

    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Act: Send prompt when workspace is empty
        prompt_text = "Just make it work"
        ws.send_json({"action": "prompt", "prompt": prompt_text})
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "success"
        assert response["action"] == "file_created"
        assert response["filename"] == expected_filename
        assert response["content"] == generated_code
        assert expected_filename in response["files"]

        mock_main_agent.generate_based_diff.assert_not_called()


@pytest.mark.asyncio
async def test_upload_and_list_files():
    """Test uploading a file and then listing files."""
    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Upload
        filename = "test.based"
        content = "uploaded content"
        ws.send_json(
            {"action": "upload_file", "filename": filename, "content": content}
        )
        response = ws.receive_json()
        assert response["status"] == "success"
        assert response["action"] == "file_uploaded"
        assert response["filename"] == filename
        assert filename in response["files"]

        # List
        ws.send_json({"action": "list_files"})
        response = ws.receive_json()
        assert response["status"] == "success"
        assert response["action"] == "file_list"
        assert filename in response["files"]


@pytest.mark.asyncio
async def test_read_file():
    """Test reading a file after uploading it."""
    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Upload
        filename = "test2.based"
        content = "read this content"
        ws.send_json(
            {"action": "upload_file", "filename": filename, "content": content}
        )
        ws.receive_json()  # upload confirmation

        # Read
        ws.send_json({"action": "read_file", "filename": filename})
        response = ws.receive_json()
        assert response["status"] == "success"
        assert response["action"] == "file_content"
        assert response["filename"] == filename
        assert response["content"] == content


@pytest.mark.asyncio
async def test_read_nonexistent_file():
    """Test reading a file that doesn't exist."""
    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Read non-existent file
        filename = "nonexistent.based"
        ws.send_json({"action": "read_file", "filename": filename})
        response = ws.receive_json()
        assert response["status"] == "error"
        assert response["error"] == "File not found"


@pytest.mark.asyncio
@patch("main.agent", new_callable=MagicMock)
# Remove unused 'agent' fixture injection
async def test_apply_diff_success(mock_main_agent):
    """Test applying a valid diff to an existing file."""
    # Arrange
    mock_main_agent.preprocess_diff.side_effect = lambda diff: diff
    filename = "apply-diff-test.based"
    initial_content = "line1\nline2\nline3"
    valid_diff = "@@ -1,3 +1,3 @@\n line1\n-line2\n+line two\n line3"
    expected_new_code = "line1\nline two\nline3"

    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Setup: Upload initial file
        ws.send_json(
            {"action": "upload_file", "filename": filename, "content": initial_content}
        )
        ws.receive_json()  # upload confirmation

        # Act: Apply valid diff
        ws.send_json({"action": "apply_diff", "filename": filename, "diff": valid_diff})
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "success"
        assert response["action"] == "diff_applied"
        assert response["filename"] == filename
        assert response["new_code"] == expected_new_code

        # Assert Agent Calls
        mock_main_agent.preprocess_diff.assert_called_once_with(valid_diff)

        # Verify change persisted in session state (using TestClient's context)
        ws.send_json({"action": "read_file", "filename": filename})
        read_response = ws.receive_json()
        assert read_response["content"] == expected_new_code


@pytest.mark.asyncio
@patch("main.apply_patch", side_effect=Exception("Simulated patch error"))
@patch("main.agent", new_callable=MagicMock)
# Remove unused 'agent' fixture injection
async def test_apply_diff_patch_error(mock_main_agent, mock_apply_patch):
    """Test applying a diff that causes apply_patch to fail."""
    # Arrange
    mock_main_agent.preprocess_diff.side_effect = lambda diff: diff
    filename = "invalid-diff-test.based"
    initial_content = "line1"
    invalid_diff = "@@ -1,1 +1,1 @@\n-line1\n+line one"

    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Setup: Upload initial file
        ws.send_json(
            {"action": "upload_file", "filename": filename, "content": initial_content}
        )
        ws.receive_json()  # upload confirmation

        # Act: Apply invalid diff
        ws.send_json(
            {"action": "apply_diff", "filename": filename, "diff": invalid_diff}
        )
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "error"
        assert response["action"] == "apply_diff_error"
        assert "Patch failed: Simulated patch error" in response["error"]

        # Assert Agent Calls
        mock_main_agent.preprocess_diff.assert_called_once_with(invalid_diff)
        mock_apply_patch.assert_called_once_with(initial_content, invalid_diff)


@pytest.mark.asyncio
async def test_apply_diff_file_not_found_error():
    """Test applying a diff to a non-existent file."""
    # Use TestClient
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # Consume initial_state

        # Act: Apply diff to non-existent file
        filename = "nonexistent.based"
        ws.send_json(
            {"action": "apply_diff", "filename": filename, "diff": "@@ -1 +1 @@\n+a"}
        )
        response = ws.receive_json()

        # Assert Response
        assert response["status"] == "error"
        assert response["action"] == "apply_diff_error"
        assert "File not found or invalid for diff" in response["error"]
