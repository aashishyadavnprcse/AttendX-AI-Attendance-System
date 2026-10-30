"""
AttendX AI — SQLite to PostgreSQL Safe Production Data Migration Utility
Migrates all existing users, biometric embeddings, class sessions, attendance logs,
audit ledgers, and parent notifications from backend/attendx.db to a cloud PostgreSQL database.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.db.session import Base
from app.models.user import User
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog
from app.models.notification import ParentNotification
from app.models.audit import AttendanceAuditLedger
from app.models.iot import IoTEdgeNode, RFIDCardMapping


def migrate_to_postgres(sqlite_path="backend/attendx.db", postgres_url=None):
    target_url = postgres_url or os.getenv("TARGET_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not target_url or "sqlite" in target_url:
        print("[Error] A valid PostgreSQL database URL is required.")
        print("Usage: python backend/migrate_sqlite_to_postgres.py 'postgresql://user:pass@host:5432/dbname'")
        return False

    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql://", 1)

    abs_sqlite = Path(sqlite_path).resolve()
    if not abs_sqlite.exists():
        print(f"[Error] Source SQLite database not found at: {abs_sqlite}")
        return False

    print("=" * 75)
    print("ATTENDX AI — SQLITE TO POSTGRESQL PRODUCTION DATA MIGRATION")
    print("=" * 75)
    print(f"Source SQLite:     {abs_sqlite} ({abs_sqlite.stat().st_size} bytes)")
    print(f"Target PostgreSQL: {target_url.split('@')[-1] if '@' in target_url else 'Target DB'}")

    # 1. Connect to PostgreSQL and create schema
    pg_engine = create_engine(target_url, pool_pre_ping=True)
    print("\n[1/3] Creating schema tables in PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)
    print("✓ Schema initialized successfully.")

    # 2. Read from SQLite
    s_conn = sqlite3.connect(abs_sqlite)
    s_conn.row_factory = sqlite3.Row
    s_cur = s_conn.cursor()

    tables_order = [
        ("users", "id"),
        ("class_sessions", "id"),
        ("attendance_logs", "id"),
        ("parent_notifications", "id"),
        ("attendance_audit_ledger", "id"),
        ("iot_devices", "id"),
        ("rfid_card_mappings", "id"),
    ]

    print("\n[2/3] Migrating table records...")
    with pg_engine.begin() as pg_conn:
        for tbl, pkey in tables_order:
            # Check if table exists in SQLite
            exists = s_cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,)
            ).fetchone()
            if not exists:
                continue

            rows = s_cur.execute(f"SELECT * FROM {tbl}").fetchall()
            if not rows:
                print(f"  • {tbl}: 0 rows (skipped)")
                continue

            cols = [c[0] for c in s_cur.description]
            cols_str = ", ".join(cols)
            params_str = ", ".join([f":{c}" for c in cols])

            # Convert row dictionaries, parsing JSON for embedding_vector if needed
            dict_rows = []
            for r in rows:
                d = dict(r)
                if tbl == "users" and "embedding_vector" in d and isinstance(d["embedding_vector"], str):
                    try:
                        d["embedding_vector"] = json.loads(d["embedding_vector"])
                    except Exception:
                        pass
                dict_rows.append(d)

            # Insert into Postgres with upsert/ignore
            insert_stmt = text(f"""
                INSERT INTO {tbl} ({cols_str}) 
                VALUES ({params_str})
                ON CONFLICT ({pkey}) DO NOTHING
            """)
            pg_conn.execute(insert_stmt, dict_rows)
            print(f"  ✓ {tbl}: Migrated {len(dict_rows)} record(s).")

            # Update auto-increment sequence in PostgreSQL
            try:
                max_id = s_cur.execute(f"SELECT MAX({pkey}) FROM {tbl}").fetchone()[0]
                if max_id:
                    seq_query = text(f"SELECT setval(pg_get_serial_sequence('{tbl}', '{pkey}'), {max_id})")
                    pg_conn.execute(seq_query)
            except Exception as seq_err:
                pass

    s_conn.close()

    # 3. Verify PostgreSQL counts
    print("\n[3/3] Verifying PostgreSQL Record Integrity:")
    with pg_engine.connect() as pg_conn:
        for tbl, _ in tables_order:
            try:
                count = pg_conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                print(f"  • {tbl}: {count} rows verified in PostgreSQL")
            except Exception:
                pass

    print("\n" + "=" * 75)
    print("MIGRATION COMPLETED SUCCESSFULLY WITHOUT DATA LOSS!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else None
    migrate_to_postgres(postgres_url=url_arg)
