"""Physical signal transform and reproducible masked crops."""

import hashlib
from pathlib import Path

import numpy as np
from scipy import signal
import soundfile as sf

from .config import FeatureConfig


def spectrogram(path: Path, expected_rate: int, config: FeatureConfig) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=False)
    if rate != expected_rate or audio.ndim != 1:
        raise ValueError(f"Unexpected WAV format: {path}")
    _, _, spectrum = signal.stft(
        audio, fs=rate, nperseg=config.fft_size,
        noverlap=config.fft_size - config.hop_size,
        boundary=None, padded=False,
    )
    return np.log1p(np.abs(spectrum)).astype(np.float32)


def crop_and_mask(features: np.ndarray, config: FeatureConfig, key: str) -> tuple[np.ndarray, np.ndarray, slice]:
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    start = int(rng.integers(0, features.shape[1] - config.crop_frames + 1))
    crop = features[:, start:start + config.crop_frames].copy()
    mask_start = int(rng.integers(1, config.crop_frames - config.mask_frames))
    region = slice(mask_start, mask_start + config.mask_frames)
    masked = crop.copy()
    masked[:, region] = interpolation_baseline(crop, region)
    return masked, crop, region


def interpolation_baseline(target: np.ndarray, region: slice) -> np.ndarray:
    """Linear time interpolation using only the two visible boundary frames."""
    left = target[:, region.start - 1]
    right = target[:, region.stop]
    fraction = (np.arange(1, region.stop - region.start + 1, dtype=np.float32) / (region.stop - region.start + 1))[None, :]
    return left[:, None] * (1 - fraction) + right[:, None] * fraction
