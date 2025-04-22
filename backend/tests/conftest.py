import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")
from agent.agent import BasedAgent


@pytest.fixture
def agent():
    """Provides a BasedAgent instance with a mocked LLM for testing."""
    # Mock the LLM initialization within the agent
    with patch("agent.agent.ChatGoogleGenerativeAI") as MockLLM:
        # Ensure GOOGLE_API_KEY check passes during init
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"}):
            instance = BasedAgent()
            # Replace the actual LLM instance with a mock
            instance.llm = MagicMock()
            return instance
