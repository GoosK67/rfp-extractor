
# Simple Ollama HTTP client for embeddings and chat
from __future__ import annotations
import os, json, requests

DEFAULT_BASE = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "llama3.1")

class OllamaClient:
    def __init__(self, base_url: str|None=None, embed_model: str|None=None, chat_model: str|None=None):
        self.base = (base_url or DEFAULT_BASE).rstrip('/')
        self.embed_model = embed_model or EMBED_MODEL
        self.chat_model = chat_model or CHAT_MODEL

    def embed(self, text: str) -> list[float]:
        url = f"{self.base}/api/embeddings"
        payload = {"model": self.embed_model, "prompt": text}
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get("embedding") or data.get("data", [{}])[0].get("embedding", [])

    def chat(self, messages: list[dict]) -> str:
        url = f"{self.base}/api/chat"
        payload = {"model": self.chat_model, "messages": messages}
        r = requests.post(url, json=payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        # Ollama returns [{role:'assistant', content:'...'}] in message or 'message' key
        msg = data.get("message") or {}
        return (msg.get("content") or "").strip()
