import numpy as np
import pytest

from acoustic_lab.projection import fit_projection, transform_projection
from acoustic_lab.windows import WindowConfig, sliding_windows, window_starts


def test_window_contract_rejects_short_audio_and_returns_complete_windows():
    config = WindowConfig(size_frames=4, hop_frames=2)
    assert window_starts(10, config) == (0, 2, 4, 6)
    features = np.arange(30, dtype=np.float32).reshape(3, 10)
    windows = sliding_windows(features, config)
    assert [window.shape for window in windows] == [(3, 4)] * 4
    with pytest.raises(ValueError, match="required"):
        window_starts(3, config)
    assert window_starts(3, WindowConfig(4, 2, "empty")) == ()


def test_projection_transforms_new_vectors_without_refitting():
    train = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
    fitted = fit_projection(train, checkpoint_sha256="abc", config={"fft": 256})
    before = transform_projection(np.array([[2, 2]], dtype=np.float32), fitted)
    after = transform_projection(np.array([[2, 2], [100, 100]], dtype=np.float32), fitted)[0]
    np.testing.assert_allclose(before[0], after)
    assert fitted.checkpoint_sha256 == "abc"
    assert fitted.version == "pca-v1"
