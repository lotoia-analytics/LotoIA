from pathlib import Path


def test_scheduler_imports_auto_feedback_loop() -> None:
    content = Path("src/lotoia/clients/client_conference_scheduler.py").read_text()
    assert "m_feedback_002_auto_loop" in content
    assert "m_feedback_001_loop" not in content
