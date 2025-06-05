import os
import sqlite3

# Path to the database file (ensure it is always relative to this script)
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create servers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            server_id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            blacklisted_status BOOLEAN DEFAULT 0,
            whitelisted_status BOOLEAN DEFAULT 0,
            invite_link TEXT
        )
    ''')

    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            dabloons REAL DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
    print(f"Database setup complete. Database file: {DB_PATH}")
