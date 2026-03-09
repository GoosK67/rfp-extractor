from __future__ import annotations
import numpy as np
from .ollama_client import OllamaClient

POSITIVE_PROTOS = [
    "The supplier shall provide first-line support and ensure incidents are resolved within agreed SLAs.",
    "De leverancier moet eindgebruikers ondersteunen en storingen binnen de SLA oplossen.",
    "Le prestataire doit assurer la gestion des incidents et fournir une assistance aux utilisateurs.",
    "The system must implement access control, security logging and monitoring.",
]
NEGATIVE_PROTOS = [
    "The HR department",
    "Request for proposal process",
    "General terms and conditions",
    "Category",
]

class SemanticRequirementClassifier:
    def __init__(self, embed_model: str | None = None):
        self.cli = OllamaClient(embed_model=embed_model)
        self.pos_centroid = self._centroid(POSITIVE_PROTOS)
        self.neg_centroid = self._centroid(NEGATIVE_PROTOS)

    def _embed(self, text: str) -> np.ndarray:
        v = self.cli.embed(text)
        return np.array(v, dtype=float)

    def _centroid(self, texts: list[str]) -> np.ndarray:
        vecs = [self._embed(t) for t in texts]
        if not vecs:
            return np.zeros(1)
        M = np.vstack(vecs)
        return M.mean(axis=0)

    @staticmethod
    def _cos(a: np.ndarray, b: np.ndarray) -> float:
        if a.size == 0 or b.size == 0:
            return 0.0
        na = np.linalg.norm(a); nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(a.dot(b)/(na*nb))

    def score(self, text: str) -> float:
        v = self._embed(text)
        s_pos = self._cos(v, self.pos_centroid)
        s_neg = self._cos(v, self.neg_centroid)
        raw = (s_pos - s_neg + 1.0) / 2.0
        return max(0.0, min(1.0, raw))