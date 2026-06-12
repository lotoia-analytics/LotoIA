from __future__ import annotations

PLANS: dict[str, dict[str, float | int | str]] = {
    "basico": {"price": 15.99, "formato_max": 15, "formats": "15D"},
    "plus": {"price": 29.99, "formato_max": 16, "formats": "15D + 16D"},
    "avancado": {"price": 39.99, "formato_max": 17, "formats": "15D + 17D"},
    "pro": {"price": 49.99, "formato_max": 18, "formats": "15D + 18D"},
    "master": {"price": 59.99, "formato_max": 19, "formats": "15D + 19D"},
    "elite": {"price": 69.99, "formato_max": 20, "formats": "15D + 20D"},
}

VALID_QUANTITIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30]
DAILY_LIMIT = 30
OFFICIAL_LANDING_HOST = "www.lotoia.chat"
OFFICIAL_LANDING_URL = f"https://{OFFICIAL_LANDING_HOST}"
