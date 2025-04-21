# Main entrypoint for Kafka backend (Milestone 1)
# This will handle incoming requests and coordinate agent logic and validation.

import asyncio  # Added for locking
import json
import logging
import sys

sys.path.append(".")
from agent.agent import BasedAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Import apply_patch if needed directly here, or handle within agent
# from unified_diff import apply_patch

app = FastAPI()
agent = BasedAgent()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("backend.log", mode="a"), logging.StreamHandler()],
)
logger = logging.getLogger("backend")

# In-memory session state (for demonstration; use a better store for production)
sessions = {}
# Lock for managing access to the sessions dictionary itself (if needed, less critical now)
# sessions_lock = asyncio.Lock()


# Remove or comment out old Pydantic models if HTTP endpoints are deprecated
# class GenerateRequest(BaseModel):
#     prompt: str
# class GenerateResponse(BaseModel):
#     code: str
# class GenerateDiffRequest(BaseModel):
#     current_code: str
#     prompt: str
# class GenerateDiffResponse(BaseModel):
#     diff: str

# Remove or comment out old HTTP endpoints if deprecated
# @app.post("/generate")
# def generate_based_code(request: GenerateRequest):
#     # This logic is now likely handled within the websocket prompt action
#     pass

# @app.post("/generate-diff", response_model=GenerateDiffResponse)
# def generate_based_diff(request: GenerateDiffRequest):
#     # This logic is now likely handled within the websocket prompt action
#     pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # TODO: Implement persistent session IDs later
    session_id = id(websocket)
    # Initialize workspace as empty, first file created by first prompt
    sessions[session_id] = {
        "messages": [],
        "workspace": {},
        "context": [],
        "lock": asyncio.Lock(),  # Add an asyncio Lock per session
    }
    session_lock = sessions[session_id]["lock"]
    logger.info(
        f"WebSocket connected for session {session_id}. Initial state: {sessions[session_id]}"
    )

    # Send initial empty file list to frontend
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
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                logger.info(f"Received message: {data}")  # Log entire message
            except Exception as e:
                logger.error(f"Invalid JSON received: {msg}. Error: {e}")
                await websocket.send_json(
                    {"status": "error", "error": f"Invalid JSON: {e}"}
                )
                continue

            action = data.get("action")
            response = {"status": "error", "error": "Unknown action"}

            # --- Acquire Lock for relevant actions ---
            # Check if action requires lock BEFORE trying to acquire
            needs_lock = action in [
                "prompt",
                "apply_diff",
                "generate_based_code",
                "generate_based_diff",
            ]

            if needs_lock:
                if session_lock.locked():
                    logger.warning(
                        f"Session {session_id} is locked. Action '{action}' rejected."
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
                    # Acquire lock if needed and not already locked
                    await session_lock.acquire()

            try:
                # --- Process Actions ---
                if action == "prompt":
                    prompt = data.get("prompt", "")
                    context = data.get(
                        "context", []
                    )  # Use provided context or empty list
                    active_file = data.get(
                        "activeFile"
                    )  # Get active file from frontend

                    # Ensure context is always a list
                    current_context = sessions[session_id].get("context", [])
                    if context:  # Append new context if provided
                        if isinstance(context, list):
                            current_context.extend(context)
                        else:
                            current_context.append(context)
                        sessions[session_id]["context"] = current_context

                    current_history = sessions[session_id]["messages"]
                    current_files = list(sessions[session_id]["workspace"].keys())

                    # --- Intent Classification ---
                    intent_result = agent.classify_prompt_intent(
                        prompt=prompt,
                        context=current_context,
                        history=current_history,
                        file_list=current_files,
                    )
                    intent = intent_result.get(
                        "intent", "EDIT_FILE"
                    )  # Default to EDIT if classification fails

                    user_message_log = {
                        "role": "user",
                        "prompt": prompt,
                        "context": context,
                        "activeFile": active_file,
                    }
                    agent_response_log = None

                    # --- Handle based on Intent ---
                    if intent == "CREATE_FILE":
                        description = intent_result.get(
                            "description", prompt[:50]
                        )  # Use description or part of prompt
                        new_filename = agent.generate_filename(description)
                        logger.info(
                            f"Intent: CREATE_FILE. Generating filename: {new_filename}"
                        )

                        # Generate initial code (potentially long operation)
                        initial_code = agent.generate_based_code(
                            prompt=prompt,  # Use the original creation prompt
                            context=current_context,
                            history=current_history,  # History helps guide initial code
                        )

                        # Update workspace and log
                        sessions[session_id]["workspace"][new_filename] = initial_code
                        agent_response_log = {
                            "role": "agent",
                            "filename": new_filename,
                            "code": initial_code,
                        }

                        # Send response to frontend
                        response = {
                            "status": "success",
                            "action": "file_created",  # Specific action for frontend
                            "filename": new_filename,
                            "content": initial_code,
                            "files": list(
                                sessions[session_id]["workspace"].keys()
                            ),  # Send updated file list
                        }

                    elif intent == "EDIT_FILE":
                        if (
                            not active_file
                            or active_file not in sessions[session_id]["workspace"]
                        ):
                            # If no file exists yet, treat as creation
                            if not current_files:
                                logger.warning(
                                    "EDIT_FILE intent but no files exist. Treating as CREATE_FILE."
                                )
                                description = intent_result.get(
                                    "description", prompt[:50]
                                )
                                new_filename = agent.generate_filename(description)
                                initial_code = agent.generate_based_code(
                                    prompt, current_context, current_history
                                )
                                sessions[session_id]["workspace"][new_filename] = (
                                    initial_code
                                )
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
                                    "files": list(
                                        sessions[session_id]["workspace"].keys()
                                    ),
                                }
                            else:
                                # If files exist but none active/valid, return error
                                logger.error(
                                    f"EDIT_FILE intent requires a valid activeFile. Provided: '{active_file}'. Existing: {current_files}"
                                )
                                response = {
                                    "status": "error",
                                    "error": f"Please select a file to edit. Active file '{active_file}' not found.",
                                    "action": "edit_error",
                                }
                        else:
                            logger.info(
                                f"Intent: EDIT_FILE. Generating diff for: {active_file}"
                            )
                            current_code = sessions[session_id]["workspace"][
                                active_file
                            ]
                            # Generate diff (potentially long operation)
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
                                "new_code": diff_result.get("new_code"),
                                "old_code": diff_result.get("old_code"),
                            }

                    # Log messages after processing
                    if user_message_log:
                        sessions[session_id]["messages"].append(user_message_log)
                    if agent_response_log:
                        sessions[session_id]["messages"].append(agent_response_log)

                # --- Other Actions (Do not require lock within this block) ---
                elif action == "upload_file":  # Usually fast, might not need lock
                    filename = data.get("filename")
                    content = data.get("content", "")
                    if filename:
                        if filename in sessions[session_id]["workspace"]:
                            logger.info(f"Overwriting existing file '{filename}'.")
                        else:
                            logger.info(f"Creating new file '{filename}'.")
                        sessions[session_id]["workspace"][filename] = content
                        response = {
                            "status": "success",
                            "action": "file_uploaded",  # Use different action name
                            "filename": filename,
                            "files": list(
                                sessions[session_id]["workspace"].keys()
                            ),  # Send updated list
                        }
                    else:
                        logger.error("Upload_file action missing filename.")
                        response = {"status": "error", "error": "Missing filename"}

                elif action == "list_files":  # Read-only, no lock needed
                    files = list(sessions[session_id]["workspace"].keys())
                    logger.info(f"Listing files: {files}")
                    response = {
                        "status": "success",
                        "action": "file_list",
                        "files": files,
                    }

                elif action == "read_file":  # Read-only, no lock needed
                    filename = data.get("filename")
                    content = sessions[session_id]["workspace"].get(filename)
                    if content is not None:
                        logger.info(f"Reading file '{filename}'.")
                        response = {
                            "status": "success",
                            "action": "file_content",  # Use different action name
                            "filename": filename,
                            "content": content,
                        }
                    else:
                        logger.warning(f"Tried to read non-existent file: {filename}")
                        response = {"status": "error", "error": "File not found"}

                elif action == "apply_diff":
                    filename = data.get("filename")
                    diff = data.get("diff", "")
                    if filename and filename in sessions[session_id]["workspace"]:
                        from unified_diff import (
                            apply_patch,  # Keep import local if only used here
                        )

                        current_code = sessions[session_id]["workspace"][filename]
                        try:
                            # Preprocessing might be needed if agent doesn't format perfectly
                            patch = agent.preprocess_diff(diff)
                            new_code = apply_patch(current_code, patch)
                            logger.info(f"Applying diff to file '{filename}'.")
                            # Update workspace (critical section)
                            sessions[session_id]["workspace"][filename] = new_code
                            response = {
                                "status": "success",
                                "action": "diff_applied",  # Use different action name
                                "filename": filename,
                                "new_code": new_code,
                            }
                        except Exception as e:
                            logger.error(
                                f"Patch failed for file '{filename}': {e}. Diff: {diff!r}"
                            )
                            response = {
                                "status": "error",
                                "error": f"Patch failed: {e}",
                                "action": "apply_diff_error",
                            }
                    else:
                        logger.warning(
                            f"Tried to apply diff to non-existent/invalid file: {filename}"
                        )
                        response = {
                            "status": "error",
                            "error": "File not found or invalid for diff",
                            "action": "apply_diff_error",
                        }

                # Send back structured response
                logger.info(f"Sending response: {response}")
                await websocket.send_json(response)

            finally:
                # --- Release Lock if it was acquired ---
                if needs_lock and session_lock.locked():
                    session_lock.release()
                    logger.debug(f"Session {session_id} lock released.")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}.")
        # Clean up session on disconnect
        if session_id in sessions:
            # Ensure lock is released if held during disconnect
            if sessions[session_id]["lock"].locked():
                sessions[session_id]["lock"].release()
            del sessions[session_id]
            logger.info(f"Session {session_id} state cleaned up.")
    except Exception as e:  # Catch other potential errors in the loop
        logger.error(
            f"Unhandled error in WebSocket loop for session {session_id}: {e}",
            exc_info=True,
        )
        # Attempt to inform client before disconnecting or closing
        try:
            await websocket.send_json(
                {"status": "error", "error": f"Internal server error: {e}"}
            )
        except:
            pass  # Ignore if send fails (connection likely already closed)
        # Clean up session on unhandled error
        if session_id in sessions:
            if sessions[session_id]["lock"].locked():
                sessions[session_id]["lock"].release()
            del sessions[session_id]
            logger.info(f"Session {session_id} state cleaned up due to error.")


# For local testing
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
