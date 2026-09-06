import hashlib
import math
import random


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
        rng = random.Random(seed)
        
        # Generate random vector (approximate standard normal using Gauss)
        vec = [rng.gauss(0, 1) for _ in range(self.dimensions)]
        
        # Calculate norm and normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
            
        return [round(float(x), 6) for x in vec]

    @staticmethod
    def cosine_similarity(v1: list[float] | None, v2: list[float] | None) -> float:
        if not v1 or not v2:
            return 0.0
            
        dot_product = sum(x * y for x, y in zip(v1, v2))
        norm_a = math.sqrt(sum(x * x for x in v1))
        norm_b = math.sqrt(sum(y * y for y in v2))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)


embedding_service = EmbeddingService()
