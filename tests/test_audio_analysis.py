import json

import numpy as np
import soundfile as sf

from acoustic_lab.audio_analysis import ANALYZER_VERSION, analyze_audio
from acoustic_lab.experiment2 import prepare_experiment2


def _write_tone(path):
    sample_rate = 8_000
    time = np.arange(sample_rate // 2, dtype=np.float32) / sample_rate
    signal = (0.4 * np.sin(2 * np.pi * 220 * time)).astype(np.float32)
    sf.write(path, signal, sample_rate, subtype="PCM_16")


def test_audio_analysis_is_deterministic_and_emits_timeline(tmp_path):
    source = tmp_path / "tone.wav"
    _write_tone(source)

    first = analyze_audio(source)
    second = analyze_audio(source)

    assert first == second
    assert first["analyzer_version"] == ANALYZER_VERSION
    assert first["contract_version"] == "pale-timeline-v1"
    assert first["frame_count"] == len(first["events"])
    assert first["events"][0]["id"] == "event-000000"
    assert first["events"][0]["confidence"] == "inferred"
    assert len(first["features"]["waveform"]) == 256
    assert len(first["spectra"][0]) == 40
    assert first["source"]["sha256"]


def test_preanalyzed_world_writes_manifest_identity_and_analysis(tmp_path):
    source = tmp_path / "tone.wav"
    _write_tone(source)
    output = tmp_path / "world"

    prepare_experiment2(source, output, preanalyze=True)

    manifest = json.loads((output / "manifest.json").read_text())
    analysis = json.loads((output / "analysis.json").read_text())
    assert manifest["analysis_artifact"] == "analysis.json"
    assert manifest["identity"] == analysis["identity"]
    assert manifest["analysis"]["precomputed"] is True
