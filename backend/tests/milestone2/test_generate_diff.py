import itertools
import sys

sys.path.insert(0, ".")
from agent.agent import MAX_ITER, BasedAgent


# Helper: fake patch application
class PatchError(Exception):
    pass


def test_generate_based_diff_success(monkeypatch):
    agent = BasedAgent()
    # LLM returns a valid diff, patch applies, validation passes
    monkeypatch.setattr(
        agent,
        "llm",
        type(
            "LLM",
            (),
            {"invoke": lambda self, msgs: type("Resp", (), {"content": "diff-ok"})()},
        )(),
    )
    monkeypatch.setattr(
        "backend.unified_diff.apply_patch", lambda code, diff: "new code"
    )
    monkeypatch.setattr(agent, "validate_code", lambda code: {"status": "success"})
    diff = agent.generate_based_diff("old code", "add a feature")
    assert diff == "diff-ok"


def test_generate_based_diff_diff_format_error(monkeypatch):
    agent = BasedAgent()
    # First diff is bad (raises), second is good, then always good
    outputs = itertools.chain(["bad-diff", "good-diff"], itertools.repeat("good-diff"))

    def fake_invoke(self, msgs):
        return type("Resp", (), {"content": next(outputs)})()

    monkeypatch.setattr(agent, "llm", type("LLM", (), {"invoke": fake_invoke})())

    def fake_patch(code, diff):
        if diff == "bad-diff":
            raise PatchError("bad format")
        return "patched code"

    monkeypatch.setattr("backend.unified_diff.apply_patch", fake_patch)
    monkeypatch.setattr(agent, "validate_code", lambda code: {"status": "success"})
    diff = agent.generate_based_diff("old code", "fix bug")
    assert diff == "good-diff"


def test_generate_based_diff_validation_error(monkeypatch):
    agent = BasedAgent()
    # Patch applies, but validation fails once, then passes, then always passes
    outputs = itertools.chain(["diff1", "diff2"], itertools.repeat("diff2"))

    def fake_invoke(self, msgs):
        return type("Resp", (), {"content": next(outputs)})()

    monkeypatch.setattr(agent, "llm", type("LLM", (), {"invoke": fake_invoke})())
    monkeypatch.setattr(
        "backend.unified_diff.apply_patch", lambda code, diff: f"patched-{diff}"
    )

    def fake_validate(code):
        if code == "patched-diff1":
            return {"status": "fail", "error": "bad"}
        return {"status": "success"}

    monkeypatch.setattr(agent, "validate_code", fake_validate)
    diff = agent.generate_based_diff("old code", "improve")
    assert diff == "diff2"


def test_generate_based_diff_max_iterations(monkeypatch):
    agent = BasedAgent()
    # Always fails validation
    outputs = itertools.chain(
        (f"diff{i}" for i in range(MAX_ITER)), itertools.repeat(f"diff{MAX_ITER - 1}")
    )

    def fake_invoke(self, msgs):
        return type("Resp", (), {"content": next(outputs)})()

    monkeypatch.setattr(agent, "llm", type("LLM", (), {"invoke": fake_invoke})())
    monkeypatch.setattr(
        "backend.unified_diff.apply_patch", lambda code, diff: f"patched-{diff}"
    )
    monkeypatch.setattr(
        agent, "validate_code", lambda code: {"status": "fail", "error": "bad"}
    )
    diff = agent.generate_based_diff("old code", "fail always")
    assert diff.startswith("diff")
