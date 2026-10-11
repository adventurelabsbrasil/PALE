"""Deterministic, local-first perceptual analysis for the first PALE world."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf


ANALYZER_VERSION = "pale-analyzer-v1"
CONTRACT_VERSION = "pale-timeline-v1"
WINDOW_SAMPLES = 2048
HOP_SAMPLES = 1024
SEED = 2042


@dataclass(frozen=True)
class AnalysisConfig:
    window_samples: int = WINDOW_SAMPLES
    hop_samples: int = HOP_SAMPLES
    seed: int = SEED


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_audio(path: Path) -> tuple[np.ndarray, int]:
    if path.suffix.lower() == ".wav":
        samples, sample_rate = sf.read(path, dtype="float32", always_2d=True)
        mono = samples.mean(axis=1)
    elif path.suffix.lower() == ".mp3":
        try:
            import torchaudio
        except (ImportError, ModuleNotFoundError) as exc:
            raise RuntimeError("MP3 analysis requires torchaudio and TorchCodec") from exc
        waveform, sample_rate = torchaudio.load(path, normalize=True, channels_first=True)
        mono = waveform.float().mean(dim=0).cpu().numpy()
    else:
        raise ValueError("PALE accepts only WAV or MP3 audio")
    if mono.size == 0:
        raise ValueError("Audio is empty")
    if not np.isfinite(mono).all():
        raise ValueError("Audio contains NaN or infinite samples")
    peak = float(np.max(np.abs(mono)))
    if peak > 0:
        mono = mono / peak
    return np.asarray(mono, dtype=np.float32), int(sample_rate)


def _normalize(values: list[float]) -> list[float]:
    array = np.asarray(values, dtype=np.float64)
    low, high = np.percentile(array, [5, 95])
    span = max(float(high - low), 1e-8)
    return [round(float(np.clip((value - low) / span, 0, 1)), 8) for value in array]


def _round_values(values: list[float]) -> list[float]:
    return [round(float(value), 8) for value in values]


def analyze_audio(
    path: Path,
    *,
    progress: Callable[[int], None] | None = None,
    config: AnalysisConfig = AnalysisConfig(),
) -> dict:
    """Analyze an audio file into a stable timeline artifact."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    source_hash = _sha256(path)
    samples, sample_rate = _load_audio(path)
    window = np.hanning(config.window_samples).astype(np.float32)
    frame_starts = list(range(0, max(1, len(samples) - config.window_samples + 1), config.hop_samples))
    raw: dict[str, list[float]] = {key: [] for key in ("rms", "low", "mid", "high", "centroid", "flux", "attack")}
    previous = np.zeros(config.window_samples // 2 + 1, dtype=np.float32)
    previous_rms = 0.0
    frame_spectra: list[np.ndarray] = []

    for index, start in enumerate(frame_starts):
        frame = samples[start : start + config.window_samples]
        if len(frame) < config.window_samples:
            frame = np.pad(frame, (0, config.window_samples - len(frame)))
        rms = float(np.sqrt(np.mean(frame * frame)))
        spectrum = np.abs(np.fft.rfft(frame * window)).astype(np.float32)
        frequencies = np.fft.rfftfreq(config.window_samples, 1 / sample_rate)
        total = max(float(spectrum[1:].sum()), 1e-8)
        centroid = float((frequencies[1:] * spectrum[1:]).sum() / total) / max(sample_rate / 2, 1)
        low = float(spectrum[(frequencies < 250)].sum() / total)
        mid = float(spectrum[(frequencies >= 250) & (frequencies < 2000)].sum() / total)
        high = float(spectrum[(frequencies >= 2000)].sum() / total)
        flux = float(np.maximum(spectrum - previous, 0).sum() / total)
        raw["rms"].append(rms)
        raw["low"].append(low)
        raw["mid"].append(mid)
        raw["high"].append(high)
        raw["centroid"].append(centroid)
        raw["flux"].append(flux)
        raw["attack"].append(max(0.0, rms - previous_rms))
        frame_spectra.append(spectrum)
        previous = spectrum
        previous_rms = rms
        if progress and (index == 0 or index == len(frame_starts) - 1 or index % 24 == 0):
            progress(round(index / max(1, len(frame_starts) - 1) * 100))

    normalized = {key: _normalize(values) for key, values in raw.items()}
    event_signal = [max(flux, attack) for flux, attack in zip(normalized["flux"], normalized["attack"])]
    density = []
    for index in range(len(event_signal)):
        start = max(0, index - 21)
        density.append(round(float(np.mean(event_signal[start : index + 1])), 8))
    normalized["density"] = density
    rms_floor = max(float(np.percentile(raw["rms"], 5)) * 1.35, float(np.percentile(raw["rms"], 95)) * 0.025)
    rms_high = max(float(np.percentile(raw["rms"], 95)), rms_floor + 1e-8)
    normalized["silence"] = [round(float(1 - np.clip((value - rms_floor) / (rms_high - rms_floor), 0, 1)), 8) for value in raw["rms"]]
    normalized["repeat"] = [0.0] * len(frame_starts)
    normalized["novelty"] = [round(float(np.clip(0.25 + signal * 0.75, 0, 1)), 8) for signal in event_signal]

    features = {key: _round_values(values) for key, values in raw.items()}
    waveform_indices = np.linspace(0, len(samples) - 1, 256, dtype=np.int64)
    features["waveform"] = _round_values(np.abs(samples[waveform_indices]).tolist())
    features.update(normalized)
    spectra = []
    for spectrum in frame_spectra:
        indices = np.linspace(1, len(spectrum) - 1, 40, dtype=np.int64)
        peak = max(float(np.max(spectrum[1:])), 1e-8)
        spectra.append(_round_values((spectrum[indices] / peak).tolist()))
    events = []
    for index, start in enumerate(frame_starts):
        dominant = max(("low", normalized["low"][index]), ("mid", normalized["mid"][index]), ("high", normalized["high"][index]), key=lambda item: item[1])[0]
        layer = "pulse/impact" if event_signal[index] >= 0.55 else f"{dominant}/energy"
        events.append({
            "id": f"event-{index:06d}",
            "time": round(start / sample_rate, 8),
            "duration": round(min(config.window_samples, len(samples) - start) / sample_rate, 8),
            "layer": layer,
            "energy": normalized["rms"][index],
            "frequency_region": dominant,
            "attack": normalized["attack"][index],
            "brightness": normalized["centroid"][index],
            "density": normalized["density"][index],
            "silence": normalized["silence"][index],
            "confidence": "inferred",
            "origin": "audio",
        })

    config_data = asdict(config)
    identity_payload = {
        "source_sha256": source_hash,
        "analyzer_version": ANALYZER_VERSION,
        "contract_version": CONTRACT_VERSION,
        "config": config_data,
    }
    identity = hashlib.sha256(json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "contract_version": CONTRACT_VERSION,
        "analyzer_version": ANALYZER_VERSION,
        "identity": identity,
        "source": {"original_name": path.name, "sha256": source_hash},
        "config": config_data,
        "sample_rate": sample_rate,
        "duration": round(len(samples) / sample_rate, 8),
        "frame_count": len(frame_starts),
        "window_samples": config.window_samples,
        "hop_samples": config.hop_samples,
        "features": features,
        "spectra": spectra,
        "events": events,
        "warnings": ["Musical entities are perceptual inferences from the audio; no instrument identity is asserted."],
    }
