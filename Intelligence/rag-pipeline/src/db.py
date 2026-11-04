"""Database connection and session management."""

import psycopg2
import psycopg2.extras
from src.config import DATABASE_URL


def get_connection():
    """Return a new psycopg2 connection."""
    return psycopg2.connect(DATABASE_URL)


def execute_sql(sql: str, params: tuple | None = None, fetch: bool = False):
    """Execute SQL and optionally return results."""
    conn = get_connection()
    conn.autocommit = True
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
    finally:
        conn.close()
