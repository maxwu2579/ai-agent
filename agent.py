import os
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# 真实天气 API（Open-Meteo，免费无需key）
def get_weather(city: str) -> str:
    """查询某个城市的真实天气"""
    # 先把城市名转成坐标
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    geo = requests.get(geo_url).json()

    if not geo.get("results"):
        return f"找不到城市：{city}"

    lat = geo["results"][0]["latitude"]
    lon = geo["results"][0]["longitude"]

    # 查真实天气
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,weathercode"
    )
    weather = requests.get(weather_url).json()
    temp = weather["current"]["temperature_2m"]
    code = weather["current"]["weathercode"]

    # 天气代码转文字
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
}

tools = [get_weather, get_exchange_rate]
system_prompt = (
    "你是一个助手。查询天气时必须使用 get_weather 工具，不能自己猜测或编造天气数据。"
)
history = []

print("Agent 启动！输入 'quit' 退出")
print("-" * 30)

while True:
    user_input = input("你：")
    if user_input.lower() == "quit":
        break

    history.append({"role": "user", "parts": [{"text": user_input}]})

    while True:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=types.GenerateContentConfig(
                tools=tools,
                system_instruction=system_prompt,
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                ),
            ),
        )

        candidate = response.candidates[0].content
        tool_calls = [p for p in candidate.parts if p.function_call]

        if not tool_calls:
            print(f"Agent：{response.text}")
            history.append({"role": "model", "parts": [{"text": response.text}]})
            break

        history.append({"role": "model", "parts": candidate.parts})
        tool_results = []

        for part in tool_calls:
            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args)
            print(f"  [调用工具] {fn_name}({fn_args})")
            result = tool_map[fn_name](**fn_args)
            print(f"  [工具结果] {result}")
            tool_results.append(
                types.Part.from_function_response(
                    name=fn_name,
                    response={"result": result},
                )
            )

        history.append({"role": "user", "parts": tool_results})
