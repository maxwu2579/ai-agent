import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def get_weather(city: str) -> str:
    """查询某个城市的真实天气"""
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    geo = requests.get(geo_url).json()
    if not geo.get("results"):
        return f"找不到城市：{city}"
    lat = geo["results"][0]["latitude"]
    lon = geo["results"][0]["longitude"]
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,weathercode"
    )
    weather = requests.get(weather_url).json()
    temp = weather["current"]["temperature_2m"]
    code = weather["current"]["weathercode"]
    if code == 0:
        desc = "晴天"
    elif code in [1, 2, 3]:
        desc = "多云"
    elif code in range(51, 68):
        desc = "下雨"
    elif code in range(71, 78):
        desc = "下雪"
    else:
        desc = "天气状况未知"
    return f"{city} 现在 {desc}，温度 {temp}°C"


def search_web(query: str) -> str:
    """搜索网页获取最新信息"""
    from ddgs import DDGS

    results = list(DDGS().text(query, max_results=3))
    if not results:
        return "没有找到相关结果"
    output = ""
    for r in results:
        output += f"标题：{r['title']}\n内容：{r['body']}\n\n"
    return output


def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """查询两种货币之间的汇率"""
    rates = {
        ("USD", "MYR"): 4.7,
        ("MYR", "USD"): 0.21,
        ("USD", "CNY"): 7.2,
        ("CNY", "USD"): 0.14,
    }
    rate = rates.get((from_currency.upper(), to_currency.upper()))
    if rate:
        return f"1 {from_currency} = {rate} {to_currency}"
    return "找不到该汇率"


tool_map = {
    "get_weather": get_weather,
    "get_exchange_rate": get_exchange_rate,
    "search_web": search_web,
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市的真实天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "查询两种货币之间的汇率",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_currency": {"type": "string"},
                    "to_currency": {"type": "string"},
                },
                "required": ["from_currency", "to_currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜索网页获取最新信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"],
            },
        },
    },
]

# Flask 应用
app = Flask(__name__)
CORS(app)  # 允许前端跨域访问


def run_agent(user_input, history):
    """运行 agent，返回回复和更新后的历史"""
    messages = history + [{"role": "user", "content": user_input}]

    while True:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content, messages

        messages.append(msg.model_dump())

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            result = tool_map[fn_name](**fn_args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "")
    history = data.get("history", [])

    if not history:
        history = [
            {
                "role": "system",
                "content": "你是一个助手，可以查天气、查汇率、搜索网页。",
            }
        ]

    reply, new_history = run_agent(user_input, history)
    return jsonify({"reply": reply, "history": new_history})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
