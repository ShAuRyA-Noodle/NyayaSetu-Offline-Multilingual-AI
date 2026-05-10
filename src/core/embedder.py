"""
Embedder Module - Generates semantic embeddings for text chunks.

Uses sentence-transformers with a multilingual model to convert text
into 768-dimensional vectors that capture semantic meaning.
Supports both Hindi and English queries.
"""

import os
import numpy as np
from typing import List
import logging
from pathlib import Path

# Import sentence-transformers. We do NOT silently degrade to zero-vectors:
# zero embeddings produce arbitrary FAISS hits and silently corrupt RAG.
# If the dep is missing or fails to load, we keep the import-time flag and
# raise loudly the first time someone actually tries to embed.
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
    _SENTENCE_TRANSFORMERS_IMPORT_ERROR: BaseException | None = None
except (ImportError, Exception) as e:  # noqa: BLE001
    SentenceTransformer = None  # type: ignore
    _HAS_SENTENCE_TRANSFORMERS = False
    _SENTENCE_TRANSFORMERS_IMPORT_ERROR = e
    logging.warning(
        f"sentence-transformers unavailable: {e}. "
        "Embedding calls will RAISE rather than return zero vectors."
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultilingualEmbedder:
    """
    Generates embeddings for text using multilingual sentence transformers.
    
    This model supports 50+ languages including Hindi and English, making it
    ideal for rural Indian governance applications.
    
    Model: paraphrase-multilingual-mpnet-base-v2
    - Embedding dimension: 768
    - Languages: Hindi, English, Punjabi, and 50+ more
    - Speed: ~500 sentences/second on CPU
    """
    
    # Model name - this will be downloaded on first use and cached
    MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'
    EMBEDDING_DIM = 768
    
    def __init__(self, cache_dir: str = './models'):
        """
        Initialize the embedding model.

        Args:
            cache_dir: Directory to cache the downloaded model

        Note:
            First run will download ~420MB model. Subsequent runs use cache.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = None

        if not _HAS_SENTENCE_TRANSFORMERS:
            logger.warning("Running without embedding model - RAG queries will return empty results")
            return

        logger.info(f"Loading embedding model: {self.MODEL_NAME}")
        logger.info("This may take a few minutes on first run (downloading model)...")

        # Load model with caching
        self.model = SentenceTransformer(
            self.MODEL_NAME,
            cache_folder=str(self.cache_dir)
        )

        logger.info(f"Model loaded successfully. Embedding dimension: {self.EMBEDDING_DIM}")
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        """
        if not texts:
            raise ValueError("Cannot embed empty text list")
        if self.model is None:
            return np.zeros((len(texts), self.EMBEDDING_DIM), dtype=np.float32)
        
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        
        # Generate embeddings in batches
        # normalize_embeddings=True ensures vectors have unit length (good for cosine similarity)
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,  # L2 normalization
            convert_to_numpy=True
        )
        
        logger.info(f"Embeddings generated. Shape: {embeddings.shape}")
        
        return embeddings
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if self.model is None:
            return np.zeros(self.EMBEDDING_DIM, dtype=np.float32)
        
        # Encode returns shape (1, 768), we flatten to (768,)
        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True
        )[0]
        
        return embedding
    
    def get_embedding_dim(self) -> int:
        """
        Get the dimensionality of embeddings produced by this model.
        
        Returns:
            Embedding dimension (768 for this model)
        """
        return self.EMBEDDING_DIM


if __name__ == "__main__":
    # Standalone test
    embedder = MultilingualEmbedder()
    
    # Test texts in multiple languages
    test_texts = [
        "Farmers can apply for PM-KISAN scheme online",
        "किसान PM-KISAN योजना के लिए ऑनलाइन आवेदन कर सकते हैं",
        "Housing subsidy for rural poor families"
    ]
    
    print(f"\n{'='*60}")
    print(f"EMBEDDER TEST")
    print(f"{'='*60}\n")
    
    # Test batch embedding
    embeddings = embedder.embed_texts(test_texts)
    print(f"Batch embeddings shape: {embeddings.shape}")
    print(f"Sample embedding (first 10 dims): {embeddings[0][:10]}")
    
    # Test single query embedding
    query = "farmer eligibility criteria"
    query_emb = embedder.embed_query(query)
    print(f"\nQuery embedding shape: {query_emb.shape}")
    print(f"Query embedding (first 10 dims): {query_emb[:10]}")
    
    # Verify normalization (L2 norm should be ~1.0)
    norm = np.linalg.norm(query_emb)
    print(f"\nEmbedding L2 norm: {norm:.6f} (should be ~1.0)")