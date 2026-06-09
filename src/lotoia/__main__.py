from __future__ import annotations

import argparse

from lotoia import cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Ferramentas oficiais do LotoIA.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("reports", help="Gera relatorios analiticos.")
    subparsers.add_parser("institutional-analytics", help="Publica a memoria analitica institucional.")
    subparsers.add_parser("adaptive-intelligence", help="Publica a inteligencia institucional adaptativa.")
    subparsers.add_parser("observational-stabilization", help="Gera o relatorio de estabilizacao observacional.")
    subparsers.add_parser("result-sync", help="Sincroniza concursos oficiais da Caixa.")
    subparsers.add_parser("official-caixa-validation", help="Valida o historico oficial da Caixa contra o banco institucional.")
    subparsers.add_parser("result-sync-scheduler", help="Monitora automatico da sincronizacao oficial da Caixa.")
    subparsers.add_parser("operational-cleanup-scheduler", help="Executa a limpeza operacional diaria.")
    subparsers.add_parser("workflow-scheduler", help="Executa o agendamento institucional de workflows.")
    subparsers.add_parser("operational-lifecycle", help="Executa o fechamento operacional completo.")
    subparsers.add_parser("backtest", help="Executa backtesting historico.")
    subparsers.add_parser("benchmark", help="Executa benchmark cientifico.")
    subparsers.add_parser("dashboard", help="Inicia o dashboard Streamlit.")

    args, remaining = parser.parse_known_args()

    if args.command == "reports":
        cli.run_reports_cli(remaining)
    elif args.command == "institutional-analytics":
        cli.run_institutional_analytics_cli(remaining)
    elif args.command == "adaptive-intelligence":
        cli.run_adaptive_institutional_intelligence_cli(remaining)
    elif args.command == "observational-stabilization":
        cli.run_observational_stabilization_cli(remaining)
    elif args.command == "result-sync":
        cli.run_result_sync_cli(remaining)
    elif args.command == "official-caixa-validation":
        cli.run_official_caixa_validation_cli(remaining)
    elif args.command == "result-sync-scheduler":
        cli.run_result_sync_scheduler_cli(remaining)
    elif args.command == "operational-cleanup-scheduler":
        cli.run_operational_cleanup_scheduler_cli(remaining)
    elif args.command == "workflow-scheduler":
        cli.run_workflow_scheduler_cli(remaining)
    elif args.command == "operational-lifecycle":
        cli.run_operational_lifecycle_cli(remaining)
    elif args.command == "backtest":
        cli.run_backtest_cli(remaining)
    elif args.command == "benchmark":
        cli.run_benchmark_cli(remaining)
    elif args.command == "dashboard":
        cli.run_dashboard_cli()
    else:
        parser.error(f"Comando desconhecido: {args.command}")


if __name__ == "__main__":
    main()
