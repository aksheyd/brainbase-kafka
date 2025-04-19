import sys

sys.path.insert(0, ".")
from agent.agent import BasedAgent

if __name__ == "__main__":
    print("Interactive BasedAgent Debug Console")
    print("Type your prompt and see each LLM output, validation result, and iteration.")
    print("Type 'exit' to quit.\n")
    agent = BasedAgent()
    while True:
        prompt = input("\nEnter your prompt: ")
        if prompt.strip().lower() == "exit":
            print("Exiting.")
            break
        print("\n--- Agent Iteration Trace ---")
        # Patch the agent to print each step inline
        import logging

        logger = logging.getLogger("backend.agent.agent")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            logger.addHandler(handler)
        code = agent.generate_based_code(prompt)
        print("\n--- Final Output ---\n")
        print(code)
        print("\n-------------------\n")
