from __future__ import annotations

DEFAULT_PLAN_ID = "completo"

PLANS: dict[str, dict[str, float | int | str]] = {
    DEFAULT_PLAN_ID: {
        "price": 99.90,
        "formato_max": 20,
        "formats": "15D (7 dias) → 15D + 20D",
        "trial_days": 7,
        "trial_formato_max": 15,
        "full_access_days": 365,
        "subscription_days": 372,
    },
}

# Planos legados — clientes ativados antes da unificação (somente leitura/enforcement).
LEGACY_PLANS: dict[str, dict[str, float | int | str]] = {
    "basico": {"price": 15.99, "formato_max": 15, "formats": "15D"},
    "plus": {"price": 29.99, "formato_max": 16, "formats": "15D + 16D"},
    "avancado": {"price": 39.99, "formato_max": 17, "formats": "15D + 17D"},
    "pro": {"price": 49.99, "formato_max": 18, "formats": "15D + 18D"},
    "master": {"price": 59.99, "formato_max": 19, "formats": "15D + 19D"},
    "elite": {"price": 69.99, "formato_max": 20, "formats": "15D + 20D"},
}

# Webhooks/checkout antigos continuam ativando o plano único atual.
LEGACY_PLAN_ALIASES: dict[str, str] = {
    plan_id: DEFAULT_PLAN_ID for plan_id in LEGACY_PLANS
}

VALID_QUANTITIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30]
DAILY_LIMIT = 30
OFFICIAL_LANDING_HOST = "www.lotoia.chat"
OFFICIAL_LANDING_URL = f"https://{OFFICIAL_LANDING_HOST}"
