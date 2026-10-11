import numpy as np
import pytest
import soundfile as sf
import torch

from acoustic_lab.ingest import ingest_audio, select_device


def test_ingest_audio_downmixes_and_normalizes_stereo_wav(tmp_path, capsys):
    path = tmp_path / "stereo.wav"
    left = np.array([0.25, -0.5, 0.0, 0.125], dtype=np.float32)
    right = np.array([0.75, 0.5, -0.25, 0.0], dtype=np.float32)
    sf.write(path, np.column_stack((left, right)), 16_000, subtype="PCM_24")

    tensor, sample_rate = ingest_audio(path)

    assert sample_rate == 16_000
    assert tensor.ndim == 1
    assert tensor.shape == (4,)
    assert tensor.device == select_device()
    assert tensor.dtype.is_floating_point
    assert torch.isfinite(tensor).all()
    assert float(tensor.abs().max()) == pytest.approx(1.0)
    assert float(tensor.min()) >= -1.0
    assert float(tensor.max()) <= 1.0
    np.testing.assert_allclose(tensor.cpu().numpy(), [1.0, 0.0, -0.25, 0.125], atol=2e-5)
    assert "shape=(4,) sample_rate=16000 device=" in capsys.readouterr().out


def test_ingest_audio_preserves_silence_as_zero(tmp_path):
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros((8, 1), dtype=np.float32), 8_000, subtype="PCM_16")

    tensor, sample_rate = ingest_audio(path)

    assert sample_rate == 8_000
    assert tensor.shape == (8,)
    assert torch.count_nonzero(tensor) == 0


def test_ingest_audio_rejects_non_wav(tmp_path):
    path = tmp_path / "audio.flac"
    path.write_bytes(b"not a wav")

    with pytest.raises(ValueError, match=r"Expected a \.wav file"):
        ingest_audio(path)


def test_ingest_audio_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_audio(tmp_path / "missing.wav")


def test_select_device_falls_back_to_cpu_when_mps_is_unavailable(monkeypatch):
    monkeypatch.setattr(torch.backends.mps, "is_built", lambda: True)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)

    assert select_device() == torch.device("cpu")
