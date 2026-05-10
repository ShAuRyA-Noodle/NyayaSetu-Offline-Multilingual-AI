-- =============================================================================
-- NyayaSetu PostgreSQL Schema
-- Mirrors the authoritative SQLite schema (from data/governance.db) exactly.
-- Translations from SQLite:
--   INTEGER PRIMARY KEY AUTOINCREMENT  ->  SERIAL PRIMARY KEY
--   BOOLEAN DEFAULT 1/0                ->  BOOLEAN DEFAULT TRUE/FALSE
--   TEXT, INTEGER, REAL, TIMESTAMP     ->  unchanged
-- Added: UNIQUE (scheme_id, officer_id) on scheme_assignments (needed for ON CONFLICT)
-- All CREATE TABLE statements use IF NOT EXISTS so this is idempotent.
-- =============================================================================

-- --- Migrations tracking -----------------------------------------------------
CREATE TABLE IF NOT EXISTS _migrations (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --- Users ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                       SERIAL PRIMARY KEY,
    username                 TEXT NOT NULL UNIQUE,
    email                    TEXT NOT NULL UNIQUE,
    phone                    TEXT UNIQUE,
    password_hash            TEXT NOT NULL,
    role                     TEXT NOT NULL DEFAULT 'citizen' CHECK (role IN ('citizen','officer','admin')),
    department               TEXT,
    designation              TEXT,
    assigned_schemes         TEXT,
    location                 TEXT,
    preferred_language       TEXT DEFAULT 'en',
    is_active                BOOLEAN DEFAULT TRUE,
    email_verified           BOOLEAN DEFAULT FALSE,
    phone_verified           BOOLEAN DEFAULT FALSE,
    created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login               TIMESTAMP,
    updated_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    failed_login_attempts    INTEGER DEFAULT 0,
    locked_until             TIMESTAMP,
    password_changed_at      TIMESTAMP,
    password_history         TEXT,
    full_name                TEXT,
    address                  TEXT,
    notification_preferences TEXT,
    login_count              INTEGER DEFAULT 0,
    avatar_url               TEXT
);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role     ON users(role);

-- --- Sessions ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    token          TEXT NOT NULL UNIQUE,
    expires_at     TIMESTAMP NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active      BOOLEAN DEFAULT TRUE,
    ip_address     TEXT,
    user_agent     TEXT,
    device_type    TEXT,
    last_activity  TIMESTAMP,
    logout_at      TIMESTAMP,
    logout_reason  TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user  ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);

-- --- User Profiles ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profiles (
    id                       SERIAL PRIMARY KEY,
    user_id                  INTEGER NOT NULL UNIQUE REFERENCES users(id),
    officer_signature_path   TEXT,
    officer_seal_path        TEXT,
    bio                      TEXT,
    saved_schemes            TEXT,
    notification_preferences TEXT,
    profile_picture_path     TEXT
);

-- --- Password Reset Tokens --------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    token      TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used       BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --- Audit Logs -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id),
    username         TEXT,
    role             TEXT,
    action_type      TEXT NOT NULL,
    resource_type    TEXT,
    resource_id      TEXT,
    endpoint_path    TEXT,
    request_method   TEXT,
    ip_address       TEXT,
    user_agent       TEXT,
    request_headers  TEXT,
    status_code      INTEGER,
    error_message    TEXT,
    duration_ms      INTEGER,
    timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_user      ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_resource  ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_status    ON audit_logs(status_code);

-- --- Legacy schemes table (pre-schemes_metadata) ----------------------------
CREATE TABLE IF NOT EXISTS schemes (
    id           SERIAL PRIMARY KEY,
    scheme_name  TEXT,
    department   TEXT,
    eligibility  TEXT,
    benefits     TEXT,
    process      TEXT
);

-- --- Schemes Metadata -------------------------------------------------------
CREATE TABLE IF NOT EXISTS schemes_metadata (
    id                  SERIAL PRIMARY KEY,
    scheme_id           TEXT NOT NULL UNIQUE,
    scheme_name         TEXT NOT NULL,
    created_by          INTEGER NOT NULL REFERENCES users(id),
    assigned_officer    INTEGER,
    source_file         TEXT NOT NULL,
    document_type       TEXT,
    file_size           INTEGER,
    status              TEXT DEFAULT 'active',
    version             INTEGER DEFAULT 1,
    total_chunks        INTEGER DEFAULT 0,
    total_characters    INTEGER DEFAULT 0,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed       TIMESTAMP,
    file_hash           TEXT,
    mime_type           TEXT,
    processing_status   TEXT DEFAULT 'completed',
    tags                TEXT,
    keywords            TEXT,
    description         TEXT,
    category            TEXT,
    target_audience     TEXT,
    department          TEXT,
    is_current_version  BOOLEAN DEFAULT TRUE,
    avg_chunk_size      REAL,
    embedding_model     TEXT,
    indexed_at          TIMESTAMP,
    view_count          INTEGER DEFAULT 0,
    query_count         INTEGER DEFAULT 0,
    avg_relevance_score REAL
);
CREATE INDEX IF NOT EXISTS idx_schemes_name    ON schemes_metadata(scheme_name);
CREATE INDEX IF NOT EXISTS idx_schemes_status  ON schemes_metadata(status);
CREATE INDEX IF NOT EXISTS idx_schemes_officer ON schemes_metadata(assigned_officer);

-- --- Scheme Versions --------------------------------------------------------
CREATE TABLE IF NOT EXISTS scheme_versions (
    id                 SERIAL PRIMARY KEY,
    scheme_id          TEXT NOT NULL REFERENCES schemes_metadata(scheme_id),
    version            INTEGER NOT NULL,
    changed_by         INTEGER NOT NULL REFERENCES users(id),
    change_type        TEXT NOT NULL,
    change_description TEXT,
    source_file        TEXT NOT NULL,
    file_size          INTEGER,
    chunk_count        INTEGER,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current         BOOLEAN DEFAULT TRUE,
    file_hash          TEXT,
    character_count    INTEGER,
    diff_summary       TEXT
);
CREATE INDEX IF NOT EXISTS idx_versions_scheme ON scheme_versions(scheme_id);

-- --- Scheme Assignments (NOTE: UNIQUE added for ON CONFLICT) ----------------
CREATE TABLE IF NOT EXISTS scheme_assignments (
    id                   SERIAL PRIMARY KEY,
    scheme_id            TEXT NOT NULL REFERENCES schemes_metadata(scheme_id),
    officer_id           INTEGER NOT NULL REFERENCES users(id),
    assigned_by          INTEGER NOT NULL REFERENCES users(id),
    assigned_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    can_edit             BOOLEAN DEFAULT TRUE,
    can_delete           BOOLEAN DEFAULT FALSE,
    can_reassign         BOOLEAN DEFAULT FALSE,
    is_active            BOOLEAN DEFAULT TRUE,
    revoked_at           TIMESTAMP,
    revoked_by           INTEGER,
    can_publish          BOOLEAN DEFAULT FALSE,
    assignment_reason    TEXT,
    responsibility_type  TEXT DEFAULT 'primary',
    UNIQUE (scheme_id, officer_id)
);
CREATE INDEX IF NOT EXISTS idx_assignments_officer ON scheme_assignments(officer_id);
CREATE INDEX IF NOT EXISTS idx_assignments_active  ON scheme_assignments(is_active);

-- --- Scheme Chunks ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS scheme_chunks (
    id                    SERIAL PRIMARY KEY,
    chunk_id              TEXT NOT NULL UNIQUE,
    scheme_id             TEXT NOT NULL REFERENCES schemes_metadata(scheme_id),
    chunk_index           INTEGER NOT NULL,
    chunk_text            TEXT NOT NULL,
    chunk_size            INTEGER NOT NULL,
    section_type          TEXT,
    section_title         TEXT,
    embedding_checksum    TEXT,
    language              TEXT DEFAULT 'en',
    keywords              TEXT,
    confidence_scores     TEXT,
    readability_score     REAL,
    information_density   REAL,
    duplicate_score       REAL,
    version               INTEGER NOT NULL DEFAULT 1,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at       TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chunks_scheme  ON scheme_chunks(scheme_id);
CREATE INDEX IF NOT EXISTS idx_chunks_section ON scheme_chunks(section_type);
CREATE INDEX IF NOT EXISTS idx_chunks_version ON scheme_chunks(scheme_id, version);

-- --- Upload History ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS upload_history (
    id                  SERIAL PRIMARY KEY,
    scheme_id           TEXT,
    uploaded_by         INTEGER NOT NULL REFERENCES users(id),
    upload_type         TEXT NOT NULL,
    filename            TEXT NOT NULL,
    file_size           INTEGER,
    file_hash           TEXT,
    status              TEXT DEFAULT 'processing',
    error_message       TEXT,
    chunks_processed    INTEGER DEFAULT 0,
    processing_time_ms  INTEGER,
    uploaded_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP,
    mime_type           TEXT,
    validation_passed   BOOLEAN,
    validation_errors   TEXT,
    retry_count         INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_upload_user ON upload_history(uploaded_by);

-- --- Grievances -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS grievances (
    id                         SERIAL PRIMARY KEY,
    grievance_id               TEXT NOT NULL UNIQUE,
    citizen_id                 INTEGER REFERENCES users(id),
    citizen_name               TEXT,
    citizen_phone              TEXT,
    citizen_email              TEXT,
    citizen_location           TEXT,
    title                      TEXT,
    description                TEXT NOT NULL,
    category                   TEXT NOT NULL,
    subcategory                TEXT,
    language                   TEXT DEFAULT 'en',
    department                 TEXT NOT NULL,
    sub_department             TEXT,
    priority                   TEXT NOT NULL,
    routing_reasoning          TEXT,
    confidence_score           REAL,
    ai_confidence              REAL,
    ai_summary                 TEXT,
    ai_reasoning               TEXT,
    estimated_resolution_days  INTEGER,
    related_schemes            TEXT,
    status                     TEXT DEFAULT 'pending',
    assigned_officer_id        INTEGER,
    assigned_officer_name      TEXT,
    submitted_by_officer_id    INTEGER REFERENCES users(id),
    submitted_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at                TIMESTAMP,
    assigned_at                TIMESTAMP,
    resolved_at                TIMESTAMP,
    closed_at                  TIMESTAMP,
    resolution_notes           TEXT,
    resolution_attachments     TEXT,
    citizen_satisfaction       INTEGER,
    has_attachments            BOOLEAN DEFAULT FALSE,
    attachment_count           INTEGER DEFAULT 0,
    attachment_urls            TEXT,
    source                     TEXT DEFAULT 'web',
    view_count                 INTEGER DEFAULT 0,
    comment_count              INTEGER DEFAULT 0,
    last_status_change_at      TIMESTAMP,
    created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_grievances_status       ON grievances(status);
CREATE INDEX IF NOT EXISTS idx_grievances_priority     ON grievances(priority);
CREATE INDEX IF NOT EXISTS idx_grievances_department   ON grievances(department);
CREATE INDEX IF NOT EXISTS idx_grievances_submitted_at ON grievances(submitted_at DESC);

-- --- Grievance Status Updates (legacy log table) ----------------------------
CREATE TABLE IF NOT EXISTS grievance_status_updates (
    id            SERIAL PRIMARY KEY,
    grievance_id  TEXT NOT NULL REFERENCES grievances(grievance_id),
    old_status    TEXT,
    new_status    TEXT NOT NULL,
    updated_by    TEXT,
    update_notes  TEXT,
    timestamp     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --- Grievance Status History -----------------------------------------------
CREATE TABLE IF NOT EXISTS grievance_status_history (
    id                SERIAL PRIMARY KEY,
    grievance_id      TEXT NOT NULL REFERENCES grievances(grievance_id),
    old_status        TEXT,
    new_status        TEXT NOT NULL,
    changed_by        INTEGER REFERENCES users(id),
    changed_by_name   TEXT,
    changed_by_role   TEXT,
    change_reason     TEXT,
    notes             TEXT,
    is_auto_change    BOOLEAN DEFAULT FALSE,
    changed_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_status_history_grievance  ON grievance_status_history(grievance_id);
CREATE INDEX IF NOT EXISTS idx_status_history_changed_at ON grievance_status_history(changed_at DESC);

-- --- Grievance Comments -----------------------------------------------------
CREATE TABLE IF NOT EXISTS grievance_comments (
    id             SERIAL PRIMARY KEY,
    grievance_id   TEXT NOT NULL REFERENCES grievances(grievance_id),
    commenter_type TEXT NOT NULL,
    commenter_name TEXT,
    comment_text   TEXT NOT NULL,
    is_internal       BOOLEAN DEFAULT FALSE,
    timestamp         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    author_id         INTEGER REFERENCES users(id),
    author_role       TEXT,
    author_name       TEXT,
    author_department TEXT,
    comment_type      TEXT DEFAULT 'note',
    is_public         BOOLEAN DEFAULT TRUE,
    is_pinned         BOOLEAN DEFAULT FALSE,
    updated_at        TIMESTAMP,
    edited_at         TIMESTAMP,
    created_at        TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_comments_grievance     ON grievance_comments(grievance_id);
CREATE INDEX IF NOT EXISTS idx_comments_author_dept   ON grievance_comments(author_department);
CREATE INDEX IF NOT EXISTS idx_grievances_submitted_by_officer
    ON grievances(submitted_by_officer_id);

-- --- SLA Configuration ------------------------------------------------------
CREATE TABLE IF NOT EXISTS sla_config (
    id                   SERIAL PRIMARY KEY,
    department           TEXT NOT NULL UNIQUE,
    critical_sla_hours   INTEGER NOT NULL DEFAULT 24,
    high_sla_hours       INTEGER NOT NULL DEFAULT 72,
    medium_sla_hours     INTEGER NOT NULL DEFAULT 168,
    low_sla_hours        INTEGER NOT NULL DEFAULT 336,
    escalation_enabled   BOOLEAN DEFAULT TRUE,
    working_hours_start  TEXT DEFAULT '09:00',
    working_hours_end    TEXT DEFAULT '17:00',
    working_days         TEXT DEFAULT '1,2,3,4,5',
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --- Grievance SLA tracking -------------------------------------------------
CREATE TABLE IF NOT EXISTS grievance_sla (
    id                      SERIAL PRIMARY KEY,
    grievance_id            TEXT NOT NULL UNIQUE REFERENCES grievances(grievance_id),
    sla_hours               INTEGER NOT NULL,
    due_date                TIMESTAMP NOT NULL,
    business_hours_used     REAL DEFAULT 0,
    is_breached             BOOLEAN DEFAULT FALSE,
    breached_at             TIMESTAMP,
    breach_duration_hours   REAL,
    is_escalated            BOOLEAN DEFAULT FALSE,
    escalation_level        INTEGER DEFAULT 0,
    escalated_at            TIMESTAMP,
    resolved_at             TIMESTAMP,
    resolution_within_sla   BOOLEAN,
    resolution_time_hours   REAL,
    is_paused               BOOLEAN DEFAULT FALSE,
    paused_at               TIMESTAMP,
    pause_reason            TEXT,
    total_paused_hours      REAL DEFAULT 0,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sla_grievance ON grievance_sla(grievance_id);
CREATE INDEX IF NOT EXISTS idx_sla_due_date  ON grievance_sla(due_date);
CREATE INDEX IF NOT EXISTS idx_sla_breached  ON grievance_sla(is_breached);

-- --- SLA Records (alt log table used by code) -------------------------------
CREATE TABLE IF NOT EXISTS sla_records (
    id            SERIAL PRIMARY KEY,
    grievance_id  TEXT NOT NULL UNIQUE REFERENCES grievances(grievance_id),
    department    TEXT,
    priority      TEXT,
    sla_hours     INTEGER,
    started_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline_at   TIMESTAMP,
    resolved_at   TIMESTAMP,
    is_breached   BOOLEAN DEFAULT FALSE,
    paused        BOOLEAN DEFAULT FALSE,
    pause_reason  TEXT,
    paused_at     TIMESTAMP
);

-- --- Grievance Notifications ------------------------------------------------
CREATE TABLE IF NOT EXISTS grievance_notifications (
    id                SERIAL PRIMARY KEY,
    grievance_id      TEXT REFERENCES grievances(grievance_id),
    recipient_id      INTEGER NOT NULL REFERENCES users(id),
    notification_type TEXT NOT NULL DEFAULT 'in_app',
    subject           TEXT,
    message           TEXT NOT NULL,
    status            TEXT DEFAULT 'pending',
    read_at           TIMESTAMP,
    priority_level    TEXT DEFAULT 'normal',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notif_user      ON grievance_notifications(recipient_id, status);
CREATE INDEX IF NOT EXISTS idx_notif_grievance ON grievance_notifications(grievance_id);

-- --- General Notifications --------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users(id),
    title             TEXT,
    message           TEXT NOT NULL,
    notification_type TEXT DEFAULT 'info',
    related_id        TEXT,
    is_read           BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --- Grievance Ratings ------------------------------------------------------
CREATE TABLE IF NOT EXISTS grievance_ratings (
    id                  SERIAL PRIMARY KEY,
    grievance_id        TEXT NOT NULL UNIQUE REFERENCES grievances(grievance_id),
    citizen_id          INTEGER NOT NULL REFERENCES users(id),
    rating              INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    resolution_quality  INTEGER CHECK (resolution_quality BETWEEN 1 AND 5),
    response_time       INTEGER CHECK (response_time BETWEEN 1 AND 5),
    officer_behavior    INTEGER CHECK (officer_behavior BETWEEN 1 AND 5),
    feedback_text       TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ratings_grievance ON grievance_ratings(grievance_id);

-- --- Grievance Escalations --------------------------------------------------
CREATE TABLE IF NOT EXISTS grievance_escalations (
    id                SERIAL PRIMARY KEY,
    grievance_id      TEXT NOT NULL REFERENCES grievances(grievance_id),
    escalation_level  INTEGER NOT NULL,
    escalated_from    INTEGER REFERENCES users(id),
    escalated_to      INTEGER REFERENCES users(id),
    reason            TEXT NOT NULL,
    auto_escalated    BOOLEAN DEFAULT FALSE,
    status            TEXT DEFAULT 'pending',
    action_taken      TEXT,
    acknowledged_at   TIMESTAMP,
    resolved_at       TIMESTAMP,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_escalation_grievance ON grievance_escalations(grievance_id);

-- --- Notices ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notices (
    id                    SERIAL PRIMARY KEY,
    notice_id             TEXT NOT NULL UNIQUE,
    reference_number      TEXT NOT NULL UNIQUE,
    scheme_id             TEXT REFERENCES schemes_metadata(scheme_id),
    scheme_name           TEXT,
    notice_type           TEXT NOT NULL CHECK (notice_type IN ('circular','order','memo','notification','advisory','amendment')),
    officer_id            INTEGER NOT NULL REFERENCES users(id),
    officer_name          TEXT,
    officer_designation   TEXT,
    officer_department    TEXT,
    subject               TEXT NOT NULL,
    body                  TEXT NOT NULL,
    formatted_html        TEXT,
    formatted_notice      TEXT,
    language              TEXT DEFAULT 'en',
    supersedes_notice_id  TEXT,
    legal_authority       TEXT,
    effective_date        TEXT,
    expiry_date           TEXT,
    status                TEXT DEFAULT 'draft' CHECK (status IN ('draft','pending_review','approved','published','archived','withdrawn')),
    reviewed_by           INTEGER REFERENCES users(id),
    reviewed_at           TIMESTAMP,
    review_notes          TEXT,
    approved_by           INTEGER REFERENCES users(id),
    approved_at           TIMESTAMP,
    published_by          INTEGER REFERENCES users(id),
    published_at          TIMESTAMP,
    withdrawn_by          INTEGER REFERENCES users(id),
    withdrawn_at          TIMESTAMP,
    withdrawal_reason     TEXT,
    target_audience       TEXT,
    distribution_channels TEXT,
    view_count            INTEGER DEFAULT 0,
    download_count        INTEGER DEFAULT 0,
    pdf_path              TEXT,
    pdf_generated_at      TIMESTAMP,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notices_id        ON notices(notice_id);
CREATE INDEX IF NOT EXISTS idx_notices_officer   ON notices(officer_id);
CREATE INDEX IF NOT EXISTS idx_notices_status    ON notices(status);
CREATE INDEX IF NOT EXISTS idx_notices_published ON notices(published_at DESC);

-- --- Officer Registration Codes ---------------------------------------------
CREATE TABLE IF NOT EXISTS officer_registration_codes (
    id           SERIAL PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,
    department   TEXT NOT NULL,
    designation  TEXT,
    created_by   INTEGER REFERENCES users(id),
    used_by      INTEGER REFERENCES users(id),
    is_used      BOOLEAN DEFAULT FALSE,
    expires_at   TIMESTAMP,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at      TIMESTAMP
);

-- --- Seed SLA defaults (idempotent) -----------------------------------------
INSERT INTO sla_config (department, critical_sla_hours, high_sla_hours, medium_sla_hours, low_sla_hours)
VALUES
    ('agriculture',     24, 72, 168, 336),
    ('rural_development', 24, 72, 168, 336),
    ('urban_development', 24, 72, 168, 336),
    ('social_welfare',  24, 48, 120, 240),
    ('health',          12, 48, 120, 240),
    ('education',       24, 72, 168, 336),
    ('finance',         24, 72, 168, 336),
    ('law_enforcement', 12, 48, 120, 240)
ON CONFLICT (department) DO NOTHING;
