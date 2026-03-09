from __future__ import annotations
import os, json, pickle
from dataclasses import dataclass
from typing import List
import numpy as np

from .ollama_client import OllamaClient
from utils.helpers import normalize_ws, hash_id, looks_like_legal_or_address, is_governance_candidate

GOV_DIR    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "governance")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "embeddings", "controls_embeddings.pkl")

@dataclass
class GovResult:
    cobit: List[str]
    itil:  List[str]
    iso:   List[str]
    explanation: str
    confidence: float

class SemanticGovernanceMapper:
    def __init__(self, embed_model: str | None = None, chat_model: str | None = None):
        self.cli = OllamaClient(embed_model=embed_model, chat_model=chat_model)
        self.controls = self._load_controls()
        self.embeds   = self._load_or_build_embeddings()
        self.min_sim  = float(os.getenv("GOV_MIN_SIM", "0.55"))  # stricter default

    def _load_controls(self):
        def _load(name):
            p = os.path.join(GOV_DIR, name)
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "cobit": _load("cobit.json"),
            "itil":  _load("itil.json"),
            "iso":   _load("iso27001.json"),
        }

    def _embed(self, text: str) -> np.ndarray:
        # float32 bespaart RAM
        return np.array(self.cli.embed(text), dtype=np.float32)

    def _load_or_build_embeddings(self):
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        embeds = {}
        for k, lst in self.controls.items():
            vecs = []
            for item in lst:
                txt = f"{item['id']} - {item['title']}: {item['description']}"
                vecs.append(self._embed(txt))
            embeds[k] = (np.vstack(vecs).astype(np.float32)) if vecs else np.zeros((0, 1), dtype=np.float32)
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "wb") as f:
            pickle.dump(embeds, f)
        return embeds

    @staticmethod
    def _cos(a: np.ndarray, B: np.ndarray) -> np.ndarray:
        if a.size == 0 or B.size == 0:
            return np.zeros((B.shape[0],), dtype=np.float32)
        a_norm = a / (np.linalg.norm(a) + 1e-9)
        B_norm = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-9)
        return B_norm.dot(a_norm)

    def _top_hits(self, sims: np.ndarray, items: list[dict], th: float | None = None, top: int = 5) -> list[tuple[str, float]]:
        th = self.min_sim if th is None else th
        idx = np.argsort(-sims)
        hits : list[tuple[str, float]] = []
        for i in idx[:top]:
            if sims[i] >= th:
                hits.append((items[i]["id"], float(sims[i])))
        return hits

    def map_text(self, text: str) -> GovResult:
        # 1) No-map guards
        if looks_like_legal_or_address(text):
            return GovResult([], [], [], "Not mapped: legal/address/party boilerplate.", 0.0)
        if not is_governance_candidate(text):
            return GovResult([], [], [], "Not mapped: no governance cues found.", 0.0)

        # 2) Embedding similarity
        v = self._embed(text)
        cobit_hits = self._top_hits(self._cos(v, self.embeds["cobit"]), self.controls["cobit"])
        itil_hits  = self._top_hits(self._cos(v, self.embeds["itil"]),  self.controls["itil"])
        iso_hits   = self._top_hits(self._cos(v, self.embeds["iso"]),   self.controls["iso"])

        conf_vals = [s for _, s in (cobit_hits + itil_hits + iso_hits)]
        confidence = round(float(sum(conf_vals) / len(conf_vals)), 2) if conf_vals else 0.0

        explanation = ""
        if cobit_hits or itil_hits or iso_hits:
            explanation = self._build_explanation(text, cobit_hits, itil_hits, iso_hits, confidence)

        return GovResult(
            cobit=[i for i, _ in cobit_hits],
            itil=[i for i, _ in itil_hits],
            iso=[i for i, _ in iso_hits],
            explanation=normalize_ws(explanation),
            confidence=confidence
        )

    def _build_explanation(self, text: str, cobit_hits, itil_hits, iso_hits, confidence: float) -> str:
        # Globaal aan/uit
        if os.getenv("GOV_EXPLAIN", "1") == "0":
            return "Explanation disabled (GOV_EXPLAIN=0)."

        # Uitleg alleen boven min-confidence?
        minconf = float(os.getenv("GOV_EXPLAIN_MINCONF", "0.0"))
        if confidence < minconf:
            return "Explanation skipped (below MINCONF)."

        payload = {
            "requirement": text,
            "hits": {
                "COBIT": cobit_hits,
                "ITIL":  itil_hits,
                "ISO27001": iso_hits
            }
        }
        messages = [
            {"role": "system", "content": "Explain in <= 60 words why this requirement matches these governance controls."},
            {"role": "user",   "content": json.dumps(payload, ensure_ascii=False)}
        ]
        expl = self.cli.chat(messages)
        if not expl:
            parts = []
            if cobit_hits: parts.append("COBIT "    + ", ".join([i for i, _ in cobit_hits]))
            if itil_hits:  parts.append("ITIL "     + ", ".join([i for i, _ in itil_hits]))
            if iso_hits:   parts.append("ISO27001 " + ", ".join([i for i, _ in iso_hits]))
            return "Mapped via semantic similarity. " + ("; ".join(parts) if parts else "")
        return expl

    @staticmethod
    def hash_id(text: str) -> str:
        return hash_id(text)