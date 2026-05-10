"""
Migration 005: Authorization columns required by P0 authz hardening pass.

Adds columns referenced by route handlers but not yet present in the schema:
  - grievances.submitted_by_officer_id      (officer-on-behalf submissions)
  - grievance_comments.is_internal          (officer-only internal notes)
  - grievance_comments.author_department    (dept scoping for internal comments)

Idempotent on both SQLite (ALTER TABLE ... ADD COLUMN guarded by try/except)
and Postgres (handled via the postgres_schema.sql / db_adapter path; see
runner._mark_legacy_applied for how the postgres bootstrap skips no-op SQLite
migrations).
"""


def upgrade(conn):
    cursor = conn.cursor()

    # grievances.submitted_by_officer_id ----------------------------------
    try:
        cursor.execute(
            "ALTER TABLE grievances ADD COLUMN submitted_by_officer_id INTEGER"
        )
    except Exception:
        # Column already exists — fine.
        pass

    # grievance_comments.is_internal --------------------------------------
    try:
        cursor.execute(
            "ALTER TABLE grievance_comments ADD COLUMN is_internal INTEGER DEFAULT 0"
        )
    except Exception:
        pass

    # grievance_comments.author_department --------------------------------
    try:
        cursor.execute(
            "ALTER TABLE grievance_comments ADD COLUMN author_department TEXT"
        )
    except Exception:
        pass

    # Helpful indexes for the new dept-scoped reads.
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_grievances_submitted_by_officer "
            "ON grievances(submitted_by_officer_id)"
        )
    except Exception:
        pass
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_grievance_comments_dept "
            "ON grievance_comments(author_department)"
        )
    except Exception:
        pass

    conn.commit()


def downgrade(conn):
    # SQLite cannot drop columns without table rebuild; left intentionally
    # empty. Postgres drop would be:
    #   ALTER TABLE grievances DROP COLUMN submitted_by_officer_id;
    #   ALTER TABLE grievance_comments DROP COLUMN is_internal;
    #   ALTER TABLE grievance_comments DROP COLUMN author_department;
    pass
