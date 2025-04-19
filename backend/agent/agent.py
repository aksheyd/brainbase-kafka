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

    def generate_based_code(self, prompt: str) -> str:
        user_prompt = f"{prompt}\n\nOnly output valid Based code. Do not include any explanation or extra text."
        system_message = SystemMessage(content=BASED_GUIDE + STRICT_INSTRUCTION)
        last_code = None
        last_error = None
        for i in range(MAX_ITER):
            messages = [system_message, HumanMessage(content=user_prompt)]
            response = self.llm.invoke(messages)
            code = response.content
            last_code = code
            validation = self.validate_code(code)
            logger.info(f"Iteration {i + 1} LLM output:\n{code}")
            logger.info(f"Iteration {i + 1} validation result: {validation}")
            if validation.get("status") == "success":
                logger.info(
                    f"Valid Based code generated in {i + 1} iteration(s). Returning result."
                )
                return validation.get("converted_code", code)
            # If failed, update prompt with error feedback
            last_error = validation.get("error") or str(validation)
            user_prompt = (
                f"{prompt}\n\nThe following validation error was returned: {last_error}\n"
                "Please fix the code. Only output valid Based code. Do not include any explanation or extra text."
            )
        logger.warning(
            f"Failed to generate valid Based code after {MAX_ITER} iterations. Returning last attempt."
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

    def generate_based_diff(self, current_code: str, prompt: str) -> str:
        """
        Generate a unified diff to modify current_code according to the prompt.
        Iterates up to MAX_ITER times on diff/validation errors.
        Returns the valid unified diff (as a string) or the last attempted diff if all fail.
        """
        diff_instructions = (
            "When generating a unified diff, unchanged lines must start with a space, "
            "removed lines with '-', and added lines with '+'. Do not omit the space for unchanged lines. "
            "The diff should be valid and directly applicable using the standard unified diff format."
        )
        user_prompt = (
            f"Given the following Based code, generate a unified diff (patch) to implement this user request: '{prompt}'.\n"
            f"{diff_instructions}\n"
            "Only output a valid unified diff. Do not include any explanation or extra text.\n"
            "Current Based code:\n" + current_code
        )
        system_message = SystemMessage(content=BASED_GUIDE + STRICT_INSTRUCTION)
        last_diff = None
        last_error = None
        for i in range(MAX_ITER):
            messages = [system_message, HumanMessage(content=user_prompt)]
            response = self.llm.invoke(messages)
            diff = response.content
            last_diff = diff
            logger.info(f"Iteration {i + 1} LLM diff output:\n{diff}")
            # Preprocess the diff before applying
            patch = self.preprocess_diff(diff)
            # Try to apply the diff
            try:
                new_code = apply_patch(current_code, patch)
            except Exception as e:
                logger.warning(f"Iteration {i + 1} diff application failed: {e}")
                user_prompt = (
                    f"The previous diff could not be applied due to this error: {e}. "
                    f"{diff_instructions}\n"
                    "Please output a valid unified diff for the request. Do not include any explanation or extra text.\n"
                    f"Current Based code:\n{current_code}"
                )
                continue
            # Validate the new code
            validation = self.validate_code(new_code)
            logger.info(f"Iteration {i + 1} validation result: {validation}")
            if validation.get("status") == "success":
                logger.info(
                    f"Valid Based code diff generated in {i + 1} iteration(s). Returning diff."
                )
                return diff
            # If failed, update prompt with error feedback
            last_error = validation.get("error") or str(validation)
            user_prompt = (
                f"Given the following Based code, generate a unified diff (patch) to implement this user request: '{prompt}'.\n"
                f"The previous diff, when applied, produced code that failed validation with this error: {last_error}. "
                f"{diff_instructions}\n"
                "Please output a valid unified diff. Do not include any explanation or extra text.\n"
                f"Current Based code:\n{current_code}"
            )
        logger.warning(
            f"Failed to generate valid Based code diff after {MAX_ITER} iterations. Returning last attempted diff."
        )
        return last_diff
