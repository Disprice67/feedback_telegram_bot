import sqlite3
from contextlib import contextmanager


class BotDatabase:
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    is_allowed BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            conn.commit()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def add_user(self, chat_id, email, is_allowed=True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO users (chat_id, email, is_allowed) VALUES (?, ?, ?)",
                (chat_id, email, is_allowed)
            )
            conn.commit()

    def remove_user(self, chat_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
            conn.commit()

    def is_user_allowed(self, chat_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_allowed FROM users WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            return result and result[0]

    def get_all_users(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id, email, is_allowed FROM users")
            return cursor.fetchall()
