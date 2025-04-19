# Main entrypoint for Kafka backend (Milestone 1)
# This will handle incoming requests and coordinate agent logic and validation.

from agent.agent import BasedAgent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI()
agent = BasedAgent()

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
    sessions[session_id] = {"messages": [], "code": ""}
    try:
        while True:
            data = await websocket.receive_text()
            # Store message in session
            sessions[session_id]["messages"].append(data)
            # For now, just echo back the message and session log
            await websocket.send_json(
                {
                    "echo": data,
                    "session_messages": sessions[session_id]["messages"],
                    "code": sessions[session_id]["code"],
                }
            )
    except WebSocketDisconnect:
        del sessions[session_id]


# For local testing
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
