import sys

from dotenv import load_dotenv
from fastapi.testclient import TestClient

sys.path.insert(0, ".")
from main import app

load_dotenv()
client = TestClient(app)


def test_generate_based_code_success(monkeypatch):
    # Simulate LLM output that passes validation on first try
    from backend.agent.agent import BasedAgent

    agent = BasedAgent()
    monkeypatch.setattr(
        agent,
        "llm",
        type(
            "LLM",
            (),
            {
                "invoke": lambda self, msgs: type(
                    "Resp", (), {"content": "state = {}"}
                )()
            },
        )(),
    )
    monkeypatch.setattr(agent, "validate_code", lambda code: {"status": "success"})
    code = agent.generate_based_code("test prompt")
    assert code == "state = {}"


def test_generate_based_code_iterates(monkeypatch):
    # Simulate LLM output that fails validation once, then passes
    from backend.agent.agent import BasedAgent

    agent = BasedAgent()
    outputs = iter(["bad code", "good code"])

    def fake_invoke(self, msgs):
        return type("Resp", (), {"content": next(outputs)})()

    monkeypatch.setattr(agent, "llm", type("LLM", (), {"invoke": fake_invoke})())

    def fake_validate(code):
        if code == "bad code":
            return {"status": "fail", "error": "Syntax error"}
        return {"status": "success"}

    monkeypatch.setattr(agent, "validate_code", fake_validate)
    code = agent.generate_based_code("test prompt")
    assert code == "good code"


def test_generate_based_code_max_iterations(monkeypatch):
    # Simulate LLM output that always fails validation
    from backend.agent.agent import MAX_ITER, BasedAgent

    agent = BasedAgent()
    outputs = (f"bad code {i}" for i in range(MAX_ITER))

    def fake_invoke(self, msgs):
        return type("Resp", (), {"content": next(outputs)})()

    monkeypatch.setattr(agent, "llm", type("LLM", (), {"invoke": fake_invoke})())
    monkeypatch.setattr(
        agent, "validate_code", lambda code: {"status": "fail", "error": "Syntax error"}
    )
    code = agent.generate_based_code("test prompt")
    assert code.startswith("bad code")


def test_generate_based_code_missing_prompt():
    response = client.post("/generate", json={})
    assert response.status_code == 422  # Unprocessable Entity
