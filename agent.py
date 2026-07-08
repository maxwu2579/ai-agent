import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from tools import execute_tool_call, tools

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": "You are a helpful AI assistant. You can check weather, exchange rates, and search the web.",
}

MAX_ITERATIONS = 5


def run_cli_agent(user_input: str, messages: List[Dict[str, Any]]) -> None:
    messages.append({"role": "user", "content": user_input})

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message
        msg_dict = msg.model_dump()

        if not msg.tool_calls:
            print(f"Agent: {msg.content}")
            messages.append({"role": "assistant", "content": msg.content})
            return

        messages.append(msg_dict)

        for tool_call in msg_dict.get("tool_calls", []):
            result, event = execute_tool_call(tool_call)
            print(event.get("message"))
            print(f"Tool result: {result}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": result,
                }
            )

    warning = "Stopped after 5 tool-calling steps to avoid an infinite loop."
    print(f"Agent: {warning}")
    messages.append({"role": "assistant", "content": warning})


if __name__ == "__main__":
    conversation = [SYSTEM_MESSAGE.copy()]
    print("Agent  started. Type 'quit' to exit.")
    print("-" * 40)

    while True:
        text = input("You: ").strip()
        if text.lower() == "quit":
            break
        if not text:
            continue
        run_cli_agent(text, conversation)
