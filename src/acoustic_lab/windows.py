"""Deterministic sliding-window contracts for feature-space probes."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WindowConfig:
    """A window is measured in STFT frames, after the canonical feature step."""

    size_frames: int
    hop_frames: int
    short_audio: str = "reject"

    def __post_init__(self) -> None:
        if self.size_frames < 1 or self.hop_frames < 1:
            raise ValueError("Window size and hop must be positive")
        if self.short_audio not in {"reject", "empty"}:
            raise ValueError("short_audio must be 'reject' or 'empty'")


def window_starts(frame_count: int, config: WindowConfig) -> tuple[int, ...]:
    """Return starts covering only complete windows, with an explicit short policy."""
    if frame_count < 0:
        raise ValueError("frame_count must be non-negative")
    if frame_count < config.size_frames:
        if config.short_audio == "reject":
            raise ValueError(
                f"Audio has {frame_count} feature frames; {config.size_frames} required"
            )
        return ()
    return tuple(range(0, frame_count - config.size_frames + 1, config.hop_frames))


def sliding_windows(features: np.ndarray, config: WindowConfig) -> tuple[np.ndarray, ...]:
    """Slice [frequency, time] features into fixed-size temporal windows."""
    if features.ndim != 2:
        raise ValueError("Expected feature matrix with shape [frequency, time]")
    return tuple(
        features[:, start : start + config.size_frames]
        for start in window_starts(features.shape[1], config)
    )
