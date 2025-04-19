import sys

sys.path.insert(0, ".")
from agent.agent import BasedAgent

if __name__ == "__main__":
    print("Interactive BasedAgent Diff Debug Console (Milestone 2)")
    print(
        "Paste your current Based code, then enter a prompt to see each diff, patch/validation result, and all iterations."
    )
    print("Type 'exit' as the prompt to quit.\n")
    agent = BasedAgent()
    print("Paste your current Based code (end with a line containing only 'END'):")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    current_code = "\n".join(lines)
    while True:
        prompt = input("\nEnter your prompt: ")
        if prompt.strip().lower() == "exit":
            print("Exiting.")
            break
        print("\n--- Agent Diff Iteration Trace ---")
        import logging

        logger = logging.getLogger("backend.agent.agent")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            logger.addHandler(handler)
        diff = agent.generate_based_diff(current_code, prompt)
        print("\n--- Final Diff Output ---\n")
        print(diff)
        print("\n------------------------\n")
        # Optionally, apply the diff to current_code for next round
        from unified_diff import apply_patch

        try:
            patch = agent.preprocess_diff(diff)
            new_code = apply_patch(current_code, patch)
            print("\n--- Updated Code After Patch ---\n")
            print(new_code)
            print("\n-------------------------------\n")
        except Exception as e:
            print(f"Patch could not be applied: {e}")
