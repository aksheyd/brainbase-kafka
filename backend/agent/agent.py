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

    def classify_prompt_intent(
        self,
        prompt: str,
        context: list | None,
        history: list | None,
        file_list: list[str],
    ) -> dict:
        """
        Classifies the user's intent (CREATE_FILE or EDIT_FILE) based on the prompt and context.
        If CREATE_FILE, also extracts a description for filename generation.
        """
        history_str = ""
        if history:
            formatted = []
            for msg in history:
                if msg.get("role") == "user":
                    formatted.append(f"User: {msg.get('prompt', '')}")
                elif msg.get("role") == "agent":
                    formatted.append(
                        f"Agent: {msg.get('code', '') or msg.get('diff', '') or msg.get('response', '')}"
                    )
            if formatted:
                history_str = "\\n\\nConversation history:\\n" + "\\n".join(formatted)

        context_str = ""
        if context:
            context_str = "\\n\\nContext:\\n" + "\\n".join(str(c) for c in context if c)

        file_list_str = (
            "\\n\\nExisting files:\\n" + "\\n".join(file_list)
            if file_list
            else "\\n\\nNo files exist yet."
        )

        # Simplified system prompt: Only CREATE_FILE or EDIT_FILE
        system_prompt = (
            "You are an AI assistant helping a user work with 'Based' code files. "
            "Analyze the user's latest prompt in the context of the conversation history and existing files. "
            "Determine the primary intent: CREATE_FILE or EDIT_FILE. "
            "1. CREATE_FILE: User explicitly wants to create a new Based file (e.g., 'create a file', 'make a new agent'). "
            "2. EDIT_FILE: User wants to modify an existing file or doesn't explicitly ask to create one (e.g., 'change x', 'add y', 'refactor', 'implement feature z'). Default to this if unsure. "
            "If the intent is CREATE_FILE, provide a concise description (2-5 words) of the file's purpose. "
            "Respond ONLY with a JSON object containing 'intent' (string: 'CREATE_FILE' or 'EDIT_FILE') and optionally 'description' (string) if the intent is CREATE_FILE. "
            'Example Response for CREATE_FILE: {"intent": "CREATE_FILE", "description": "simple weather chatbot"} '
            'Example Response for EDIT_FILE: {"intent": "EDIT_FILE"}'
        )

        user_message = f"{history_str}{context_str}{file_list_str}\\n\\nUser prompt: '{prompt}'\\n\\nDetermine the intent and respond ONLY with the JSON object."

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        logger.info(f"[Agent] Classifying intent (CREATE/EDIT) for prompt: {prompt!r}")
        try:
            response = self.llm.invoke(messages)
            content = self.strip_code_blocks(response.content).strip()
            logger.debug(f"[Agent] Raw intent classification response: {content!r}")
            import json

            try:
                intent_data = json.loads(content)
                # Check for valid intents ONLY
                if intent_data.get("intent") in ["CREATE_FILE", "EDIT_FILE"]:
                    logger.info(f"[Agent] Classified intent: {intent_data}")
                    return intent_data
                else:
                    logger.warning(
                        f"[Agent] LLM returned invalid intent structure: {content}. Defaulting to EDIT_FILE."
                    )
                    return {"intent": "EDIT_FILE"}
            except json.JSONDecodeError:
                logger.error(
                    f"[Agent] Failed to parse intent JSON from LLM: {content}. Defaulting to EDIT_FILE."
                )
                return {"intent": "EDIT_FILE"}
        except Exception as e:
            logger.error(f"[Agent] Error during intent classification LLM call: {e}")
            return {"intent": "EDIT_FILE"}

    def generate_filename(self, description: str) -> str:
        """
        Generates a suitable filename (e.g., 'my-agent.based') from a description.
        """
        system_prompt = (
            "You are a filename generation assistant. Given a description of a file's purpose, "
            "create a concise, lowercase, dash-separated filename consisting of 1-3 words. "
            "The filename MUST end with the '.based' extension. "
            "Respond ONLY with the generated filename string. "
            "Example Input: 'simple weather chatbot' Example Output: 'weather-chatbot.based' "
            "Example Input: 'utility functions' Example Output: 'utils.based'"
        )
        user_message = f"Description: '{description}'\\n\\nGenerate the filename."

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        logger.info(f"[Agent] Generating filename for description: {description!r}")
        try:
            response = self.llm.invoke(messages)
            filename = self.strip_code_blocks(response.content).strip().lower()
            # Basic validation
            if (
                filename.endswith(".based")
                and " " not in filename
                and "/" not in filename
                and len(filename) > 6
            ):
                logger.info(f"[Agent] Generated filename: {filename}")
                return filename
            else:
                logger.warning(
                    f"[Agent] LLM generated invalid filename: {filename}. Using fallback."
                )
                # Fallback: create a safe name from description
                import re

                safe_name = re.sub(r"[^a-z0-9]+", "-", description.lower()).strip("-")
                safe_name = re.sub(r"-+", "-", safe_name)  # Collapse multiple dashes
                if not safe_name:
                    safe_name = "agent"  # Absolute fallback
                return f"{safe_name[:30]}.based"  # Limit length

        except Exception as e:
            logger.error(
                f"[Agent] Error during filename generation LLM call: {e}. Using fallback."
            )
            # Fallback: create a safe name from description
            import re

            safe_name = re.sub(r"[^a-z0-9]+", "-", description.lower()).strip("-")
            safe_name = re.sub(r"-+", "-", safe_name)  # Collapse multiple dashes
            if not safe_name:
                safe_name = "agent"  # Absolute fallback
            return f"{safe_name[:30]}.based"  # Limit length

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
