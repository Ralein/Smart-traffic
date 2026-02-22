"""
app.py
Main Flask application — Smart Traffic Signal Management System.
"""

import threading
import time
from flask import Flask, render_template
from models import init_db, seed_signals, get_all_signals, update_signal, record_history
from traffic_logic import (
    calculate_green_time, classify_density, simulate_vehicle_count,
    determine_phase, get_cycle_length,
)
from routes import api

app = Flask(__name__)
app.register_blueprint(api)

# ─── Background simulation ───────────────────────────────────────────

TICK_INTERVAL = 3  # seconds between background ticks


def background_ticker():
    """
    Runs in a daemon thread. Every TICK_INTERVAL seconds it:
    1. Decrements each signal's countdown.
    2. Updates current phase.
    3. When countdown hits 0, re-simulates vehicle count and resets cycle.
    """
    while True:
        time.sleep(TICK_INTERVAL)
        try:
            signals = get_all_signals()
            for sig in signals:
                # Skip emergency signals — they stay green
                if sig["emergency"]:
                    continue

                new_countdown = sig["countdown"] - TICK_INTERVAL
                if new_countdown <= 0:
                    # New cycle: simulate new vehicle count
                    vc = simulate_vehicle_count()
                    gt = calculate_green_time(vc)
                    density = classify_density(vc)
                    new_countdown = get_cycle_length(gt)
                    phase = determine_phase(new_countdown, gt)
                    update_signal(
                        sig["id"],
                        vehicle_count=vc,
                        green_time=gt,
                        density=density,
                        countdown=new_countdown,
                        current_phase=phase,
                    )
                    record_history(sig["id"], vc, gt, density)
                else:
                    phase = determine_phase(new_countdown, sig["green_time"])
                    update_signal(sig["id"], countdown=new_countdown, current_phase=phase)
        except Exception as e:
            print(f"[ticker error] {e}")


# ─── Routes ───────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    """Serve the admin dashboard."""
    signals = get_all_signals()
    return render_template("dashboard.html", signals=signals)


# ─── Startup ──────────────────────────────────────────────────────────

def create_app():
    """Initialize DB, seed data, and start background thread."""
    init_db()
    seed_signals()

    # Set initial countdowns for all signals
    signals = get_all_signals()
    for sig in signals:
        gt = calculate_green_time(sig["vehicle_count"])
        density = classify_density(sig["vehicle_count"])
        cycle = get_cycle_length(gt)
        update_signal(
            sig["id"],
            green_time=gt,
            density=density,
            countdown=cycle,
            current_phase="green",
        )
        record_history(sig["id"], sig["vehicle_count"], gt, density)

    # Start background simulation thread
    ticker = threading.Thread(target=background_ticker, daemon=True)
    ticker.start()


if __name__ == "__main__":
    create_app()
    print("=" * 60)
    print("  Smart Traffic Signal Management System")
    print("  Dashboard → http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=False, port=5000, use_reloader=False)
