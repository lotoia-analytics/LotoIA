# C:\Projetos\LotoIA\dashboard\labels.py
ANALYTICAL_PAGES = [
    "estatisticas_historicas",
    "backtesting",
    "ml_governance",
    "historical_intelligence",
    "analytics_intelligence",
    "ml_intelligence",
    "observability",
    "relatorios",
    "historico_experimental",
    "calibracao_experimental",
    "benchmark_cientifico",
    "reports_engine",
]

OPERATIONAL_PAGES = [
    "geracao_jogos",
    "conferir_jogos",
    "reconciliacao_operacional",
    "workflows",
    "jogo_expandido_experimental",
]

PAGES = ANALYTICAL_PAGES + OPERATIONAL_PAGES

PAGE_GROUPS = {
    "Analiticos": ANALYTICAL_PAGES,
    "Operacoes": OPERATIONAL_PAGES,
}

MODE_PAGES = {
    "operacional": OPERATIONAL_PAGES,
    "executivo": [
        "estatisticas_historicas",
        "historical_intelligence",
        "analytics_intelligence",
        "ml_intelligence",
        "ml_governance",
        "observability",
        "relatorios",
        "historico_experimental",
        "calibracao_experimental",
        "benchmark_cientifico",
        "reports_engine",
    ],
    "auditoria": [
        "observability",
        "ml_governance",
        "workflows",
        "historical_intelligence",
        "reports_engine",
        "benchmark_cientifico",
    ],
}

LABELS = {
    "geracao_jogos": "Gerar Jogos",
    "conferir_jogos": "Conferir Jogos",
    "reconciliacao_operacional": "Simular Resultado",
    "estatisticas_historicas": "Dashboard",
    "historical_intelligence": "Histórico",
    "analytics_intelligence": "Análises",
    "ml_intelligence": "Inteligência Adaptativa",
    "jogo_expandido_experimental": "Jogo Expandido",
    "backtesting": "Insights",
    "calibracao_experimental": "Scheduler",
    "benchmark_cientifico": "Observability",
    "historico_experimental": "Timeline",
    "relatorios": "Relatórios",
    "ml_governance": "Governança ML",
    "observability": "Monitoramento",
    "workflows": "Automação",
    "reports_engine": "Persistência Operacional",
}
