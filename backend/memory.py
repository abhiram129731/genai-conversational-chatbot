
import sqlite3
import uuid

from pathlib import Path
from contextlib import closing

# Database location: project root
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "chatbot.db"

MAX_HISTORY = 50


def get_connection():
    return sqlite3.connect(DB_PATH)


# Create database tables automatically
def init_db():
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT DEFAULT 'New conversation',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
                )
            """)

            conn.execute("PRAGMA foreign_keys = ON")


# Create a new conversation
def create_conversation():
    conversation_id = str(uuid.uuid4())

    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO conversations (id) VALUES (?)",
                (conversation_id,)
            )

    return conversation_id


# Store a message
def add_message(conversation_id, role, content):
    with closing(get_connection()) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        with conn:
            cursor = conn.execute("""
                INSERT INTO messages
                (conversation_id, role, content)
                VALUES (?, ?, ?)
            """, (conversation_id, role, content))

            if cursor.rowcount == 0:
                raise ValueError("Unable to save message")

            # Set title from the first user message
            if role == "user":
                conn.execute("""
                    UPDATE conversations
                    SET title = CASE
                        WHEN title = 'New conversation' THEN ?
                        ELSE title
                    END,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (content[:40], conversation_id))


# Retrieve complete conversation history
def get_history(conversation_id):
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,)).fetchall()

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ]


# Retrieve recent messages for Gemini context
def get_recent_history(conversation_id):
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (conversation_id, MAX_HISTORY)).fetchall()

    rows.reverse()

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ]


# Get all conversations
def get_all_conversations():
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row

        conversations = conn.execute("""
            SELECT id
            FROM conversations
            ORDER BY updated_at DESC
        """).fetchall()

    return {
        row["id"]: get_history(row["id"])
        for row in conversations
    }


# Delete a conversation
def delete_conversation(conversation_id):
    with closing(get_connection()) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        with conn:
            cursor = conn.execute("""
                DELETE FROM conversations
                WHERE id = ?
            """, (conversation_id,))

            return cursor.rowcount > 0


# Check whether a conversation exists
def conversation_exists(conversation_id):
    with closing(get_connection()) as conn:
        result = conn.execute("""
            SELECT 1
            FROM conversations
            WHERE id = ?
        """, (conversation_id,)).fetchone()

    return result is not None


# Initialize database when this module loads
init_db()
