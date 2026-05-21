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
from lotoia.generator.basic_generator import generate_best_games
from lotoia.public.services import LeadCaptureRequest, LeadCaptureService

MAX_GAMES_PER_SESSION = 10
DEFAULT_GAMES_COUNT = 5
DEFAULT_POOL_SIZE = 20
ONLINE_MARKER = "USER PANEL ONLINE"

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


def render_generate_page(events: list[dict[str, Any]]) -> None:
    st.header("Gerar Jogos")
    st.markdown(
        "<div style='font-size:0.78rem; text-transform:uppercase; letter-spacing:0.14em; color:#6b7f93; margin-bottom:0.15rem;'>Geracao assistida</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:1.0rem; font-weight:700; color:#1f2f44; margin:0 0 0.7rem 0;'>LotoIA</div>",
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
        "<div style='font-size:1rem; font-weight:700; color:#1f2f44; margin:0.2rem 0 0.4rem 0;'>LotoIA</div>",
        unsafe_allow_html=True,
    )
    ml_enabled = st.toggle("ML light", value=False)

    if st.button("Gerar", type="primary", disabled=not lead_ready):
        try:
            lead_service = LeadCaptureService()
            lead_payload = LeadCaptureRequest(first_name=first_name, whatsapp=whatsapp, source="user_panel")
            lead_capture = lead_service.capture(lead_payload, ip_address="", user_agent="user_panel")
            result = _generate_user_games(int(count), int(pool_size), ml_enabled)
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
        st.session_state["user_last_generation"] = {**result, "lead": lead_capture.lead, "lead_normalized_whatsapp": lead_capture.normalized_whatsapp}


def render_check_page(events: list[dict[str, Any]]) -> None:
    st.header("Conferir Concurso")
    contest_id = st.number_input("Concurso", min_value=1, value=1)
    numbers_text = st.text_input("Dezenas", value="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")

    if st.button("Conferir", type="primary"):
        try:
            numbers = _parse_numbers(numbers_text)
            result = _check_user_contest(int(contest_id), numbers)
        except Exception as exc:
            st.error(str(exc))
            _record_event(events, "conferencia_falha", str(exc))
            return

        st.success(f"{result['hits']} acertos no concurso {result['contest']}.")
        st.write("Dezenas sorteadas:", _format_numbers(result["correct_numbers"]))
        st.write("Dezenas enviadas:", _format_numbers(result["selected_numbers"]))
        _record_event(events, "conferencia", f"concurso {result['contest']} com {result['hits']} acertos")
        st.session_state["user_last_check"] = result


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


def main() -> None:
    st.set_page_config(page_title="LotoIA User", page_icon="L", layout="wide")

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
