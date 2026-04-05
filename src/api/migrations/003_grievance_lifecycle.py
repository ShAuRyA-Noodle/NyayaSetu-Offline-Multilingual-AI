"""
Migration 003: Grievance Lifecycle

SLA tracking, notifications, ratings, escalations, enhanced comments/status history.
"""


def upgrade(conn):
    cursor = conn.cursor()

    # Enhance grievances table
    for col_def in [
        "subcategory TEXT",
        "ai_confidence REAL",
        "ai_summary TEXT",
        "ai_reasoning TEXT",
        "has_attachments BOOLEAN DEFAULT 0",
        "attachment_count INTEGER DEFAULT 0",
        "attachment_urls TEXT",
        "source TEXT DEFAULT 'web'",
        "view_count INTEGER DEFAULT 0",
        "comment_count INTEGER DEFAULT 0",
        "last_status_change_at TIMESTAMP",
    ]:
        try:
            cursor.execute(f"ALTER TABLE grievances ADD COLUMN {col_def}")
        except Exception:
            pass

    # Grievance status history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievance_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_by INTEGER,
            changed_by_name TEXT,
            changed_by_role TEXT,
            change_reason TEXT,
            notes TEXT,
            is_auto_change BOOLEAN DEFAULT 0,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grievance_id) REFERENCES grievances(grievance_id),
            FOREIGN KEY (changed_by) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status_history_grievance ON grievance_status_history(grievance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status_history_changed_at ON grievance_status_history(changed_at DESC)")

    # Enhance grievance_comments
    for col_def in [
        "author_id INTEGER",
        "author_role TEXT",
        "author_name TEXT",
        "comment_type TEXT DEFAULT 'note'",
        "is_public BOOLEAN DEFAULT 1",
        "is_pinned BOOLEAN DEFAULT 0",
        "updated_at TIMESTAMP",
        "edited_at TIMESTAMP",
    ]:
        try:
            cursor.execute(f"ALTER TABLE grievance_comments ADD COLUMN {col_def}")
        except Exception:
            pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_grievance ON grievance_comments(grievance_id)")

    # SLA Configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sla_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT NOT NULL UNIQUE,
            critical_sla_hours INTEGER NOT NULL DEFAULT 24,
            high_sla_hours INTEGER NOT NULL DEFAULT 72,
            medium_sla_hours INTEGER NOT NULL DEFAULT 168,
            low_sla_hours INTEGER NOT NULL DEFAULT 336,
            escalation_enabled BOOLEAN DEFAULT 1,
            working_hours_start TEXT DEFAULT '09:00',
            working_hours_end TEXT DEFAULT '17:00',
            working_days TEXT DEFAULT '1,2,3,4,5',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Pre-populate departments
    departments = [
        ('agriculture', 24, 72, 168, 336),
        ('rural_development', 24, 72, 168, 336),
        ('urban_development', 24, 72, 168, 336),
        ('social_welfare', 24, 48, 120, 240),
        ('health', 12, 48, 120, 240),
        ('education', 24, 72, 168, 336),
        ('finance', 24, 72, 168, 336),
        ('law_enforcement', 12, 48, 120, 240),
    ]
    for dept in departments:
        try:
            cursor.execute("""
                INSERT INTO sla_config (department, critical_sla_hours, high_sla_hours, medium_sla_hours, low_sla_hours)
                VALUES (?, ?, ?, ?, ?)
            """, dept)
        except Exception:
            pass

    # Grievance SLA tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievance_sla (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT UNIQUE NOT NULL,
            sla_hours INTEGER NOT NULL,
            due_date TIMESTAMP NOT NULL,
            business_hours_used REAL DEFAULT 0,
            is_breached BOOLEAN DEFAULT 0,
            breached_at TIMESTAMP,
            breach_duration_hours REAL,
            is_escalated BOOLEAN DEFAULT 0,
            escalation_level INTEGER DEFAULT 0,
            escalated_at TIMESTAMP,
            resolved_at TIMESTAMP,
            resolution_within_sla BOOLEAN,
            resolution_time_hours REAL,
            is_paused BOOLEAN DEFAULT 0,
            paused_at TIMESTAMP,
            pause_reason TEXT,
            total_paused_hours REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grievance_id) REFERENCES grievances(grievance_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sla_grievance ON grievance_sla(grievance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sla_due_date ON grievance_sla(due_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sla_breached ON grievance_sla(is_breached)")

    # Notifications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievance_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT,
            recipient_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL DEFAULT 'in_app',
            subject TEXT,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            read_at TIMESTAMP,
            priority_level TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grievance_id) REFERENCES grievances(grievance_id),
            FOREIGN KEY (recipient_id) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON grievance_notifications(recipient_id, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_grievance ON grievance_notifications(grievance_id)")

    # Ratings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievance_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT UNIQUE NOT NULL,
            citizen_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            resolution_quality INTEGER CHECK(resolution_quality BETWEEN 1 AND 5),
            response_time INTEGER CHECK(response_time BETWEEN 1 AND 5),
            officer_behavior INTEGER CHECK(officer_behavior BETWEEN 1 AND 5),
            feedback_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grievance_id) REFERENCES grievances(grievance_id),
            FOREIGN KEY (citizen_id) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ratings_grievance ON grievance_ratings(grievance_id)")

    # Escalations log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievance_escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id TEXT NOT NULL,
            escalation_level INTEGER NOT NULL,
            escalated_from INTEGER,
            escalated_to INTEGER,
            reason TEXT NOT NULL,
            auto_escalated BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'pending',
            action_taken TEXT,
            acknowledged_at TIMESTAMP,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grievance_id) REFERENCES grievances(grievance_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_escalation_grievance ON grievance_escalations(grievance_id)")

    conn.commit()


def downgrade(conn):
    for table in [
        "grievance_escalations", "grievance_ratings",
        "grievance_notifications", "grievance_sla",
        "sla_config", "grievance_status_history",
    ]:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()
