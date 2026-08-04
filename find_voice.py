import requests, json
r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": "sk_3b1a10b084a5ff8066d17f458fc83a2ed0ceef62d00d0483"})
voices = r.json()["voices"]
for v in voices:
    name = v["name"].lower()
    if "leo" in name or "antonio" in name or "ant" in name:
        print(f"{v['name']}: {v['voice_id']}")
if not any("leo" in v["name"].lower() or "antonio" in v["name"].lower() for v in voices):
    print("--- ALL VOICES ---")
    for v in voices:
        print(f"{v['name']}: {v['voice_id']}")
