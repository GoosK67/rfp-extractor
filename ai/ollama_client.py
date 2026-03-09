from __future__ import annotations
import os
import requests

DEFAULT_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
EMBED_MODEL  = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL   = os.getenv("OLLAMA_CHAT_MODEL",  "qwen2.5:3b-instruct")  # licht & snel default

class OllamaClient:
    def __init__(self, base_url: str | None = None, embed_model: str | None = None, chat_model: str | None = None):
        self.base = (base_url or DEFAULT_BASE).rstrip("/")
        self.embed_model = embed_model or EMBED_MODEL
        self.chat_model  = chat_model  or CHAT_MODEL

    # Embeddings (blijft synchronously; server moet embed endpoint ondersteunen)
    def embed(self, text: str) -> list[float]:
        url = f"{self.base}/api/embeddings"
        payload = {"model": self.embed_model, "prompt": text}
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data.get("embedding") or data.get("data", [{}])[0].get("embedding", [])

    # Chat met fail-fast timeout & RAM-vriendelijke opties
    def chat(self, messages: list[dict], options: dict | None = None) -> str | None:
        url = f"{self.base}/api/chat"
        payload = {"model": self.chat_model, "messages": messages}

        default_opts = {
            "num_ctx":     int(os.getenv("OLLAMA_NUM_CTX", "512")),
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
            "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "128")),
        }
        if options:
            default_opts.update(options)
        payload["options"] = default_opts

        timeout = int(os.getenv("OLLAMA_CHAT_TIMEOUT", "10"))  # kort, liever fallback dan hang
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            msg = data.get("message") or {}
            return (msg.get("content") or "").strip()
        except Exception:
            return None  # nooit hangen of crashen