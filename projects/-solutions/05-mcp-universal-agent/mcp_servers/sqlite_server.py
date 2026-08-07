"""SQLite MCP server.

Exposes a small, safe subset of SQLite: schema introspection, parameterised
queries, and automatic seeding of a demo schema on first run. The database
path is taken from ``MCP_SQLITE_PATH`` (default ``./data/agent.db``).

Run as a stdio MCP server::

    MCP_SQLITE_PATH=./data/agent.db python3 -m mcp_servers.sqlite_server
"""

from __future__ import annotations

import os
import sqlite3
from typing import List

from mcp.server.fastmcp import FastMCP

_DB_PATH = os.environ.get("MCP_SQLITE_PATH", "./data/agent.db")
os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)

mcp = FastMCP("sqlite")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _seed_if_empty() -> None:
    """Create a tiny demo schema on first run so the agent has something to
    query. Idempotent – only seeds if the 'users' table is missing."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        if {"users", "orders", "products"} <= {r[0] for r in cur.fetchall()}:
            return
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                country TEXT,
                signup_date TEXT
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER DEFAULT 1,
                total REAL,
                order_date TEXT
            );
            INSERT OR IGNORE INTO users VALUES
                (1,'Dana Lee','dana@example.com','USA','2024-01-15'),
                (2,'Amir Khan','amir@example.com','Pakistan','2024-02-03'),
                (3,'Priya N.','priya@example.com','India','2024-03-22'),
                (4,'Sam Okoro','sam@example.com','Nigeria','2024-04-10');
            INSERT OR IGNORE INTO products VALUES
                (1,'Widget',9.99,120),
                (2,'Gadget',24.50,40),
                (3,'Gizmo',99.00,8);
            INSERT OR IGNORE INTO orders VALUES
                (1,1,2,2,49.00,'2024-05-01'),
                (2,3,1,5,49.95,'2024-05-08'),
                (3,2,3,1,99.00,'2024-05-15'),
                (4,1,1,1,9.99,'2024-06-02');
            """
        )
        conn.commit()
    finally:
        conn.close()


# Seed on import so the very first connection from the agent already sees data.
_seed_if_empty()


@mcp.tool()
def list_tables() -> List[str]:
    """Return the names of all tables in the SQLite database.

    Always call this first if you don't know the schema. Use ``describe_table``
    to see columns for a specific table.

    Returns:
        List of table names (strings), ordered alphabetically.
    """
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


@mcp.tool()
def describe_table(table: str) -> List[dict]:
    """Return column metadata (name, type, notnull, default, pk) for ``table``.

    Use this after ``list_tables`` to learn which columns exist before writing
    a SELECT. The output mirrors SQLite's ``PRAGMA table_info``.

    Args:
        table: Name of the table to describe.

    Returns:
        List of dicts, one per column, with keys: ``cid``, ``name``, ``type``,
        ``notnull``, ``default``, ``pk``.
    """
    conn = _connect()
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@mcp.tool()
def run_query(sql: str, params: list | None = None) -> dict:
    """Execute a SQL statement and return rows (for SELECT) or rowcount
    (for INSERT / UPDATE / DELETE).

    Statements are parameterised via ``?`` placeholders and ``params`` to
    prevent SQL injection. DDL (CREATE TABLE, etc.) is allowed but COMMIT
    happens automatically.

    Examples:
        run_query("SELECT * FROM users WHERE country = ?", ["USA"])
        run_query("INSERT INTO orders (user_id, product_id, quantity, total, order_date) VALUES (?, ?, ?, ?, ?)",
                  [1, 1, 2, 19.98, "2024-07-01"])

    Args:
        sql: A single SQL statement. ``?`` placeholders are filled from
            ``params``.
        params: Optional list of values for the ``?`` placeholders.

    Returns:
        Dict with keys: ``columns`` (list of column names), ``rows`` (list of
        dicts) for SELECT; OR ``rowcount`` for INSERT/UPDATE/DELETE.
    """
    conn = _connect()
    try:
        cur = conn.execute(sql, params or [])
        if cur.description is not None:
            columns = [d[0] for d in cur.description]
            rows = [dict(r) for r in cur.fetchall()]
            conn.commit()
            return {"columns": columns, "rows": rows}
        conn.commit()
        return {"rowcount": cur.rowcount}
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
