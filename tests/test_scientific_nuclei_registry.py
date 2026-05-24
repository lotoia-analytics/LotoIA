from __future__ import annotations

from lotoia.governance import build_scientific_nuclei_registry, validate_scientific_nuclei_registry


def test_scientific_nuclei_registry_covers_consolidated_engines() -> None:
    registry = build_scientific_nuclei_registry()

    assert registry.page_labels["geracao_jogos"] == "Gerar Jogos"
    assert registry.page_labels["jogo_expandido_experimental"] == "Expansivo"
    assert registry.page_labels["backtesting"] == "Testar Estratégia"
    assert registry.page_labels["benchmark_cientifico"] == "Comparativos"
    assert registry.page_labels["ml_intelligence"] == "Ranking ML"
    assert registry.page_labels["estatisticas_historicas"] == "Jogos Passados"
    assert registry.page_labels["relatorios"] == "Analíticas Persistidas"
    assert registry.score_ml_contract_ready is True
    assert registry.runtime_stability_ready is True


def test_scientific_nuclei_registry_validation_is_clean() -> None:
    registry = build_scientific_nuclei_registry()
    report = validate_scientific_nuclei_registry(registry)

    assert report.valid is True
    assert report.errors == ()
    assert report.warnings == ()

