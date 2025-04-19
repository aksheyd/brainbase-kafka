import sys

sys.path.insert(0, ".")
from unified_diff import make_patch

old = """loop:
    res = talk("Hello! I'm a weather bot. I can tell you the weather for any city. Just tell me which city you're interested in.", True)
until "user mentions a city":
    city_info = res.ask(question="Extract the city name from the user's input.", example={"city": "London"})
    city = city_info["city"]
    weather_data = api.get_req(
        url="https://weatherapi.io/api/weather",
        params={"city": city, "api_key": "YOUR_API_KEY"}
    )
    weather_report = weather_data.ask(
        question="Summarize the weather data into a concise weather report.",
        example={"temperature": "25C", "condition": "Sunny", "wind": "15km/h"}
    )
    return weather_report
"""

new = """loop:
    res = talk("Hello! I'm Carlos, a weather bot. I can tell you the weather for any city. Just tell me which city you're interested in.", True)
until "user mentions a city":
    city_info = res.ask(question="Extract the city name from the user's input.", example={"city": "London"})
    city = city_info["city"]
    weather_data = api.get_req(
        url="https://weatherapi.io/api/weather",
        params={"city": city, "api_key": "YOUR_API_KEY"}
    )
    weather_report = weather_data.ask(
        question="Summarize the weather data into a concise weather report.",
        example={"temperature": "25C", "condition": "Sunny", "wind": "15km/h"}
    )
    return weather_report
"""

print("\n--- Diff using make_patch (your unified_diff.py) ---\n")
diff = make_patch(old, new)
print(diff)
print("\n--------------------------\n")
