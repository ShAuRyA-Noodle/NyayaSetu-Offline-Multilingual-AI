"""
Centralized Database Manager

Provides connection management, context managers, and migration support
for the NyayaSetu governance database.

Backend selection is automatic based on DATABASE_URL:
  - Unset/empty or sqlite://... -> SQLite (local dev)
  - postgresql://... or postgres://... -> PostgreSQL (production)

Route code does not need to change between backends. The db_adapter layer
translates SQLite idioms (?, PRAGMA, datetime('now'), lastrowid, etc.) to
their Postgres equivalents at runtime.
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Optional

from . import db_adapter

logger = logging.getLogger(__name__)

# Kept for backwards compatibility with any code that imports DB_PATH directly
DB_PATH = db_adapter.get_db_path()


def get_db_path() -> str:
    return db_adapter.get_db_path()


# Re-export adapter primitives so existing `from .database import get_db` keeps working
get_db = db_adapter.get_db
get_connection = db_adapter.get_connection


def _init_postgres_schema():
    """Execute postgres_schema.sql once on startup (idempotent)."""
    from pathlib import Path
    schema_path = Path(__file__).parent / "postgres_schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Postgres schema file missing: {schema_path}")
    sql = schema_path.read_text(encoding="utf-8")
    # psycopg2 can execute a multi-statement script via a single execute() call
    with get_db() as conn:
        # Use the raw psycopg2 cursor - multi-statement DDL doesn't need adapter translation
        raw_cur = conn._conn.cursor()
        try:
            raw_cur.execute(sql)
        finally:
            raw_cur.close()
    logger.info("Postgres schema initialized from postgres_schema.sql")


def _ensure_sqlite_unique_indexes(conn):
    """Add UNIQUE indexes required for ON CONFLICT clauses (SQLite-only)."""
    try:
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_scheme_assignments_pair
            ON scheme_assignments(scheme_id, officer_id)
        """)
    except Exception as e:
        logger.debug(f"uq_scheme_assignments_pair index creation skipped: {e}")


def init_core_tables():
    """Create core tables if they don't exist (called on startup)."""
    if db_adapter.IS_POSTGRES:
        _init_postgres_schema()
        return
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'citizen'
                    CHECK(role IN ('citizen', 'officer', 'admin')),
                department TEXT,
                designation TEXT,
                assigned_schemes TEXT,
                location TEXT,
                preferred_language TEXT DEFAULT 'en',
                is_active BOOLEAN DEFAULT 1,
                email_verified BOOLEAN DEFAULT 0,
                phone_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                officer_signature_path TEXT,
                officer_seal_path TEXT,
                bio TEXT,
                saved_schemes TEXT,
                notification_preferences TEXT,
                profile_picture_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grievances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grievance_id TEXT UNIQUE NOT NULL,
                citizen_id INTEGER,
                citizen_name TEXT,
                citizen_phone TEXT,
                citizen_email TEXT,
                citizen_location TEXT,
                title TEXT,
                description TEXT NOT NULL,
                category TEXT,
                language TEXT DEFAULT 'en',
                department TEXT,
                sub_department TEXT,
                assigned_officer_id INTEGER,
                assigned_officer_name TEXT,
                priority TEXT DEFAULT 'medium',
                confidence_score REAL,
                estimated_resolution_days INTEGER,
                related_schemes TEXT,
                status TEXT DEFAULT 'pending',
                routing_reasoning TEXT,
                submitted_at TIMESTAMP,
                accepted_at TIMESTAMP,
                assigned_at TIMESTAMP,
                resolved_at TIMESTAMP,
                closed_at TIMESTAMP,
                resolution_notes TEXT,
                resolution_attachments TEXT,
                citizen_satisfaction INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (citizen_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grievance_status_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grievance_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                updated_by TEXT,
                update_notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (grievance_id) REFERENCES grievances(grievance_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grievance_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grievance_id TEXT NOT NULL,
                commenter_type TEXT,
                commenter_name TEXT,
                comment_text TEXT NOT NULL,
                is_internal BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (grievance_id) REFERENCES grievances(grievance_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schemes_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_id TEXT UNIQUE NOT NULL,
                scheme_name TEXT NOT NULL,
                created_by INTEGER,
                assigned_officer INTEGER,
                source_file TEXT,
                document_type TEXT,
                file_size INTEGER,
                status TEXT DEFAULT 'active',
                version INTEGER DEFAULT 1,
                total_chunks INTEGER DEFAULT 0,
                total_characters INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheme_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                changed_by INTEGER,
                change_type TEXT,
                change_description TEXT,
                source_file TEXT,
                file_size INTEGER,
                chunk_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT 1,
                FOREIGN KEY (scheme_id) REFERENCES schemes_metadata(scheme_id),
                FOREIGN KEY (changed_by) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheme_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_id TEXT NOT NULL,
                officer_id INTEGER NOT NULL,
                assigned_by INTEGER,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                can_edit BOOLEAN DEFAULT 1,
                can_delete BOOLEAN DEFAULT 0,
                can_reassign BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                revoked_at TIMESTAMP,
                revoked_by INTEGER,
                FOREIGN KEY (scheme_id) REFERENCES schemes_metadata(scheme_id),
                FOREIGN KEY (officer_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_id TEXT,
                uploaded_by INTEGER,
                upload_type TEXT,
                filename TEXT,
                file_size INTEGER,
                file_hash TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                chunks_processed INTEGER DEFAULT 0,
                processing_time_ms INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
        """)

        # Officer registration codes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officer_registration_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                designation TEXT,
                created_by INTEGER,
                used_by INTEGER,
                is_used BOOLEAN DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (used_by) REFERENCES users(id)
            )
        """)

        # Ensure all critical columns exist (handles pre-migration DBs)
        _ensure_columns_exist(conn)
        _ensure_sqlite_unique_indexes(conn)

        logger.info("Core tables initialized")


def _ensure_column_exists(conn, table: str, column: str, col_type: str, default=None):
    """Add a column to a table if it doesn't already exist. Dialect-aware."""
    if db_adapter.IS_POSTGRES:
        # In Postgres mode the full schema is created by postgres_schema.sql
        # which already includes every column. No-op for safety.
        return
    # SQLite path
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        default_clause = f"DEFAULT {default}" if default is not None else ""
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} {default_clause}")
        logger.info(f"Added missing column: {table}.{column}")


def _ensure_columns_exist(conn):
    """Ensure all columns referenced by route code exist in the database."""
    # -- users --
    _ensure_column_exists(conn, "users", "login_count", "INTEGER", 0)
    _ensure_column_exists(conn, "users", "failed_login_attempts", "INTEGER", 0)
    _ensure_column_exists(conn, "users", "locked_until", "TIMESTAMP")

    # -- sessions --
    _ensure_column_exists(conn, "sessions", "ip_address", "TEXT")
    _ensure_column_exists(conn, "sessions", "user_agent", "TEXT")
    _ensure_column_exists(conn, "sessions", "device_type", "TEXT")
    _ensure_column_exists(conn, "sessions", "last_activity", "TIMESTAMP")
    _ensure_column_exists(conn, "sessions", "logout_at", "TIMESTAMP")
    _ensure_column_exists(conn, "sessions", "logout_reason", "TEXT")

    # -- grievances --
    _ensure_column_exists(conn, "grievances", "citizen_id", "INTEGER")
    _ensure_column_exists(conn, "grievances", "subcategory", "TEXT")
    _ensure_column_exists(conn, "grievances", "ai_confidence", "REAL")
    _ensure_column_exists(conn, "grievances", "ai_summary", "TEXT")
    _ensure_column_exists(conn, "grievances", "ai_reasoning", "TEXT")
    _ensure_column_exists(conn, "grievances", "view_count", "INTEGER", 0)
    _ensure_column_exists(conn, "grievances", "comment_count", "INTEGER", 0)
    _ensure_column_exists(conn, "grievances", "last_status_change_at", "TIMESTAMP")

    # -- schemes_metadata --
    _ensure_column_exists(conn, "schemes_metadata", "view_count", "INTEGER", 0)
    _ensure_column_exists(conn, "schemes_metadata", "query_count", "INTEGER", 0)
    _ensure_column_exists(conn, "schemes_metadata", "category", "TEXT")
    _ensure_column_exists(conn, "schemes_metadata", "department", "TEXT")
    _ensure_column_exists(conn, "schemes_metadata", "file_hash", "TEXT")
    _ensure_column_exists(conn, "schemes_metadata", "indexed_at", "TIMESTAMP")
    _ensure_column_exists(conn, "schemes_metadata", "tags", "TEXT")
    _ensure_column_exists(conn, "schemes_metadata", "keywords", "TEXT")
    _ensure_column_exists(conn, "schemes_metadata", "description", "TEXT")
    _ensure_column_exists(conn, "schemes_metadata", "target_audience", "TEXT")

    # -- scheme_versions --
    _ensure_column_exists(conn, "scheme_versions", "file_hash", "TEXT")
    _ensure_column_exists(conn, "scheme_versions", "character_count", "INTEGER")

    # -- grievance_comments (ensure migration columns exist) --
    _ensure_column_exists(conn, "grievance_comments", "author_id", "INTEGER")
    _ensure_column_exists(conn, "grievance_comments", "author_name", "TEXT")
    _ensure_column_exists(conn, "grievance_comments", "author_role", "TEXT")
    _ensure_column_exists(conn, "grievance_comments", "comment_type", "TEXT", "'note'")
    _ensure_column_exists(conn, "grievance_comments", "is_public", "BOOLEAN", 1)
    _ensure_column_exists(conn, "grievance_comments", "created_at", "TIMESTAMP")

    # -- notices table (may not exist yet) --
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id TEXT UNIQUE NOT NULL,
            reference_number TEXT,
            scheme_name TEXT NOT NULL,
            notice_type TEXT NOT NULL,
            officer_id INTEGER,
            officer_name TEXT,
            officer_department TEXT,
            officer_designation TEXT,
            subject TEXT,
            body TEXT,
            formatted_notice TEXT,
            language TEXT DEFAULT 'en',
            effective_date TEXT,
            status TEXT DEFAULT 'draft',
            reviewed_by INTEGER,
            reviewed_at TIMESTAMP,
            review_notes TEXT,
            approved_by INTEGER,
            approved_at TIMESTAMP,
            published_by INTEGER,
            published_at TIMESTAMP,
            withdrawn_by INTEGER,
            withdrawn_at TIMESTAMP,
            withdrawal_reason TEXT,
            view_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -- scheme_chunks table --
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheme_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id TEXT UNIQUE,
            scheme_id TEXT NOT NULL,
            chunk_index INTEGER,
            chunk_text TEXT,
            chunk_size INTEGER,
            section_type TEXT,
            section_title TEXT,
            language TEXT DEFAULT 'en',
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -- grievance_status_history (new extended table) --
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grievance_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_by INTEGER,
            changed_by_name TEXT,
            changed_by_role TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -- grievance_ratings --
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grievance_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT UNIQUE NOT NULL,
            citizen_id INTEGER,
            rating INTEGER,
            resolution_quality INTEGER,
            response_time INTEGER,
            officer_behavior INTEGER,
            feedback_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -- notifications --
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            message TEXT NOT NULL,
            notification_type TEXT DEFAULT 'info',
            related_id TEXT,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -- sla_records --
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sla_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT UNIQUE NOT NULL,
            department TEXT,
            priority TEXT,
            sla_hours INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline_at TIMESTAMP,
            resolved_at TIMESTAMP,
            is_breached BOOLEAN DEFAULT 0,
            paused BOOLEAN DEFAULT 0,
            pause_reason TEXT,
            paused_at TIMESTAMP
        )
    """)

    # -- sla_config --
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sla_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT UNIQUE NOT NULL,
            critical_sla_hours INTEGER DEFAULT 24,
            high_sla_hours INTEGER DEFAULT 72,
            medium_sla_hours INTEGER DEFAULT 168,
            low_sla_hours INTEGER DEFAULT 336,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
