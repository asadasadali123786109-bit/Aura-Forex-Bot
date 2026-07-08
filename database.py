import sqlite3

DB_NAME = "data/bot.db"


def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO users
    (user_id, username, first_name)
    VALUES (?, ?, ?)
    """, (user_id, username, first_name))

    conn.commit()
    conn.close()
