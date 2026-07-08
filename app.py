import json
import os
import uuid
from typing import Any, Dict, Generator, List, Tuple

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from openai import OpenAI

from tools import execute_tool_call, tools

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

app = Flask(__name__)

# Development CORS only. For production, replace "*" with your real frontend domain.
CORS(app, resources={r"/*": {"origins": "*"}})

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are a helpful AI assistant. You can check real-time weather, "
        "real exchange rates, and search the web. Always respond in English. "
        "When you use tools, explain the final answer naturally and briefly."
    ),
}

MAX_ITERATIONS = 5
MAX_HISTORY_MESSAGES = 30
SESSION_STORE: Dict[str, List[Dict[str, Any]]] = {}


def sse(data: Dict[str, Any]) -> str:
    """Convert dict to Server-Sent Events format."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def get_or_create_session(session_id: str | None) -> Tuple[str, List[Dict[str, Any]]]:
    """Keep conversation history on the server instead of trusting frontend history."""
    if not session_id or session_id not in SESSION_STORE:
        session_id = str(uuid.uuid4())
        SESSION_STORE[session_id] = [SYSTEM_MESSAGE.copy()]
    return session_id, SESSION_STORE[session_id]


def trim_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep system prompt plus recent messages.
    This keeps demo cost lower and reduces prompt-injection risk from frontend history.
    """
    system = messages[0]
    recent = messages[1:][-MAX_HISTORY_MESSAGES:]

    # Avoid starting with orphan tool messages after trimming.
    while recent and recent[0].get("role") == "tool":
        recent.pop(0)

    return [system] + recent


def stream_model_once(
    messages: List[Dict[str, Any]],
) -> Generator[Dict[str, Any], None, Tuple[Dict[str, Any], bool]]:
    """
    Stream one DeepSeek response.
    It can either stream final text, or return tool calls when the model chooses tools.
    """
    content_parts: List[str] = []
    tool_call_parts: Dict[int, Dict[str, Any]] = {}

    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        stream=True,
    )

    for chunk in stream:
        choice = chunk.choices[0]
        delta = choice.delta

        if getattr(delta, "content", None):
            text = delta.content
            content_parts.append(text)
            yield {"type": "content", "content": text}

        for tool_delta in getattr(delta, "tool_calls", None) or []:
            index = tool_delta.index
            current = tool_call_parts.setdefault(
                index,
                {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                },
            )

            if getattr(tool_delta, "id", None):
                current["id"] += tool_delta.id
            if getattr(tool_delta, "type", None):
                current["type"] = tool_delta.type

            function_delta = getattr(tool_delta, "function", None)
            if function_delta:
                if getattr(function_delta, "name", None):
                    current["function"]["name"] += function_delta.name
                if getattr(function_delta, "arguments", None):
                    current["function"]["arguments"] += function_delta.arguments

    tool_calls = [tool_call_parts[i] for i in sorted(tool_call_parts)]

    assistant_message: Dict[str, Any] = {
        "role": "assistant",
        "content": "".join(content_parts) or None,
    }

    if tool_calls:
        assistant_message["tool_calls"] = tool_calls
        return assistant_message, True

    return assistant_message, False


def run_agent_sse(
    user_input: str, session_id: str | None
) -> Generator[str, None, None]:
    session_id, messages = get_or_create_session(session_id)
    yield sse({"type": "session", "session_id": session_id})

    user_input = (user_input or "").strip()
    if not user_input:
        yield sse({"type": "error", "message": "Message cannot be empty."})
        yield sse({"type": "done", "session_id": session_id})
        return

    messages.append({"role": "user", "content": user_input})

    try:
        for iteration in range(1, MAX_ITERATIONS + 1):
            model_events = stream_model_once(messages)
            try:
                while True:
                    event = next(model_events)
                    yield sse(event)
            except StopIteration as stop:
                assistant_message, has_tool_calls = stop.value

            if not has_tool_calls:
                messages.append(assistant_message)
                SESSION_STORE[session_id] = trim_history(messages)
                yield sse({"type": "done", "session_id": session_id})
                return

            messages.append(assistant_message)

            for tool_call in assistant_message.get("tool_calls", []):
                result, event = execute_tool_call(tool_call)

                yield sse(
                    {
                        "type": "tool_start",
                        "name": event.get("name"),
                        "args": event.get("args", {}),
                        "message": event.get("message"),
                    }
                )

                yield sse(
                    {
                        "type": "tool_result",
                        "name": event.get("name"),
                        "result": event.get("result", result),
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": result,
                    }
                )

        warning = (
            "I stopped after 5 tool-calling steps to avoid an infinite ReAct loop. "
            "Please try asking the question more directly."
        )
        messages.append({"role": "assistant", "content": warning})
        SESSION_STORE[session_id] = trim_history(messages)
        yield sse({"type": "content", "content": warning})
        yield sse({"type": "done", "session_id": session_id})

    except Exception as exc:
        yield sse({"type": "error", "message": f"Server error: {exc}"})
        yield sse({"type": "done", "session_id": session_id})


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "")
    session_id = data.get("session_id")

    return Response(
        run_agent_sse(user_input, session_id),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/reset", methods=["POST"])
def reset():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")

    if session_id and session_id in SESSION_STORE:
        SESSION_STORE.pop(session_id)

    return jsonify({"ok": True})


if __name__ == "__main__":
    # debug=True is for local development only.
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
