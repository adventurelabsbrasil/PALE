"""Metadata-free WAV ingestion for the next acoustic model stage."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Union

import torch


PathLike = Union[str, Path]


def select_device() -> torch.device:
    """Prefer Apple's MPS backend, falling back to CPU when unavailable."""
    if torch.backends.mps.is_built() and torch.backends.mps.is_available():
        # Use the explicit device spelling returned by tensors after transfer.
        return torch.device("mps:0")
    return torch.device("cpu")


def _load_torchaudio():
    try:
        import torchaudio
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "torchaudio and TorchCodec are required; run `uv sync --python /opt/homebrew/bin/python3.12` first"
        ) from exc
    return torchaudio


def ingest_audio(file_path: PathLike) -> tuple[torch.Tensor, int]:
    """Load a WAV as normalized mono audio on MPS or CPU.

    Only samples and sample rate are retained. Container metadata, tags and
    channel layout are intentionally discarded after loading.
    """
    path = Path(file_path)
    if path.suffix.lower() != ".wav":
        raise ValueError(f"Expected a .wav file, got: {path}")
    if not path.is_file():
        raise FileNotFoundError(path)

    torchaudio = _load_torchaudio()
    waveform, sample_rate = torchaudio.load(path, normalize=True, channels_first=True)
    if waveform.ndim != 2 or waveform.shape[0] < 1 or waveform.shape[1] < 1:
        raise ValueError(f"Expected non-empty audio with shape [channels, time], got {tuple(waveform.shape)}")
    if not torch.is_floating_point(waveform):
        waveform = waveform.float()
    if not torch.isfinite(waveform).all():
        raise ValueError("Audio contains NaN or infinite samples")

    # Channel identity is intentionally discarded: the model receives one
    # physical pressure waveform, not a semantic stereo interpretation.
    mono = waveform.mean(dim=0)
    peak = mono.abs().amax()
    if peak > 0:
        mono = mono / peak
    mono = mono.clamp(-1.0, 1.0).contiguous()
    device = select_device()
    tensor = mono.to(device)
    print(f"shape={tuple(tensor.shape)} sample_rate={sample_rate} device={tensor.device}")
    return tensor, int(sample_rate)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a raw WAV as a normalized mono PyTorch tensor")
    parser.add_argument("file_path", type=Path)
    args = parser.parse_args()
    ingest_audio(args.file_path)


if __name__ == "__main__":
    main()
