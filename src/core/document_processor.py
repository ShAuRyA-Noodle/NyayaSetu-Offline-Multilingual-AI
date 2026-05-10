"""
Document Processor for NyayaSetu
Extracts text from PDF, DOCX, and TXT files
"""

import fitz  # PyMuPDF
from docx import Document
import re
from typing import List
import logging

logger = logging.getLogger(__name__)

# 10 MB of *text* (not file size) — past this we stop reading and warn.
# Real govt PDFs that exceed this cap are typically scanned-image bundles
# that should be OCR-routed, not loaded directly into the embedder.
MAX_EXTRACTED_CHARS = 10 * 1024 * 1024  # 10 MB of text


class DocumentProcessor:
    """Process uploaded documents and extract text"""

    def extract_text(self, file_path: str, filename: str) -> str:
        """
        Extract text from uploaded file

        Args:
            file_path: Path to the file
            filename: Name of the file (to determine type)

        Returns:
            Extracted text as string (capped at MAX_EXTRACTED_CHARS).
        """
        try:
            if filename.endswith('.pdf'):
                text = self._extract_from_pdf(file_path)
            elif filename.endswith('.docx'):
                text = self._extract_from_docx(file_path)
            elif filename.endswith('.txt'):
                text = self._extract_from_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {filename}")

            # OOM guard. Capping is preferable to dying mid-embed and losing
            # the rest of the upload batch.
            if len(text) > MAX_EXTRACTED_CHARS:
                logger.warning(
                    "Extracted text from %s exceeds cap (%d > %d chars). Truncating.",
                    filename, len(text), MAX_EXTRACTED_CHARS,
                )
                text = text[:MAX_EXTRACTED_CHARS]
            return text
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            raise
    
    def _extract_from_pdf(self, path: str) -> str:
        """Extract text from PDF"""
        logger.info(f"Extracting text from PDF: {path}")
        doc = fitz.open(path)
        text = ""
        for page_num, page in enumerate(doc):
            text += page.get_text()
        doc.close()
        logger.info(f"Extracted {len(text)} characters from PDF")
        return text
    
    def _extract_from_docx(self, path: str) -> str:
        """Extract text from DOCX"""
        logger.info(f"Extracting text from DOCX: {path}")
        doc = Document(path)
        text = "\n".join([para.text for para in doc.paragraphs])
        logger.info(f"Extracted {len(text)} characters from DOCX")
        return text
    
    def _extract_from_txt(self, path: str) -> str:
        """Extract text from TXT"""
        logger.info(f"Reading text file: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"Read {len(text)} characters from TXT")
        return text
    
    def chunk_text(self, text: str, max_length: int = 1000) -> List[str]:
        """
        Split text into chunks for vector database
        
        Args:
            text: Text to chunk
            max_length: Maximum chunk size in characters
            
        Returns:
            List of text chunks
        """
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If adding this paragraph exceeds max_length
            if len(current_chunk) + len(para) + 2 > max_length:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # Start new chunk with this paragraph
                current_chunk = para
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def validate_document(self, text: str, min_chars: int = 500) -> bool:
        """
        Validate extracted text
        
        Args:
            text: Extracted text
            min_chars: Minimum required characters
            
        Returns:
            True if valid, False otherwise
        """
        if not text or len(text.strip()) < min_chars:
            logger.warning(f"Document too short: {len(text)} chars (min: {min_chars})")
            return False
        return True