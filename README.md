# AI Agent Assistant

A full-stack AI agent that can autonomously decide which tools to use, execute them, and respond in natural language. Built with a Python (Flask) backend and a Vue 3 frontend, powered by the DeepSeek API.

## Features

- **Autonomous tool calling** — the agent decides on its own which tool to use based on the user's question
- **Real-time weather** — looks up live weather for any city via the Open-Meteo API
- **Currency exchange rates** — converts between common currencies
- **Web search** — searches the web for up-to-date information using DuckDuckGo
- **Conversation memory** — remembers earlier messages in the same session
- **ReAct loop** — chains multiple tool calls to handle complex, multi-step questions
- **Clean web interface** — a simple chat UI built with Vue 3

## Tech Stack

- **Backend:** Python, Flask, Flask-CORS
- **Frontend:** Vue 3 (CDN), HTML, CSS
- **LLM:** DeepSeek API (OpenAI-compatible)
- **Tools:** Open-Meteo (weather), DuckDuckGo (search)

## How It Works

The agent follows a ReAct (Reasoning + Acting) loop:

1. The user sends a message
2. The LLM decides whether a tool is needed and which one
3. If a tool is called, the backend runs it and returns the result to the LLM
4. The LLM either calls another tool or produces a final answer
5. The answer is sent back to the frontend

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A DeepSeek API key

### Installation

1. Clone the repository:

```
git clone https://github.com/maxwu2579/ai-agent.git
cd ai-agent
```

2. Install dependencies:

```
pip install flask flask-cors openai requests python-dotenv ddgs
```

3. Create a `.env` file in the project root and add your API key:

```
DEEPSEEK_API_KEY=your_api_key_here
```

### Running the App

1. Start the backend:

```
python app.py
```

The server runs at `http://127.0.0.1:5000`.

2. Open `index.html` in your browser.

3. Start chatting — ask about the weather, exchange rates, or anything that needs a web search.

## Project Structure

```
ai-agent/
├── agent.py       # Command-line version of the agent
├── app.py         # Flask backend (web API)
├── index.html     # Vue 3 frontend
├── .gitignore     # Excludes .env and other files
└── README.md
```

## Notes

- The `.env` file is excluded from version control to keep the API key private.
- This project uses Flask's development server, which is intended for local use only.

## License

This project is for educational and portfolio purposes.
