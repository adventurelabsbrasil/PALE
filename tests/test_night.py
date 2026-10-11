from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from acoustic_lab import night


def test_overnight_tick_counts_attempts_not_artifact_sequence(tmp_path, monkeypatch):
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    monkeypatch.setattr(night, "LAB", tmp_path)
    monkeypatch.setattr(night, "START", now - timedelta(minutes=1))
    monkeypatch.setattr(night, "END", now + timedelta(minutes=1))
    monkeypatch.setattr(night.os, "nice", lambda _: None)
    seen = []

    def fake_cycle(sequence, allowance):
        seen.append((sequence, allowance))
        return {"elapsed_seconds": 7.0}

    monkeypatch.setattr(night, "cycle", fake_cycle)
    first = night.tick()
    second = night.tick()
    assert seen == [(101, 60), (102, 60)]
    assert first["cycles"] == 1
    assert second["cycles"] == 2
    assert second["spent_seconds"] == 14.0
