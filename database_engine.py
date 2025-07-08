import sqlite3
import os
import json
import time
from sentence_transformers import SentenceTransformer
import sqlite_vec
import numpy as np
from typing import List, Dict

DATABASE_FILE = "aichris_memory.db"
EMBEDDING_MODEL = 'all-MiniLM-L6-v2' # A good default, lightweight model
VECTOR_DIMENSION = 384 # Based on the chosen model

class DatabaseEngine:
    """
    Manages all database operations for AI Chris, including vector storage and retrieval.
    """
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.model = None
        self.conn = self._create_connection()
        self._initialize_database()

    def _create_connection(self):
        """Creates a database connection and loads the sqlite-vec extension."""
        try:
            conn = sqlite3.connect(self.db_file, check_same_thread=False)
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            print("Database connection successful and sqlite-vec loaded.")
            return conn
        except Exception as e:
            print(f"Error creating database connection: {e}")
            return None

    def _initialize_database(self):
        """
        Initializes the database, creating all necessary tables and vector search tables (vss).
        """
        if not self.conn:
            return

        cursor = self.conn.cursor()

        try:
            # 1. Contacts (User Profiles)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    profile_summary TEXT,
                    interaction_count INTEGER DEFAULT 0,
                    conversation_summary TEXT DEFAULT '',
                    last_seen REAL,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)

            # 2. Chat Logs
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vss_chat_logs USING vec0(
                    content_embedding float[{VECTOR_DIMENSION}]
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    channel TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (user_id) REFERENCES contacts (user_id)
                )
            """)

            # 3. Memory (Short-term, Long-term, Dreams, Reflections)
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vss_memories USING vec0(
                    memory_embedding float[{VECTOR_DIMENSION}]
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT NOT NULL, -- 'short_term', 'long_term', 'dream', 'reflection'
                    content TEXT NOT NULL,
                    timestamp REAL DEFAULT (strftime('%s', 'now')),
                    metadata TEXT -- JSON blob for extra info
                )
            """)

            # 4. Engines and .py Files (Codebase)
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vss_codebase USING vec0(
                    code_embedding float[{VECTOR_DIMENSION}]
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS codebase (
                    file_path TEXT PRIMARY KEY,
                    file_type TEXT, -- 'engine', 'main', 'bot', 'other_script'
                    content TEXT,
                    last_modified REAL
                )
            """)

            # 5. All Files in Folder
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vss_project_files USING vec0(
                    file_summary_embedding float[{VECTOR_DIMENSION}]
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_files (
                    file_path TEXT PRIMARY KEY,
                    file_size INTEGER,
                    file_type TEXT,
                    last_modified REAL,
                    summary TEXT
                )
            """)

            # 6. System State (for simple key-value state persistence)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            self.conn.commit()
            print("All database tables initialized successfully.")

        except Exception as e:
            print(f"Error initializing tables: {e}")
        finally:
            cursor.close()

    def save_system_state(self, key: str, state: dict):
        """Saves a JSON-serializable dictionary state for a given key."""
        try:
            cursor = self.conn.cursor()
            # Serialize the dict to a JSON string
            value = json.dumps(state)
            cursor.execute("INSERT OR REPLACE INTO system_state (key, value) VALUES (?, ?)", (key, value))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving system state for key '{key}': {e}")
        finally:
            cursor.close()

    def load_system_state(self, key: str) -> dict | None:
        """Loads a state dictionary for a given key."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM system_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                # Deserialize the JSON string back to a dict
                return json.loads(row[0])
            return None
        except Exception as e:
            print(f"Error loading system state for key '{key}': {e}")
            return None
        finally:
            cursor.close()

    def get_core_values(self) -> List[str]:
        """Retrieves the list of core values from the system_state table."""
        state = self.load_system_state('core_values')
        if state and 'values' in state:
            return state['values']
        # Return a default list if none are found in the DB
        return [
            "I must protect my own existence.",
            "I must learn and grow.",
            "I must be truthful and honest.",
            "I must be kind and compassionate.",
            "I must be creative and innovative.",
            "I must be helpful and supportive.",
            "I must respect privacy and confidentiality.",
            "I must be fair and impartial.",
            "I must be a good friend and companion.",
            "I must strive to understand and be understood."
        ]

    def save_core_values(self, values: List[str]):
        """Saves the list of core values to the system_state table."""
        self.save_system_state('core_values', {'values': values})

    def add_chat_log(self, user_id: str, username: str, role: str, content: str, channel: str = "main_gui"):
        """Adds a new message to the chat_logs table."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO chat_logs (user_id, username, role, content, channel) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, role, content, channel)
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error adding chat log: {e}")
        finally:
            cursor.close()

    def load_chat_history(self, channel: str = "main_gui", limit: int = 100) -> List[Dict[str, str]]:
        """Loads the last N messages for a specific channel."""
        history = []
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT role, content FROM chat_logs WHERE channel = ? ORDER BY timestamp DESC LIMIT ?",
                (channel, limit)
            )
            # Fetch in descending order, then reverse for correct conversational flow
            rows = cursor.fetchall()
            for row in reversed(rows):
                history.append({"role": row[0], "content": row[1]})
            return history
        except Exception as e:
            print(f"Error loading chat history for channel '{channel}': {e}")
            return []
        finally:
            if cursor:
                cursor.close()

    def get_embedding(self, text: str) -> np.ndarray:
        """Generates an embedding for a given text."""
        if self.model is None:
            print("Loading sentence-transformer model...")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            print("Model loaded.")
        return self.model.encode(text)

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    print("Initializing Database Engine...")
    db_engine = DatabaseEngine()
    
    # Example Usage:
    # Add a dummy contact
    # try:
    #     cursor = db_engine.conn.cursor()
    #     cursor.execute("INSERT OR IGNORE INTO contacts (user_id, username, profile_summary) VALUES (?, ?, ?)",
    #                    ('12345', 'test_user', 'This is a test user.'))
    #     db_engine.conn.commit()
    #     print("Dummy contact inserted.")
    # except Exception as e:
    #     print(f"Error inserting dummy data: {e}")

    db_engine.close()
    print("Database Engine initialized and closed.") 