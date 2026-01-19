import os
import sqlite3
import sys


def migrate_sessions(db_path: str, target_email: str) -> None:
    """Migrate sessions from 'default' user to a specific email."""
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check count of default sessions
        cursor.execute("SELECT count(*) FROM sessions WHERE user_id = 'default'")
        count = cursor.fetchone()[0]

        print(f"Found {count} sessions belonging to 'default' user.")

        if count == 0:
            print("No sessions to migrate.")
            return

        print(f"Migrating authentication for {count} sessions to '{target_email}'...")

        cursor.execute(
            "UPDATE sessions SET user_id = ? WHERE user_id = 'default'", (target_email,)
        )
        conn.commit()
        print(f"✅ Successfully migrated {cursor.rowcount} sessions.")

    except Exception as e:
        print(f"❌ Error migrating sessions: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate_default_sessions.py <your_email>")
        print("Example: python migrate_default_sessions.py user@example.com")
        sys.exit(1)

    email = sys.argv[1]
    db_path = ".sre_agent_sessions.db"
    migrate_sessions(db_path, email)
