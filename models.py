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
        # Real Coimbatore intersections
        signals = [
            ("Signal-A", "Gandhipuram Bus Stand",       11.0168, 76.9558),
            ("Signal-B", "RS Puram Junction",            11.0045, 76.9550),
            ("Signal-C", "Ukkadam Bus Stop",             10.9925, 76.9610),
            ("Signal-D", "Singanallur Signal",           11.0065, 77.0020),
            ("Signal-E", "Peelamedu Junction",           11.0270, 77.0170),
            ("Signal-F", "Saibaba Colony",               11.0240, 76.9660),
        ]
        conn.executemany(
            "INSERT INTO signals (name, location, lat, lng) VALUES (?, ?, ?, ?)",
            signals,
        )
        conn.commit()
    conn.close()


def relocate_signals(center_lat: float, center_lng: float):
    """
    Reposition all signals around a new center point (user's location).
    Spreads them in a ~2km radius.
    """
    import random
    conn = get_db()
    signals = conn.execute("SELECT id FROM signals ORDER BY id").fetchall()
    offsets = [
        ( 0.005,  0.003),
        (-0.004,  0.006),
        ( 0.007, -0.004),
        (-0.006, -0.005),
        ( 0.003,  0.008),
        (-0.008,  0.002),
        ( 0.009, -0.007),
        ( 0.002, -0.009),
    ]
    for i, sig in enumerate(signals):
        off = offsets[i % len(offsets)]
        # Add small jitter for realism
        jitter_lat = random.uniform(-0.001, 0.001)
        jitter_lng = random.uniform(-0.001, 0.001)
        new_lat = center_lat + off[0] + jitter_lat
        new_lng = center_lng + off[1] + jitter_lng
        conn.execute(
            "UPDATE signals SET lat = ?, lng = ? WHERE id = ?",
            (round(new_lat, 6), round(new_lng, 6), sig["id"]),
        )
    conn.commit()
    conn.close()


def add_signal(name: str, location: str, lat: float, lng: float):
    """Add a new signal to the system."""
    conn = get_db()
    conn.execute(
        "INSERT INTO signals (name, location, lat, lng) VALUES (?, ?, ?, ?)",
        (name, location, lat, lng),
    )
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return new_id


def delete_signal(signal_id: int) -> bool:
    """Delete a signal and its history. Returns True if found."""
    conn = get_db()
    existing = conn.execute("SELECT id FROM signals WHERE id = ?", (signal_id,)).fetchone()
    if not existing:
        conn.close()
        return False
    conn.execute("DELETE FROM history WHERE signal_id = ?", (signal_id,))
    conn.execute("DELETE FROM signals WHERE id = ?", (signal_id,))
    conn.commit()
    conn.close()
    return True


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
    return [dict(r) for r in reversed(rows)]


def get_analytics():
    """Compute system-wide analytics from history data."""
    conn = get_db()

    # Total history records
    total_records = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    # Peak vehicle count ever recorded
    peak_row = conn.execute(
        "SELECT signal_id, vehicle_count, timestamp FROM history ORDER BY vehicle_count DESC LIMIT 1"
    ).fetchone()

    # Average vehicle count across all history
    avg_row = conn.execute(
        "SELECT AVG(vehicle_count) as avg_vc FROM history"
    ).fetchone()

    # Per-signal stats
    signal_stats = conn.execute("""
        SELECT s.id, s.name,
               COUNT(h.id) as total_snapshots,
               COALESCE(AVG(h.vehicle_count), 0) as avg_vehicles,
               COALESCE(MAX(h.vehicle_count), 0) as peak_vehicles,
               COALESCE(MIN(h.vehicle_count), 0) as min_vehicles
        FROM signals s
        LEFT JOIN history h ON h.signal_id = s.id
        GROUP BY s.id
        ORDER BY avg_vehicles DESC
    """).fetchall()

    # Density distribution across all history
    density_dist = conn.execute("""
        SELECT density, COUNT(*) as count
        FROM history
        GROUP BY density
    """).fetchall()

    conn.close()

    return {
        "total_snapshots": total_records,
        "peak": {
            "signal_id": peak_row["signal_id"] if peak_row else None,
            "vehicle_count": peak_row["vehicle_count"] if peak_row else 0,
            "timestamp": peak_row["timestamp"] if peak_row else None,
        } if peak_row else None,
        "average_vehicles": round(avg_row["avg_vc"], 1) if avg_row and avg_row["avg_vc"] else 0,
        "signal_rankings": [dict(r) for r in signal_stats],
        "density_distribution": {r["density"]: r["count"] for r in density_dist},
    }
