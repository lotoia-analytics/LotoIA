# -*- coding: utf-8 -*-
from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

import json
import os
import random
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text

from lotoia.database.adapter import InstitutionalDatabaseAdapter
from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, ImportedContest, ReconciliationGame, ReconciliationRun, create_database, get_engine, get_session
from lotoia.experiments.hb_geometry_audit import DEFAULT_HB_GEOMETRY_DIR, run_hb_geometry_audit
from lotoia.generator.engine import generate_ranked_games


BUILD_MARKER = "institutional-clean-runtime-v1"
APP_BUILD = BUILD_MARKER
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.png"
HB_GEOMETRY_DIR = Path(os.fspath(DEFAULT_HB_GEOMETRY_DIR))
HB_GEOMETRY_PROGRESS_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.progress.json"
HB_GEOMETRY_JSON_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.json"
HB_GEOMETRY_CSV_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.csv"
DB_PATH = DEFAULT_DATABASE_PATH

_JOB_LOCK = threading.Lock()
_JOB_STATE: dict[str, Any] = {
    "running": False,
    "completed": False,
    "current_scenario": "-",
    "processed_batches": 0,
    "contests_processed": 0,
    "elapsed_time": 0.0,
    "error": "",
    "result": None,
    "started_at": None,
}


def _safe_json_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_csv_load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _mask_database_url(database_url: str) -> str:
    text = str(database_url or "").strip()
    if not text:
        return "-"
    if "@" not in text:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    scheme, remainder = text.split("://", maxsplit=1) if "://" in text else ("", text)
    if "@" not in remainder:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    credentials, host_part = remainder.split("@", maxsplit=1)
    if ":" in credentials:
        username = credentials.split(":", maxsplit=1)[0]
        masked_credentials = f"{username}:***"
    else:
        masked_credentials = "***"
    prefix = f"{scheme}://" if scheme else ""
    return f"{prefix}{masked_credentials}@{host_part}"


def _apply_institutional_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.0rem; padding-bottom: 2rem; max-width: 100%; }
        section[data-testid="stMain"] > div.block-container {
            max-width: 100%;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
        }
        .stApp { background: linear-gradient(180deg, #fbfdff 0%, #f2f6fb 100%); }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f7fbff 0%, #eef4fa 100%);
            border-right: 1px solid rgba(18, 52, 86, 0.10);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.9rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        section[data-testid="stSidebar"] img {
            width: 92% !important;
            max-width: 340px !important;
            display: block;
            margin: 0 auto 0.4rem auto;
        }
        .lotoia-sidebar-divider {
            border-top: 1px solid rgba(18, 52, 86, 0.14);
            margin: 0.85rem 0;
        }
        .lotoia-nav-hint {
            font-size: 0.74rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #7a8795;
            margin-bottom: 0.65rem;
        }
        .lotoia-section-title {
            font-size: 1.7rem;
            font-weight: 800;
            color: #123456;
            margin-bottom: 0.2rem;
            letter-spacing: 0.01em;
        }
        .lotoia-section-subtitle {
            font-size: 0.92rem;
            color: #5a6b7e;
            margin-bottom: 1rem;
            line-height: 1.5;
        }
        .lotoia-kpi-card {
            background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 16px;
            padding: 0.95rem 1rem 0.85rem 1rem;
            box-shadow: 0 6px 22px rgba(18, 52, 86, 0.05);
            min-height: 114px;
        }
        .lotoia-kpi-label {
            color: #5a6b7e;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.35rem;
        }
        .lotoia-kpi-value {
            color: #123456;
            font-size: 1.72rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.3rem;
        }
        .lotoia-kpi-caption {
            color: #718399;
            font-size: 0.8rem;
            line-height: 1.4;
        }
        .lotoia-operational-hint {
            color: #6d7f92;
            font-size: 0.86rem;
            margin-top: -0.15rem;
            margin-bottom: 0.5rem;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 14px;
            padding: 0.85rem 0.95rem;
            box-shadow: 0 4px 14px rgba(18, 52, 86, 0.04);
        }
        div[data-testid="stMetric"] label {
            color: #5a6b7e;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        div[data-testid="stMetric"] [data-testid="metric-container"] {
            gap: 0.2rem;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #123456;
            font-weight: 800;
        }
        section[data-testid="stMain"] .stButton > button {
            border-radius: 12px;
            border: 1px solid rgba(18, 52, 86, 0.12);
            background: #ffffff;
            color: #123456;
            min-height: 44px;
            font-weight: 700;
            box-shadow: 0 3px 10px rgba(18, 52, 86, 0.04);
        }
        section[data-testid="stMain"] .stButton > button:hover {
            border-color: rgba(18, 52, 86, 0.20);
            background: #f8fbff;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, #ff6666 0%, #ff4d4d 100%);
            color: #ffffff;
            border-color: rgba(255, 77, 77, 0.35);
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"]:hover {
            background: linear-gradient(180deg, #ff7777 0%, #ff5f5f 100%);
            color: #ffffff;
        }
        .lotoia-table-wrap {
            padding-top: 0.15rem;
            padding-bottom: 0.15rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_logo() -> None:
    try:
        if LOGO_PATH.exists():
            st.sidebar.image(str(LOGO_PATH), use_container_width=True)
    except Exception:
        st.sidebar.markdown(
            '<div style="font-weight:900;color:#123456;text-align:center;font-size:1.1rem;letter-spacing:0.12em;margin-bottom:0.4rem;">LotoIA</div>',
            unsafe_allow_html=True,
        )


@st.cache_resource(show_spinner=False)
def _get_engine_cached():
    return get_engine(DB_PATH)


def _database_snapshot() -> dict[str, Any]:
    adapter = InstitutionalDatabaseAdapter(DB_PATH)
    engine = _get_engine_cached()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    preferred_tables = [
        "generation_events",
        "generated_games",
        "reconciliation_runs",
        "reconciliation_games",
        "reconciliation_events",
        "imported_contests",
        "expansion_events",
        "operational_logs",
    ]
    latest_fields = {
        "generation_events": "created_at",
        "generated_games": "created_at",
        "reconciliation_runs": "created_at",
        "reconciliation_games": "created_at",
        "reconciliation_events": "created_at",
        "imported_contests": "contest_number",
        "expansion_events": "created_at",
        "operational_logs": "created_at",
    }
    counts: dict[str, int] = {}
    latest: dict[str, Any] = {}
    with engine.begin() as connection:
        for table in preferred_tables:
            if table not in table_names:
                counts[table] = 0
                latest[table] = "-"
                continue
            try:
                counts[table] = int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0)
            except Exception:
                counts[table] = 0
            latest_field = latest_fields.get(table, "created_at")
            if latest_field in {"created_at", "contest_number"}:
                try:
                    value = connection.execute(text(f'SELECT MAX("{latest_field}") FROM "{table}"')).scalar()
                    latest[table] = value if value is not None else "-"
                except Exception:
                    latest[table] = "-"
            else:
                latest[table] = "-"
    return {
        "backend": adapter.backend,
        "database_url": adapter.database_url,
        "database_source": adapter.database_source,
        "counts": counts,
        "latest": latest,
        "tables": sorted(table_names),
    }


def _hb_geometry_state() -> dict[str, Any]:
    with _JOB_LOCK:
        state = dict(_JOB_STATE)
    progress = _safe_json_load(HB_GEOMETRY_PROGRESS_FILE)
    report = _safe_json_load(HB_GEOMETRY_JSON_FILE)
    csv_frame = _safe_csv_load(HB_GEOMETRY_CSV_FILE)
    summary = report.get("summary") or progress.get("summary") or {}
    return {
        "job": state,
        "progress": progress,
        "report": report,
        "summary": summary,
        "csv_frame": csv_frame,
    }


def _load_latest_imported_contest() -> dict[str, Any] | None:
    with get_session(DB_PATH) as session:
        row = session.query(ImportedContest).order_by(ImportedContest.contest_number.desc()).first()
        if row is None:
            return None
        dezenas = [int(number) for number in str(row.dezenas or "").replace(",", " ").split() if str(number).isdigit()]
        return {
            "contest_number": int(row.contest_number),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            "data": str(row.data or ""),
            "dezenas": dezenas,
            "metadata_json": str(row.metadata_json or "{}"),
        }


def _build_simulated_draw(size: int = 15) -> list[int]:
    return sorted(random.sample(range(1, 26), k=max(1, min(size, 25))))


def _run_institutional_generation(*, total_games: int, snapshot: dict[str, Any]) -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:gerar_jogos"
    started = time.monotonic()
    seed = int(time.time()) % 1_000_000
    target_contest = snapshot["latest"].get("imported_contests", "-")
    games = generate_ranked_games(total_games=total_games, seed=seed, ml_enabled=False)
    generation_snapshot = _persist_generation_snapshot(
        games=games,
        seed=seed,
        target_contest=int(target_contest) if str(target_contest).isdigit() else None,
    )
    st.session_state["institutional_generation"] = {
        "seed": seed,
        "games": games,
        "total_games": total_games,
        "generation_event_id": generation_snapshot["generation_event_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "runtime_status": "generated",
        "elapsed_time": round(time.monotonic() - started, 3),
    }
    st.session_state["institutional_generation_result"] = {
        "generation_event_id": generation_snapshot["generation_event_id"],
        "seed": seed,
        "jogos": games,
    }


def _run_institutional_conference() -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:conferir_jogos"
    latest_contest = _load_latest_imported_contest()
    generation_state = st.session_state.get("institutional_generation") or {}
    if not generation_state.get("games"):
        st.session_state["institutional_check_result"] = {"warning": "Gere jogos antes de conferir."}
        return
    if latest_contest is None:
        st.session_state["institutional_check_result"] = {
            "warning": "imported_contests ainda está vazio. Sincronize o resultado oficial para habilitar a conferência automática."
        }
        return
    comparison = _compare_games_against_contest(
        generation_event_id=int(generation_state.get("generation_event_id") or 0),
        games=list(generation_state.get("games") or []),
        contest=latest_contest,
    )
    st.session_state["institutional_check"] = {
        "runtime_status": "checked",
        "timestamp": datetime.now(UTC).isoformat(),
        "contest_number": comparison["contest_number"],
        "best_hits": comparison["best_hits"],
        "total_hits": comparison["total_hits"],
    }
    st.session_state["institutional_check_result"] = comparison


def _run_institutional_simulation() -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
    generation_state = st.session_state.get("institutional_generation") or {}
    simulated_numbers = _build_simulated_draw(15)
    games = list(generation_state.get("games") or [])
    simulation_rows: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        numbers = sorted(int(number) for number in game.get("numbers", []))
        matched = sorted(set(numbers) & set(simulated_numbers))
        simulation_rows.append(
            {
                "jogo": index,
                "dezenas": " ".join(f"{number:02d}" for number in numbers),
                "hits": len(matched),
                "premiado": "sim" if len(matched) >= 11 else "nao",
            }
        )
    st.session_state["institutional_simulation"] = {
        "runtime_status": "simulated",
        "timestamp": datetime.now(UTC).isoformat(),
        "contest_numbers": simulated_numbers,
        "results": simulation_rows,
    }
    st.session_state["institutional_simulation_result"] = simulation_rows


def _persist_generation_snapshot(*, games: list[dict[str, Any]], seed: int, target_contest: int | None) -> dict[str, Any]:
    started_at = time.monotonic()
    with get_session(DB_PATH) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=games,
            ml_enabled=0,
            seed=seed,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
        )
        session.add(event)
        session.flush()
        generation_event_id = int(event.id)
        for index, game in enumerate(games, start=1):
            session.add(
                GeneratedGame(
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    target_contest=target_contest,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=index,
                    numbers=list(game.get("numbers", [])),
                    profile_type=str(game.get("profile_type", "")),
                    final_score=dict(game.get("final_score", {})) if isinstance(game.get("final_score"), dict) else {},
                    quadra_score=dict(game.get("quadra_score", {})) if isinstance(game.get("quadra_score"), dict) else {},
                    context_json={
                        "source": "institutional_app",
                        "target_contest": target_contest,
                        "build_marker": BUILD_MARKER,
                    },
                )
            )
        event.execution_time_ms = round((time.monotonic() - started_at) * 1000, 2)
        session.commit()
        return {
            "generation_event_id": generation_event_id,
            "seed": seed,
            "games_count": len(games),
            "target_contest": target_contest,
        }


def _compare_games_against_contest(*, generation_event_id: int, games: list[dict[str, Any]], contest: dict[str, Any]) -> dict[str, Any]:
    official_numbers = sorted(int(number) for number in contest.get("dezenas", []))
    results: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        numbers = sorted(int(number) for number in game.get("numbers", []))
        matched = sorted(set(numbers) & set(official_numbers))
        results.append(
            {
                "game_index": index,
                "numbers": numbers,
                "hits": len(matched),
                "matched_numbers": matched,
                "prize_status": "premiado" if len(matched) >= 11 else "nao_premiado",
                "prize_tier": f"faixa_{len(matched)}" if len(matched) >= 11 else "",
            }
        )
    best_hits = max((int(row["hits"]) for row in results), default=0)
    total_hits = sum(int(row["hits"]) for row in results)
    prize_count = sum(1 for row in results if int(row["hits"]) >= 11)
    with get_session(DB_PATH) as session:
        run = ReconciliationRun(
            generation_event_id=generation_event_id,
            lead_id=None,
            contest_id=int(contest["contest_number"]),
            source="institutional",
            status="reconciled" if results else "sem_jogos",
            prize_count=prize_count,
            total_hits=total_hits,
            best_hits=best_hits,
            payload={
                "source": "institutional",
                "contest_id": int(contest["contest_number"]),
                "best_hits": best_hits,
                "total_hits": total_hits,
                "prize_count": prize_count,
            },
        )
        session.add(run)
        session.flush()
        for game in results:
            session.add(
                ReconciliationGame(
                    reconciliation_run_id=run.id,
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    contest_id=int(contest["contest_number"]),
                    game_index=int(game["game_index"]),
                    numbers=list(game["numbers"]),
                    hits=int(game["hits"]),
                    matched_numbers=list(game["matched_numbers"]),
                    prize_status=str(game["prize_status"]),
                    prize_tier=str(game["prize_tier"]),
                    context_json={"source": "institutional", "build_marker": BUILD_MARKER},
                )
            )
        session.commit()
    return {
        "contest_number": int(contest["contest_number"]),
        "contest_date": str(contest.get("data", "")),
        "official_numbers": official_numbers,
        "results": results,
        "best_hits": best_hits,
        "total_hits": total_hits,
        "prize_count": prize_count,
        "reconciliation": {"id": int(run.id), "contest_id": int(contest["contest_number"])},
    }


def _start_hb_geometry_job(*, resume: bool) -> None:
    def _runner() -> None:
        started_at = time.monotonic()
        with _JOB_LOCK:
            _JOB_STATE.update(
                {
                    "running": True,
                    "completed": False,
                    "error": "",
                    "started_at": started_at,
                }
            )
        try:
            result = run_hb_geometry_audit(
                contests_analyzed=30,
                games_count=5,
                pool_size=18,
                history_window=200,
                batch_size=5,
                lightweight=True,
                resume=resume,
                max_batches_per_run=1,
                output_dir=HB_GEOMETRY_DIR,
            )
            with _JOB_LOCK:
                _JOB_STATE.update(
                    {
                        "running": False,
                        "completed": bool(result.completed),
                        "current_scenario": str(result.scenarios[0]["scenario"]) if result.scenarios else "-",
                        "processed_batches": int(result.processed_batches),
                        "contests_processed": int(result.contests_analyzed),
                        "elapsed_time": float(time.monotonic() - started_at),
                        "error": "",
                        "result": result.to_dict(),
                    }
                )
        except Exception as exc:  # pragma: no cover
            with _JOB_LOCK:
                _JOB_STATE.update(
                    {
                        "running": False,
                        "completed": False,
                        "error": str(exc),
                        "elapsed_time": float(time.monotonic() - started_at),
                    }
                )

    thread = threading.Thread(target=_runner, daemon=True, name="hb-geometry-audit")
    thread.start()


def _reset_hb_geometry_job() -> None:
    for path in (HB_GEOMETRY_JSON_FILE, HB_GEOMETRY_CSV_FILE, HB_GEOMETRY_PROGRESS_FILE):
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
    with _JOB_LOCK:
        _JOB_STATE.update(
            {
                "running": False,
                "completed": False,
                "current_scenario": "-",
                "processed_batches": 0,
                "contests_processed": 0,
                "elapsed_time": 0.0,
                "error": "",
                "result": None,
                "started_at": None,
            }
        )


def _render_sidebar(page: str, snapshot: dict[str, Any]) -> str:
    _apply_institutional_styles()
    _render_sidebar_logo()
    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-nav-hint">Navegação</div>', unsafe_allow_html=True)
    st.sidebar.title("LotoIA")
    st.sidebar.caption(f"build={APP_BUILD}")
    st.sidebar.caption("Painel institucional limpo")
    choice = st.sidebar.radio("Navegação", ["Operacional", "Analítico", "HB Geometry"], index=["Operacional", "Analítico", "HB Geometry"].index(page))
    st.sidebar.divider()
    st.sidebar.caption("DATABASE_URL conectada")
    if page == "Operacional":
        st.sidebar.markdown("**Operações**")
        total_games = int(st.sidebar.selectbox("Quantidade de jogos", [15, 16, 17, 18], index=0, key="institutional_total_games"))
        if st.sidebar.button("Gerar Jogos", type="primary", use_container_width=True):
            _run_institutional_generation(total_games=total_games, snapshot=snapshot)
            st.rerun()
        if st.sidebar.button("Conferir Jogos", use_container_width=True):
            _run_institutional_conference()
            st.rerun()
        if st.sidebar.button("Simular Resultado", use_container_width=True):
            _run_institutional_simulation()
            st.rerun()
        st.sidebar.markdown("**Cobertura estrutural**")
        if st.sidebar.button("Gerador LotoIA", use_container_width=True):
            st.session_state["institutional_last_ui_event"] = "operacional:gerador_lotoia"
            st.rerun()
        if st.sidebar.button("Históricos Institucional", use_container_width=True):
            st.session_state["institutional_last_ui_event"] = "operacional:historicos_institucional"
            st.rerun()
        if st.sidebar.button("Memória Analítica", use_container_width=True):
            st.session_state["institutional_last_ui_event"] = "operacional:memoria_analitica"
            st.rerun()
    return choice


def _ensure_institutional_schema() -> None:
    create_database(DB_PATH)


def _render_operational_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Operacional")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[4].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))

    top_cols = st.columns([1.3, 1.3, 1.8])
    top_cols[0].caption(f"Concurso alvo: {snapshot['latest'].get('imported_contests', '-')}")
    top_cols[1].caption("Cada jogo mantém 15 dezenas da Lotofácil.")
    top_cols[2].caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")

    st.markdown("#### Motor de geração")
    gen_cols = st.columns([1.25, 1.25, 1.5])
    generation_state = st.session_state.get("institutional_generation") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    if generation_result:
        st.success(
            f"Geração concluída. generation_event_id={generation_result.get('generation_event_id', '-')} | jogos={len(generation_result.get('jogos') or [])} | seed={generation_result.get('seed', '-')}"
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_result.get("jogos") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    elif generation_state.get("games"):
        st.info("Última geração carregada. Use a sidebar para gerar, conferir ou simular novamente.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_state.get("games") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("Use a barra lateral para acionar geração, conferência e simulação.")

    st.markdown("#### Cobertura estrutural")
    cover_result = st.session_state.get("institutional_simulation_result")
    if cover_result:
        st.dataframe(pd.DataFrame(cover_result), hide_index=True, use_container_width=True)

    check_result = st.session_state.get("institutional_check_result")
    if isinstance(check_result, dict) and check_result.get("results"):
        st.markdown("#### Conferência")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "jogo": row["game_index"],
                        "dezenas": " ".join(f"{number:02d}" for number in row["numbers"]),
                        "hits": row["hits"],
                        "premiado": row["prize_status"],
                    }
                    for row in check_result["results"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    summary_cols = st.columns(4)
    summary_cols[0].metric("último evento", st.session_state.get("institutional_last_ui_event", "-"))
    summary_cols[1].metric("runtime", st.session_state.get("institutional_generation", {}).get("runtime_status", "idle"))
    summary_cols[2].metric("simulação", st.session_state.get("institutional_simulation", {}).get("runtime_status", "-"))
    summary_cols[3].metric("timestamp", datetime.now(UTC).strftime("%H:%M:%S"))


def _render_analytical_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Analítico")
    st.write("Snapshot institucional do banco atual via DATABASE_URL.")
    diag_cols = st.columns(3)
    diag_cols[0].metric("backend", snapshot["backend"])
    diag_cols[1].metric("database_source", snapshot["database_source"])
    diag_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    st.caption(f"database_url: {_mask_database_url(snapshot['database_url'])}")
    table_rows = []
    for table, count in snapshot["counts"].items():
        table_rows.append(
            {
                "tabela": table,
                "contagem": int(count),
                "ultima_persistencia": snapshot["latest"].get(table, "-"),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)


def _render_hb_geometry_page(state: dict[str, Any]) -> None:
    st.subheader("HB Geometry")
    st.write("Auditoria incremental isolada do motor oficial.")
    job = state["job"]
    progress = state["progress"]
    summary = state["summary"]
    csv_frame = state["csv_frame"]
    button_cols = st.columns(3)
    if button_cols[0].button("Iniciar Auditoria", type="primary", use_container_width=True, disabled=bool(job.get("running"))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:iniciar"
        _start_hb_geometry_job(resume=bool(progress) and not bool(progress.get("completed", False)))
        st.rerun()
    if button_cols[1].button("Continuar Auditoria", use_container_width=True, disabled=bool(job.get("running")) or not bool(progress) or bool(progress.get("completed", False))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:continuar"
        _start_hb_geometry_job(resume=True)
        st.rerun()
    if button_cols[2].button("Resetar Auditoria", use_container_width=True, disabled=bool(job.get("running"))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:resetar"
        _reset_hb_geometry_job()
        st.rerun()
    status_cols = st.columns(4)
    status_cols[0].metric("contests_processed", int(job.get("contests_processed", 0)))
    status_cols[1].metric("processed_batches", int(job.get("processed_batches", 0)))
    status_cols[2].metric("completed", "sim" if bool(job.get("completed")) else "não")
    status_cols[3].metric("elapsed_time", f"{float(job.get('elapsed_time', 0.0)):.1f}s")
    st.caption(f"current_scenario: {job.get('current_scenario', '-')}")
    if job.get("error"):
        st.error(f"HB Geometry error: {job['error']}")
    if progress:
        st.info(
            " | ".join(
                [
                    f"checkpoint={HB_GEOMETRY_PROGRESS_FILE.name}",
                    f"resume={'true' if bool(progress) and not bool(progress.get('completed', False)) else 'false'}",
                    f"last_contest={progress.get('last_contest', '-')}",
                    f"current_batch={progress.get('current_batch', '-')}",
                ]
            )
        )
    if summary:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Métrica": "avg_hits", "Valor": round(float(summary.get("hb_baseline", {}).get("average_hits", 0.0)), 4)},
                    {"Métrica": "11+", "Valor": int(summary.get("hb_baseline", {}).get("hits_11_plus", 0))},
                    {"Métrica": "12+", "Valor": int(summary.get("hb_baseline", {}).get("hits_12_plus", 0))},
                    {"Métrica": "overlap", "Valor": round(float(summary.get("hb_baseline", {}).get("average_overlap", 0.0)), 4)},
                    {"Métrica": "entropy", "Valor": round(float(summary.get("hb_baseline", {}).get("entropy", 0.0)), 4)},
                    {
                        "Métrica": "dominant_numbers",
                        "Valor": ", ".join(
                            f"{item['number']}:{item['frequency']}" for item in summary.get("hb_baseline", {}).get("dominant_numbers", [])[:5]
                        )
                        or "-",
                    },
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    if not csv_frame.empty:
        with st.expander("CSV consolidado", expanded=False):
            st.dataframe(csv_frame.tail(20), hide_index=True, use_container_width=True)
    st.caption(f"json: {HB_GEOMETRY_JSON_FILE} | csv: {HB_GEOMETRY_CSV_FILE} | progress: {HB_GEOMETRY_PROGRESS_FILE}")


def main() -> None:
    st.set_page_config(page_title="LotoIA Institucional", page_icon="🧭", layout="wide")
    _ensure_institutional_schema()
    snapshot = _database_snapshot()
    page = _render_sidebar(st.session_state.get("institutional_page", "Operacional"), snapshot)
    st.session_state["institutional_page"] = page
    st.title("LotoIA Institucional")
    st.success(BUILD_MARKER)
    st.caption("Painel mínimo, isolado e pronto para o runtime novo.")
    if page == "Operacional":
        _render_operational_page(snapshot)
    elif page == "Analítico":
        _render_analytical_page(snapshot)
    else:
        _render_hb_geometry_page(_hb_geometry_state())


if __name__ == "__main__":
    main()
