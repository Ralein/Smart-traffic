"""
routes.py
REST API endpoints for the traffic signal system.
"""

from flask import Blueprint, jsonify, request
from models import (
    get_all_signals, get_signal, update_signal,
    record_history, get_history, relocate_signals,
    add_signal, delete_signal, get_analytics,
)
from traffic_logic import (
    calculate_green_time, classify_density, simulate_vehicle_count,
    determine_phase, get_cycle_length, calculate_efficiency,
)

api = Blueprint("api", __name__)


@api.route("/signals", methods=["GET"])
def all_signals():
    """Return all signals with computed efficiency scores."""
    signals = get_all_signals()
    for sig in signals:
        sig["efficiency"] = calculate_efficiency(
            sig["vehicle_count"], sig["green_time"], sig["current_phase"]
        )
    return jsonify(signals)


@api.route("/signal/<int:signal_id>", methods=["GET"])
def one_signal(signal_id):
    """Return a single signal."""
    sig = get_signal(signal_id)
    if sig is None:
        return jsonify({"error": "Signal not found"}), 404
    sig["efficiency"] = calculate_efficiency(
        sig["vehicle_count"], sig["green_time"], sig["current_phase"]
    )
    return jsonify(sig)


@api.route("/override", methods=["POST"])
def override_signal():
    """
    Manually set vehicle count (and recalculate timing) or directly set green time.
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
    """Toggle emergency priority mode for a signal."""
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


@api.route("/move-signal", methods=["POST"])
def move_signal():
    """
    Move a signal to new coordinates (from draggable map markers).

    Body JSON:
        signal_id: int (required)
        lat:       float (required)
        lng:       float (required)
    """
    data = request.get_json(force=True)
    signal_id = data.get("signal_id")
    lat = data.get("lat")
    lng = data.get("lng")
    if signal_id is None or lat is None or lng is None:
        return jsonify({"error": "signal_id, lat, and lng are required"}), 400
    sig = get_signal(signal_id)
    if sig is None:
        return jsonify({"error": "Signal not found"}), 404
    update_signal(signal_id, lat=float(lat), lng=float(lng))
    return jsonify({"status": "ok", "signal": get_signal(signal_id)})


@api.route("/relocate", methods=["POST"])
def relocate():
    """
    Reposition all signals around the user's actual location.

    Body JSON:
        lat: float (required)
        lng: float (required)
    """
    data = request.get_json(force=True)
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"error": "lat and lng are required"}), 400
    relocate_signals(float(lat), float(lng))
    return jsonify({"status": "ok", "signals": get_all_signals()})


@api.route("/add-signal", methods=["POST"])
def add_signal_route():
    """
    Add a new signal.

    Body JSON:
        name:     str (required)
        location: str (required)
        lat:      float (required)
        lng:      float (required)
    """
    data = request.get_json(force=True)
    name = data.get("name")
    location = data.get("location", "")
    lat = data.get("lat")
    lng = data.get("lng")

    if not name or lat is None or lng is None:
        return jsonify({"error": "name, lat, and lng are required"}), 400

    new_id = add_signal(name, location, float(lat), float(lng))

    # Initialize the new signal
    from traffic_logic import simulate_vehicle_count
    vc = simulate_vehicle_count()
    gt = calculate_green_time(vc)
    density = classify_density(vc)
    update_signal(
        new_id,
        vehicle_count=vc,
        green_time=gt,
        density=density,
        countdown=get_cycle_length(gt),
        current_phase="green",
    )
    record_history(new_id, vc, gt, density)

    return jsonify({"status": "ok", "signal": get_signal(new_id)}), 201


@api.route("/delete-signal/<int:signal_id>", methods=["DELETE"])
def delete_signal_route(signal_id):
    """Delete a signal by ID."""
    success = delete_signal(signal_id)
    if not success:
        return jsonify({"error": "Signal not found"}), 404
    return jsonify({"status": "ok", "deleted": signal_id})


@api.route("/analytics", methods=["GET"])
def analytics():
    """Return system-wide analytics (rankings, density distribution, peak data)."""
    data = get_analytics()
    return jsonify(data)
