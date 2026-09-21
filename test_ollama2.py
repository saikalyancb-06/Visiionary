import requests, json

r = requests.post("http://127.0.0.1:11434/api/generate", json={
    "model": "qwen3.5:9b",
    "prompt": "You are an AI assistant. What is 2 + 2? Return a JSON object with key result.",
    "stream": False
})
print("STATUS:", r.status_code)
data = r.json()
print("THINKING / TEXT:", data.get("response") or data.get("thinking"))
print("RAW KEYS:", list(data.keys()))
if "response" in data:
    print("RESPONSE LEN:", len(data["response"]))
