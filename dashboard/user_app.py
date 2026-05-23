from __future__ import annotations

import io
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.ingestion.result_sync_scheduler import ResultSyncScheduler
from lotoia.ingestion.result_sync_service import ResultSyncService
from lotoia.database import public_repository as _public_repository
from lotoia.public.reconciliation import reconcile_smoke_validation
from lotoia.public.services import LeadCaptureRequest, LeadCaptureService

MAX_GAMES_PER_SESSION = 10
DEFAULT_GAMES_COUNT = 5
DEFAULT_POOL_SIZE = 20
ONLINE_MARKER = "USER PANEL ONLINE"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
USER_DB_PATH = PROJECT_ROOT / DEFAULT_DATABASE_PATH


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_numbers(numbers: list[int]) -> str:
    return " ".join(f"{number:02d}" for number in numbers)


def _parse_numbers(text: str) -> list[int]:
    tokens = [token for token in text.replace(",", " ").split() if token]
    numbers = [int(token) for token in tokens]
    if len(numbers) != 15:
        raise ValueError("Cada jogo deve conter exatamente 15 dezenas.")
    if len(set(numbers)) != 15:
        raise ValueError("As dezenas nao podem se repetir dentro do mesmo jogo.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas devem estar entre 1 e 25.")
    return sorted(numbers)


def _generate_user_games(count: int, pool_size: int, ml_enabled: bool) -> dict[str, Any]:
    from lotoia.generator.basic_generator import generate_best_games

    if count < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")
    if count > MAX_GAMES_PER_SESSION:
        raise ValueError("A quantidade maxima por geracao e de 10 jogos.")
    if pool_size < count:
        raise ValueError("O pool deve ser maior ou igual a quantidade solicitada.")

    result = generate_best_games(count=count, pool_size=pool_size, ml_enabled=ml_enabled)
    games = result["games"]
    compact_games = [
        {
            "ranking": index + 1,
            "numbers": game["numbers"],
            "final_score": float(game["final_score"]["final_score"]),
            "quadra_score": game["quadra_score"],
        }
        for index, game in enumerate(games)
    ]
    return {
        "count": len(compact_games),
        "games": compact_games,
        "raw_games": result["games"],
        "metadata": {
            "generated_at": _timestamp(),
            "ml_enabled": ml_enabled,
            "pool_size": pool_size,
            "strategy": "ranking_hibrido",
        },
    }


@st.cache_data(show_spinner=False)
def _load_history_cached(history_path: str) -> list[dict[str, Any]]:
    return [
        {
            "contest": draw.contest,
            "date": draw.date,
            "numbers": draw.numbers,
        }
        for draw in load_draws_csv(Path(history_path))
    ]


def _find_draw(contest_id: int, history_path: Path = DEFAULT_HISTORY_PATH) -> dict[str, Any]:
    draws = _load_history_cached(str(history_path))
    for draw in draws:
        if draw["contest"] == contest_id:
            return draw
    raise ValueError(f"Concurso {contest_id} nao encontrado.")


def _check_user_contest(contest_id: int, numbers: list[int], history_path: Path = DEFAULT_HISTORY_PATH) -> dict[str, Any]:
    draw = _find_draw(contest_id, history_path=history_path)
    correct_numbers = sorted(draw["numbers"])
    selected_numbers = sorted(numbers)
    hits = len(set(correct_numbers) & set(selected_numbers))
    return {
        "contest": contest_id,
        "date": draw["date"],
        "hits": hits,
        "correct_numbers": correct_numbers,
        "selected_numbers": selected_numbers,
        "result_label": f"{hits} acertos",
    }


def _recent_history_dataframe(events: list[dict[str, Any]]) -> pd.DataFrame:
    if not events:
        return pd.DataFrame(columns=["timestamp", "type", "details"])
    rows = []
    for event in reversed(events[-20:]):
        rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "type": event.get("type", ""),
                "details": event.get("details", ""),
            }
        )
    return pd.DataFrame(rows)


def _bootstrap_official_results_sync() -> list[dict[str, Any]]:
    contest_repository = ContestRepository(USER_DB_PATH)
    scheduler = ResultSyncScheduler(
        service=ResultSyncService(repository=contest_repository),
    )
    summaries = scheduler.run_due_checks()
    if any(summary.synced_contests for summary in summaries):
        try:
            st.cache_data.clear()
        except Exception:
            pass
    return [summary.to_dict() for summary in summaries]


def _build_light_report_pdf(title: str, lines: list[str], table: pd.DataFrame | None = None) -> bytes:
    del table
    body_lines = [title, "LotoIA | User Panel", *lines[:20]]
    text = "\n".join(body_lines)
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    wrapped = textwrap.wrap(escaped, width=72) or [""]

    stream_lines = ["BT", "/F1 12 Tf", "72 760 Td"]
    first = True
    for line in wrapped:
        if first:
            stream_lines.append(f"({line}) Tj")
            first = False
        else:
            stream_lines.append("T*")
            stream_lines.append(f"({line}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("latin-1", "ignore")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    )
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(
        b"5 0 obj << /Length "
        + str(len(stream)).encode("ascii")
        + b" >> stream\n"
        + stream
        + b"\nendstream endobj\n"
    )

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(output.tell())
        output.write(obj)
    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        (
            "trailer << /Size {size} /Root 1 0 R >>\n"
            "startxref\n{xref}\n%%EOF\n"
        ).format(size=len(objects) + 1, xref=xref_offset).encode("ascii")
    )
    return output.getvalue()


def _user_indicator(games: list[dict[str, Any]]) -> tuple[str, str]:
    if not games:
        return "Sem indicadores", "Nenhum jogo gerado ainda."
    avg_score = sum(game["final_score"] for game in games) / len(games)
    if avg_score >= 70:
        return "Bom", f"Score medio {avg_score:.1f}"
    if avg_score >= 45:
        return "Neutro", f"Score medio {avg_score:.1f}"
    return "Baixo", f"Score medio {avg_score:.1f}"


def _render_sidebar() -> str:
    logo_path = PROJECT_ROOT / "assets" / "logo.png"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=220)
    return st.sidebar.radio(
        "Navegacao",
        [
            "Gerar Jogos",
            "Conferir Concurso",
            "Historico",
            "Relatorios",
        ],
    )


def _record_event(events: list[dict[str, Any]], event_type: str, details: str) -> None:
    events.append({"timestamp": _timestamp(), "type": event_type, "details": details})


def _refresh_institutional_usage_views() -> None:
    try:
        st.cache_data.clear()
    except Exception:
        pass


def _build_lead_service() -> LeadCaptureService:
    try:
        return LeadCaptureService(db_path=USER_DB_PATH)
    except TypeError:
        return LeadCaptureService()


def _save_generation_event(**kwargs: Any) -> dict[str, Any]:
    return _public_repository.save_generation_event(**kwargs)


def _save_check_event(**kwargs: Any) -> dict[str, Any]:
    return _public_repository.save_check_event(**kwargs)


def _save_report_event(**kwargs: Any) -> dict[str, Any]:
    return _public_repository.save_report_event(**kwargs)


save_generation_event = _save_generation_event
save_check_event = _save_check_event
save_report_event = _save_report_event


def render_generate_page(events: list[dict[str, Any]]) -> None:
    st.header("Gerar Jogos")
    st.markdown(
        "<div style='font-size:0.78rem; text-transform:uppercase; letter-spacing:0.14em; color:#6b7f93; margin-bottom:0.15rem;'>Geracao assistida</div>",
        unsafe_allow_html=True,
    )
    lead_col1, lead_col2 = st.columns(2)
    first_name = lead_col1.text_input("Primeiro nome", key="user_first_name")
    whatsapp = lead_col2.text_input("WhatsApp", key="user_whatsapp")
    first_name = " ".join((first_name or "").strip().split())
    whatsapp = " ".join((whatsapp or "").strip().split())
    lead_ready = bool(first_name and whatsapp)
    count = st.number_input("Quantidade", min_value=1, max_value=MAX_GAMES_PER_SESSION, value=DEFAULT_GAMES_COUNT)
    pool_size = st.number_input("Pool", min_value=int(count), max_value=100, value=max(int(count) * 4, DEFAULT_POOL_SIZE))
    st.markdown(
        "<div style='font-size:1rem; font-weight:800; color:#3b4fe0; margin:0.2rem 0 0.35rem 0;'>LotoIA</div>",
        unsafe_allow_html=True,
    )
    ml_enabled = st.toggle("LotoIA", value=False, label_visibility="collapsed")

    if st.button("Gerar", type="primary", disabled=not lead_ready):
        try:
            lead_service = _build_lead_service()
            lead_payload = LeadCaptureRequest(first_name=first_name, whatsapp=whatsapp, source="user_panel")
            lead_capture = lead_service.capture(lead_payload, ip_address="", user_agent="user_panel")
            result = _generate_user_games(int(count), int(pool_size), ml_enabled)
            generation_event = save_generation_event(
                lead_id=int(lead_capture.lead["id"]),
                generated_games=result.get("raw_games", result["games"]),
                ml_enabled=ml_enabled,
                seed=int(result["metadata"]["generated_at"].split()[0].replace("-", "")) if result.get("metadata") else 0,
                strategy="ranking_hibrido",
                ranking_score=0.91,
                execution_time_ms=0.0,
                target_contest=None,
                origin="user_panel",
                generation_mode="ranking_hibrido",
                context={
                    "source": "user_panel",
                    "ml_enabled": bool(ml_enabled),
                    "pool_size": int(pool_size),
                },
                first_name=lead_capture.lead["first_name"],
                whatsapp=lead_capture.normalized_whatsapp,
                db_path=USER_DB_PATH,
            )
        except Exception as exc:
            st.error(str(exc))
            _record_event(events, "geracao_falha", str(exc))
            return

        games = result["games"]
        st.success(f"{len(games)} jogos gerados.")
        st.caption(f"Lead: {lead_capture.lead['first_name']} | {lead_capture.normalized_whatsapp}")
        st.caption(f"Indicador: {_user_indicator(games)[0]}")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "ranking": game["ranking"],
                        "jogo": _format_numbers(game["numbers"]),
                        "score": round(game["final_score"], 2),
                    }
                    for game in games
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
        _record_event(events, "geracao", f"{len(games)} jogos")
        st.session_state["user_last_generation"] = {
            **result,
            "lead": lead_capture.lead,
            "lead_normalized_whatsapp": lead_capture.normalized_whatsapp,
            "generation_event_id": int(generation_event["id"]),
        }
        _refresh_institutional_usage_views()


def render_check_page(events: list[dict[str, Any]]) -> None:
    st.header("Conferir Concurso")
    smoke_mode = st.checkbox("Simulacao operacional", value=True)

    if smoke_mode:
        baseline_text = st.text_input(
            "Baseline de fumaça",
            value="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15",
        )
        generation = st.session_state.get("user_last_generation")
        if st.button("Validar baseline", type="primary"):
            try:
                baseline_numbers = _parse_numbers(baseline_text)
                if not generation:
                    raise ValueError("Gere jogos antes de executar a validacao de fumaça.")
                smoke_result = reconcile_smoke_validation(
                    generation_event_id=int(generation["generation_event_id"]),
                    lead_id=int(generation["lead"]["id"]),
                    generated_games=list(generation["raw_games"]),
                    baseline_numbers=baseline_numbers,
                    db_path=USER_DB_PATH,
                )
                save_check_event(
                    lead_id=int(generation["lead"]["id"]),
                    contest_id=0,
                    selected_numbers=baseline_numbers,
                    hits=int(smoke_result["best_hits"]),
                    result_payload=smoke_result,
                    db_path=USER_DB_PATH,
                )
            except Exception as exc:
                st.error(str(exc))
                _record_event(events, "validacao_falha", str(exc))
                return

            st.success(f"Baseline operacional validada com {smoke_result['best_hits']} acertos.")
            st.write("Dezenas baseline:", _format_numbers(smoke_result["baseline_numbers"]))
            st.write("Origem:", smoke_result["source"])
            recon_df = pd.DataFrame(
                [
                    {
                        "jogo": game["game_index"],
                        "dezenas": _format_numbers(game["numbers"]),
                        "acertos": game["hits"],
                        "coincidentes": _format_numbers(game["matched_numbers"]),
                        "status": game["prize_status"],
                        "faixa": game["prize_tier"],
                    }
                    for game in smoke_result["reconciled_games"]
                ]
            )
            st.dataframe(recon_df, hide_index=True, use_container_width=True)
            _record_event(events, "validacao_operacional", f"{smoke_result['best_hits']} acertos")
            st.session_state["user_last_check"] = smoke_result
            _refresh_institutional_usage_views()
        return

    contest_id = st.number_input("Concurso", min_value=1, value=1)
    numbers_text = st.text_input("Dezenas", value="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")

    if st.button("Conferir", type="primary"):
        try:
            numbers = _parse_numbers(numbers_text)
            result = _check_user_contest(int(contest_id), numbers)
            lead_service = _build_lead_service()
            lead_payload = LeadCaptureRequest(first_name=first_name, whatsapp=whatsapp, source="user_panel")
            lead_capture = lead_service.capture(lead_payload, ip_address="", user_agent="user_panel")
            save_check_event(
                lead_id=int(lead_capture.lead["id"]),
                contest_id=int(contest_id),
                selected_numbers=numbers,
                hits=int(result["hits"]),
                result_payload={
                    "contest_id": int(contest_id),
                    "execution_time_ms": 0.0,
                    "source": "user_panel",
                    "user_agent": "user_panel",
                    "correct_numbers": result["correct_numbers"],
                    "selected_numbers": numbers,
                    "hits": int(result["hits"]),
                    "contest": int(result["contest"]),
                },
                db_path=USER_DB_PATH,
            )
        except Exception as exc:
            st.error(str(exc))
            _record_event(events, "conferencia_falha", str(exc))
            return

        st.success(f"{result['hits']} acertos no concurso {result['contest']}.")
        st.write("Dezenas sorteadas:", _format_numbers(result["correct_numbers"]))
        st.write("Dezenas enviadas:", _format_numbers(result["selected_numbers"]))
        _record_event(events, "conferencia", f"concurso {result['contest']} com {result['hits']} acertos")
        st.session_state["user_last_check"] = {
            **result,
            "lead": lead_capture.lead,
            "lead_normalized_whatsapp": lead_capture.normalized_whatsapp,
        }
        _refresh_institutional_usage_views()


def render_history_page(events: list[dict[str, Any]]) -> None:
    st.header("Historico")
    history = _recent_history_dataframe(events)
    if history.empty:
        st.info("Nenhuma execucao registrada ainda.")
    else:
        st.dataframe(history, hide_index=True, use_container_width=True)


def render_reports_page(events: list[dict[str, Any]]) -> None:
    st.header("Relatorios")
    generation = st.session_state.get("user_last_generation")
    check = st.session_state.get("user_last_check")
    report_event_payload = None

    summary_rows = []
    if generation:
        summary_rows.append(
            {
                "tipo": "geracao",
                "quantidade": generation["count"],
                "indicador": _user_indicator(generation["games"])[0],
            }
        )
    if check:
        summary_rows.append(
            {
                "tipo": "conferencia",
                "quantidade": check["hits"],
                "indicador": f"Concurso {check['contest']}",
            }
        )
    summary = pd.DataFrame(summary_rows)
    report_lead = None
    if generation and isinstance(generation.get("lead"), dict):
        report_lead = generation["lead"]
    elif check and isinstance(check.get("lead"), dict):
        report_lead = check["lead"]
    if report_lead:
        report_event_payload = save_report_event(
            lead_id=int(report_lead["id"]),
            generation_event_id=int(generation["generation_event_id"]) if generation and generation.get("generation_event_id") is not None else None,
            report_type="user_report",
            generation_origin="user_panel",
            runtime_origin="user_panel",
            strategy_profile=str(generation["metadata"].get("strategy", "")) if generation and isinstance(generation.get("metadata"), dict) else "",
            payload={
                "summary_rows": summary_rows,
                "has_generation": bool(generation),
                "has_check": bool(check),
                "event_count": len(events),
            },
            db_path=USER_DB_PATH,
        )
    if summary.empty:
        st.info("Nenhum relatorio disponivel ainda.")
    else:
        st.dataframe(summary, hide_index=True, use_container_width=True)

    csv_bytes = summary.to_csv(index=False).encode("utf-8") if not summary.empty else b""
    pdf_bytes = _build_light_report_pdf(
        "Relatorio User",
        [
            f"Total de eventos: {len(events)}",
            f"Ultima geracao: {'sim' if generation else 'nao'}",
            f"Ultima conferencia: {'sim' if check else 'nao'}",
        ],
        summary,
    )

    if csv_bytes:
        st.download_button("Baixar CSV", data=csv_bytes, file_name="lotoia_user_report.csv", mime="text/csv")
    st.download_button("Baixar PDF", data=pdf_bytes, file_name="lotoia_user_report.pdf", mime="application/pdf")
    if report_event_payload:
        st.caption(f"Relatorio institucional persistido: {report_event_payload['id']}")


def main() -> None:
    st.set_page_config(page_title="LotoIA User", page_icon="L", layout="wide")

    sync_summaries = _bootstrap_official_results_sync()
    if sync_summaries and any(summary.get("synced_contests") for summary in sync_summaries):
        latest_synced = sync_summaries[-1]
        contests = latest_synced.get("synced_contests", [])
        if contests:
            st.caption("Resultados oficiais sincronizados: " + ", ".join(str(contest) for contest in contests))

    events = st.session_state.setdefault("user_events", [])
    page = _render_sidebar()

    if page == "Gerar Jogos":
        render_generate_page(events)
    elif page == "Conferir Concurso":
        render_check_page(events)
    elif page == "Historico":
        render_history_page(events)
    elif page == "Relatorios":
        render_reports_page(events)


if __name__ == "__main__":
    main()
