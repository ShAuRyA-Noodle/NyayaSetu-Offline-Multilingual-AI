"""
Migration 001: Enterprise Authentication System

Adds:
- Enhanced user fields (lockout, password history, profile)
- Enhanced sessions (IP, device tracking)
- Audit logs table
- Password reset tokens table
"""


def upgrade(conn):
    cursor = conn.cursor()

    # Check existing columns before altering
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    user_additions = {
        "failed_login_attempts": "INTEGER DEFAULT 0",
        "locked_until": "TIMESTAMP",
        "password_changed_at": "TIMESTAMP",
        "password_history": "TEXT",
        "full_name": "TEXT",
        "address": "TEXT",
        "notification_preferences": "TEXT",
        "login_count": "INTEGER DEFAULT 0",
        "avatar_url": "TEXT",
    }

    for col, col_type in user_additions.items():
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

    # Enhanced sessions
    cursor.execute("PRAGMA table_info(sessions)")
    session_cols = {row[1] for row in cursor.fetchall()}

    session_additions = {
        "ip_address": "TEXT",
        "user_agent": "TEXT",
        "device_type": "TEXT",
        "last_activity": "TIMESTAMP",
        "logout_at": "TIMESTAMP",
        "logout_reason": "TEXT",
    }

    for col, col_type in session_additions.items():
        if col not in session_cols:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_type}")

    # Audit logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            role TEXT,
            action_type TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            endpoint_path TEXT,
            request_method TEXT,
            ip_address TEXT,
            user_agent TEXT,
            request_headers TEXT,
            status_code INTEGER,
            error_message TEXT,
            duration_ms INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_logs(status_code)")

    # Password reset tokens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()


def downgrade(conn):
    conn.execute("DROP TABLE IF EXISTS password_reset_tokens")
    conn.execute("DROP TABLE IF EXISTS audit_logs")
    conn.commit()
