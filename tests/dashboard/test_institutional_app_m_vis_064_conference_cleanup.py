"""M-VIS-064 — Limpeza visual e operacional da tela Conferir Resultados.

Garante que:
- a tela abre direto em Conferência oficial (governança não fica no topo);
- detalhes técnicos/governança ficam num expansor fechado no final;
- o resultado principal mostra apenas jogos 11+ e gerações com pelo menos um 11+;
- gerações com best_hits < 11 (ex.: 8/9/10) não aparecem no resultado principal;
- o resumo mostra a distribuição 11/12/13/14/15;
- regra M-OPS-062 e sincronização preservadas.
"""

from __future__ import annotations

import inspect

import pytest

from dashboard import institutional_app as admin_app


PAGE_SOURCE = inspect.getsource(admin_app._render_conference_page)
PREMIUM_SOURCE = inspect.getsource(admin_app._render_conference_summary_and_premium)


# --------------------------------------------------------------------------- #
# Estrutura da tela (source inspection)
# --------------------------------------------------------------------------- #
def test_technical_details_collapsed_at_end() -> None:
    assert 'st.expander("Detalhes técnicos e governança", expanded=False)' in PAGE_SOURCE


def test_governance_not_at_top() -> None:
    # Governança deve aparecer DEPOIS da Conferência oficial (dentro do expansor técnico).
    idx_conf = PAGE_SOURCE.index('### Conferência oficial')
    idx_gov = PAGE_SOURCE.index("render_conference_governance_section")
    idx_tech = PAGE_SOURCE.index('st.expander("Detalhes técnicos e governança"')
    assert idx_conf < idx_tech < idx_gov


def test_page_uses_summary_and_audit_helpers() -> None:
    assert "_render_conference_summary_and_premium" in PAGE_SOURCE
    assert "_render_conference_technical_audit" in PAGE_SOURCE


def test_no_debug_writes_in_page() -> None:
    assert "st.write(total_runs)" not in PAGE_SOURCE
    assert "Diagnóstico temporário" not in PAGE_SOURCE
    assert "Resumo geral" not in PAGE_SOURCE  # substituído por "Resumo da conferência"


def test_m_ops_062_rules_preserved() -> None:
    assert "conference_all_official=True" in PAGE_SOURCE
    assert "_resolve_latest_official_conference_contest" in PAGE_SOURCE
    assert "_load_official_conference_generation_groups" in PAGE_SOURCE
    assert 'key="conference_sync_latest"' in PAGE_SOURCE
    assert "_render_official_sync_feedback" in PAGE_SOURCE


def test_premium_filters_below_11() -> None:
    assert ">= 11" in PREMIUM_SOURCE
    assert 'best_hits", 0) or 0) < 11' in PREMIUM_SOURCE


# --------------------------------------------------------------------------- #
# Comportamento do resumo + resultados 11+
# --------------------------------------------------------------------------- #
class _Recorder:
    def __init__(self) -> None:
        self.markdowns: list[str] = []
        self.metrics: dict[str, object] = {}
        self.dataframes: list = []
        self.infos: list[str] = []

    def markdown(self, text, *a, **k) -> None:
        self.markdowns.append(str(text))

    def caption(self, *a, **k) -> None:
        return None

    def write(self, *a, **k) -> None:
        return None

    def info(self, text, *a, **k) -> None:
        self.infos.append(str(text))

    def metric(self, label, value, *a, **k) -> None:
        self.metrics[str(label)] = value

    def dataframe(self, df, *a, **k) -> None:
        self.dataframes.append(df)

    def columns(self, spec):
        count = len(spec) if isinstance(spec, list) else spec
        return [self for _ in range(count)]


def _row(game_index: int, hits: int) -> dict:
    nums = list(range(1, 16))
    return {
        "game_index": game_index,
        "numbers": nums,
        "cartao_final": nums,
        "hits": hits,
        "matched_numbers": nums[:hits],
        "prize_status": "premiado" if hits >= 11 else "nao_premiado",
        "formato_cartao": 15,
    }


def _generation(event_id: int, hits_list: list[int]) -> dict:
    return {
        "generation_event_id": event_id,
        "best_hits": max(hits_list),
        "total_games": len(hits_list),
        "formato_cartao": 15,
        "results": [_row(i + 1, h) for i, h in enumerate(hits_list)],
    }


def _build_results() -> list[dict]:
    return [
        _generation(101, [13, 9, 11]),  # tem 11+ -> aparece
        _generation(102, [10, 8]),       # best_hits 10 -> NÃO aparece
        _generation(103, [11, 7]),       # tem 11 -> aparece
    ]


def test_premium_results_only_show_generations_with_11_plus(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr(admin_app, "st", recorder)
    results = _build_results()
    status = {101: "officialized", 103: "approved_with_warning"}

    admin_app._render_conference_summary_and_premium({"contest_number": 3713}, results, status)

    joined = " ".join(recorder.markdowns)
    assert "Geração #101" in joined
    assert "Geração #103" in joined
    assert "Geração #102" not in joined  # best_hits 10 excluída


def test_summary_distribution_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr(admin_app, "st", recorder)
    results = _build_results()

    admin_app._render_conference_summary_and_premium({"contest_number": 3713}, results, {})

    # 11 aparece em 101 (1) e 103 (1) = 2; 13 em 101 = 1
    assert recorder.metrics["Jogos com 11"] == 2
    assert recorder.metrics["Jogos com 12"] == 0
    assert recorder.metrics["Jogos com 13"] == 1
    assert recorder.metrics["Jogos com 14"] == 0
    assert recorder.metrics["Jogos com 15"] == 0
    assert recorder.metrics["Concurso"] == 3713


def test_premium_dataframes_only_contain_11_plus(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr(admin_app, "st", recorder)
    results = _build_results()

    admin_app._render_conference_summary_and_premium({"contest_number": 3713}, results, {})

    assert recorder.dataframes  # pelo menos uma geração 11+
    for df in recorder.dataframes:
        assert all(int(hits) >= 11 for hits in df["hits"].tolist())


def test_premium_empty_when_no_11_plus(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr(admin_app, "st", recorder)
    results = [_generation(201, [8, 9, 10])]

    admin_app._render_conference_summary_and_premium({"contest_number": 3713}, results, {})

    assert any("Nenhum jogo com 11" in message for message in recorder.infos)
    assert not recorder.dataframes


def test_build_marker_bumped() -> None:
    from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS

    assert BUILD_MARKER == "institutional-adm-runtime-v49"
    assert BUILD_MARKER not in DEPRECATED_BUILD_MARKERS
    assert "institutional-adm-runtime-v48" in DEPRECATED_BUILD_MARKERS
