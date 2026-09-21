import requests

r = requests.post("http://127.0.0.1:11434/api/generate", json={
    "model": "qwen3.5:9b",
    "prompt": "Respond with JSON: {\"status\": \"ok\"}",
    "stream": False,
    "format": "json"
})
print("STATUS:", r.status_code)
print("RESPONSE:", r.json().get("response"))
