"""
models.py
SQLite data layer for traffic signals and history.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traffic.db")


def get_db():
    """Get a new database connection (one per call for thread safety)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            vehicle_count INTEGER DEFAULT 0,
            green_time INTEGER DEFAULT 25,
            density TEXT DEFAULT 'Low',
            current_phase TEXT DEFAULT 'green',
            countdown INTEGER DEFAULT 25,
            emergency INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            vehicle_count INTEGER NOT NULL,
            green_time INTEGER NOT NULL,
            density TEXT NOT NULL,
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );
    """)
    conn.commit()
    conn.close()


def seed_signals():
    """Insert default signals if the table is empty."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    if count == 0:
        signals = [
            ("Signal-A", "Main Street & 1st Ave",   12.9716, 77.5946),
            ("Signal-B", "Park Road & 2nd Ave",      12.9750, 77.5900),
            ("Signal-C", "Market Square",             12.9680, 77.5990),
            ("Signal-D", "Highway Junction",          12.9800, 77.5850),
            ("Signal-E", "University Gate",           12.9650, 77.6050),
            ("Signal-F", "Station Road",              12.9780, 77.6010),
        ]
        conn.executemany(
            "INSERT INTO signals (name, location, lat, lng) VALUES (?, ?, ?, ?)",
            signals,
        )
        conn.commit()
    conn.close()


def get_all_signals():
    """Return all signals as a list of dicts."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM signals ORDER BY id").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_signal(signal_id: int):
    """Return a single signal dict or None."""
    conn = get_db()
    row = conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_signal(signal_id: int, **kwargs):
    """Update arbitrary columns for a signal."""
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [signal_id]
    conn = get_db()
    conn.execute(f"UPDATE signals SET {cols} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def record_history(signal_id: int, vehicle_count: int, green_time: int, density: str):
    """Append a snapshot to the history table."""
    conn = get_db()
    conn.execute(
        "INSERT INTO history (signal_id, timestamp, vehicle_count, green_time, density) VALUES (?, ?, ?, ?, ?)",
        (signal_id, datetime.now().isoformat(), vehicle_count, green_time, density),
    )
    conn.commit()
    conn.close()


def get_history(signal_id: int, limit: int = 50):
    """Return recent history for a signal."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history WHERE signal_id = ? ORDER BY id DESC LIMIT ?",
        (signal_id, limit),
    ).fetchall()
    conn.close()
    # Return in chronological order
    return [dict(r) for r in reversed(rows)]

