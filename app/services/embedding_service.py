import hashlib
import numpy as np


class EmbeddingService:
    """
    384-dimensional vector embedding service.
    Provides deterministic normalized embeddings for development/testing
    and can easily be bound to SentenceTransformers or Gemma embeddings.
    """
    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def generate_embedding(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.dimensions

        # Deterministic pseudo-random vector based on SHA-256 hash of text
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dimensions)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return [round(float(x), 6) for x in vec]

    @staticmethod
    def cosine_similarity(v1: list[float] | None, v2: list[float] | None) -> float:
        if not v1 or not v2:
            return 0.0
        a = np.array(v1)
        b = np.array(v2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


embedding_service = EmbeddingService()
