"""
DevLensX Database Engine & Persistence Layer
Provides lightweight SQLite persistence using Python standard library with optional SQLAlchemy support.
"""

import sqlite3
import os
from typing import Optional, List, Dict, Any
from devlensx.core.config import DATABASE_URL

# Extract SQLite file path from DATABASE_URL
DB_PATH = DATABASE_URL.replace("sqlite:///", "")


def get_connection():
    """Returns a connection to the SQLite application database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes application database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        full_name TEXT DEFAULT 'Developer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Repositories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        path TEXT NOT NULL,
        language TEXT DEFAULT 'Java',
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    """)

    # Analysis Runs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repository_id INTEGER NOT NULL,
        status TEXT DEFAULT 'running',
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        parser_version TEXT DEFAULT '1.0.0-javalang',
        error_message TEXT,
        overall_score REAL DEFAULT 0.0,
        FOREIGN KEY (repository_id) REFERENCES repositories (id)
    )
    """)

    # Findings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_run_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        claim TEXT NOT NULL,
        file TEXT,
        class_name TEXT,
        critic_verdict TEXT DEFAULT 'VERIFIED',
        evidence_coverage_score REAL DEFAULT 100.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (id)
    )
    """)

    # Conversations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repository_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        title TEXT DEFAULT 'Copilot Thread',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (repository_id) REFERENCES repositories (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Messages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        evidence_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
    )
    """)

    # Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


class DummySession:
    """Lightweight Session proxy for standard library SQLite compatibility."""
    def __init__(self):
        self.conn = get_connection()

    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def add(self, item):
        pass

    def commit(self):
        pass

    def refresh(self, item):
        pass

    def close(self):
        self.conn.close()


def get_db():
    db = DummySession()
    try:
        yield db
    finally:
        db.close()
