# backend/agent.py
# LangChain x Gemini to handle creation of based code, based diffs, intent
#   classification, and filename generation

import json
import logging
import os
import re
import sys

import requests

sys.path.insert(0, ".")  # for imports inside non-main folder

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.unified_diff import apply_patch

load_dotenv()


# --- Constants ---
BASED_GUIDE_PATH = os.path.join(os.path.dirname(__file__), "BASED_GUIDE.md")
with open(BASED_GUIDE_PATH, "r") as f:
    BASED_GUIDE = f.read()

# Can change this to other gemini models or can change LLM in init
MODEL_CODE = "gemini-2.0-flash"

# Instruction appended to LLM prompts to ensure output is only code.
STRICT_INSTRUCTION = (
    "\n\nIMPORTANT: At all times, your output must be valid Based code only. "
    "Do not include explanations, comments, or any text outside of Based code blocks."
)

# URL for the external Based code validation service.
VALIDATION_URL = "https://brainbase-engine-python.onrender.com/validate"
# Maximum number of attempts for validation loops.
MAX_ITER = 5

# --- Logging Setup ---
LOG_PATH = os.path.join(os.path.dirname(__file__), "agent.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class BasedAgent:
    """
    An agent responsible for generating and modifying Based code using an LLM,
    handling intent classification, filename generation, code validation,
    and diff generation/application.
    """

    def __init__(self):
        """Initializes the BasedAgent with a Google Generative AI LLM."""
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        self.llm = ChatGoogleGenerativeAI(model=MODEL_CODE)

    def validate_code(self, code: str) -> dict:
        """
        Validates the provided Based code using an external service.

        Args:
            code: The Based code string to validate.

        Returns:
            A dictionary containing the validation status ('success' or 'fail')
            and potentially an 'error' message or 'converted_code'.

        Raises:
            requests.exceptions.RequestException: If the validation request fails.
        """
        resp = requests.post(
            VALIDATION_URL,
            json={"code": code},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def strip_code_blocks(self, text: str) -> str:
        """
        Removes Markdown code block fences (```) from a string.

        Args:
            text: The input string potentially containing code blocks.

        Returns:
            The string with code block fences removed.
        """
        # Remove triple backticks and optional language identifiers
        return re.sub(r"```[a-zA-Z]*\n?|```", "", text).strip()

    def _format_history_for_prompt(self, history: list | None) -> str:
        """Formats conversation history into a string for LLM prompts."""
        if not history:
            return ""
        formatted = []
        for msg in history:
            role = msg.get("role")
            content = ""
            if role == "user":
                content = f"User: {msg.get('prompt', '')}"
            elif role == "agent":
                # Describe the agent's action instead of code to reduce context window size
                if msg.get("code"):
                    agent_action = "[Generated initial code]"
                elif msg.get("diff"):
                    agent_action = "[Generated diff]"
                else:
                    agent_action = msg.get("response", "[Agent response]")
                content = f"Agent: {agent_action} for file {msg.get('filename', 'N/A')}"

            if content:
                formatted.append(content)

        return "\n\nConversation history:\n" + "\n".join(formatted) if formatted else ""

    def _format_context_for_prompt(self, context: list | str | None) -> str:
        """Formats context information into a string for LLM prompts."""
        if not context:
            return ""
        if isinstance(context, list):
            # Filter out empty context items
            context_items = [str(c) for c in context if c]
            return "\n\nContext:\n" + "\n".join(context_items) if context_items else ""
        elif isinstance(context, str):
            return f"\n\nContext:\n{context}"

    def classify_prompt_intent(
        self,
        prompt: str,
        context: list | None,
        history: list | None,
        file_list: list[str],
    ) -> dict:
        """
        Classifies the user's intent (CREATE_FILE or EDIT_FILE) using an LLM.

        Analyzes the prompt along with conversation history, context, and existing
        files to determine if the user wants to create a new file or edit an
        existing one.

        Args:
            prompt: The user's latest input prompt.
            context: Additional context information.
            history: The conversation history.
            file_list: A list of existing filenames in the workspace.

        Returns:
            A dictionary containing the classified 'intent' (string: 'CREATE_FILE'
            or 'EDIT_FILE') and optionally a 'description' (string) if the intent
            is CREATE_FILE. Defaults to {'intent': 'EDIT_FILE'} on failure.
        """
        history_str = self._format_history_for_prompt(history)
        context_str = self._format_context_for_prompt(context)
        file_list_str = (
            "\n\nExisting files:\n" + "\n".join(file_list)
            if file_list
            else "\n\nNo files exist yet."
        )

        # System prompt guides the LLM on how to classify the intent
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

        # User message provides all necessary information for classification
        user_message = f"{history_str}{context_str}{file_list_str}\n\nUser prompt: '{prompt}'\n\nDetermine the intent and respond ONLY with the JSON object."

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        logger.info(f"[Agent] Classifying intent (CREATE/EDIT) for prompt: {prompt!r}")
        try:
            response = self.llm.invoke(messages)
            # Strip potential markdown and whitespace
            content = self.strip_code_blocks(response.content).strip()
            logger.debug(f"[Agent] Raw intent classification response: {content!r}")

            # Attempt to parse the JSON response
            try:
                intent_data = json.loads(content)
                # Validate the structure and content of the response
                if intent_data.get("intent") in ["CREATE_FILE", "EDIT_FILE"]:
                    logger.info(f"[Agent] Classified intent: {intent_data}")
                    return intent_data
                else:
                    # Log warning if structure is invalid but parsable
                    logger.warning(
                        f"[Agent] LLM returned invalid intent structure: {content}. Defaulting to EDIT_FILE."
                    )
                    return {"intent": "EDIT_FILE"}
            except json.JSONDecodeError:
                # Log error if JSON parsing fails
                logger.error(
                    f"[Agent] Failed to parse intent JSON from LLM: {content}. Defaulting to EDIT_FILE."
                )
                return {"intent": "EDIT_FILE"}
        except Exception as e:
            # Default fallback to EDIT_FILE
            logger.error(f"[Agent] Error during intent classification LLM call: {e}")
            return {"intent": "EDIT_FILE"}

    def generate_filename(self, description: str) -> str:
        """
        Generates a suitable filename (e.g., 'my-agent.based') from a description using the LLM.

        Args:
            description: A short description of the file's purpose.

        Returns:
            A generated filename string ending in '.based'. Includes fallback logic
            for invalid LLM responses.
        """
        # System prompt guides the LLM on filename format
        system_prompt = (
            "You are a filename generation assistant. Given a description of a file's purpose, "
            "create a concise, lowercase, dash-separated filename consisting of 1-3 words. "
            "The filename MUST end with the '.based' extension. "
            "Respond ONLY with the generated filename string. "
            "Example Input: 'simple weather chatbot' Example Output: 'weather-chatbot.based' "
            "Example Input: 'utility agent' Example Output: 'util-agent.based'"
        )
        user_message = f"Description: '{description}'\n\nGenerate the filename."

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        logger.info(f"[Agent] Generating filename for description: {description!r}")
        try:
            response = self.llm.invoke(messages)
            filename = self.strip_code_blocks(response.content).strip().lower()

            # Basic validation for the generated filename
            is_valid = (
                filename.endswith(".based")
                and " " not in filename
                and "/" not in filename  # Basic check for path separators
                and len(filename) > 6  # e.g., 'a.based' is technically valid but short
            )

            if is_valid:
                logger.info(f"[Agent] Generated filename: {filename}")
                return filename
            else:
                logger.warning(
                    f"[Agent] LLM generated invalid filename: '{filename}'. Using fallback."
                )
                return self._create_fallback_filename(description)

        except Exception as e:
            logger.error(
                f"[Agent] Error during filename generation LLM call: {e}. Using fallback."
            )
            return self._create_fallback_filename(description)

    def _create_fallback_filename(self, description: str) -> str:
        """Creates a safe fallback filename from a description."""
        # Remove invalid characters, replace spaces with dashes
        safe_name = re.sub(r"[^a-z0-9]+", "-", description.lower()).strip("-")
        # Collapse multiple dashes into one
        safe_name = re.sub(r"-+", "-", safe_name)
        # Ensure filename is not empty
        if not safe_name:
            safe_name = "agent"  # Absolute fallback
        # Limit length and add extension
        return f"{safe_name[:20]}.based"

    def generate_based_code(self, prompt: str, context=None, history=None) -> str:
        """
        Generates Based code from a prompt, context, and history using the LLM.

        Iteratively prompts the LLM and validates the output, providing feedback
        on errors until valid code is generated or MAX_ITER is reached.

        Args:
            prompt: The user's prompt describing the desired code.
            context: Additional context information.
            history: The conversation history.

        Returns:
            The generated (and validated, if successful) Based code string.
            Returns the last attempt if validation fails after MAX_ITER.
        """
        history_str = self._format_history_for_prompt(history)
        context_str = self._format_context_for_prompt(context)

        # Initial user prompt for the first iteration
        user_prompt_content = f"{history_str}\n\nUser Request: {prompt}{context_str}\n\nOnly output valid Based code. Do not include any explanation or extra text."
        system_message = SystemMessage(content=BASED_GUIDE + STRICT_INSTRUCTION)

        last_code_attempt = ""
        last_error_message = ""

        logger.info(
            f"[Agent] generate_based_code called. Prompt: {prompt!r} | Context: {context!r} | History: {history!r}"
        )

        for i in range(MAX_ITER):
            logger.debug(f"[Agent] generate_based_code: Iteration {i + 1}/{MAX_ITER}")
            messages = [system_message, HumanMessage(content=user_prompt_content)]

            try:
                response = self.llm.invoke(messages)
                code_attempt = self.strip_code_blocks(response.content)
                last_code_attempt = code_attempt  # Store the latest attempt

                # Validate the generated code
                validation_result = self.validate_code(code_attempt)
                logger.info(
                    f"[Agent] Iteration {i + 1} validation result: {validation_result}"
                )

                if validation_result.get("status") == "success":
                    logger.info(
                        f"[Agent] Valid Based code generated in {i + 1} iteration(s). Returning result."
                    )
                    # Return the validated and potentially converted code
                    return validation_result.get("converted_code", code_attempt)

                # Prepare feedback for the next iteration if validation failed
                last_error_message = validation_result.get("error") or str(
                    validation_result
                )
                user_prompt_content = (
                    f"{history_str}\n\nUser Request: {prompt}{context_str}\n\n"
                    f"The previous code attempt failed validation with this error:\n{last_error_message}\n\n"
                    "Please fix the code. Only output valid Based code. Do not include any explanation or extra text."
                )

            except requests.exceptions.RequestException as req_err:
                logger.error(f"[Agent] Validation request failed: {req_err}")
                last_error_message = f"Validation service request failed: {req_err}"

                # For now, if network drops, just iterate again
                user_prompt_content = (
                    f"{history_str}\n\nUser Request: {prompt}{context_str}\n\n"
                    f"Could not validate the previous attempt due to a network error: {last_error_message}\n\n"
                    "Please try generating the code again. Only output valid Based code."
                )
            except Exception as llm_err:
                logger.error(f"[Agent] LLM invocation failed: {llm_err}")
                last_error_message = f"LLM call failed: {llm_err}"

                # If LLM fails, we can't easily continue the loop with feedback.
                # Break or return last known good state? For now, break and return last attempt.
                break

        # Loop finished without success
        logger.warning(
            f"[Agent] Failed to generate valid Based code after {MAX_ITER} iterations. Last error: {last_error_message}. Returning last attempt."
        )
        return last_code_attempt

    def preprocess_diff(self, diff: str) -> str:
        """
        Cleans up a raw diff string generated by the LLM.

        Removes Markdown code blocks, strips leading whitespace from header lines,
        and removes potential '--- filename' / '+++ filename' lines sometimes added by LLMs.

        Args:
            diff: The raw diff string.

        Returns:
            A cleaned diff string suitable for `apply_patch`.
        """
        lines = diff.splitlines()
        # Remove markdown code block in case not caught with regex
        lines = [line for line in lines if not line.strip().startswith("```")]

        processed_lines = []
        skip_next_line = False
        for i, line in enumerate(lines):
            if skip_next_line:
                skip_next_line = False
                continue

            # Remove --- a/file.txt +++ b/file.txt style headers if present
            if (
                line.startswith("--- ")
                and i + 1 < len(lines)
                and lines[i + 1].startswith("+++ ")
            ):
                # Check if the part after ---/+++ looks like a path or /dev/null
                path_pattern = r"(\S+|/dev/null)"
                if re.match(rf"--- {path_pattern}", line) and re.match(
                    rf"\+\+\+ {path_pattern}", lines[i + 1]
                ):
                    skip_next_line = True
                    continue  # Skip both lines

            # Strip leading spaces ONLY from diff metadata lines (---, +++, @@)
            # This handles cases where LLM might indent these lines incorrectly.
            stripped_line = line.lstrip()
            if stripped_line.startswith(("---", "+++", "@@")):
                processed_lines.append(stripped_line)
            else:
                processed_lines.append(line)  # Keep original spacing for content lines

        # Join lines back, ensuring a newline at the end if the original had one
        # (though apply_patch might handle this)
        cleaned_diff = "\n".join(processed_lines)
        if diff.endswith("\n") and not cleaned_diff.endswith("\n"):
            cleaned_diff += "\n"

        return cleaned_diff

    def generate_based_diff(
        self, current_code: str, prompt: str, context=None, history=None
    ) -> dict:
        """
        Generates a unified diff to modify Based code based on a prompt.

        Iteratively prompts the LLM to produce a diff, applies it, validates
        the resulting code, and provides feedback on errors until a valid diff
        is generated or MAX_ITER is reached.

        Returns old and new code for use in frontend (monaco diff viewer)

        Args:
            current_code: The existing Based code string.
            prompt: The user's prompt describing the desired changes.
            context: Additional context information.
            history: The conversation history.

        Returns:
            A dictionary containing:
            - 'diff': The raw diff string generated by the LLM (last attempt if failed).
            - 'new_code': The code resulting from applying the diff (validated if successful).
            - 'old_code': The original `current_code` passed to the function.
            Returns the last attempted diff/code if validation fails after MAX_ITER.
        """
        # Specific instructions for generating diffs
        diff_instructions = (
            "When generating a unified diff, unchanged lines must start with a space, "
            "removed lines with '-', and added lines with '+'. Do not omit the space for unchanged lines. "
            "The diff should be valid and directly applicable using the standard unified diff format."
        )
        history_str = self._format_history_for_prompt(history)
        context_str = self._format_context_for_prompt(context)

        # Initial user prompt for the first iteration
        user_prompt_content = (
            f"{history_str}\n\nGiven the following Based code, generate a unified diff (patch) to implement this user request: '{prompt}'."
            f"{context_str}\n"
            f"{diff_instructions}\n"
            "Only output a valid unified diff. Do not include any explanation or extra text.\n"
            "Current Based code:\n```based\n{current_code}\n```"  # Use code block for clarity
        )
        system_message = SystemMessage(content=BASED_GUIDE + STRICT_INSTRUCTION)

        last_diff_attempt = ""
        last_error_message = ""
        last_generated_new_code = current_code  # Start with original code

        logger.info(
            f"[Agent] generate_based_diff called. Prompt: {prompt!r} | Context: {context!r} | History: {history!r}"
        )

        for i in range(MAX_ITER):
            logger.debug(f"[Agent] generate_based_diff: Iteration {i + 1}/{MAX_ITER}")
            messages = [system_message, HumanMessage(content=user_prompt_content)]

            try:
                response = self.llm.invoke(messages)
                diff_attempt = self.strip_code_blocks(response.content)
                last_diff_attempt = diff_attempt  # Store the latest raw diff

                # Preprocess and apply the generated diff
                patch = self.preprocess_diff(diff_attempt)
                try:
                    new_code_attempt = apply_patch(current_code, patch)
                    last_generated_new_code = (
                        new_code_attempt  # Store code resulting from this diff
                    )
                except Exception as patch_err:
                    # If applying the patch fails, provide feedback and retry
                    logger.warning(
                        f"[Agent] Iteration {i + 1} diff application failed: {patch_err}. Diff:\n{diff_attempt}"
                    )
                    last_error_message = (
                        f"The generated diff could not be applied: {patch_err}"
                    )
                    user_prompt_content = (
                        f"{history_str}\n\nUser Request: '{prompt}'{context_str}\n\n"
                        f"The previous diff attempt failed to apply with this error:\n{last_error_message}\n\n"
                        f"{diff_instructions}\n"
                        "Please generate a corrected unified diff. Only output the diff.\n"
                        f"Current Based code:\n```based\n{current_code}\n```"
                    )
                    continue  # Skip validation, go to next iteration

                # Validate the code resulting from the patch
                validation_result = self.validate_code(new_code_attempt)
                logger.info(
                    f"[Agent] Iteration {i + 1} diff validation result: {validation_result}"
                )

                if validation_result.get("status") == "success":
                    logger.info(
                        f"[Agent] Valid Based code diff generated in {i + 1} iteration(s). Returning diff, new_code, and old_code."
                    )
                    # Return the successful diff and the validated new code
                    validated_new_code = validation_result.get(
                        "converted_code", new_code_attempt
                    )
                    return {
                        "diff": diff_attempt,
                        "new_code": validated_new_code,
                        "old_code": current_code,
                    }

                # Prepare feedback for the next iteration if validation failed
                last_error_message = validation_result.get("error") or str(
                    validation_result
                )
                user_prompt_content = (
                    f"{history_str}\n\nUser Request: '{prompt}'{context_str}\n\n"
                    f"The previous diff, when applied, produced code that failed validation with this error:\n{last_error_message}\n\n"
                    f"{diff_instructions}\n"
                    "Please generate a corrected unified diff. Only output the diff.\n"
                    f"Current Based code:\n```based\n{current_code}\n```"
                )

            except requests.exceptions.RequestException as req_err:
                logger.error(f"[Agent] Validation request failed: {req_err}")
                last_error_message = f"Validation service request failed: {req_err}"
                # Update prompt to indicate validation service issue
                user_prompt_content = (
                    f"{history_str}\n\nUser Request: '{prompt}'{context_str}\n\n"
                    f"Could not validate the code resulting from the previous diff due to a network error: {last_error_message}\n\n"
                    f"{diff_instructions}\nPlease try generating the diff again.\n"
                    f"Current Based code:\n```based\n{current_code}\n```"
                )
            except Exception as llm_err:
                logger.error(f"[Agent] LLM invocation failed: {llm_err}")
                last_error_message = f"LLM call failed: {llm_err}"
                # Exit loop on LLM error
                break

        # Loop finished without success
        logger.warning(
            f"[Agent] Failed to generate valid Based code diff after {MAX_ITER} iterations. Last error: {last_error_message}. Returning last attempted diff."
        )
        return {
            "diff": last_diff_attempt,
            "new_code": last_generated_new_code,  # Return code from last *successful* patch apply, even if invalid -> NOTE: may cause frontend issues
            "old_code": current_code,
        }
