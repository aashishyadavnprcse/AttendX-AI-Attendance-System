"""
AttendX Safe Database Migration & Schema Reconciliation Script.
Idempotently adds missing columns and triggers to attendx.db without data loss.
"""

import os
import sqlite3

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "attendx.db"))


def column_exists(cursor, table_name, column_name):
    cols = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()
    return any(c[1] == column_name for c in cols)


def migrate_database(db_path=DB_PATH):
    print(f"[Migration] Opening database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Reconcile 'users' table
    if not column_exists(cursor, "users", "hashed_password"):
        print("[Migration] Adding 'hashed_password' column to 'users'...")
        cursor.execute("ALTER TABLE users ADD COLUMN hashed_password TEXT;")
        cursor.execute("UPDATE users SET hashed_password = password_hash WHERE hashed_password IS NULL;")
        print("[Migration] Populated 'hashed_password' from existing 'password_hash'.")
    else:
        # Sync any records where one is set and the other is not
        cursor.execute("UPDATE users SET hashed_password = password_hash WHERE hashed_password IS NULL AND password_hash IS NOT NULL;")
        cursor.execute("UPDATE users SET password_hash = hashed_password WHERE password_hash IS NULL AND hashed_password IS NOT NULL;")

    if not column_exists(cursor, "users", "last_parent_alert_at"):
        print("[Migration] Adding 'last_parent_alert_at' column to 'users'...")
        cursor.execute("ALTER TABLE users ADD COLUMN last_parent_alert_at TEXT;")

    if not column_exists(cursor, "users", "phone"):
        print("[Migration] Adding 'phone' column to 'users'...")
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT;")

    if not column_exists(cursor, "users", "parent_notifications_enabled"):
        print("[Migration] Adding 'parent_notifications_enabled' column to 'users'...")
        cursor.execute("ALTER TABLE users ADD COLUMN parent_notifications_enabled INTEGER NOT NULL DEFAULT 1;")

    # Seed default phone numbers for enrolled students if missing
    cursor.execute("UPDATE users SET phone = '+91 98765 43210' WHERE email = 'sarah.chen@student.attendx.ai' AND (phone IS NULL OR phone = '');")
    cursor.execute("UPDATE users SET phone = '+91 98765 43211' WHERE email = 'alex.mercer@student.attendx.ai' AND (phone IS NULL OR phone = '');")
    cursor.execute("UPDATE users SET phone = '+91 98765 43212' WHERE email = 'demo.student@example.com' AND (phone IS NULL OR phone = '');")
    cursor.execute("UPDATE users SET parent_name = 'Demo Guardian', parent_phone = '+91 98765 43219' WHERE email = 'demo.student@example.com' AND (parent_phone IS NULL OR parent_phone = '');")

    # 2. Reconcile 'class_sessions' table
    if not column_exists(cursor, "class_sessions", "require_geofence"):
        print("[Migration] Adding 'require_geofence' column to 'class_sessions'...")
        cursor.execute("ALTER TABLE class_sessions ADD COLUMN require_geofence INTEGER NOT NULL DEFAULT 1;")

    if not column_exists(cursor, "class_sessions", "allowed_ip_subnet"):
        print("[Migration] Adding 'allowed_ip_subnet' column to 'class_sessions'...")
        cursor.execute("ALTER TABLE class_sessions ADD COLUMN allowed_ip_subnet TEXT;")

    if not column_exists(cursor, "class_sessions", "allowed_wifi_bssid"):
        print("[Migration] Adding 'allowed_wifi_bssid' column to 'class_sessions'...")
        cursor.execute("ALTER TABLE class_sessions ADD COLUMN allowed_wifi_bssid TEXT;")

    if not column_exists(cursor, "class_sessions", "require_campus_network"):
        print("[Migration] Adding 'require_campus_network' column to 'class_sessions'...")
        cursor.execute("ALTER TABLE class_sessions ADD COLUMN require_campus_network INTEGER NOT NULL DEFAULT 0;")

    # 3. Reconcile 'attendance_logs' table
    if not column_exists(cursor, "attendance_logs", "client_ip"):
        print("[Migration] Adding 'client_ip' column to 'attendance_logs'...")
        cursor.execute("ALTER TABLE attendance_logs ADD COLUMN client_ip TEXT;")

    if not column_exists(cursor, "attendance_logs", "wifi_bssid"):
        print("[Migration] Adding 'wifi_bssid' column to 'attendance_logs'...")
        cursor.execute("ALTER TABLE attendance_logs ADD COLUMN wifi_bssid TEXT;")

    # 4. Reconcile 'parent_notifications' table for Automatic Absent Notifications
    if not column_exists(cursor, "parent_notifications", "session_id"):
        print("[Migration] Adding 'session_id' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN session_id INTEGER;")

    if not column_exists(cursor, "parent_notifications", "recipient_type"):
        print("[Migration] Adding 'recipient_type' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN recipient_type TEXT DEFAULT 'PARENT';")

    if not column_exists(cursor, "parent_notifications", "recipient_name"):
        print("[Migration] Adding 'recipient_name' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN recipient_name TEXT;")

    if not column_exists(cursor, "parent_notifications", "recipient_phone"):
        print("[Migration] Adding 'recipient_phone' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN recipient_phone TEXT;")

    if not column_exists(cursor, "parent_notifications", "delivery_provider"):
        print("[Migration] Adding 'delivery_provider' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN delivery_provider TEXT DEFAULT 'SIMULATED_GATEWAY';")

    if not column_exists(cursor, "parent_notifications", "error_message"):
        print("[Migration] Adding 'error_message' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN error_message TEXT;")

    if not column_exists(cursor, "parent_notifications", "is_cancelled"):
        print("[Migration] Adding 'is_cancelled' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN is_cancelled INTEGER DEFAULT 0;")

    if not column_exists(cursor, "parent_notifications", "retry_count"):
        print("[Migration] Adding 'retry_count' column to 'parent_notifications'...")
        cursor.execute("ALTER TABLE parent_notifications ADD COLUMN retry_count INTEGER DEFAULT 0;")

    # 5. Triggers to keep password_hash and hashed_password synchronized in users table
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_users_sync_pwd_insert
    AFTER INSERT ON users
    BEGIN
        UPDATE users SET
            hashed_password = COALESCE(NEW.hashed_password, NEW.password_hash),
            password_hash = COALESCE(NEW.password_hash, NEW.hashed_password)
        WHERE id = NEW.id;
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_users_sync_pwd_update
    AFTER UPDATE OF password_hash, hashed_password ON users
    BEGIN
        UPDATE users SET
            hashed_password = CASE 
                WHEN NEW.password_hash != OLD.password_hash AND (NEW.hashed_password = OLD.hashed_password OR NEW.hashed_password IS NULL) 
                THEN NEW.password_hash 
                ELSE COALESCE(NEW.hashed_password, NEW.password_hash) 
            END,
            password_hash = CASE 
                WHEN NEW.hashed_password != OLD.hashed_password AND (NEW.password_hash = OLD.password_hash OR NEW.password_hash IS NULL) 
                THEN NEW.hashed_password 
                ELSE COALESCE(NEW.password_hash, NEW.hashed_password) 
            END
        WHERE id = NEW.id;
    END;
    """)

    conn.commit()
    conn.close()
    print("[Migration] Schema reconciliation completed successfully.")


if __name__ == "__main__":
    migrate_database()
