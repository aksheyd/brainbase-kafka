# Main entrypoint for Kafka backend (Milestone 1)
# This will handle incoming requests and coordinate agent logic and validation.

import json
import logging
import sys

sys.path.append(".")
from agent.agent import BasedAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

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


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    code: str


class GenerateDiffRequest(BaseModel):
    current_code: str
    prompt: str


class GenerateDiffResponse(BaseModel):
    diff: str


@app.post("/generate")
def generate_based_code(request: GenerateRequest):
    code = agent.generate_based_code(request.prompt)
    return code


@app.post("/generate-diff", response_model=GenerateDiffResponse)
def generate_based_diff(request: GenerateDiffRequest):
    diff = agent.generate_based_diff(request.current_code, request.prompt)
    return GenerateDiffResponse(diff=diff)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = id(websocket)
    sessions[session_id] = {
        "messages": [],
        "workspace": {
            "agent.based": ""  # Initialize with an empty agent.based file
        },
        "context": [],
    }
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                logger.info(f"Received action: {data.get('action')} | Data: {data}")
            except Exception as e:
                logger.error(f"Invalid JSON received: {msg}")
                await websocket.send_json(
                    {"status": "error", "error": f"Invalid JSON: {e}"}
                )
                continue
            action = data.get("action")
            response = {"status": "error", "error": "Unknown action"}
            # Handle each action type
            if action == "prompt":
                prompt = data.get("prompt", "")
                context = data.get("context", "")
                if context:
                    sessions[session_id]["context"].append(context)
                # Pass context and history to agent
                code = agent.generate_based_code(
                    prompt,
                    sessions[session_id]["context"],
                    history=sessions[session_id]["messages"],
                )
                sessions[session_id]["messages"].append(
                    {"role": "user", "prompt": prompt, "context": context}
                )
                sessions[session_id]["messages"].append({"role": "agent", "code": code})
                # Optionally update a file in workspace
                filename = data.get("filename")
                if filename:
                    if filename in sessions[session_id]["workspace"]:
                        logger.info(f"Updating file '{filename}' in workspace.")
                        sessions[session_id]["workspace"][filename] = code
                    else:
                        logger.warning(
                            f"[WARN] Tried to update non-existent file: {filename}. Workspace files: {list(sessions[session_id]['workspace'].keys())}"
                        )
                response = {
                    "status": "success",
                    "action": "prompt",
                    "code": code,
                    "session": sessions[session_id],
                }
            elif action == "generate_diff":
                prompt = data.get("prompt", "")
                current_code = data.get("current_code", "")
                context = data.get("context", "")
                if context:
                    sessions[session_id]["context"].append(context)
                diff_result = agent.generate_based_diff(
                    current_code,
                    prompt,
                    sessions[session_id]["context"],
                    history=sessions[session_id]["messages"],
                )
                # diff_result is a dict with keys: diff, new_code, old_code
                response = {
                    "status": "success",
                    "action": "generate_diff",
                    "diff": diff_result.get("diff"),
                    "new_code": diff_result.get("new_code"),
                    "old_code": diff_result.get("old_code"),
                    "session": sessions[session_id],
                }
            elif action == "upload_file":
                filename = data.get("filename")
                content = data.get("content", "")
                if filename:
                    if filename in sessions[session_id]["workspace"]:
                        logger.info(
                            f"Overwriting existing file '{filename}' in workspace."
                        )
                    else:
                        logger.info(f"Creating new file '{filename}' in workspace.")
                    sessions[session_id]["workspace"][filename] = content
                    response = {
                        "status": "success",
                        "action": "upload_file",
                        "filename": filename,
                    }
                else:
                    logger.error("Upload_file action missing filename.")
                    response = {"status": "error", "error": "Missing filename"}
            elif action == "list_files":
                files = list(sessions[session_id]["workspace"].keys())
                logger.info(f"Listing files: {files}")
                response = {"status": "success", "action": "list_files", "files": files}
            elif action == "read_file":
                filename = data.get("filename")
                content = sessions[session_id]["workspace"].get(filename)
                if content is not None:
                    logger.info(f"Reading file '{filename}' from workspace.")
                    response = {
                        "status": "success",
                        "action": "read_file",
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
                    from unified_diff import apply_patch

                    current_code = sessions[session_id]["workspace"][filename]
                    try:
                        patch = agent.preprocess_diff(diff)
                        new_code = apply_patch(current_code, patch)
                        logger.info(f"Applying diff to file '{filename}'.")
                        sessions[session_id]["workspace"][filename] = new_code
                        response = {
                            "status": "success",
                            "action": "apply_diff",
                            "filename": filename,
                            "new_code": new_code,
                        }
                    except Exception as e:
                        logger.error(f"Patch failed for file '{filename}': {e}")
                        response = {"status": "error", "error": f"Patch failed: {e}"}
                else:
                    logger.warning(
                        f"Tried to apply diff to non-existent file: {filename}"
                    )
                    response = {"status": "error", "error": "File not found"}
            elif action == "update_context":
                context = data.get("context", "")
                sessions[session_id]["context"].append(context)
                logger.info(f"Updated context for session {session_id}.")
                response = {
                    "status": "success",
                    "action": "update_context",
                    "context": sessions[session_id]["context"],
                }
            # Send back structured response
            logger.info(f"Sending response for action '{action}': {response}")
            await websocket.send_json(response)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}.")
        del sessions[session_id]


# For local testing
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
