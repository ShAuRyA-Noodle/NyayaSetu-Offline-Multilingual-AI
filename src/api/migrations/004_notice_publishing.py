"""
Migration 004: Notice Publishing System

Full notice lifecycle: draft, review, approve, publish, withdraw.
"""


def upgrade(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id TEXT UNIQUE NOT NULL,
            reference_number TEXT UNIQUE NOT NULL,
            scheme_id TEXT,
            scheme_name TEXT,
            notice_type TEXT NOT NULL CHECK(notice_type IN ('circular','order','memo','notification','advisory','amendment')),
            officer_id INTEGER NOT NULL,
            officer_name TEXT,
            officer_designation TEXT,
            officer_department TEXT,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            formatted_html TEXT,
            formatted_notice TEXT,
            language TEXT DEFAULT 'en',
            supersedes_notice_id TEXT,
            legal_authority TEXT,
            effective_date TEXT,
            expiry_date TEXT,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft','pending_review','approved','published','archived','withdrawn')),
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
            target_audience TEXT,
            distribution_channels TEXT,
            view_count INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            pdf_path TEXT,
            pdf_generated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (officer_id) REFERENCES users(id),
            FOREIGN KEY (scheme_id) REFERENCES schemes_metadata(scheme_id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notices_id ON notices(notice_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notices_officer ON notices(officer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notices_status ON notices(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notices_published ON notices(published_at DESC)")

    conn.commit()


def downgrade(conn):
    conn.execute("DROP TABLE IF EXISTS notices")
    conn.commit()
