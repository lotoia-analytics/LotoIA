"""M-ML-VIS-058-FIX-02 — Detalhes técnicos da Central ML com nomes institucionais.

Garante que os expansores técnicos do cockpit de calibração:
- usam nomes institucionais claros (renomeados);
- não usam mais os títulos técnicos antigos (ex.: "Bloqueios constitucionais");
- permanecem fechados por padrão (expanded=False);
- preservam rastreabilidade (trace, feature attribution, 6 bases, memória ML, histórico PostgreSQL).
"""

from __future__ import annotations

import inspect

import dashboard.institutional_ml_calibration_cockpit as cockpit


EXPANDER_SOURCE = inspect.getsource(cockpit._render_technical_expanders)


NEW_EXPANDER_TITLES = (
    "Memória ML — Limiares por Formato 15D a 23D",
    "Detalhes por lote",
    "Leitura usada da Cobertura Estrutural",
    "Registro completo da decisão ML",
    "Proteções constitucionais ativas",
    "Rastreamento da decisão",
    "Pesos e fatores considerados",
    "Leitura ML pelas 6 Bases",
    "Histórico e auditoria PostgreSQL",
)

OLD_EXPANDER_TITLES = (
    "Snapshot Cobertura Estrutural (técnico)",
    "Blocos decisórios completos",
    "Bloqueios constitucionais",
    'st.expander("Decision trace"',
    'st.expander("Feature attribution"',
    "ML × 6 Bases (detalhado)",
    "Histórico de decisões / auditoria PostgreSQL",
    "Memória ML — limiares 15D a 23D",
)


def test_new_institutional_expander_names_present() -> None:
    for title in NEW_EXPANDER_TITLES:
        assert f'st.expander("{title}"' in EXPANDER_SOURCE, title


def test_old_technical_expander_names_absent() -> None:
    for title in OLD_EXPANDER_TITLES:
        assert title not in EXPANDER_SOURCE, title


def test_constitutional_blocks_renamed() -> None:
    # Aceite 3: "Bloqueios constitucionais" não pode mais aparecer como título.
    assert "Bloqueios constitucionais" not in EXPANDER_SOURCE
    assert 'st.expander("Proteções constitucionais ativas"' in EXPANDER_SOURCE


def test_all_technical_expanders_closed_by_default() -> None:
    # Nenhum expander técnico pode abrir por padrão.
    assert "expanded=True" not in EXPANDER_SOURCE
    assert EXPANDER_SOURCE.count("st.expander(") == EXPANDER_SOURCE.count("expanded=False")


def test_traceability_sources_preserved() -> None:
    # Não remover rastreabilidade: trace, feature attribution, 6 bases, memória e histórico.
    assert "decision_trace" in EXPANDER_SOURCE
    assert "feature_attribution" in EXPANDER_SOURCE
    assert "ml_six_bases_reading" in EXPANDER_SOURCE or "build_ml_six_bases_operational_summary" in EXPANDER_SOURCE
    assert "overlap_format_memory" in EXPANDER_SOURCE
    assert "events" in EXPANDER_SOURCE


def test_build_marker_bumped() -> None:
    from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS

    assert BUILD_MARKER == "institutional-adm-runtime-v48"
    assert BUILD_MARKER not in DEPRECATED_BUILD_MARKERS
