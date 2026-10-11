"""Deterministic, local-first perceptual analysis for the first PALE world."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf

from .artifact import RESOURCE_LIMITS, analysis_identity, validate_analysis
from .event_contract import CONTRACT_VERSION, PERCEPTUAL_LAYERS, validate_entity, validate_event, validate_relation
from .provenance import DIDACTIC_VERSION, SIGNAL_DOMAINS, annotate_event


ANALYZER_VERSION = "pale-analyzer-v1"
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


def _load_audio(path: Path) -> tuple[np.ndarray, int, np.ndarray, float, int]:
    if path.suffix.lower() == ".wav":
        try:
            samples, sample_rate = sf.read(path, dtype="float32", always_2d=True)
        except Exception as exc:
            raise ValueError(f"Audio decoding failed: {path.name}") from exc
        mono = samples.mean(axis=1)
        channel_count = samples.shape[1]
        channel_delta = samples[:, 0] - samples[:, 1] if samples.shape[1] > 1 else np.zeros(len(samples), dtype=np.float32)
    elif path.suffix.lower() == ".mp3":
        try:
            import torchaudio
        except (ImportError, ModuleNotFoundError) as exc:
            raise RuntimeError("MP3 analysis requires torchaudio and TorchCodec") from exc
        try:
            waveform, sample_rate = torchaudio.load(path, normalize=True, channels_first=True)
        except Exception as exc:
            raise ValueError(f"Audio decoding failed: {path.name}") from exc
        channels = waveform.float().cpu().numpy()
        channel_count = channels.shape[0]
        mono = channels.mean(axis=0)
        channel_delta = channels[0] - channels[1] if channels.shape[0] > 1 else np.zeros(len(mono), dtype=np.float32)
    else:
        raise ValueError("PALE accepts only WAV or MP3 audio")
    if mono.size == 0:
        raise ValueError("Audio is empty")
    if not np.isfinite(mono).all():
        raise ValueError("Audio contains NaN or infinite samples")
    input_peak = float(np.max(np.abs(mono)))
    if input_peak > 0:
        mono = mono / input_peak
    return np.asarray(mono, dtype=np.float32), int(sample_rate), np.asarray(channel_delta, dtype=np.float32), input_peak, channel_count


def _normalize(values: list[float]) -> list[float]:
    array = np.asarray(values, dtype=np.float64)
    low, high = np.percentile(array, [5, 95])
    span = max(float(high - low), 1e-8)
    return [round(float(np.clip((value - low) / span, 0, 1)), 8) for value in array]


def _round_values(values: list[float]) -> list[float]:
    return [round(float(value), 8) for value in values]


def _semantic_model(normalized: dict[str, list[float]], events: list[dict], duration: float, seed: int) -> tuple[list[dict], list[dict]]:
    """Build stable perceptual entities and relations from the shared timeline."""
    signals = {
        "low": normalized["low"],
        "impact": normalized["attack"],
        "harmony": [min(1.0, (low + mid + high) / 3) for low, mid, high in zip(normalized["low"], normalized["mid"], normalized["high"])],
        "line": normalized["centroid"],
        "texture": normalized["high"],
        "space": normalized["silence"],
    }
    entities = []
    for index, layer in enumerate(PERCEPTUAL_LAYERS):
        values = signals[layer]
        event_ids = [event["id"] for event, value in zip(events, values) if value >= 0.35]
        energy = round(float(np.mean(values)), 8)
        entities.append({
            "id": f"entity-{layer}-000001",
            "layer": layer,
            "confidence": "inferred",
            "time": 0.0,
            "duration": round(duration, 8),
            "position": {
                "x": round(float(np.cos(index * np.pi / 3) * (1.0 + energy)), 8),
                "y": round(float(np.sin(index * np.pi / 3) * (1.0 + energy)), 8),
                "z": round(float((energy - 0.5) * 2 + (seed % 17) / 100), 8),
            },
            "energy": energy,
            "event_ids": event_ids,
            "provenance": "perceptual signal aggregate; not an instrument or musical identity",
        })
        validate_entity(entities[-1])

    relations = []
    for left in range(len(entities)):
        for right in range(left + 1, len(entities)):
            a, b = signals[PERCEPTUAL_LAYERS[left]], signals[PERCEPTUAL_LAYERS[right]]
            strength = 1.0 - min(1.0, float(np.mean(np.abs(np.asarray(a) - np.asarray(b)))))
            relation_type = "synchronization" if strength >= 0.7 else "contrast"
            relation = {
                "id": f"relation-{PERCEPTUAL_LAYERS[left]}-{PERCEPTUAL_LAYERS[right]}",
                "source": entities[left]["id"],
                "target": entities[right]["id"],
                "type": relation_type,
                "confidence": "inferred",
                "strength": round(strength, 8),
                "event_ids": sorted(set(entities[left]["event_ids"]) & set(entities[right]["event_ids"])),
            }
            validate_relation(relation)
            relations.append(relation)
    return entities, relations


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
    if path.stat().st_size > RESOURCE_LIMITS["max_audio_bytes"]:
        raise ValueError("audio file exceeds the PALE input-size limit")
    source_hash = _sha256(path)
    samples, sample_rate, channel_delta, input_peak, channel_count = _load_audio(path)
    if len(samples) / sample_rate > RESOURCE_LIMITS["max_duration_seconds"]:
        raise ValueError("audio duration exceeds the PALE limit")
    estimated_frames = max(1, len(samples) - config.window_samples + 1 + config.hop_samples - 1) // config.hop_samples
    if estimated_frames > RESOURCE_LIMITS["max_frames"]:
        raise ValueError("audio frame count exceeds the PALE limit")
    window = np.hanning(config.window_samples).astype(np.float32)
    frame_starts = list(range(0, max(1, len(samples) - config.window_samples + 1), config.hop_samples))
    raw: dict[str, list[float]] = {key: [] for key in ("rms", "low", "mid", "high", "centroid", "flux", "attack", "stereo_width")}
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
        side = channel_delta[start : start + config.window_samples]
        if len(side) < config.window_samples:
            side = np.pad(side, (0, config.window_samples - len(side)))
        raw["stereo_width"].append(float(np.sqrt(np.mean(side * side))))
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
        event = {
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
        }
        event = annotate_event(event)
        validate_event(event)
        events.append(event)

    entities, relations = _semantic_model(normalized, events, len(samples) / sample_rate, config.seed)

    config_data = asdict(config)
    identity = analysis_identity(source_hash, ANALYZER_VERSION, CONTRACT_VERSION, config_data)
    result = {
        "contract_version": CONTRACT_VERSION,
        "analyzer_version": ANALYZER_VERSION,
        "identity": identity,
        "source": {"original_name": path.name, "sha256": source_hash, "bytes": path.stat().st_size, "channels": channel_count},
        "config": config_data,
        "sample_rate": sample_rate,
        "duration": round(len(samples) / sample_rate, 8),
        "frame_count": len(frame_starts),
        "window_samples": config.window_samples,
        "hop_samples": config.hop_samples,
        "features": features,
        "spectra": spectra,
        "events": events,
        "entities": entities,
        "relations": relations,
        "warnings": ["Musical entities are perceptual inferences from the audio; no instrument identity is asserted."],
        "didactic": {
            "version": DIDACTIC_VERSION,
            "enabled_by_default": False,
            "domains": list(SIGNAL_DOMAINS),
            "not_claimed": ["instrumento", "acorde", "melodia", "intenção"],
        },
    }
    if input_peak == 0:
        result["warnings"].append("Audio is digital silence; normalized features remain zero.")
    elif input_peak >= 0.999:
        result["warnings"].append("Input reaches digital full scale; clipping may be present.")
    validate_analysis(result)
    return result
