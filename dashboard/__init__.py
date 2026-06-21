"""Dashboard package for LotoIA."""

# Hotfix M-OPS-283: manter approved_with_warning conferível no painel ADM.
# Import intencional no bootstrap para que dashboard.institutional_app já receba
# as funções de elegibilidade corrigidas ao importar lot_operational_status.
try:  # pragma: no cover - defesa de bootstrap
    from . import conference_visibility_hotfix as _conference_visibility_hotfix  # noqa: F401
except Exception:
    _conference_visibility_hotfix = None
