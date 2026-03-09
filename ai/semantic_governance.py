
from __future__ import annotations
import os, json, pickle
from dataclasses import dataclass
from typing import List
import numpy as np
from .ollama_client import OllamaClient
from utils.helpers import hash_id, normalize_ws

GOV_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'governance')
CACHE_PATH = os.path.join(os.path.dirname(__file__), 'embeddings', 'controls_embeddings.pkl')

@dataclass
class GovResult:
    cobit: List[str]
    itil: List[str]
    iso: List[str]
    explanation: str
    confidence: float

class SemanticGovernanceMapper:
    def __init__(self, embed_model: str|None=None, chat_model: str|None=None):
        self.cli = OllamaClient(embed_model=embed_model, chat_model=chat_model)
        self.controls = self._load_controls()
        self.embeds = self._load_or_build_embeddings()

    def _load_controls(self):
        def _load(name):
            p = os.path.join(GOV_DIR, name)
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'cobit': _load('cobit.json'),
            'itil': _load('itil.json'),
            'iso': _load('iso27001.json')
        }

    def _embed(self, text:str) -> np.ndarray:
        return np.array(self.cli.embed(text), dtype=float)

    def _load_or_build_embeddings(self):
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                pass
        embeds = {}
        for k, lst in self.controls.items():
            vecs = []
            for item in lst:
                txt = f"{item['id']} - {item['title']}: {item['description']}"
                vecs.append(self._embed(txt))
            embeds[k] = np.vstack(vecs) if vecs else np.zeros((0,1))
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, 'wb') as f:
            pickle.dump(embeds, f)
        return embeds

    @staticmethod
    def _cos(a: np.ndarray, B: np.ndarray) -> np.ndarray:
        if a.size == 0 or B.size == 0:
            return np.zeros((B.shape[0],), dtype=float)
        a_norm = a/ (np.linalg.norm(a)+1e-9)
        B_norm = B/ (np.linalg.norm(B, axis=1, keepdims=True)+1e-9)
        return B_norm.dot(a_norm)

    def _top_hits(self, sims: np.ndarray, items:list[dict], th:float=0.45, top:int=5) -> list[tuple[str,float]]:
        idx = np.argsort(-sims)
        hits = []
        for i in idx[:top]:
            if sims[i] >= th:
                hits.append((items[i]['id'], float(sims[i])))
        return hits

    def map_text(self, text: str) -> GovResult:
        v = self._embed(text)
        cobit_hits = self._top_hits(self._cos(v, self.embeds['cobit']), self.controls['cobit'])
        itil_hits  = self._top_hits(self._cos(v, self.embeds['itil']),  self.controls['itil'])
        iso_hits   = self._top_hits(self._cos(v, self.embeds['iso']),   self.controls['iso'])

        conf_vals = [s for _,s in (cobit_hits+itil_hits+iso_hits)]
        confidence = round(float(sum(conf_vals)/len(conf_vals)), 2) if conf_vals else 0.0

        # Build explanation with the LLM (Ollama chat)
        expl = ""
        if cobit_hits or itil_hits or iso_hits:
            framework_snip = {
                'COBIT': cobit_hits,
                'ITIL': itil_hits,
                'ISO27001': iso_hits
            }
            sys_prompt = "You are a governance analyst. Explain briefly why the requirement maps to the listed controls. Be concise (<=60 words)."
            usr = {
                'text': text,
                'hits': framework_snip
            }
            messages = [
                {"role":"system","content":sys_prompt},
                {"role":"user","content":json.dumps(usr, ensure_ascii=False)}
            ]
            try:
                expl = self.cli.chat(messages)
            except Exception:
                # Fallback template explanation
                parts = []
                if cobit_hits:
                    parts.append(f"COBIT {', '.join([i for i,_ in cobit_hits])}")
                if itil_hits:
                    parts.append(f"ITIL {', '.join([i for i,_ in itil_hits])}")
                if iso_hits:
                    parts.append(f"ISO27001 {', '.join([i for i,_ in iso_hits])}")
                expl = "Matched: " + "; ".join(parts)

        return GovResult(
            cobit=[i for i,_ in cobit_hits],
            itil=[i for i,_ in itil_hits],
            iso=[i for i,_ in iso_hits],
            explanation=normalize_ws(expl),
            confidence=confidence
        )

    @staticmethod
    def hash_id(text: str) -> str:
        return hash_id(text)
