from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .scientific_governance import (
    BENCHMARK_EXPANSION,
    BENCHMARK_RANDOM,
    BENCHMARK_RANKING_HYBRID,
    BENCHMARK_SCORE_ML,
    BENCHMARK_STATISTICAL_BASELINE,
    DATASET_BENCHMARK,
    DATASET_EXPANSION,
    DATASET_ML,
    DATASET_OPERATIONAL,
    DATASET_VALIDATION,
    SCIENTIFIC_OBSERVABILITY_METRICS,
)
from .temporal_history_registry import (
    TEMPORAL_HISTORY_BENCHMARK,
    TEMPORAL_HISTORY_CONFERENCE,
    TEMPORAL_HISTORY_EXPANSION,
    TEMPORAL_HISTORY_ML,
    TEMPORAL_HISTORY_OPERATIONS,
    TEMPORAL_HISTORY_VALIDATION,
)
from .temporal_scientific_governance import (
    TEMPORAL_BENCHMARK_STRATEGIES,
    TEMPORAL_OPERATIONAL_NUCLEI,
    TEMPORAL_RUNTIME_INTEGRITY_METRICS,
)

SCIENTIFIC_NUCLEI_REGISTRY_VERSION = "0.1.0"
SCIENTIFIC_NUCLEI_REGISTRY_STATUS = "scientific_nuclei_consolidation_active"

CORE_NUCLEI = (
    "geracao_jogos",
    "backtesting",
    "benchmark_cientifico",
    "ml_intelligence",
    "estatisticas_historicas",
    "relatorios",
)

SCIENTIFIC_MODE_SECTIONS = {
    "operacional": (
        {
            "title": "Motor de geração",
            "description": "Geração operacional, conferência e memória institucional.",
            "pages": ("geracao_jogos", "conferir_jogos", "reconciliacao_operacional"),
        },
        {
            "title": "Cobertura estrutural",
            "description": "Cobertura probabilística e leitura analítica do acervo.",
            "pages": ("estatisticas_historicas", "historical_intelligence"),
        },
    ),
    "analitico": (
        {
            "title": "Validação temporal",
            "description": "Walk-forward, benchmark e leitura científica supervisionada.",
            "pages": ("backtesting", "benchmark_cientifico", "ml_intelligence"),
        },
        {
            "title": "Histórico e persistência",
            "description": "Artefatos científicos, observabilidade e governança.",
            "pages": ("relatorios", "ml_governance", "observability", "workflows", "historico_experimental", "calibracao_experimental", "reports_engine"),
        },
    ),
}

__all__ = [
    "SCIENTIFIC_NUCLEI_REGISTRY_VERSION",
    "SCIENTIFIC_NUCLEI_REGISTRY_STATUS",
    "CORE_NUCLEI",
    "SCIENTIFIC_MODE_SECTIONS",
    "ScientificNucleus",
    "ScientificNucleusSection",
    "ScientificNucleiRegistry",
    "ScientificNucleiValidationReport",
    "build_scientific_nuclei_registry",
    "validate_scientific_nuclei_registry",
]


@dataclass(frozen=True, slots=True)
class ScientificNucleus:
    nucleus_id: str
    page_id: str
    display_name: str
    scientific_finality: str
    persistence_artifact: str
    temporal_contract: str
    validation_mode: str
    visual_identity: str
    runtime_scope: str
    source_tables: tuple[str, ...]
    score_ml_ready: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "nucleus_id": self.nucleus_id,
            "page_id": self.page_id,
            "display_name": self.display_name,
            "scientific_finality": self.scientific_finality,
            "persistence_artifact": self.persistence_artifact,
            "temporal_contract": self.temporal_contract,
            "validation_mode": self.validation_mode,
            "visual_identity": self.visual_identity,
            "runtime_scope": self.runtime_scope,
            "source_tables": self.source_tables,
            "score_ml_ready": self.score_ml_ready,
        }


@dataclass(frozen=True, slots=True)
class ScientificNucleusSection:
    mode: str
    title: str
    description: str
    pages: tuple[str, ...]
    visual_identity: str

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "title": self.title,
            "description": self.description,
            "pages": self.pages,
            "visual_identity": self.visual_identity,
        }


@dataclass(frozen=True, slots=True)
class ScientificNucleiRegistry:
    registry_version: str
    status: str
    nuclei: tuple[ScientificNucleus, ...]
    mode_sections: dict[str, tuple[ScientificNucleusSection, ...]]
    page_labels: dict[str, str]
    page_audit_matrix: dict[str, dict[str, str]]
    score_ml_contract_ready: bool
    runtime_stability_ready: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "registry_version": self.registry_version,
            "status": self.status,
            "nuclei": [nucleus.as_dict() for nucleus in self.nuclei],
            "mode_sections": {
                mode: [section.as_dict() for section in sections]
                for mode, sections in self.mode_sections.items()
            },
            "page_labels": self.page_labels,
            "page_audit_matrix": self.page_audit_matrix,
            "score_ml_contract_ready": self.score_ml_contract_ready,
            "runtime_stability_ready": self.runtime_stability_ready,
        }

    @property
    def page_ids(self) -> tuple[str, ...]:
        return tuple(self.page_labels.keys())

    def sections_for_mode(self, mode: str) -> tuple[ScientificNucleusSection, ...]:
        return self.mode_sections.get(mode, ())


@dataclass(frozen=True, slots=True)
class ScientificNucleiValidationReport:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def assert_valid(self) -> None:
        if not self.valid:
            raise ValueError("; ".join(self.errors))


def build_scientific_nuclei_registry() -> ScientificNucleiRegistry:
    nuclei = (
        ScientificNucleus(
            nucleus_id="geracao_jogos",
            page_id="geracao_jogos",
            display_name="Gerar Jogos",
            scientific_finality="geracao operacional",
            persistence_artifact=TEMPORAL_HISTORY_OPERATIONS,
            temporal_contract="operation_only",
            validation_mode="operational_runtime",
            visual_identity="operational_core",
            runtime_scope="public_runtime",
            source_tables=("generation_events", "generated_games"),
        ),
        ScientificNucleus(
            nucleus_id="backtesting",
            page_id="backtesting",
            display_name="Testar Estratégia",
            scientific_finality="walk-forward",
            persistence_artifact=TEMPORAL_HISTORY_VALIDATION,
            temporal_contract="strict_train_before_test",
            validation_mode="walk_forward_validation",
            visual_identity="validation_engine",
            runtime_scope="scientific_runtime",
            source_tables=("imported_contests", "benchmark_runs", "backtest_runs"),
        ),
        ScientificNucleus(
            nucleus_id="benchmark_cientifico",
            page_id="benchmark_cientifico",
            display_name="Comparativos",
            scientific_finality="benchmark temporal",
            persistence_artifact=TEMPORAL_HISTORY_BENCHMARK,
            temporal_contract="future_relative_only",
            validation_mode="temporal_benchmark",
            visual_identity="benchmark_engine",
            runtime_scope="scientific_runtime",
            source_tables=("benchmark_runs", "backtest_runs"),
        ),
        ScientificNucleus(
            nucleus_id="ml_intelligence",
            page_id="ml_intelligence",
            display_name="Ranking ML",
            scientific_finality="reranking supervisionado",
            persistence_artifact=TEMPORAL_HISTORY_ML,
            temporal_contract="feature_cutoff_before_label",
            validation_mode="supervised_rerank",
            visual_identity="supervised_engine",
            runtime_scope="scientific_runtime",
            source_tables=("ml_usage_events",),
            score_ml_ready=True,
        ),
        ScientificNucleus(
            nucleus_id="estatisticas_historicas",
            page_id="estatisticas_historicas",
            display_name="Jogos Passados",
            scientific_finality="historico institucional",
            persistence_artifact=TEMPORAL_HISTORY_CONFERENCE,
            temporal_contract="historical_cutoff_only",
            validation_mode="historical_memory",
            visual_identity="historical_engine",
            runtime_scope="public_runtime",
            source_tables=("check_events", "generation_events"),
        ),
        ScientificNucleus(
            nucleus_id="relatorios",
            page_id="relatorios",
            display_name="Analíticas Persistidas",
            scientific_finality="persistencia científica",
            persistence_artifact=TEMPORAL_HISTORY_OPERATIONS,
            temporal_contract="immutable_snapshot",
            validation_mode="scientific_persistence",
            visual_identity="persistence_engine",
            runtime_scope="scientific_runtime",
            source_tables=("report_events", "operational_logs", "audit_trail"),
        ),
    )

    page_labels = {
        "geracao_jogos": "Gerar Jogos",
        "conferir_jogos": "Conferir Jogos",
        "reconciliacao_operacional": "Simular Resultado",
        "estatisticas_historicas": "Jogos Passados",
        "historical_intelligence": "Memória Analítica",
        "analytics_intelligence": "Análise Estrutural",
        "ml_intelligence": "Ranking ML",
        "backtesting": "Testar Estratégia",
        "calibracao_experimental": "Estratégia Operacional",
        "benchmark_cientifico": "Comparativos",
        "historico_experimental": "Histórico Operacional",
        "relatorios": "Analíticas Persistidas",
        "ml_governance": "Governança Científica",
        "observability": "Observabilidade Científica",
        "workflows": "Fluxos Institucionais",
        "reports_engine": "Relatórios Científicos",
    }

    page_audit_matrix = {
        "geracao_jogos": {"category": "operacional", "usage": "alto", "action": "permanecer"},
        "conferir_jogos": {"category": "operacional", "usage": "alto", "action": "permanecer"},
        "reconciliacao_operacional": {"category": "operacional", "usage": "alto", "action": "permanecer"},
        "estatisticas_historicas": {"category": "historico", "usage": "medio", "action": "recolher"},
        "historical_intelligence": {"category": "memoria_analitica", "usage": "medio", "action": "recolher"},
        "analytics_intelligence": {"category": "analise_estrutural", "usage": "medio", "action": "recolher"},
        "ml_intelligence": {"category": "ranking_supervisionado", "usage": "baixo", "action": "recolher"},
        "backtesting": {"category": "validacao_temporal", "usage": "baixo", "action": "ocultar"},
        "calibracao_experimental": {"category": "estrategia_operacional", "usage": "baixo", "action": "ocultar"},
        "benchmark_cientifico": {"category": "benchmark_temporal", "usage": "baixo", "action": "ocultar"},
        "historico_experimental": {"category": "historico_operacional", "usage": "baixo", "action": "ocultar"},
        "relatorios": {"category": "persistencia_cientifica", "usage": "medio", "action": "recolher"},
        "ml_governance": {"category": "governanca_cientifica", "usage": "medio", "action": "recolher"},
        "observability": {"category": "observabilidade_cientifica", "usage": "medio", "action": "recolher"},
        "workflows": {"category": "fluxos_institucionais", "usage": "alto", "action": "permanecer"},
        "reports_engine": {"category": "relatorios_cientificos", "usage": "baixo", "action": "ocultar"},
    }

    mode_sections = {
        "operacional": tuple(
            ScientificNucleusSection(mode="operacional", visual_identity="operational_core", **section)
            for section in SCIENTIFIC_MODE_SECTIONS["operacional"]
        ),
        "analitico": tuple(
            ScientificNucleusSection(mode="analitico", visual_identity="scientific_engine", **section)
            for section in SCIENTIFIC_MODE_SECTIONS["analitico"]
        ),
    }

    return ScientificNucleiRegistry(
        registry_version=SCIENTIFIC_NUCLEI_REGISTRY_VERSION,
        status=SCIENTIFIC_NUCLEI_REGISTRY_STATUS,
        nuclei=nuclei,
        mode_sections=mode_sections,
        page_labels=page_labels,
        page_audit_matrix=page_audit_matrix,
        score_ml_contract_ready=_score_ml_contract_ready(),
        runtime_stability_ready=_runtime_stability_ready(),
    )


def validate_scientific_nuclei_registry(registry: ScientificNucleiRegistry) -> ScientificNucleiValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    nuclei_by_id = {nucleus.nucleus_id: nucleus for nucleus in registry.nuclei}
    missing = [nucleus_id for nucleus_id in CORE_NUCLEI if nucleus_id not in nuclei_by_id]
    if missing:
        errors.append(f"missing core nuclei: {', '.join(missing)}")

    for nucleus in registry.nuclei:
        required_fields = {
            "display_name": nucleus.display_name,
            "scientific_finality": nucleus.scientific_finality,
            "persistence_artifact": nucleus.persistence_artifact,
            "temporal_contract": nucleus.temporal_contract,
            "validation_mode": nucleus.validation_mode,
            "visual_identity": nucleus.visual_identity,
            "runtime_scope": nucleus.runtime_scope,
        }
        if any(not str(value).strip() for value in required_fields.values()):
            errors.append(f"nucleus {nucleus.nucleus_id} has incomplete scientific identity")

    if not registry.score_ml_contract_ready:
        errors.append("score_ml contract not ready for supervised activation")
    if not registry.runtime_stability_ready:
        errors.append("runtime stability contract not ready")

    if "ml_intelligence" in nuclei_by_id and not nuclei_by_id["ml_intelligence"].score_ml_ready:
        errors.append("ranking_ml nucleus must be marked score_ml_ready")

    return ScientificNucleiValidationReport(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))


def _score_ml_contract_ready() -> bool:
    required_datasets = {
        DATASET_OPERATIONAL,
        DATASET_BENCHMARK,
        DATASET_ML,
        DATASET_VALIDATION,
        DATASET_EXPANSION,
    }
    required_strategies = {
        BENCHMARK_RANKING_HYBRID,
        BENCHMARK_EXPANSION,
        BENCHMARK_SCORE_ML,
        BENCHMARK_RANDOM,
        BENCHMARK_STATISTICAL_BASELINE,
    }
    required_metrics = {
        "drift_temporal",
        "score_stability",
        "benchmark_evolution",
        "statistical_degradation",
    }
    return (
        required_datasets == {
            DATASET_OPERATIONAL,
            DATASET_BENCHMARK,
            DATASET_ML,
            DATASET_VALIDATION,
            DATASET_EXPANSION,
        }
        and required_strategies == set(TEMPORAL_BENCHMARK_STRATEGIES)
        and required_metrics == set(SCIENTIFIC_OBSERVABILITY_METRICS)
    )


def _runtime_stability_ready() -> bool:
    required_nuclei = set(TEMPORAL_OPERATIONAL_NUCLEI)
    required_metrics = set(TEMPORAL_RUNTIME_INTEGRITY_METRICS)
    return (
        required_nuclei == {
            "jogos_passados",
            "testar_estrategia",
            "comparativos_operacionais",
            "ranking_ml",
            "analiticas_persistidas",
        }
        and required_metrics == {
            "leakage_temporal",
            "datasets_correct",
            "benchmark_clean",
            "historical_segregation",
            "features_valid",
            "temporal_window_valid",
        }
    )
