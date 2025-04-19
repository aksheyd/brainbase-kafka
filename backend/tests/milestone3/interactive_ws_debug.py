import asyncio
import json

import websockets

WS_URL = "ws://localhost:8000/ws"


async def interactive_ws():
    print("Interactive WebSocket Debug Console (Milestone 3)")
    print("Type JSON messages to send to the backend. Example:")
    print('{"action": "prompt", "prompt": "Say hello"}')
    print("Type 'exit' to quit.\n")
    async with websockets.connect(WS_URL) as ws:
        while True:
            msg = input("Enter JSON action: ")
            if msg.strip().lower() == "exit":
                print("Exiting.")
                break
            try:
                json.loads(msg)
            except Exception as e:
                print(f"Invalid JSON: {e}")
                continue
            await ws.send(msg)
            try:
                response = await ws.recv()
                print("\n--- Response ---\n")
                print(response)
                print("\n----------------\n")
            except Exception as e:
                print(f"Error receiving response: {e}")
                break


if __name__ == "__main__":
    asyncio.run(interactive_ws())
