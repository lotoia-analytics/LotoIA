from pathlib import Path


POLICY_PATH = Path("docs/governance/POLITICA_ML_ASSISTIVO.md")
ADR_PATH = Path("docs/adr/ADR-042-POLITICA-ML-ASSISTIVO.md")


REQUIRED_RULES = (
    "ML nao substitui a Lei 15",
    "ML nao altera regras soberanas automaticamente",
    "ML nao gera jogos sem rastreabilidade",
    "ML nao opera como motor preditivo central",
    "ML pode auxiliar ranking, analise, clusterizacao, diagnostico e validacao",
    "explicavel, testavel, reversivel e auditavel",
    "validacao temporal",
    "relatorio comparativo",
)


def test_ml_assistive_policy_is_formalized() -> None:
    text = POLICY_PATH.read_text(encoding="utf-8")

    assert POLICY_PATH.exists()
    assert "POLITICA_ML_ASSISTIVO_FORMALIZADA" in text
    for rule in REQUIRED_RULES:
        assert rule in text


def test_ml_assistive_policy_adr_is_registered() -> None:
    text = ADR_PATH.read_text(encoding="utf-8")

    assert ADR_PATH.exists()
    assert "Accepted" in text
    assert "docs/governance/POLITICA_ML_ASSISTIVO.md" in text
    assert "POLITICA_ML_ASSISTIVO_FORMALIZADA" in text
