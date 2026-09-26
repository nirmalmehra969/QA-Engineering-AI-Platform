import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "qa_assistant.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_schema():
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_schema()
    print("Database schema initialized successfully.")
