from __future__ import annotations

import json
import os

import requests


def generate(prompt: str, model: str | None = None) -> str:
    model = model or os.getenv("OLLAMA_MODEL", "qwen3.6:27b")
    response = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You output valid JSON only. Do not include markdown or reasoning.",
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.8,
                "num_predict": 1200,
            },
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    if "message" in payload:
        return payload["message"].get("content", "").strip()
    return payload.get("response", "").strip()


def extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Model did not return JSON: {text}")
    return json.loads(text[start : end + 1])
