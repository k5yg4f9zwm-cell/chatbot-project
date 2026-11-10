import sqlite3
import os
import shutil
from werkzeug.security import generate_password_hash, check_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_query TEXT NOT NULL,
    matched_faq_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(matched_faq_id) REFERENCES faqs(id)
);
"""


class ChatbotError(Exception):
    """Чатбот қателерін өңдеу класы."""
    pass


def connect(path=":memory:"):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    return db


def add_admin(db, username, password):
    u = (username or "").strip()
    if not u or not password:
        raise ChatbotError("Логин мен құпия сөз бос болмауы тиіс")
    p_hash = generate_password_hash(password)
    try:
        db.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", (u, p_hash))
        db.commit()
    except sqlite3.IntegrityError:
        raise ChatbotError("Мұндай әкімші бұрыннан бар")


def verify_admin(db, username, password):
    row = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return True
    return False


def add_faq(db, question, answer, category):
    q = (question or "").strip()
    a = (answer or "").strip()
    c = (category or "").strip()
    if not q or not a:
        raise ChatbotError("Сұрақ пен жауап бос болмауы тиіс")

    # Дәл осындай сұрақ базада бар екенін тексеру (дубликаттың алдын алу)
    existing = db.execute("SELECT id FROM faqs WHERE question = ?", (q,)).fetchone()
    if existing:
        return existing["id"]

    cur = db.execute("INSERT INTO faqs (question, answer, category) VALUES (?, ?, ?)", (q, a, c))
    db.commit()
    return cur.lastrowid


def update_faq(db, faq_id, question, answer, category):
    q = (question or "").strip()
    a = (answer or "").strip()
    c = (category or "").strip()
    if not q or not a:
        raise ChatbotError("Сұрақ пен жауап бос болмауы тиіс")
    db.execute("UPDATE faqs SET question = ?, answer = ?, category = ? WHERE id = ?", (q, a, c, faq_id))
    db.commit()


def delete_faq(db, faq_id):
    cur = db.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
    db.commit()
    if cur.rowcount == 0:
        raise ChatbotError("FAQ табылмады")


def search_faq(db, query):
    q = (query or "").strip()
    if not q:
        raise ChatbotError("Іздеу сөзі бос болмауы тиіс")

    # DISTINCT косылды — кайталанатын жолдарды сүзеді
    cur = db.execute(
        "SELECT DISTINCT * FROM faqs WHERE question LIKE ? OR answer LIKE ?",
        (f"%{q}%", f"%{q}%")
    )
    results = cur.fetchall()
    matched_id = results[0]["id"] if results else None

    db.execute("INSERT INTO logs (student_query, matched_faq_id) VALUES (?, ?)", (q, matched_id))
    db.commit()

    return results


def get_all_faqs(db):
    return db.execute("SELECT * FROM faqs ORDER BY id DESC").fetchall()


def get_logs(db):
    return db.execute("""
        SELECT l.id, l.student_query, l.timestamp, f.question as matched_question 
        FROM logs l 
        LEFT JOIN faqs f ON l.matched_faq_id = f.id 
        ORDER BY l.id DESC
    """).fetchall()


def backup_database(db_path, backup_path):
    if not os.path.exists(db_path):
        raise ChatbotError("Дерекқор файлы табылмады")
    shutil.copy(db_path, backup_path)
    return True


def restore_database(backup_path, db_path):
    if not os.path.exists(backup_path):
        raise ChatbotError("Сақтық көшірме файлы табылмады")
    shutil.copy(backup_path, db_path)
    return True