from __future__ import annotations

PLANS: dict[str, dict[str, float | int]] = {
    "basico": {"price": 15.99, "formato_max": 15},
    "plus": {"price": 29.99, "formato_max": 16},
    "avancado": {"price": 39.99, "formato_max": 17},
    "pro": {"price": 49.99, "formato_max": 18},
    "master": {"price": 59.99, "formato_max": 19},
    "elite": {"price": 69.99, "formato_max": 20},
}

VALID_QUANTITIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30]
DAILY_LIMIT = 30
