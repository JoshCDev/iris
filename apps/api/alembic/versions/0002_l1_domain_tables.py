"""L1 domain tables (WEBAPP_SPEC sec 9.2)."""
from alembic import op

revision = "0002_l1_domain_tables"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

# One statement per entry: SQLite's cursor.execute (used by the SQLAlchemy
# engine) rejects multi-statement scripts, so each op.execute runs one.
_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS water_observations (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL REFERENCES plots(id),
        source TEXT NOT NULL,
        raw_distance REAL,
        level_cm REAL NOT NULL,
        calibration_id INTEGER,
        actor TEXT,
        observed_at TEXT NOT NULL,
        received_at TEXT NOT NULL,
        quality_state TEXT NOT NULL DEFAULT 'ok',
        demo INTEGER NOT NULL DEFAULT 1
    );
    """,
    """
    CREATE INDEX ix_water_observations_plot
        ON water_observations(plot_id, observed_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS weather_snapshots (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL REFERENCES plots(id),
        source TEXT NOT NULL,
        adm4 TEXT,
        fetched_at TEXT NOT NULL,
        window_end TEXT NOT NULL,
        rain72_mm REAL,
        availability TEXT NOT NULL,
        stale_since TEXT,
        demo INTEGER NOT NULL DEFAULT 1
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_weather_snapshots_plot
        ON weather_snapshots(plot_id, id);
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL REFERENCES plots(id),
        observation_id INTEGER NOT NULL REFERENCES water_observations(id),
        weather_snapshot_id INTEGER REFERENCES weather_snapshots(id),
        stage TEXT NOT NULL,
        action TEXT NOT NULL,
        reason_codes TEXT NOT NULL,
        ruleset_version TEXT NOT NULL,
        needs_review INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        superseded_at TEXT,
        demo INTEGER NOT NULL DEFAULT 1
    );
    """,
    """
    CREATE INDEX ix_recommendations_plot
        ON recommendations(plot_id, created_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS action_confirmations (
        id INTEGER PRIMARY KEY,
        recommendation_id INTEGER NOT NULL REFERENCES recommendations(id),
        actor_id INTEGER,
        status TEXT NOT NULL,
        action_at TEXT,
        volume_m3 REAL,
        note TEXT,
        created_at TEXT NOT NULL,
        demo INTEGER NOT NULL DEFAULT 1
    );
    """,
    """
    CREATE INDEX ix_action_confirmations_rec
        ON action_confirmations(recommendation_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS leaf_assessments (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER REFERENCES plots(id),
        image_hash TEXT NOT NULL,
        retention_mode TEXT NOT NULL DEFAULT 'operational',
        model_version TEXT NOT NULL,
        guard_result TEXT NOT NULL,
        class TEXT,
        confidence REAL,
        severity TEXT,
        evidence_type TEXT NOT NULL DEFAULT 'public-dataset',
        created_at TEXT NOT NULL,
        demo INTEGER NOT NULL DEFAULT 1
    );
    """,
    """
    CREATE INDEX ix_leaf_assessments_plot
        ON leaf_assessments(plot_id, created_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS evidence_runs (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL,
        version TEXT NOT NULL,
        parameters_json TEXT NOT NULL,
        outputs_json TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        demo INTEGER NOT NULL DEFAULT 1
    );
    """,
    # L2 scaffolds (schema only; auth/membership stubbed while demo mode is on).
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        display_name TEXT NOT NULL,
        locale TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS plot_memberships (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL,
        credential_hash TEXT,
        status TEXT NOT NULL,
        last_seen TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS calibrations (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL,
        device_id INTEGER,
        pipe_zero_cm REAL NOT NULL,
        method TEXT NOT NULL,
        actor TEXT,
        calibrated_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL,
        source_type TEXT NOT NULL,
        source_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        priority TEXT NOT NULL,
        owner_id INTEGER,
        status TEXT NOT NULL,
        resolution TEXT,
        created_at TEXT NOT NULL,
        resolved_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS assistant_sessions (
        id INTEGER PRIMARY KEY,
        plot_id INTEGER NOT NULL,
        user_id INTEGER,
        locale TEXT NOT NULL,
        mode TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY,
        actor_type TEXT NOT NULL,
        actor_id INTEGER,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        resource_id INTEGER,
        correlation_id TEXT,
        created_at TEXT NOT NULL
    );
    """,
]


def upgrade() -> None:
    for sql in _STATEMENTS:
        op.execute(sql)


def downgrade() -> None:
    for t in ("audit_log", "assistant_sessions", "reviews", "calibrations",
              "devices", "plot_memberships", "users", "evidence_runs",
              "leaf_assessments", "action_confirmations", "recommendations",
              "weather_snapshots", "water_observations"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
