"""
Retriever Module - Fast similarity search using FAISS vector store.

Builds and queries FAISS index for efficient nearest-neighbor search.
Persists index to disk for quick startup without re-embedding.
"""

import numpy as np
from typing import List, Dict, Tuple
import logging
from pathlib import Path
import pickle

# Import FAISS
try:
    import faiss
except ImportError:
    raise ImportError(
        "faiss-cpu not installed. "
        "Run: pip install faiss-cpu"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FAISSRetriever:
    """
    FAISS-based vector store for fast similarity search.
    
    Uses FAISS IndexFlatIP (Inner Product) for exact search.
    With normalized embeddings, inner product = cosine similarity.
    
    Supports:
    - Building index from embeddings
    - Persisting to disk
    - Loading from disk
    - Fast top-k retrieval with metadata
    """
    
    def __init__(self, embedding_dim: int = 768):
        """
        Initialize FAISS retriever.
        
        Args:
            embedding_dim: Dimension of embedding vectors (768 for multilingual mpnet)
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.metadata = []  # List of metadata dicts, one per chunk
        
        logger.info(f"FAISSRetriever initialized with dimension: {embedding_dim}")
    
    def build_index(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict[str, str]]
    ) -> None:
        """
        Build FAISS index from embeddings and associate metadata.
        
        Args:
            embeddings: numpy array of shape (n_chunks, embedding_dim)
            metadata: List of n_chunks metadata dictionaries
        
        Raises:
            ValueError: If embeddings and metadata lengths don't match
            ValueError: If embeddings have wrong dimension
        """
        if len(embeddings) != len(metadata):
            raise ValueError(
                f"Embeddings ({len(embeddings)}) and metadata ({len(metadata)}) "
                f"length mismatch"
            )
        
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} doesn't match "
                f"expected {self.embedding_dim}"
            )
        
        logger.info(f"Building FAISS index with {len(embeddings)} vectors...")
        
        # Create FAISS index
        # IndexFlatIP: Exact search using inner product (= cosine similarity for normalized vectors)
        # This is CPU-based and works offline
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        
        # Add vectors to index
        # FAISS requires float32
        embeddings_f32 = embeddings.astype(np.float32)
        self.index.add(embeddings_f32)
        
        # Store metadata
        self.metadata = metadata
        
        logger.info(f"Index built successfully. Total vectors: {self.index.ntotal}")
    
    def save_index(self, index_path: str, metadata_path: str) -> None:
        """
        Persist FAISS index and metadata to disk.
        
        This allows quick startup without re-embedding.
        
        Args:
            index_path: Path to save FAISS index (.index file)
            metadata_path: Path to save metadata (.pkl file)
        
        Raises:
            RuntimeError: If index hasn't been built yet
        """
        if self.index is None:
            raise RuntimeError("Cannot save index before building it")
        
        index_path = Path(index_path)
        metadata_path = Path(metadata_path)
        
        # Create parent directories
        index_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving FAISS index to: {index_path}")
        faiss.write_index(self.index, str(index_path))
        
        logger.info(f"Saving metadata to: {metadata_path}")
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        logger.info("Index and metadata saved successfully")
    
    def load_index(self, index_path: str, metadata_path: str) -> None:
        """
        Load FAISS index and metadata from disk.
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata pickle file
        
        Raises:
            FileNotFoundError: If index or metadata files don't exist
        """
        index_path = Path(index_path)
        metadata_path = Path(metadata_path)
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        
        logger.info(f"Loading FAISS index from: {index_path}")
        self.index = faiss.read_index(str(index_path))
        
        logger.info(f"Loading metadata from: {metadata_path}")
        with open(metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)
        
        logger.info(f"Index loaded successfully. Total vectors: {self.index.ntotal}")
    
    def retrieve(
        self,
        query_embedding: np.ndarray,
        top_k: int = 3
    ) -> List[Tuple[float, Dict[str, str]]]:
        """
        Retrieve top-k most similar chunks for a query.
        
        Args:
            query_embedding: Query embedding vector, shape (embedding_dim,)
            top_k: Number of top results to return
        
        Returns:
            List of (score, metadata) tuples, sorted by score (highest first)
            
            score: Similarity score (higher = more similar)
            metadata: Dictionary containing scheme info and section type
        
        Raises:
            RuntimeError: If index hasn't been built or loaded
            ValueError: If query_embedding has wrong dimension
        """
        if self.index is None:
            raise RuntimeError("Index not built or loaded")
        
        if query_embedding.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Query embedding dimension {query_embedding.shape[0]} doesn't match "
                f"index dimension {self.embedding_dim}"
            )
        
        # Ensure top_k doesn't exceed available vectors
        top_k = min(top_k, self.index.ntotal)
        
        # Reshape query to (1, embedding_dim) and convert to float32
        query_f32 = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Search index
        # scores: shape (1, top_k) - similarity scores
        # indices: shape (1, top_k) - indices of matched vectors
        scores, indices = self.index.search(query_f32, top_k)
        
        # Flatten results
        scores = scores[0]  # shape (top_k,)
        indices = indices[0]  # shape (top_k,)
        
        # Combine scores with metadata
        results = []
        for score, idx in zip(scores, indices):
            if idx < len(self.metadata):  # Safety check
                results.append((float(score), self.metadata[idx]))
        
        logger.info(f"Retrieved {len(results)} results for query")
        
        return results
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get index statistics.
        
        Returns:
            Dictionary with index statistics
        """
        if self.index is None:
            return {'status': 'not_initialized'}
        
        return {
            'status': 'ready',
            'total_vectors': self.index.ntotal,
            'embedding_dim': self.embedding_dim,
            'metadata_count': len(self.metadata)
        }


if __name__ == "__main__":
    # Standalone test with dummy data
    print(f"\n{'='*60}")
    print(f"RETRIEVER TEST")
    print(f"{'='*60}\n")
    
    # Create dummy embeddings
    n_chunks = 5
    embedding_dim = 768
    
    np.random.seed(42)
    dummy_embeddings = np.random.randn(n_chunks, embedding_dim).astype(np.float32)
    # Normalize
    dummy_embeddings = dummy_embeddings / np.linalg.norm(dummy_embeddings, axis=1, keepdims=True)
    
    dummy_metadata = [
        {'scheme_name': f'Scheme_{i}', 'section_type': 'eligibility', 'chunk_id': f'chunk_{i}'}
        for i in range(n_chunks)
    ]
    
    # Test build and retrieve
    retriever = FAISSRetriever(embedding_dim=embedding_dim)
    retriever.build_index(dummy_embeddings, dummy_metadata)
    
    print(f"Index stats: {retriever.get_stats()}")
    
    # Test retrieval
    query_emb = dummy_embeddings[0]  # Use first embedding as query
    results = retriever.retrieve(query_emb, top_k=3)
    
    print(f"\nTop-3 retrieval results:")
    for i, (score, meta) in enumerate(results, 1):
        print(f"{i}. Score: {score:.4f} | Scheme: {meta['scheme_name']} | Section: {meta['section_type']}")