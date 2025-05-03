import sqlite3

DB_PATH = "papersage.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Notebooks: stores per-user notebook metadata
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notebooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        name TEXT NOT NULL UNIQUE,
        processed INTEGER DEFAULT 0,
        faiss_path TEXT
    )
    """)
    # Notes: stores both custom and AI-generated notes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notebook_id INTEGER NOT NULL,
        content TEXT,
        FOREIGN KEY(notebook_id) REFERENCES notebooks(id)
    )
    """)
    conn.commit()
    conn.close()


def get_notebooks(user):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, processed, faiss_path FROM notebooks WHERE user = ?", (user,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_notebook(user, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO notebooks (user, name) VALUES (?,?)",
        (user, name)
    )
    conn.commit()
    conn.close()


def delete_notebook(user, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM notebooks WHERE user = ? AND name = ?",
        (user, name)
    )
    conn.commit()
    conn.close()


def update_notebook_processing(notebook_id, processed, faiss_path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE notebooks SET processed = ?, faiss_path = ? WHERE id = ?",
        (int(processed), faiss_path, notebook_id)
    )
    conn.commit()
    conn.close()


def add_note_to_db(notebook_id, content):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (notebook_id, content) VALUES (?,?)",
        (notebook_id, content)
    )
    conn.commit()
    conn.close()


def get_notes_from_db(notebook_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT content FROM notes WHERE notebook_id = ?",
        (notebook_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [r["content"] for r in rows]
