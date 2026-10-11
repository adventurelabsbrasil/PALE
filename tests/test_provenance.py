import numpy as np
import soundfile as sf

from acoustic_lab.audio_analysis import analyze_audio
from acoustic_lab.provenance import DIDACTIC_VERSION, didactic_explanation


def test_audio_events_persist_provenance_and_explicit_limits(tmp_path):
    source = tmp_path / "tone.wav"
    time = np.arange(8_000, dtype=np.float32) / 8_000
    sf.write(source, (0.4 * np.sin(2 * np.pi * 220 * time)).astype(np.float32), 8_000)

    event = analyze_audio(source)["events"][0]

    assert event["provenance"]["status"] == "inferred"
    assert event["explanation"]["version"] == DIDACTIC_VERSION
    assert {"instrumento", "acorde", "melodia", "intenção"}.issubset(event["explanation"]["not_claimed"])
    assert any(signal["label"] == "Harmonia" for signal in event["explanation"]["signals"])
    harmony = next(signal for signal in event["explanation"]["signals"] if signal["label"] == "Harmonia")
    assert "não é determinada" in harmony["limit"]


def test_didactic_explanation_does_not_upgrade_uncertain_hypothesis():
    event = {"confidence": "hypothesis", "origin": "synthetic", "energy": 0.4}
    explanation = didactic_explanation(event)

    assert explanation["provenance"]["status"] == "uncertain"
    assert explanation["provenance"]["origin"] == "synthetic"
