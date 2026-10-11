import json

import numpy as np
import pytest
import soundfile as sf

from acoustic_lab.artifact import ARTIFACT_VERSION, load_artifact
from acoustic_lab.audio_analysis import AnalysisConfig, analyze_audio
from acoustic_lab.experiment2 import prepare_experiment2


def _write(path, samples, sample_rate=8_000):
    sf.write(path, np.asarray(samples, dtype=np.float32), sample_rate, subtype="PCM_16")


def test_artifact_round_trip_is_local_and_rejects_tampering(tmp_path):
    source = tmp_path / "stereo.wav"
    left = np.linspace(-1, 1, 4096, dtype=np.float32)
    _write(source, np.column_stack([left, -left]), 16_000)
    output = tmp_path / "world"
    prepare_experiment2(source, output, preanalyze=True)

    artifact = load_artifact(output / "artifact.json")
    assert artifact["artifact"] == ARTIFACT_VERSION
    assert artifact["privacy"] == {"audio_included": False, "processing": "local-only", "remote_upload": False}
    assert artifact["analysis"]["source"]["channels"] == 2
    assert max(artifact["analysis"]["features"]["stereo_width"]) > 0

    tampered = json.loads((output / "artifact.json").read_text())
    tampered["analysis"]["identity"] = "changed"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="identities"):
        load_artifact(bad)


def test_analysis_records_input_edges_and_config_identity(tmp_path):
    silence = tmp_path / "silence.wav"
    clipped = tmp_path / "clipped.wav"
    _write(silence, np.zeros(2048), 8_000)
    _write(clipped, np.ones(2048), 22_050)

    silent = analyze_audio(silence)
    loud = analyze_audio(clipped)
    changed = analyze_audio(clipped, config=AnalysisConfig(seed=99))
    assert "digital silence" in silent["warnings"][1]
    assert "clipping" in loud["warnings"][1]
    assert loud["sample_rate"] == 22_050
    assert loud["identity"] != changed["identity"]


def test_analysis_reports_decode_failures_without_partial_artifact(tmp_path):
    invalid = tmp_path / "broken.wav"
    invalid.write_bytes(b"not a wave")
    with pytest.raises(ValueError, match="decoding"):
        analyze_audio(invalid)
    with pytest.raises(ValueError, match="decoding"):
        prepare_experiment2(invalid, tmp_path / "world", preanalyze=True)
    assert not (tmp_path / "world").exists()
