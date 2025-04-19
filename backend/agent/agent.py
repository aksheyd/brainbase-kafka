import logging
import os
import sys

import requests

sys.path.insert(0, ".")

from config import MODEL_CODE
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from unified_diff import apply_patch

load_dotenv()

BASED_GUIDE_PATH = os.path.join(os.path.dirname(__file__), "BASED_GUIDE.md")
with open(BASED_GUIDE_PATH, "r") as f:
    BASED_GUIDE = f.read()

STRICT_INSTRUCTION = (
    "\n\nIMPORTANT: At all times, your output must be valid Based code only. "
    "Do not include explanations, comments, or any text outside of Based code blocks."
    "Always use Based looping and avoid While True loops."
)

VALIDATION_URL = "https://brainbase-engine-python.onrender.com/validate"
MAX_ITER = 5

# Configure logging to write to a file
LOG_PATH = os.path.join(os.path.dirname(__file__), "agent.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class BasedAgent:
    def __init__(self):
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        self.llm = ChatGoogleGenerativeAI(model=MODEL_CODE)

    def validate_code(self, code: str) -> dict:
        resp = requests.post(
            VALIDATION_URL,
            json={"code": code},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def strip_code_blocks(self, text: str) -> str:
        # Remove all triple backtick code block formatting
        import re

        # Remove ``` and optional language specifier
        return re.sub(r"```[a-zA-Z]*\n?|```", "", text)

    def generate_based_code(self, prompt: str, context=None, history=None) -> str:
        history_str = ""
        if history:
            # Format history as readable chat log
            formatted = []
            for msg in history:
                if msg.get("role") == "user":
                    formatted.append(f"User: {msg.get('prompt', '')}")
                elif msg.get("role") == "agent":
                    formatted.append(f"Agent: {msg.get('code', '')}")
            if formatted:
                history_str = "\n\nConversation history:\n" + "\n".join(formatted)
        context_str = ""
        if context:
            if isinstance(context, list):
                context_str = "\n\nContext:\n" + "\n".join(str(c) for c in context if c)
            elif isinstance(context, str):
                context_str = f"\n\nContext:\n{context}"
        user_prompt = f"{history_str}\n\n{prompt}{context_str}\n\nOnly output valid Based code. Do not include any explanation or extra text."
        system_message = SystemMessage(content=BASED_GUIDE + STRICT_INSTRUCTION)
        last_code = None
        last_error = None
        logger.info(
            f"[Agent] generate_based_code called. Prompt: {prompt!r} | Context: {context!r} | History: {history!r}"
        )
        for i in range(MAX_ITER):
            messages = [system_message, HumanMessage(content=user_prompt)]
            response = self.llm.invoke(messages)
            code = self.strip_code_blocks(response.content)
            last_code = code
            validation = self.validate_code(code)
            logger.info(f"[Agent] Iteration {i + 1} validation result: {validation}")
            if validation.get("status") == "success":
                logger.info(
                    f"[Agent] Valid Based code generated in {i + 1} iteration(s). Returning result."
                )
                return validation.get("converted_code", code)
            # If failed, update prompt with error feedback
            last_error = validation.get("error") or str(validation)
            user_prompt = (
                f"{history_str}\n\n{prompt}{context_str}\n\nThe following validation error was returned: {last_error}\n"
                "Please fix the code. Only output valid Based code. Do not include any explanation or extra text."
            )
        logger.warning(
            f"[Agent] Failed to generate valid Based code after {MAX_ITER} iterations. Returning last attempt."
        )
        return last_code

    def preprocess_diff(self, diff: str) -> str:
        lines = diff.splitlines()
        # Remove markdown code block tags
        lines = [line for line in lines if not line.strip().startswith("```")]
        # Strip leading spaces ONLY from header lines
        for i, line in enumerate(lines):
            if line.lstrip().startswith(("---", "+++", "@@")):
                lines[i] = line.lstrip()
        # Remove leading file name lines if present
        if lines and lines[0].startswith("--- "):
            if len(lines) > 1 and lines[1].startswith("+++ "):
                lines = lines[2:]
            else:
                lines = lines[1:]
        return "\n".join(lines)

    def generate_based_diff(
        self, current_code: str, prompt: str, context=None, history=None
    ) -> dict:
        """
        Generate a unified diff to modify current_code according to the prompt.
        Iterates up to MAX_ITER times on diff/validation errors.
        Returns a dict with the valid unified diff (as a string), the new code, and the old code.
        """
        diff_instructions = (
            "When generating a unified diff, unchanged lines must start with a space, "
            "removed lines with '-', and added lines with '+'. Do not omit the space for unchanged lines. "
            "The diff should be valid and directly applicable using the standard unified diff format."
        )
        history_str = ""
        if history:
            formatted = []
            for msg in history:
                if msg.get("role") == "user":
                    formatted.append(f"User: {msg.get('prompt', '')}")
                elif msg.get("role") == "agent":
                    formatted.append(f"Agent: {msg.get('code', '')}")
            if formatted:
                history_str = "\n\nConversation history:\n" + "\n".join(formatted)
        context_str = ""
        if context:
            if isinstance(context, list):
                context_str = "\n\nContext:\n" + "\n".join(str(c) for c in context if c)
            elif isinstance(context, str):
                context_str = f"\n\nContext:\n{context}"
        user_prompt = (
            f"{history_str}\n\nGiven the following Based code, generate a unified diff (patch) to implement this user request: '{prompt}'."
            f"{context_str}\n"
            f"{diff_instructions}\n"
            "Only output a valid unified diff. Do not include any explanation or extra text.\n"
            "Current Based code:\n" + current_code
        )
        system_message = SystemMessage(content=BASED_GUIDE + STRICT_INSTRUCTION)
        last_diff = None
        last_error = None
        last_new_code = None
        logger.info(
            f"[Agent] generate_based_diff called. Prompt: {prompt!r} | Context: {context!r} | History: {history!r}"
        )
        for i in range(MAX_ITER):
            messages = [system_message, HumanMessage(content=user_prompt)]
            response = self.llm.invoke(messages)
            diff = self.strip_code_blocks(response.content)
            last_diff = diff
            patch = self.preprocess_diff(diff)
            try:
                new_code = apply_patch(current_code, patch)
                last_new_code = new_code
            except Exception as e:
                logger.warning(
                    f"[Agent] Iteration {i + 1} diff application failed: {e}"
                )
                user_prompt = (
                    f"{history_str}\n\nThe previous diff could not be applied due to this error: {e}. "
                    f"{context_str}\n"
                    f"{diff_instructions}\n"
                    "Please output a valid unified diff for the request. Do not include any explanation or extra text.\n"
                    f"Current Based code:\n{current_code}"
                )
                continue
            validation = self.validate_code(new_code)
            logger.info(
                f"[Agent] Iteration {i + 1} diff validation result: {validation}"
            )
            if validation.get("status") == "success":
                logger.info(
                    f"[Agent] Valid Based code diff generated in {i + 1} iteration(s). Returning diff, new_code, and old_code."
                )
                return {"diff": diff, "new_code": new_code, "old_code": current_code}
            last_error = validation.get("error") or str(validation)
            user_prompt = (
                f"{history_str}\n\nGiven the following Based code, generate a unified diff (patch) to implement this user request: '{prompt}'.\n"
                f"{context_str}\n"
                f"The previous diff, when applied, produced code that failed validation with this error: {last_error}. "
                f"{diff_instructions}\n"
                "Please output a valid unified diff. Do not include any explanation or extra text.\n"
                f"Current Based code:\n{current_code}"
            )
        logger.warning(
            f"[Agent] Failed to generate valid Based code diff after {MAX_ITER} iterations. Returning last attempted diff."
        )
        return {
            "diff": last_diff,
            "new_code": last_new_code if last_new_code is not None else current_code,
            "old_code": current_code,
        }
