# backend/main.py
# FastAPI endpoint to handle all websocket & agent routing
# See COMM_PROTOCOL.md for more info

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

sys.path.append(".")  # for imports inside non-main folder
from agent.agent import BasedAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from utils.unified_diff import apply_patch

app = FastAPI()
agent = BasedAgent()

# --- Logging Setup ---
LOG_PATH = os.path.join(os.path.dirname(__file__), "backend.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# --- Session Management ---
# In-memory storage for active WebSocket sessions.
# Each session stores: messages (history), workspace (files), context, and a lock.
# NOTE: This is not persistent and will be lost on server restart.
sessions: Dict[int, Dict[str, Any]] = {}


# --- Helper Functions for WebSocket Actions ---
async def handle_prompt_action(
    session_id: int, data: Dict[str, Any], websocket: WebSocket
):
    """Handles the 'prompt' action: classify intent, generate code/diff."""
    session = sessions[session_id]
    prompt = data.get("prompt", "")
    context = data.get("context", [])
    active_file = data.get("activeFile")  # File context from frontend

    # --- Prepare context and history ---
    current_context = session.get("context", [])
    if context:
        if isinstance(context, list):
            current_context.extend(context)
        else:
            current_context.append(context)
        session["context"] = current_context

    current_history = session["messages"]
    current_files = list(session["workspace"].keys())

    # --- Classify Intent using Agent ---
    logger.info(
        f"Session {session_id}: Classifying intent for prompt: '{prompt[:50]}...'"
    )
    intent_result = agent.classify_prompt_intent(
        prompt=prompt,
        context=current_context,
        history=current_history,
        file_list=current_files,
    )
    intent = intent_result.get("intent", "EDIT_FILE")  # Default to EDIT_FILE
    logger.info(f"Session {session_id}: Classified intent as {intent}")

    user_message_log = {
        "role": "user",
        "prompt": prompt,
        "context": context,
        "activeFile": active_file,
    }
    agent_response_log = None
    response = {"status": "error", "error": "Intent processing failed"}  # Default error

    # --- Handle based on Intent ---
    if intent == "CREATE_FILE":
        description = intent_result.get("description", prompt[:50])
        new_filename = agent.generate_filename(description)
        logger.info(
            f"Session {session_id}: Intent CREATE_FILE. Generating code for new file: {new_filename}"
        )

        # Generate initial based code (no diff)
        initial_code = agent.generate_based_code(
            prompt=prompt,
            context=current_context,
            history=current_history,
        )

        # Update workspace and prepare log/response
        session["workspace"][new_filename] = initial_code
        agent_response_log = {
            "role": "agent",
            "filename": new_filename,
            "code": initial_code,
        }
        response = {
            "status": "success",
            "action": "file_created",  # Specific action for frontend
            "filename": new_filename,
            "content": initial_code,
            "files": list(session["workspace"].keys()),  # Send updated file list
        }

    elif intent == "EDIT_FILE":
        # Check if a valid file is active for editing
        if not active_file or active_file not in session["workspace"]:
            # If no files exist at all, treat as implicit creation (same as above)
            if not current_files:
                logger.warning(
                    f"Session {session_id}: EDIT_FILE intent but no files exist. Treating as CREATE_FILE."
                )
                description = intent_result.get("description", prompt[:50])
                new_filename = agent.generate_filename(description)
                initial_code = agent.generate_based_code(
                    prompt, current_context, current_history
                )
                session["workspace"][new_filename] = initial_code
                agent_response_log = {
                    "role": "agent",
                    "filename": new_filename,
                    "code": initial_code,
                }
                response = {
                    "status": "success",
                    "action": "file_created",
                    "filename": new_filename,
                    "content": initial_code,
                    "files": list(session["workspace"].keys()),
                }
            else:
                # Files exist, but no valid active file selected
                logger.error(
                    f"Session {session_id}: EDIT_FILE intent requires a valid activeFile. Provided: '{active_file}'. Existing: {current_files}"
                )
                response = {
                    "status": "error",
                    "error": f"Please select a file to edit. Active file '{active_file}' not found or invalid.",
                    "action": "edit_error",  # Specific error action
                }
        else:
            # Valid active file, proceed with generating diff
            logger.info(
                f"Session {session_id}: Intent EDIT_FILE. Generating diff for: {active_file}"
            )
            current_code = session["workspace"][active_file]

            # Generate diff
            diff_result = agent.generate_based_diff(
                current_code=current_code,
                prompt=prompt,
                context=current_context,
                history=current_history,
            )
            agent_response_log = {
                "role": "agent",
                "filename": active_file,
                "diff": diff_result.get("diff"),
            }
            response = {
                "status": "success",
                "action": "diff_generated",  # Specific action for frontend
                "filename": active_file,
                "diff": diff_result.get("diff"),
                "new_code": diff_result.get(
                    "new_code"
                ),  # For monaco diffviewer in frontend
                "old_code": diff_result.get(
                    "old_code"
                ),  # For monaco diffviewer in frontend
            }

    # Log messages after processing
    if user_message_log:
        session["messages"].append(user_message_log)
    if agent_response_log:
        session["messages"].append(agent_response_log)

    # Send the final response back to the client
    logger.info(
        f"Session {session_id}: Sending '{response.get('action', 'unknown')}' response."
    )
    await websocket.send_json(response)


async def handle_upload_file_action(
    session_id: int, data: Dict[str, Any], websocket: WebSocket
):
    """Handles the 'upload_file' action."""
    session = sessions[session_id]
    filename = data.get("filename")
    content = data.get("content", "")
    response = {"status": "error", "error": "Missing filename"}  # Default error

    if filename:
        log_msg = f"Creating new file '{filename}'."
        if filename in session["workspace"]:
            log_msg = f"Overwriting existing file '{filename}'."
        logger.info(f"Session {session_id}: {log_msg}")

        session["workspace"][filename] = content
        response = {
            "status": "success",
            "action": "file_uploaded",  # Specific action name
            "filename": filename,
            "files": list(session["workspace"].keys()),  # Send updated list
        }
    else:
        logger.error(f"Session {session_id}: Upload_file action missing filename.")

    await websocket.send_json(response)


async def handle_list_files_action(session_id: int, websocket: WebSocket):
    """Handles the 'list_files' action."""
    session = sessions[session_id]
    files = list(session["workspace"].keys())
    logger.info(f"Session {session_id}: Listing files: {files}")
    response = {
        "status": "success",
        "action": "file_list",  # Specific action name
        "files": files,
    }
    await websocket.send_json(response)


async def handle_read_file_action(
    session_id: int, data: Dict[str, Any], websocket: WebSocket
):
    """Handles the 'read_file' action."""
    session = sessions[session_id]
    filename = data.get("filename")
    content = session["workspace"].get(filename)  # Safely get content - critical
    response = {"status": "error", "error": "File not found"}  # Default error

    if content is not None:
        logger.info(f"Session {session_id}: Reading file '{filename}'.")
        response = {
            "status": "success",
            "action": "file_content",  # Specific action name
            "filename": filename,
            "content": content,
        }
    else:
        logger.warning(
            f"Session {session_id}: Tried to read non-existent file: {filename}"
        )

    await websocket.send_json(response)


async def handle_apply_diff_action(
    session_id: int, data: Dict[str, Any], websocket: WebSocket
):
    """Handles the 'apply_diff' action."""
    session = sessions[session_id]
    filename = data.get("filename")
    diff = data.get("diff", "")
    response = {
        "status": "error",
        "error": "File not found or invalid for diff",
        "action": "apply_diff_error",
    }  # Default error

    if filename and filename in session["workspace"]:
        current_code = session["workspace"][filename]
        try:
            # Preprocessing might be needed for non-determenistic agent errors
            patch = agent.preprocess_diff(diff)
            new_code = apply_patch(current_code, patch)
            logger.info(f"Session {session_id}: Applying diff to file '{filename}'.")

            # --- Critical Section: Update workspace ---
            session["workspace"][filename] = new_code
            # --- End Critical Section ---

            response = {
                "status": "success",
                "action": "diff_applied",  # Specific action name
                "filename": filename,
                "new_code": new_code,  # Send the final applied code
            }
        except Exception as e:
            logger.error(
                f"Session {session_id}: Patch failed for file '{filename}': {e}. Diff: {diff!r}"
            )
            response = {
                "status": "error",
                "error": f"Patch failed: {e}",
                "action": "apply_diff_error",  # Specific error action
            }
    else:
        logger.warning(
            f"Session {session_id}: Tried to apply diff to non-existent/invalid file: {filename}"
        )
        # Keep default error response

    await websocket.send_json(response)


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles WebSocket connections, manages session state, and routes actions.

    Establishes a connection, initializes session state (including a lock),
    and enters a loop to receive JSON messages from the client. Each message
    should contain an 'action' field, which determines how the message is processed.
    Handles locking for potentially long-running or state-modifying actions
    ('prompt', 'apply_diff'). Cleans up session state on disconnect or error.
    """
    await websocket.accept()
    session_id = id(websocket)  # Use object ID as a simple session identifier

    # Initialize session state
    sessions[session_id] = {
        "messages": [],  # Stores conversation history [{role, content}, ...]
        "workspace": {},  # Stores file content {filename: content}
        "context": [],  # Stores arbitrary context data
        "lock": asyncio.Lock(),  # Lock to prevent concurrent modification actions
    }
    session_lock = sessions[session_id]["lock"]
    logger.info(
        f"WebSocket connected for session {session_id}. Initial state: {sessions[session_id]}"
    )

    # Send initial state to frontend (e.g., empty file list)
    await websocket.send_json(
        {
            "status": "success",
            "action": "initial_state",
            "files": [],
            "activeFile": None,  # No file active initially
        }
    )

    try:
        while True:
            # --- Receive and Parse Message ---
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                action = data.get("action")
                logger.info(
                    f"Session {session_id}: Received action '{action}' with data: {data}"
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"Session {session_id}: Invalid JSON received: {msg}. Error: {e}"
                )
                await websocket.send_json(
                    {"status": "error", "error": f"Invalid JSON: {e}"}
                )
                continue
            except Exception as e:  # Catch other potential errors during receive/parse
                logger.error(
                    f"Session {session_id}: Error processing received message: {e}"
                )
                await websocket.send_json(
                    {"status": "error", "error": f"Error processing message: {e}"}
                )
                continue  # Or break, depending on desired behavior

            if not action:
                logger.warning(
                    f"Session {session_id}: Received message with no action: {data}"
                )
                await websocket.send_json(
                    {"status": "error", "error": "Missing 'action' field"}
                )
                continue

            # --- Action Locking ---
            # Define actions that require exclusive access to session state
            # (primarily those involving LLM calls or modifying files based on LLM output)
            actions_requiring_lock = ["prompt", "apply_diff"]

            needs_lock = action in actions_requiring_lock
            lock_acquired = False

            if needs_lock:
                if session_lock.locked():
                    logger.warning(
                        f"Session {session_id}: Action '{action}' rejected, lock already held."
                    )
                    await websocket.send_json(
                        {
                            "status": "error",
                            "error": "Another operation is already in progress. Please wait.",
                            "action": "operation_rejected",
                        }
                    )
                    continue
                else:
                    # Try to acquire the lock
                    await session_lock.acquire()
                    lock_acquired = True
                    logger.debug(
                        f"Session {session_id}: Lock acquired for action '{action}'."
                    )

            # --- Process Action ---
            try:
                # Route to the appropriate handler based on the action
                if action == "prompt":
                    await handle_prompt_action(session_id, data, websocket)
                elif action == "upload_file":
                    await handle_upload_file_action(session_id, data, websocket)
                elif action == "list_files":
                    await handle_list_files_action(session_id, websocket)
                elif action == "read_file":
                    await handle_read_file_action(session_id, data, websocket)
                elif action == "apply_diff":
                    await handle_apply_diff_action(session_id, data, websocket)
                else:
                    logger.warning(
                        f"Session {session_id}: Received unknown action '{action}'."
                    )
                    await websocket.send_json(
                        {"status": "error", "error": f"Unknown action: {action}"}
                    )

            except Exception as handler_exc:
                # Catch errors within action handlers
                logger.error(
                    f"Session {session_id}: Error during action '{action}': {handler_exc}",
                    exc_info=True,
                )
                try:
                    await websocket.send_json(
                        {
                            "status": "error",
                            "error": f"Error processing action '{action}': {handler_exc}",
                        }
                    )
                except (
                    Exception
                ):  # Ignore sending error message if connection is broken
                    pass
            finally:
                # --- Release Lock ---
                if lock_acquired:
                    session_lock.release()
                    logger.debug(
                        f"Session {session_id}: Lock released for action '{action}'."
                    )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}.")

    except Exception as e:
        logger.error(
            f"Unhandled error in WebSocket loop for session {session_id}: {e}",
            exc_info=True,
        )
        # Attempt to inform client before closing (might fail if connection is already broken)
        try:
            await websocket.send_json(
                {"status": "error", "error": f"Internal server error: {e}"}
            )
        except Exception:
            pass

    finally:
        # --- Session Cleanup ---
        if session_id in sessions:
            logger.info(f"Cleaning up session {session_id}.")
            # Ensure lock is released if held during disconnect/error
            session_lock = sessions[session_id]["lock"]
            if session_lock.locked():
                try:
                    session_lock.release()
                    logger.debug(f"Session {session_id}: Lock released during cleanup.")
                except RuntimeError:  # Lock might already be released
                    pass

            # Remove session data from memory
            del sessions[session_id]
            logger.info(f"Session {session_id} state cleaned up.")


# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting backend server with Uvicorn...")

    # NOTE: disable reload in prod
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
