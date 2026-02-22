"""
traffic_logic.py
Signal timing algorithm, density classification, and vehicle simulation.
"""

import random


def calculate_green_time(vehicle_count: int) -> int:
    """
    Determine green light duration based on vehicle density.

    Rules:
        > 40 vehicles  → 70 seconds
        20–40 vehicles → 45 seconds
        < 20 vehicles  → 25 seconds
    """
    if vehicle_count > 40:
        return 70
    elif vehicle_count >= 20:
        return 45
    else:
        return 25


def classify_density(vehicle_count: int) -> str:
    """Classify traffic density as Low, Medium, or High."""
    if vehicle_count > 40:
        return "High"
    elif vehicle_count >= 20:
        return "Medium"
    else:
        return "Low"


def get_density_color(density: str) -> str:
    """Return a Tailwind-friendly color name for a density level."""
    return {"Low": "green", "Medium": "amber", "High": "red"}.get(density, "gray")


def simulate_vehicle_count() -> int:
    """Generate a random vehicle count between 1 and 80."""
    return random.randint(1, 80)


def determine_phase(countdown: int, green_time: int) -> str:
    """
    Determine signal phase based on countdown and green time.

    Full cycle = green_time + 5s yellow + 5s red.
    """
    if countdown > 8:
        return "green"
    elif countdown > 3:
        return "yellow"
    else:
        return "red"


def get_cycle_length(green_time: int) -> int:
    """Total cycle length = green + 5s yellow + 5s red."""
    return green_time + 10


def calculate_efficiency(vehicle_count: int, green_time: int, current_phase: str) -> int:
    """
    Calculate a signal efficiency score (0-100).

    Factors:
    - How well the green time matches the vehicle demand
    - Whether the phase is appropriate for the load
    """
    # Ideal green time for this count
    ideal_gt = calculate_green_time(vehicle_count)

    # Timing match score (100 = perfect, less if over/under-timed)
    if ideal_gt == 0:
        timing_score = 100
    else:
        ratio = min(green_time, ideal_gt) / max(green_time, ideal_gt)
        timing_score = int(ratio * 100)

    # Phase appropriateness bonus
    phase_bonus = 0
    if vehicle_count > 40 and current_phase == "green":
        phase_bonus = 10  # Heavy traffic getting green is good
    elif vehicle_count < 10 and current_phase == "red":
        phase_bonus = 5   # Light traffic being red saves cross-traffic

    # Throughput penalty — high vehicles with low green is bad
    throughput_penalty = 0
    if vehicle_count > 50 and green_time < 45:
        throughput_penalty = 20
    elif vehicle_count > 30 and green_time < 25:
        throughput_penalty = 15

    score = max(0, min(100, timing_score + phase_bonus - throughput_penalty))
    return score
