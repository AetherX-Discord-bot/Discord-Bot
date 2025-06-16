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
            display_name TEXT,
            username TEXT,
            personal_prefix TEXT,
            bio TEXT,
            profile_picture TEXT,
            dm_enabled BOOLEAN DEFAULT 0,
            show_status BOOLEAN DEFAULT 0,
            show_dabloons BOOLEAN DEFAULT 0,
            dabloons REAL DEFAULT 0,
            karma INTEGER DEFAULT 0,
            xp REAL DEFAULT 0,
            level INTEGER DEFAULT 1
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS server_settings (
            server_id INTEGER PRIMARY KEY,
            prefix TEXT,
            welcome_channel_id INTEGER,
            welcome_message TEXT,
            leveling_channel_id INTEGER,
            leveling_message TEXT,
            leveling_xp_per_message INTEGER DEFAULT 10,
            leveling_xp_per_reaction INTEGER DEFAULT 5,
            leveling_xp_per_command INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS server_leveling (
            server_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    def has_data():
        if not os.path.exists(DB_PATH):
            return False
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 1 FROM servers LIMIT 1")
            if c.fetchone():
                conn.close()
                return True
            c.execute("SELECT 1 FROM users LIMIT 1")
            if c.fetchone():
                conn.close()
                return True
            conn.close()
        except Exception:
            return False
        return False

    if os.path.exists(DB_PATH) and has_data():
        confirm = input(f"Database already exists at {DB_PATH} and contains data. Do you want to reset it? (y/n): ").strip().lower()
        if confirm == 'y':
            os.remove(DB_PATH)
            print("Database file removed. Setting up a new database...")
            setup_database()
            print(f"Database reset complete. Database file: {DB_PATH}")
        else:
            print("Database setup aborted. Existing database was not changed.")
    else:
        setup_database()
        print(f"Database setup complete. Database file: {DB_PATH}")
