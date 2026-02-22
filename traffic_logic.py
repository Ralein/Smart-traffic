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
    colors = {
        "Low": "green",
        "Medium": "amber",
        "High": "red",
    }
    return colors.get(density, "gray")


def simulate_vehicle_count() -> int:
    """Generate a random vehicle count between 1 and 80."""
    return random.randint(1, 80)


def determine_phase(countdown: int, green_time: int) -> str:
    """
    Determine signal phase based on countdown and green time.
    
    Timeline (counting down from green_time + yellow + red):
        - Green phase:  countdown > 8  (yellow + red cushion)
        - Yellow phase: countdown > 3
        - Red phase:    countdown <= 3
    
    For simplicity, a full cycle = green_time + 5 (yellow) + 5 (red all-clear).
    The countdown runs from (green_time + 10) down to 0, then resets.
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
