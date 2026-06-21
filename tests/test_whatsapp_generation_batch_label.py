from __future__ import annotations

from unittest.mock import patch

from lotoia.clients.whatsapp_service import generate_whatsapp_games
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL


def test_generate_whatsapp_games_uses_sovereign_batch_label(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    captured: dict[str, object] = {}

    def _fake_generate_ranked_games(**kwargs):
        captured.update(kwargs)
        return [
            {"numbers": list(range(1, 16)), "final_score": {"final_score": 1.0}},
            {"numbers": list(range(1, 16)), "final_score": {"final_score": 1.0}},
        ]

    with patch(
        "lotoia.clients.whatsapp_service.generate_ranked_games",
        side_effect=_fake_generate_ranked_games,
    ):
        games, _event = generate_whatsapp_games(
            targets=[(15, 2)],
            phone="5511999999999",
            client_name="Ana",
            db_path=db_path,
        )

    assert captured.get("batch_label") == BATCH_LABEL
    assert len(games) == 2
