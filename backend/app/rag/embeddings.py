"""
Embedding Service - Generates vector embeddings using sentence-transformers
Uses all-MiniLM-L6-v2 for fast, high-quality semantic embeddings (free, local)
"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from loguru import logger
from app.config import settings


class EmbeddingService:
    """Singleton embedding service using sentence-transformers"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            logger.info(f"🔄 Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(settings.embedding_model)
            logger.info("✅ Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            embedding = self._model.encode(
                text,
                convert_to_tensor=False,
                normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently"""
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        try:
            logger.info(f"🔄 Generating embeddings for {len(valid_texts)} chunks")
            embeddings = self._model.encode(
                valid_texts,
                batch_size=32,
                convert_to_tensor=False,
                normalize_embeddings=True,
                show_progress_bar=True
            )
            logger.info("✅ Batch embeddings generated")
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"❌ Batch embedding failed: {e}")
            raise

    def compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Compute cosine similarity between two embeddings"""
        arr1 = np.array(emb1)
        arr2 = np.array(emb2)

        # Cosine similarity (vectors are normalized so dot product = cosine similarity)
        similarity = np.dot(arr1, arr2)
        return float(similarity)

    def compute_similarity_score(self, emb1: List[float], emb2: List[float]) -> float:
        """Return similarity as percentage (0-100)"""
        sim = self.compute_similarity(emb1, emb2)
        # Convert from [-1, 1] range to [0, 100] percentage
        return round((sim + 1) / 2 * 100, 2)


# Singleton instance
embedding_service = EmbeddingService()
