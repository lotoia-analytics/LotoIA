from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lotoia.database import DEFAULT_DATABASE_PATH, ContestRepository, create_database, list_runs
from lotoia.ingestion.result_sync_scheduler import ResultSyncScheduler
from lotoia.ingestion.result_sync_service import ResultSyncService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_basic_analysis_cli() -> None:
    from lotoia.statistics.basic import summarize_draws

    summary = summarize_draws([])
    print("LotoIA - analise inicial")
    print(f"Concursos carregados: {summary['total_draws']}")
    print(f"Dezenas monitoradas: {summary['numbers_tracked']}")


def run_backtest_cli(argv: list[str] | None = None) -> None:
    from lotoia.backtesting import run_backtest

    parser = argparse.ArgumentParser(description="Executa backtesting historico do LotoIA.")
    parser.add_argument("--contests", type=int, default=5, help="Quantidade de concursos analisados.")
    parser.add_argument("--games", type=int, default=5, help="Quantidade de jogos por concurso.")
    parser.add_argument("--pool-size", type=int, default=20, help="Tamanho do pool de candidatos.")
    parser.add_argument("--history-window", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42, help="Seed para geracao reprodutivel.")
    args = parser.parse_args(argv)

    result = run_backtest(
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


def run_benchmark_cli(argv: list[str] | None = None) -> None:
    from lotoia.benchmark import run_benchmark

    parser = argparse.ArgumentParser(description="Executa benchmark cientifico do LotoIA.")
    parser.add_argument("--contests", type=int, default=5)
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--pool-size", type=int, default=20)
    parser.add_argument("--history-window", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/benchmark"))
    args = parser.parse_args(argv)

    result = run_benchmark(
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
        output_dir=args.output_dir,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


def run_dashboard_cli() -> None:
    from streamlit.web import bootstrap

    dashboard_path = PROJECT_ROOT / "dashboard" / "app.py"
    bootstrap.run(
        str(dashboard_path),
        False,
        [],
        {
            "server.port": 8501,
            "server.headless": True,
            "browser.gatherUsageStats": False,
        },
    )


def init_database_cli() -> None:
    create_database()
    print(f"Banco inicializado em {DEFAULT_DATABASE_PATH}")


def show_runs_cli() -> None:
    print(json.dumps(list_runs(), ensure_ascii=False, indent=2, default=str))


def run_weight_calibration_cli(argv: list[str] | None = None) -> None:
    from lotoia.calibration import WeightConfiguration, compare_weight_configurations
    from lotoia.statistics.advanced import FINAL_SCORE_WEIGHTS

    parser = argparse.ArgumentParser(description="Compara configuracoes de pesos do LotoIA.")
    parser.add_argument("--contests", type=int, default=3)
    parser.add_argument("--games", type=int, default=3)
    parser.add_argument("--pool-size", type=int, default=8)
    parser.add_argument("--history-window", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    result = compare_weight_configurations(
        configurations=[_official_configuration(), _balanced_configuration()],
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_reports_cli(argv: list[str] | None = None) -> None:
    from lotoia.backtesting import run_backtest
    from lotoia.calibration import WeightConfiguration, compare_weight_configurations
    from lotoia.reports import generate_backtest_report
    from lotoia.statistics.advanced import FINAL_SCORE_WEIGHTS

    parser = argparse.ArgumentParser(description="Gera relatorios analiticos do LotoIA.")
    parser.add_argument("--contests", type=int, default=3)
    parser.add_argument("--games", type=int, default=3)
    parser.add_argument("--pool-size", type=int, default=8)
    parser.add_argument("--history-window", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    args = parser.parse_args(argv)

    backtest = run_backtest(
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    calibration = compare_weight_configurations(
        [_official_configuration(), _balanced_configuration()],
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    summary = generate_backtest_report(backtest, calibration, args.output_dir)
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))


def run_institutional_analytics_cli(argv: list[str] | None = None) -> None:
    from lotoia.analytics import publish_institutional_analytics

    parser = argparse.ArgumentParser(description="Publica a memoria analitica institucional do LotoIA.")
    parser.add_argument("--report-dir", type=Path, default=Path("reports") / "analytics")
    parser.add_argument(
        "--executive-report-path",
        type=Path,
        default=Path("reports") / "analytics" / "executive_analytical_report.json",
    )
    parser.add_argument(
        "--historical-report-path",
        type=Path,
        default=Path("reports") / "analytics" / "institutional_historical_intelligence.json",
    )
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=Path("reports") / "analytics" / "institutional_analytics_snapshot.json",
    )
    args = parser.parse_args(argv)

    payload = publish_institutional_analytics(
        report_dir=args.report_dir,
        executive_report_path=args.executive_report_path,
        historical_report_path=args.historical_report_path,
        snapshot_path=args.snapshot_path,
    )
    payload = {
        **payload,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_observational_stabilization_cli(argv: list[str] | None = None) -> None:
    from lotoia.observability import persist_observational_stabilization_report

    parser = argparse.ArgumentParser(description="Gera o relatorio de estabilizacao observacional do LotoIA.")
    parser.add_argument("--report-path", type=Path, default=Path("reports") / "observability" / "observational_stabilization.json")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DATABASE_PATH)
    args = parser.parse_args(argv)

    payload = persist_observational_stabilization_report(args.report_path, db_path=args.db_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_result_sync_cli(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sincroniza concursos oficiais da Caixa no LotoIA.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--report-path", type=Path, default=Path("reports") / "ingestion" / "result_sync.json")
    args = parser.parse_args(argv)

    service = ResultSyncService(repository=ContestRepository(args.db_path))
    payload = service.sync_to_report(args.report_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_official_caixa_validation_cli(argv: list[str] | None = None) -> None:
    from lotoia.ingestion.official_caixa_validation import run_official_caixa_validation

    parser = argparse.ArgumentParser(description="Valida deterministicamente o histórico oficial da Caixa contra o banco institucional.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--last-n", type=int, default=100)
    parser.add_argument("--report-dir", type=Path, default=Path("reports") / "institutional_caixa_validation")
    args = parser.parse_args(argv)

    result = run_official_caixa_validation(db_path=args.db_path, last_n=int(args.last_n), report_dir=args.report_dir)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, default=str))


def run_result_sync_scheduler_cli(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Executa o monitor automatico da sincronizacao oficial da Caixa.")
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--stop-after-first-success", action="store_true")
    args = parser.parse_args(argv)

    scheduler = ResultSyncScheduler()
    scheduler.run_forever(
        poll_seconds=args.poll_seconds,
        stop_after_first_success=bool(args.stop_after_first_success),
    )


def run_operational_cleanup_scheduler_cli(argv: list[str] | None = None) -> None:
    from lotoia.scheduling.daily_cleanup_scheduler import DailyOperationalCleanupScheduler

    parser = argparse.ArgumentParser(description="Executa a limpeza operacional diaria da LotoIA.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args(argv)

    scheduler = DailyOperationalCleanupScheduler()
    scheduler.run_forever(poll_seconds=args.poll_seconds)


def run_workflow_scheduler_cli(argv: list[str] | None = None) -> None:
    from lotoia.workflows.workflow_scheduler import WorkflowScheduler

    parser = argparse.ArgumentParser(description="Executa o agendamento institucional de workflows.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--run-once", action="store_true")
    args = parser.parse_args(argv)

    scheduler = WorkflowScheduler()
    if args.run_once:
        payload = scheduler.run_due_workflows()
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    scheduler.run_forever(poll_seconds=args.poll_seconds)


def run_operational_lifecycle_cli(argv: list[str] | None = None) -> None:
    from lotoia.public.operational_lifecycle import OperationalLifecycleEngine

    parser = argparse.ArgumentParser(description="Executa o fechamento operacional completo do LotoIA.")
    parser.add_argument("--contest-id", type=int, required=True)
    parser.add_argument("--generation-event-id", type=int, required=True)
    parser.add_argument("--official-numbers", type=str, required=True, help="Lista separada por virgulas com as dezenas oficiais.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--report-dir", type=Path, default=Path("reports") / "operational")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args(argv)

    engine = OperationalLifecycleEngine(args.db_path)
    official_numbers = [int(part.strip()) for part in args.official_numbers.split(",") if part.strip()]
    with ContestsRepositoryAdapter(args.db_path) as adapter:
        games = adapter.load_generated_games(args.generation_event_id)
        lead_id = adapter.load_lead_id(args.generation_event_id)
    report = engine.close_day(
        contest_id=args.contest_id,
        generated_games=games,
        official_numbers=official_numbers,
        generation_event_id=args.generation_event_id,
        lead_id=lead_id,
        cleanup=bool(args.cleanup),
        report_dir=args.report_dir,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


def run_adaptive_institutional_intelligence_cli(argv: list[str] | None = None) -> None:
    from lotoia.analytics import publish_adaptive_institutional_intelligence

    parser = argparse.ArgumentParser(description="Publica a inteligencia institucional adaptativa do LotoIA.")
    parser.add_argument("--report-dir", type=Path, default=Path("reports") / "analytics")
    parser.add_argument(
        "--memory-path",
        type=Path,
        default=Path("reports") / "analytics" / "adaptive_institutional_memory.json",
    )
    parser.add_argument(
        "--timeline-path",
        type=Path,
        default=Path("reports") / "analytics" / "adaptive_institutional_timeline.json",
    )
    parser.add_argument(
        "--insights-path",
        type=Path,
        default=Path("reports") / "analytics" / "adaptive_institutional_insights.json",
    )
    args = parser.parse_args(argv)

    payload = publish_adaptive_institutional_intelligence(
        report_dir=args.report_dir,
        memory_path=args.memory_path,
        timeline_path=args.timeline_path,
        insights_path=args.insights_path,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _official_configuration() -> WeightConfiguration:
    from lotoia.calibration import WeightConfiguration
    from lotoia.statistics.advanced import FINAL_SCORE_WEIGHTS

    return WeightConfiguration(
        name="official",
        duo=FINAL_SCORE_WEIGHTS["duo_score"],
        terno=FINAL_SCORE_WEIGHTS["terno_score"],
        quadra=FINAL_SCORE_WEIGHTS["quadra_score"],
        quina=FINAL_SCORE_WEIGHTS["quina_score"],
        delay=FINAL_SCORE_WEIGHTS["delay_score"],
        frequency=FINAL_SCORE_WEIGHTS["frequency_score"],
        sum=FINAL_SCORE_WEIGHTS["sum_score"],
        sequence=FINAL_SCORE_WEIGHTS["sequence_score"],
    )


def _balanced_configuration() -> WeightConfiguration:
    from lotoia.calibration import WeightConfiguration

    return WeightConfiguration("balanced_experimental", 12, 16, 20, 18, 12, 10, 6, 6)


class ContestsRepositoryAdapter:
    def __init__(self, db_path: Path) -> None:
        self.repository = ContestRepository(db_path)

    def __enter__(self) -> "ContestsRepositoryAdapter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.repository.connection.close()

    def load_generated_games(self, generation_event_id: int) -> list[dict[str, Any]]:
        cursor = self.repository.connection.cursor()
        rows = cursor.execute(
            """
            SELECT game_index, numbers, profile_type, final_score, quadra_score, context_json, lead_id, target_contest, origin, generation_mode
            FROM generated_games
            WHERE generation_event_id = ?
            ORDER BY game_index
            """,
            (generation_event_id,),
        ).fetchall()
        games: list[dict[str, Any]] = []
        for row in rows:
            numbers_raw = row[1]
            try:
                parsed_numbers = json.loads(numbers_raw) if numbers_raw else []
            except Exception:
                parsed_numbers = [int(number) for number in str(numbers_raw).split(",") if str(number).strip()]
            games.append(
                {
                    "game_index": row[0],
                    "numbers": [int(number) for number in parsed_numbers],
                    "profile_type": row[2],
                    "final_score": json.loads(row[3] or "{}"),
                    "quadra_score": json.loads(row[4] or "{}"),
                    "context_json": json.loads(row[5] or "{}"),
                    "lead_id": row[6],
                    "target_contest": row[7],
                    "origin": row[8],
                    "generation_mode": row[9],
                }
            )
        return games

    def load_lead_id(self, generation_event_id: int) -> int | None:
        cursor = self.repository.connection.cursor()
        row = cursor.execute(
            """
            SELECT lead_id
            FROM generated_games
            WHERE generation_event_id = ?
            ORDER BY game_index
            LIMIT 1
            """,
            (generation_event_id,),
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else None
