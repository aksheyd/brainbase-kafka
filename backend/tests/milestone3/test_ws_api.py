import json

import pytest
import websockets

WS_URL = "ws://localhost:8000/ws"


@pytest.mark.asyncio
async def test_prompt(monkeypatch):
    # Patch agent to return predictable code
    from agent.agent import BasedAgent

    monkeypatch.setattr(
        BasedAgent, "generate_based_code", lambda self, prompt: "state = {}\n"
    )
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({"action": "prompt", "prompt": "Say hello"}))
        response = await ws.recv()
        data = json.loads(response)
        assert data["status"] == "success"
        assert data["action"] == "prompt"
        assert "code" in data


@pytest.mark.asyncio
async def test_upload_and_list_files():
    async with websockets.connect(WS_URL) as ws:
        await ws.send(
            json.dumps(
                {
                    "action": "upload_file",
                    "filename": "test.based",
                    "content": "state = {}",
                }
            )
        )
        response = await ws.recv()
        data = json.loads(response)
        assert data["status"] == "success"
        await ws.send(json.dumps({"action": "list_files"}))
        response = await ws.recv()
        data = json.loads(response)
        assert data["status"] == "success"
        assert "test.based" in data["files"]


@pytest.mark.asyncio
async def test_read_file():
    async with websockets.connect(WS_URL) as ws:
        await ws.send(
            json.dumps(
                {
                    "action": "upload_file",
                    "filename": "test2.based",
                    "content": "state = {}",
                }
            )
        )
        await ws.recv()
        await ws.send(json.dumps({"action": "read_file", "filename": "test2.based"}))
        response = await ws.recv()
        data = json.loads(response)
        assert data["status"] == "success"
        assert data["filename"] == "test2.based"
        assert data["content"] == "state = {}"


@pytest.mark.asyncio
async def test_update_context():
    async with websockets.connect(WS_URL) as ws:
        await ws.send(
            json.dumps({"action": "update_context", "context": {"foo": "bar"}})
        )
        response = await ws.recv()
        data = json.loads(response)
        assert data["status"] == "success"
        assert data["context"]["foo"] == "bar"
