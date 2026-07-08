# AI Agent Assistant

AI Agent Assistant is a full-stack AI agent web application built with a Python Flask backend and a Vue 3 frontend.  
It uses the DeepSeek API as the main reasoning model and can automatically decide when to call external tools, such as weather lookup, currency exchange rate lookup, and web search.

This project is designed as a portfolio and interview demonstration project to show how an AI agent works beyond a normal chatbot.

---

## Features

- **DeepSeek-powered AI agent**  
  Uses the DeepSeek API as the main LLM for understanding user questions and generating responses.

- **Autonomous tool calling**  
  The agent can decide by itself whether a tool is needed and which tool should be used.

- **Real-time weather lookup**  
  Uses the Open-Meteo API to get live weather information for different cities.

- **Real-time currency exchange rates**  
  Uses the Frankfurter API to fetch real exchange rates instead of using hard-coded fake data.

- **Web search**  
  Uses DuckDuckGo search through DDGS to get up-to-date web information.

- **Visible tool execution process**  
  The frontend shows messages such as “Checking weather...” or “Getting exchange rate...”, making the agent process easier to understand during a demo.

- **SSE streaming response**  
  Uses Server-Sent Events to stream the AI response gradually, creating a typewriter-style experience.

- **Server-side conversation memory**  
  Stores conversation history on the backend using a session ID instead of trusting the frontend to send the whole history.

- **Basic error handling**  
  Handles API errors, invalid tool calls, JSON parsing errors, and tool execution failures.

- **ReAct-style loop limit**  
  Uses a maximum iteration limit to avoid infinite tool-calling loops.

---

## Tech Stack

- **Backend:** Python, Flask, Flask-CORS
- **Frontend:** Vue 3 CDN, HTML, CSS, JavaScript
- **LLM:** DeepSeek API
- **Weather API:** Open-Meteo
- **Exchange Rate API:** Frankfurter
- **Web Search:** DDGS / DuckDuckGo
- **Streaming:** Server-Sent Events

---

## How It Works

The agent follows a simple ReAct-style workflow:

1. The user sends a message from the web interface.
2. The Flask backend sends the message to the DeepSeek API.
3. DeepSeek decides whether a tool is needed.
4. If a tool is needed, the backend executes the selected tool.
5. The tool result is sent back to DeepSeek.
6. DeepSeek generates the final response.
7. The response is streamed back to the frontend using SSE.

This makes the system different from a normal chatbot because it can use external tools to get real-time information.

---

## Project Structure

```text
ai-agent/
├── agent.py              # Command-line version of the agent
├── app.py                # Flask backend and web API
├── tools.py              # Tool functions and tool schemas
├── index.html            # Vue 3 frontend
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variable file
├── .gitignore            # Files excluded from Git
└── README.md             # Project documentation
