"""Sistema de Versionamento de Modelos para CORE_003.

Rastreia versões do pipeline com mudanças e resultados de backtest.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModelVersioning:
    """Sistema de versionamento de modelos CORE_003."""

    def __init__(self, versions_file: str = "data/model_versions.json"):
        self.versions_file = Path(versions_file)
        self.versions: dict[str, dict[str, Any]] = {}
        self._load_versions()

    def _load_versions(self) -> None:
        """Carrega versões do arquivo."""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, "r", encoding="utf-8") as f:
                    self.versions = json.load(f)
                logger.info(
                    "[Versioning] Carregadas %d versões de %s",
                    len(self.versions),
                    self.versions_file,
                )
            except Exception as e:
                logger.error("[Versioning] Erro ao carregar versões: %s", e)
                self.versions = {}
        else:
            logger.info(
                "[Versioning] Arquivo de versões não encontrado, iniciando vazio"
            )
            self.versions = {}

    def _save_versions(self) -> None:
        """Salva versões no arquivo."""
        try:
            self.versions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.versions_file, "w", encoding="utf-8") as f:
                json.dump(self.versions, f, indent=2, ensure_ascii=False)
            logger.info("[Versioning] Versões salvas em %s", self.versions_file)
        except Exception as e:
            logger.error("[Versioning] Erro ao salvar versões: %s", e)

    def register_version(
        self,
        version: str,
        changes: list[str],
        backtest_results: dict[str, Any] | None = None,
        config_changes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Registra nova versão do modelo.

        Args:
            version: String da versão (ex: "v3.0.0")
            changes: Lista de mudanças realizadas
            backtest_results: Resultados de backtest (opcional)
            config_changes: Mudanças na configuração (opcional)

        Returns:
            Dicionário com informações da versão registrada
        """
        if version in self.versions:
            logger.warning("[Versioning] Versão %s já existe, atualizando", version)

        version_info = {
            "version": version,
            "release_date": datetime.now().isoformat(),
            "changes": changes,
            "backtest_results": backtest_results or {},
            "config_changes": config_changes or {},
            "status": "active",
        }

        self.versions[version] = version_info
        self._save_versions()

        logger.info(
            "[Versioning] Versão %s registrada | changes=%d backtest=%s",
            version,
            len(changes),
            "yes" if backtest_results else "no",
        )

        return version_info

    def get_version(self, version: str) -> dict[str, Any] | None:
        """Retorna informações de uma versão específica."""
        return self.versions.get(version)

    def get_latest_version(self) -> dict[str, Any] | None:
        """Retorna a versão mais recente."""
        if not self.versions:
            return None

        # Ordenar por data de release
        sorted_versions = sorted(
            self.versions.items(),
            key=lambda x: x[1].get("release_date", ""),
            reverse=True,
        )

        return sorted_versions[0][1] if sorted_versions else None

    def compare_versions(
        self,
        version_a: str,
        version_b: str,
    ) -> dict[str, Any]:
        """Compara duas versões do modelo.

        Args:
            version_a: Primeira versão
            version_b: Segunda versão

        Returns:
            Dicionário com comparação
        """
        ver_a = self.versions.get(version_a)
        ver_b = self.versions.get(version_b)

        if not ver_a or not ver_b:
            return {"error": "Uma ou ambas versões não encontradas"}

        # Comparar resultados de backtest
        backtest_a = ver_a.get("backtest_results", {})
        backtest_b = ver_b.get("backtest_results", {})

        comparison = {
            "version_a": version_a,
            "version_b": version_b,
            "release_date_a": ver_a.get("release_date"),
            "release_date_b": ver_b.get("release_date"),
            "changes_a": ver_a.get("changes", []),
            "changes_b": ver_b.get("changes", []),
            "backtest_comparison": {},
        }

        # Comparar métricas de backtest
        for metric in ["hit_rate_11_13", "avg_overlap", "triplet_hit_rate"]:
            if metric in backtest_a and metric in backtest_b:
                val_a = backtest_a[metric]
                val_b = backtest_b[metric]
                diff = val_b - val_a
                comparison["backtest_comparison"][metric] = {
                    "version_a": val_a,
                    "version_b": val_b,
                    "difference": diff,
                    "improvement": diff > 0,
                }

        return comparison

    def list_versions(self) -> list[dict[str, Any]]:
        """Lista todas as versões ordenadas por data."""
        sorted_versions = sorted(
            self.versions.values(),
            key=lambda x: x.get("release_date", ""),
            reverse=True,
        )
        return sorted_versions

    def update_backtest_results(
        self,
        version: str,
        backtest_results: dict[str, Any],
    ) -> bool:
        """Atualiza resultados de backtest de uma versão.

        Args:
            version: String da versão
            backtest_results: Novos resultados de backtest

        Returns:
            True se atualizado com sucesso
        """
        if version not in self.versions:
            logger.error("[Versioning] Versão %s não encontrada", version)
            return False

        self.versions[version]["backtest_results"] = backtest_results
        self._save_versions()

        logger.info("[Versioning] Backtest atualizado para versão %s", version)
        return True


# Instância global
_versioning_system = ModelVersioning()


def register_model_version(
    version: str,
    changes: list[str],
    backtest_results: dict[str, Any] | None = None,
    config_changes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Função simplificada para registrar versão.

    Args:
        version: String da versão
        changes: Lista de mudanças
        backtest_results: Resultados de backtest
        config_changes: Mudanças na configuração

    Returns:
        Informações da versão registrada
    """
    return _versioning_system.register_version(
        version, changes, backtest_results, config_changes
    )


def get_model_version(version: str) -> dict[str, Any] | None:
    """Retorna informações de uma versão."""
    return _versioning_system.get_version(version)


def get_latest_model_version() -> dict[str, Any] | None:
    """Retorna a versão mais recente."""
    return _versioning_system.get_latest_version()


def compare_model_versions(version_a: str, version_b: str) -> dict[str, Any]:
    """Compara duas versões."""
    return _versioning_system.compare_versions(version_a, version_b)


def list_model_versions() -> list[dict[str, Any]]:
    """Lista todas as versões."""
    return _versioning_system.list_versions()
