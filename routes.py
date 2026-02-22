"""
routes.py
REST API endpoints for the traffic signal system.
"""

from flask import Blueprint, jsonify, request
from models import (
    get_all_signals, get_signal, update_signal,
    record_history, get_history,
)
from traffic_logic import (
    calculate_green_time, classify_density, simulate_vehicle_count,
    determine_phase, get_cycle_length,
)

api = Blueprint("api", __name__)


@api.route("/signals", methods=["GET"])
def all_signals():
    """Return all signals."""
    signals = get_all_signals()
    return jsonify(signals)


@api.route("/signal/<int:signal_id>", methods=["GET"])
def one_signal(signal_id):
    """Return a single signal."""
    sig = get_signal(signal_id)
    if sig is None:
        return jsonify({"error": "Signal not found"}), 404
    return jsonify(sig)


@api.route("/override", methods=["POST"])
def override_signal():
    """
    Manually set vehicle count (and recalculate timing) or directly set green time.
    
    Body JSON:
        signal_id:      int (required)
        vehicle_count:  int (optional) — recalculates green_time & density
        green_time:     int (optional) — directly override green duration
    """
    data = request.get_json(force=True)
    signal_id = data.get("signal_id")
    if signal_id is None:
        return jsonify({"error": "signal_id is required"}), 400

    sig = get_signal(signal_id)
    if sig is None:
        return jsonify({"error": "Signal not found"}), 404

    vehicle_count = data.get("vehicle_count")
    green_time = data.get("green_time")

    updates = {}
    vc = sig["vehicle_count"]

    if vehicle_count is not None:
        vc = int(vehicle_count)
        gt = calculate_green_time(vc)
        density = classify_density(vc)
        updates.update(
            vehicle_count=vc,
            green_time=gt,
            density=density,
            countdown=get_cycle_length(gt),
            current_phase="green",
        )
    
    if green_time is not None:
        updates["green_time"] = int(green_time)
        updates["countdown"] = get_cycle_length(int(green_time))
        updates["current_phase"] = "green"

    if updates:
        update_signal(signal_id, **updates)
        # Record history
        final = get_signal(signal_id)
        record_history(signal_id, final["vehicle_count"], final["green_time"], final["density"])

    return jsonify({"status": "ok", "signal": get_signal(signal_id)})


@api.route("/simulate", methods=["GET"])
def simulate():
    """Regenerate random vehicle counts for all signals."""
    signals = get_all_signals()
    results = []
    for sig in signals:
        if sig["emergency"]:
            results.append(sig)
            continue
        vc = simulate_vehicle_count()
        gt = calculate_green_time(vc)
        density = classify_density(vc)
        update_signal(
            sig["id"],
            vehicle_count=vc,
            green_time=gt,
            density=density,
            countdown=get_cycle_length(gt),
            current_phase="green",
        )
        record_history(sig["id"], vc, gt, density)
        results.append(get_signal(sig["id"]))
    return jsonify(results)


@api.route("/history/<int:signal_id>", methods=["GET"])
def signal_history(signal_id):
    """Return vehicle count history for a signal."""
    limit = request.args.get("limit", 50, type=int)
    rows = get_history(signal_id, limit)
    return jsonify(rows)



@api.route("/emergency", methods=["POST"])
def toggle_emergency():
    """
    Toggle emergency priority mode for a signal.
    
    Body JSON:
        signal_id: int (required)
        enable:    bool (required)
    """
    data = request.get_json(force=True)
    signal_id = data.get("signal_id")
    enable = data.get("enable", False)

    if signal_id is None:
        return jsonify({"error": "signal_id is required"}), 400

    sig = get_signal(signal_id)
    if sig is None:
        return jsonify({"error": "Signal not found"}), 404

    if enable:
        update_signal(signal_id, emergency=1, current_phase="green", countdown=999)
    else:
        # Restore normal operation
        vc = sig["vehicle_count"]
        gt = calculate_green_time(vc)
        update_signal(
            signal_id,
            emergency=0,
            current_phase="green",
            countdown=get_cycle_length(gt),
            green_time=gt,
        )

    return jsonify({"status": "ok", "signal": get_signal(signal_id)})
