"""
Chunker Module - Converts database records into semantic chunks with metadata.

This module reads scheme data from SQLite and creates structured text chunks
that preserve context and traceability. Each chunk represents a single section
of a scheme (eligibility, benefits, or process).
"""

import sqlite3
from typing import List, Dict, Tuple
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemeChunker:
    """
    Converts scheme database records into text chunks with metadata.
    
    Each scheme is broken into 3 chunks:
    - Eligibility criteria
    - Benefits provided
    - Application process
    
    This preserves granular traceability for explainability.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize chunker with database path.
        
        Args:
            db_path: Path to SQLite database containing schemes
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        logger.info(f"Chunker initialized with database: {db_path}")
    
    def create_chunks(self) -> List[Tuple[str, Dict[str, str]]]:
        """
        Read all schemes from database and create semantic chunks.
        
        Returns:
            List of tuples: [(chunk_text, metadata), ...]
            
            chunk_text: Human-readable text content
            metadata: {
                'scheme_name': str,
                'department': str,
                'section_type': str,  # 'eligibility' | 'benefits' | 'process'
                'chunk_id': str  # Unique identifier
            }
        
        Raises:
            sqlite3.Error: If database query fails
        """
        chunks = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Fetch all schemes
            cursor.execute("""
                SELECT scheme_name, department, eligibility, benefits, process
                FROM schemes
            """)
            
            schemes = cursor.fetchall()
            
            if not schemes:
                logger.warning("No schemes found in database")
                return chunks
            
            logger.info(f"Processing {len(schemes)} schemes into chunks")
            
            for scheme in schemes:
                scheme_name = scheme['scheme_name']
                department = scheme['department']
                
                # Create chunk for ELIGIBILITY section
                if scheme['eligibility'] and scheme['eligibility'].strip():
                    chunk_text = self._format_chunk(
                        scheme_name=scheme_name,
                        section_type='Eligibility',
                        content=scheme['eligibility']
                    )
                    metadata = {
                        'scheme_name': scheme_name,
                        'department': department,
                        'section_type': 'eligibility',
                        'chunk_id': f"{scheme_name}_eligibility"
                    }
                    chunks.append((chunk_text, metadata))
                
                # Create chunk for BENEFITS section
                if scheme['benefits'] and scheme['benefits'].strip():
                    chunk_text = self._format_chunk(
                        scheme_name=scheme_name,
                        section_type='Benefits',
                        content=scheme['benefits']
                    )
                    metadata = {
                        'scheme_name': scheme_name,
                        'department': department,
                        'section_type': 'benefits',
                        'chunk_id': f"{scheme_name}_benefits"
                    }
                    chunks.append((chunk_text, metadata))
                
                # Create chunk for PROCESS section
                if scheme['process'] and scheme['process'].strip():
                    chunk_text = self._format_chunk(
                        scheme_name=scheme_name,
                        section_type='Application Process',
                        content=scheme['process']
                    )
                    metadata = {
                        'scheme_name': scheme_name,
                        'department': department,
                        'section_type': 'process',
                        'chunk_id': f"{scheme_name}_process"
                    }
                    chunks.append((chunk_text, metadata))
            
            conn.close()
            logger.info(f"Created {len(chunks)} chunks from {len(schemes)} schemes")
            
            return chunks
        
        except sqlite3.Error as e:
            logger.error(f"Database error while creating chunks: {e}")
            raise
    
    def _format_chunk(self, scheme_name: str, section_type: str, content: str) -> str:
        """
        Format a chunk with structured context for better retrieval.
        
        This format helps the embedding model understand context:
        - What scheme this is about
        - What aspect (eligibility/benefits/process)
        - The actual content
        
        Args:
            scheme_name: Name of the scheme
            section_type: Type of section (Eligibility/Benefits/Process)
            content: The actual content text
        
        Returns:
            Formatted chunk text
        """
        # Structured format that helps embedding model capture semantics
        formatted = f"""Scheme: {scheme_name}
Section: {section_type}

{content}"""
        
        return formatted.strip()
    
    def get_chunk_stats(self) -> Dict[str, int]:
        """
        Get statistics about chunks (useful for monitoring).
        
        Returns:
            Dictionary with chunk statistics
        """
        chunks = self.create_chunks()
        
        stats = {
            'total_chunks': len(chunks),
            'eligibility_chunks': sum(1 for _, m in chunks if m['section_type'] == 'eligibility'),
            'benefits_chunks': sum(1 for _, m in chunks if m['section_type'] == 'benefits'),
            'process_chunks': sum(1 for _, m in chunks if m['section_type'] == 'process'),
        }
        
        return stats


if __name__ == "__main__":
    # Standalone test
    chunker = SchemeChunker("data/governance.db")
    chunks = chunker.create_chunks()
    
    print(f"\n{'='*60}")
    print(f"CHUNKER TEST - Created {len(chunks)} chunks")
    print(f"{'='*60}\n")
    
    for i, (text, metadata) in enumerate(chunks[:3], 1):
        print(f"Chunk {i}:")
        print(f"  Scheme: {metadata['scheme_name']}")
        print(f"  Section: {metadata['section_type']}")
        print(f"  Text preview: {text[:150]}...")
        print()
    
    stats = chunker.get_chunk_stats()
    print(f"Statistics: {stats}")