"""
Migration 002: Advanced Scheme Management

Enhances schemes_metadata, scheme_versions, scheme_assignments, upload_history.
Adds scheme_chunks table for granular chunk tracking.
"""


def upgrade(conn):
    cursor = conn.cursor()

    # Enhanced schemes_metadata
    for col_def in [
        "file_hash TEXT",
        "mime_type TEXT",
        "processing_status TEXT DEFAULT 'completed'",
        "tags TEXT",
        "keywords TEXT",
        "description TEXT",
        "category TEXT",
        "target_audience TEXT",
        "department TEXT",
        "is_current_version BOOLEAN DEFAULT 1",
        "avg_chunk_size REAL",
        "embedding_model TEXT",
        "indexed_at TIMESTAMP",
        "view_count INTEGER DEFAULT 0",
        "query_count INTEGER DEFAULT 0",
        "avg_relevance_score REAL",
    ]:
        try:
            cursor.execute(f"ALTER TABLE schemes_metadata ADD COLUMN {col_def}")
        except Exception:
            pass

    # Enhanced scheme_versions
    for col_def in [
        "file_hash TEXT",
        "character_count INTEGER",
        "diff_summary TEXT",
    ]:
        try:
            cursor.execute(f"ALTER TABLE scheme_versions ADD COLUMN {col_def}")
        except Exception:
            pass

    # Enhanced scheme_assignments
    for col_def in [
        "can_publish BOOLEAN DEFAULT 0",
        "assignment_reason TEXT",
        "responsibility_type TEXT DEFAULT 'primary'",
    ]:
        try:
            cursor.execute(f"ALTER TABLE scheme_assignments ADD COLUMN {col_def}")
        except Exception:
            pass

    # Enhanced upload_history
    for col_def in [
        "mime_type TEXT",
        "validation_passed BOOLEAN",
        "validation_errors TEXT",
        "retry_count INTEGER DEFAULT 0",
    ]:
        try:
            cursor.execute(f"ALTER TABLE upload_history ADD COLUMN {col_def}")
        except Exception:
            pass

    # Scheme chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheme_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id TEXT UNIQUE NOT NULL,
            scheme_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            chunk_size INTEGER NOT NULL,
            section_type TEXT,
            section_title TEXT,
            embedding_checksum TEXT,
            language TEXT DEFAULT 'en',
            keywords TEXT,
            confidence_scores TEXT,
            readability_score REAL,
            information_density REAL,
            duplicate_score REAL,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated_at TIMESTAMP,
            FOREIGN KEY (scheme_id) REFERENCES schemes_metadata(scheme_id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_scheme ON scheme_chunks(scheme_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_section ON scheme_chunks(section_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_version ON scheme_chunks(scheme_id, version)")

    conn.commit()


def downgrade(conn):
    conn.execute("DROP TABLE IF EXISTS scheme_chunks")
    conn.commit()
