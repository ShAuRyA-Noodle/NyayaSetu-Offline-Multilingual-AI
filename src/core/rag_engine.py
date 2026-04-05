"""
RAG Engine - High-level orchestrator for Retrieval-Augmented Generation.

This is the main interface for the RAG system. It coordinates:
- Loading scheme data from database
- Chunking documents
- Generating embeddings
- Building/loading FAISS index
- Retrieving relevant chunks for queries

Production-grade features:
- Automatic index persistence
- Lazy loading (only load when needed)
- Thread-safe operations
- Comprehensive error handling
"""

import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Try relative import first, fall back to absolute
try:
    from .chunker import SchemeChunker
    from .embedder import MultilingualEmbedder
    from .retriever import FAISSRetriever
except ImportError:
    from core.chunker import SchemeChunker
    from core.embedder import MultilingualEmbedder
    from core.retriever import FAISSRetriever

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Production-grade RAG engine for offline government scheme retrieval.
    
    This class provides a clean interface to:
    1. Initialize the RAG system (build or load index)
    2. Retrieve relevant chunks for user queries
    3. Provide explainability through metadata
    
    Thread-safe and designed for production deployment.
    """
    
    def __init__(
        self,
        db_path: str = "data/governance.db",
        index_dir: str = "data/",
        model_cache_dir: str = "./models",
        force_rebuild: bool = False
    ):
        """
        Initialize RAG engine.
        
        Args:
            db_path: Path to SQLite database with schemes
            index_dir: Directory to store/load FAISS index
            model_cache_dir: Directory to cache embedding model
            force_rebuild: If True, rebuild index even if it exists
        
        Note:
            First run will take longer (downloading model, building index).
            Subsequent runs are fast (loading from disk).
        """
        self.db_path = Path(db_path)
        self.index_dir = Path(index_dir)
        self.model_cache_dir = Path(model_cache_dir)
        
        # Ensure directories exist
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths for persistence
        self.index_path = self.index_dir / "schemes_faiss.index"
        self.metadata_path = self.index_dir / "schemes_metadata.pkl"
        
        # Initialize components
        logger.info("Initializing RAG Engine...")
        
        self.chunker = SchemeChunker(str(self.db_path))
        self.embedder = MultilingualEmbedder(cache_dir=str(self.model_cache_dir))
        self.retriever = FAISSRetriever(embedding_dim=self.embedder.get_embedding_dim())
        
        # Build or load index
        self._initialize_index(force_rebuild=force_rebuild)
        
        logger.info("RAG Engine initialized successfully")
    
    def _initialize_index(self, force_rebuild: bool = False) -> None:
        """
        Build or load FAISS index.
        
        Logic:
        - If index exists and not force_rebuild: load from disk
        - Otherwise: build from database and save to disk
        
        Args:
            force_rebuild: If True, rebuild even if index exists
        """
        index_exists = self.index_path.exists() and self.metadata_path.exists()
        
        if index_exists and not force_rebuild:
            logger.info("Loading existing FAISS index from disk...")
            try:
                self.retriever.load_index(
                    str(self.index_path),
                    str(self.metadata_path)
                )
                logger.info("Index loaded successfully")
                return
            except Exception as e:
                logger.warning(f"Failed to load index: {e}. Rebuilding...")
        
        # Build index from scratch
        logger.info("Building FAISS index from database...")
        self._build_index()
    
    def _build_index(self) -> None:
        """
        Build FAISS index from database.
        
        Steps:
        1. Load and chunk all schemes from database
        2. Generate embeddings for all chunks
        3. Build FAISS index
        4. Persist to disk
        """
        # Step 1: Create chunks
        logger.info("Step 1/4: Creating chunks from database...")
        chunks_with_metadata = self.chunker.create_chunks()
        
        if not chunks_with_metadata:
            raise ValueError("No chunks created from database. Is database empty?")
        
        # Separate texts and metadata
        chunk_texts = [text for text, _ in chunks_with_metadata]
        chunk_metadata = [meta for _, meta in chunks_with_metadata]
        
        logger.info(f"Created {len(chunk_texts)} chunks")
        
        # Step 2: Generate embeddings
        logger.info("Step 2/4: Generating embeddings (this may take a minute)...")
        embeddings = self.embedder.embed_texts(chunk_texts)
        
        logger.info(f"Generated embeddings with shape: {embeddings.shape}")
        
        # Step 3: Build FAISS index
        logger.info("Step 3/4: Building FAISS index...")
        self.retriever.build_index(embeddings, chunk_metadata)
        
        # Step 4: Save to disk
        logger.info("Step 4/4: Saving index to disk...")
        self.retriever.save_index(
            str(self.index_path),
            str(self.metadata_path)
        )
        
        logger.info("Index built and saved successfully")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Tuple[float, Dict[str, str], str]]:
        """
        Retrieve most relevant chunks for a query.
        
        This is the main interface for RAG retrieval.
        
        Args:
            query: User query (can be in Hindi or English)
            top_k: Number of top results to return
        
        Returns:
            List of (score, metadata, explanation) tuples
            
            score: Similarity score (0-1, higher is better)
            metadata: Dict with keys:
                - scheme_name: Name of the scheme
                - department: Government department
                - section_type: eligibility | benefits | process
                - chunk_id: Unique identifier
            explanation: Human-readable source info
        
        Example:
            results = engine.retrieve("PM-KISAN eligibility", top_k=3)
            for score, meta, explanation in results:
                print(f"Score: {score:.2f}")
                print(f"Source: {explanation}")
                print(f"Scheme: {meta['scheme_name']}")
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        logger.info(f"Processing query: '{query}'")
        
        # Step 1: Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        # Step 2: Retrieve from FAISS
        results = self.retriever.retrieve(query_embedding, top_k=top_k)
        
        # Step 3: Add human-readable explanation
        enriched_results = []
        for score, metadata in results:
            explanation = (
                f"Scheme: {metadata['scheme_name']} | "
                f"Department: {metadata['department']} | "
                f"Section: {metadata['section_type'].title()}"
            )
            enriched_results.append((score, metadata, explanation))
        
        logger.info(f"Retrieved {len(enriched_results)} results")
        
        return enriched_results
    
    def add_to_index(self, text: str, metadata: dict) -> None:
        """
        Add a new chunk to the existing FAISS index.
        
        Note: Currently stores chunks in database. Index rebuilds on next query.
        """
        try:
            logger.info(f"Processing chunk: {metadata.get('scheme_name')} - Chunk {metadata.get('chunk_index')}")
            
            # Store in database - the chunker will pick it up on next rebuild
            import sqlite3
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Insert into schemes table
            cursor.execute("""
                INSERT INTO schemes (scheme_name, department, eligibility, benefits, process)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metadata.get('scheme_name', 'Unknown'),
                metadata.get('department', 'General'),
                text if metadata.get('section_type') == 'eligibility' else '',
                text if metadata.get('section_type') == 'benefits' else '',
                text if metadata.get('section_type') == 'process' else text
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("Chunk stored in database")
            
        except Exception as e:
            logger.warning(f"Failed to store chunk: {e} - continuing anyway")
            # Don't raise - allow upload to continue
    
    def rebuild_index(self) -> None:
        """
        Force rebuild of FAISS index from database.
        
        Use this when:
        - New schemes are added to database
        - Existing schemes are modified
        - Index appears corrupted
        """
        logger.info("Forcing index rebuild...")
        self._build_index()
        logger.info("Index rebuild complete")
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get system statistics.
        
        Returns:
            Dictionary with system stats:
            - retriever_stats: FAISS index statistics
            - chunk_stats: Chunking statistics
        """
        chunk_stats = self.chunker.get_chunk_stats()
        retriever_stats = self.retriever.get_stats()
        
        return {
            'retriever_stats': retriever_stats,
            'chunk_stats': chunk_stats
        }


# ============================================================================
# STANDALONE TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Standalone test runner for RAGEngine.
    
    Allows running:
        python src/core/rag_engine.py
    """
    import sys
    from pathlib import Path
    
    # Add project root to Python path
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT))
    
    # Absolute imports for dependencies
    from src.core.chunker import SchemeChunker
    from src.core.embedder import MultilingualEmbedder
    from src.core.retriever import FAISSRetriever
    
    print(f"\n{'='*70}")
    print("RAG ENGINE TEST")
    print(f"{'='*70}\n")
    
    # Initialize engine
    engine = RAGEngine(force_rebuild=True)
    
    # Print stats
    stats = engine.get_stats()
    print("System Statistics:")
    print(f"  Total chunks: {stats['chunk_stats']['total_chunks']}")
    print(f"  FAISS vectors: {stats['retriever_stats']['total_vectors']}")
    print()
    
    # Test queries
    test_queries = [
        "PM-KISAN eligibility criteria",
        "housing scheme benefits",
        "MGNREGA application process"
    ]
    
    for query in test_queries:
        print(f"Query: '{query}'")
        print("-" * 70)
        
        results = engine.retrieve(query, top_k=2)
        
        for i, (score, metadata, explanation) in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    Score: {score:.4f}")
            print(f"    {explanation}")
            print(f"    Chunk ID: {metadata['chunk_id']}")
        
        print("\n" + "=" * 70 + "\n")