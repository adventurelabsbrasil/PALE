import pytest

from acoustic_lab.audio_analysis import analyze_audio
from acoustic_lab.event_contract import REQUIRED_EVENT_FIELDS, synthetic_event, validate_event


def test_synthetic_and_imported_events_share_the_required_contract(tmp_path):
    synthetic = synthetic_event(
        event_id="synthetic-pluck-000001",
        time=0.25,
        duration=0.4,
        pitch=60,
        energy=0.7,
        attack=0.8,
        brightness=0.6,
    )
    for field in REQUIRED_EVENT_FIELDS:
        assert field in synthetic

    import numpy as np
    import soundfile as sf

    source = tmp_path / "tone.wav"
    time = np.arange(8_000, dtype=np.float32) / 8_000
    sf.write(source, (0.4 * np.sin(2 * np.pi * 220 * time)).astype(np.float32), 8_000)
    imported = analyze_audio(source)["events"][0]
    assert set(REQUIRED_EVENT_FIELDS) <= imported.keys()
    assert synthetic["origin"] == "synthetic"
    assert imported["origin"] == "audio"
    validate_event(imported)


def test_event_contract_rejects_unconfirmed_synthetic_inference():
    event = synthetic_event(
        event_id="synthetic-noise-000001",
        time=0,
        duration=0.2,
        pitch=48,
        energy=0.2,
        attack=0.4,
        brightness=0.1,
    )
    event["confidence"] = "inferred"
    validate_event(event)
    event["origin"] = "unknown"
    with pytest.raises(ValueError, match="origin"):
        validate_event(event)
