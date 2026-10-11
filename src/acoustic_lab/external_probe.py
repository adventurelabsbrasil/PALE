"""Dual-world external-audio probe for the isolated Three.js experiment."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
import soundfile as sf
from scipy import signal
import torch

from .config import Config, load_config
from .features import crop_and_mask, spectrogram
from .model import FuturePredictor, MaskedPredictor
from .projection import FittedProjection, fit_projection, transform_projection
from .training import embeddings, load_features
from .windows import WindowConfig, sliding_windows


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "artifacts/phase1-final"
DEFAULT_WORLD_B = ROOT / "artifacts/experience-preview-audio-reactive/future_predictor.pt"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _decode_audio(path: Path, expected_rate: int) -> tuple[np.ndarray, int, float, bool]:
    """Decode common audio through torchaudio, then canonicalize to mono PCM."""
    try:
        import torchaudio
    except ImportError as exc:
        raise RuntimeError("torchaudio is required for MP3/WAV external probes") from exc
    waveform, rate = torchaudio.load(path, normalize=True, channels_first=True)
    if waveform.ndim != 2 or waveform.shape[1] == 0:
        raise ValueError("Audio must contain at least one non-empty channel")
    audio = waveform.float().mean(dim=0).cpu().numpy().astype(np.float32)
    if not np.isfinite(audio).all():
        raise ValueError("Audio contains NaN or infinite samples")
    peak = float(np.max(np.abs(audio)))
    source_clipping = bool(np.any(np.abs(audio) >= 0.999))
    if peak > 0:
        audio = np.clip(audio / peak, -1.0, 1.0)
    if rate != expected_rate:
        gcd = np.gcd(rate, expected_rate)
        audio = signal.resample_poly(audio, expected_rate // gcd, rate // gcd).astype(np.float32)
        rate = expected_rate
    return audio, int(rate), peak, source_clipping


def _save_canonical_audio(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    sf.write(path, audio, sample_rate, subtype="PCM_16")


def _load_world_b(checkpoint_path: Path, config: Config) -> FuturePredictor:
    frequency_bins = config.features.fft_size // 2 + 1
    model = FuturePredictor(frequency_bins)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model


def _world_b_vectors(model: FuturePredictor, index: list[dict], features: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    result = {}
    with torch.no_grad():
        for item in index:
            spectrum = features[item["id"]]
            midpoint = spectrum.shape[1] // 2
            past = spectrum[:, :midpoint].mean(axis=1).astype(np.float32)
            _, hidden = model(torch.from_numpy(past[None]))
            result[item["id"]] = hidden.numpy()[0]
    return result


def _world_b_window_vectors(model: FuturePredictor, windows: tuple[np.ndarray, ...]) -> np.ndarray:
    if not windows:
        return np.empty((0, model.encoder[0].out_features), dtype=np.float32)
    past = np.stack([window[:, : window.shape[1] // 2].mean(axis=1) for window in windows]).astype(np.float32)
    with torch.no_grad():
        _, hidden = model(torch.from_numpy(past))
    return hidden.numpy()


def _world_a_window_vectors(model: MaskedPredictor, windows: tuple[np.ndarray, ...], config) -> np.ndarray:
    if not windows:
        return np.empty((0, model.encoder[0].out_channels), dtype=np.float32)
    vectors = []
    with torch.no_grad():
        for number, window in enumerate(windows):
            masked, _, region = crop_and_mask(window, config, f"external-probe:{number}")
            mask = np.zeros((1, 1, config.crop_frames), dtype=np.float32)
            mask[:, :, region] = 1
            _, hidden = model(torch.from_numpy(masked[None]), torch.from_numpy(mask))
            vectors.append(hidden.numpy()[0])
    return np.stack(vectors)


def _distance_metrics(coordinates: np.ndarray) -> dict[str, float]:
    if len(coordinates) < 2:
        return {"adjacent_mean": 0.0, "adjacent_max": 0.0}
    distances = np.linalg.norm(np.diff(coordinates, axis=0), axis=1)
    return {"adjacent_mean": float(distances.mean()), "adjacent_max": float(distances.max())}


def _acoustic_window_features(
    audio: np.ndarray,
    sample_rate: int,
    fft_size: int,
    hop_size: int,
    crop_frames: int,
    hop_frames: int,
    count: int,
) -> list[dict[str, float]]:
    """Extract physical, non-semantic signals for the exploratory visual layer."""
    window_length = fft_size + hop_size * (crop_frames - 1)
    frequencies = np.fft.rfftfreq(fft_size, 1 / sample_rate) / (sample_rate / 2)
    window = np.hanning(fft_size).astype(np.float32)
    raw: list[tuple[float, float, float, float, float]] = []
    previous_spectrum = None
    previous_rms = 0.0
    for number in range(count):
        start = number * hop_frames * hop_size
        segment = audio[start:start + window_length]
        if len(segment) < window_length:
            segment = np.pad(segment, (0, window_length - len(segment)))
        rms = float(np.sqrt(np.mean(segment * segment)))
        spectra = []
        for frame_start in range(0, window_length - fft_size + 1, hop_size):
            frame = segment[frame_start:frame_start + fft_size] * window
            spectra.append(np.abs(np.fft.rfft(frame)))
        spectrum = np.mean(np.stack(spectra), axis=0)
        total = float(spectrum.sum())
        centroid = float(np.dot(spectrum, frequencies) / total) if total else 0.0
        spread = float(np.sqrt(np.dot(spectrum, (frequencies - centroid) ** 2) / total)) if total else 0.0
        flux = float(np.mean(np.abs(spectrum - previous_spectrum)) / (np.mean(spectrum) + 1e-6)) if previous_spectrum is not None else 0.0
        attack = max(0.0, rms - previous_rms) / 0.2
        raw.append((rms, centroid, spread, flux, min(1.0, attack)))
        previous_spectrum, previous_rms = spectrum, rms
    features = [
        {
            "rms": round(min(1.0, values[0]), 6),
            "centroid": round(min(1.0, values[1]), 6),
            "spread": round(min(1.0, values[2]), 6),
            "flux": round(min(1.0, 1.0 - np.exp(-values[3])), 6),
            "attack": round(values[4], 6),
        }
        for values in raw
    ]
    for index, feature in enumerate(features):
        score = feature["attack"] * .65 + feature["flux"] * .35
        previous = features[index - 1]["attack"] * .65 + features[index - 1]["flux"] * .35 if index else -1
        following = features[index + 1]["attack"] * .65 + features[index + 1]["flux"] * .35 if index + 1 < len(features) else -1
        feature["onset_strength"] = round(score, 6)
        feature["onset"] = bool(
            (index == 0 and score >= .2)
            or (index > 0 and score >= previous and score >= following and score >= .14)
        )
    return features


def _write_web(output: Path) -> None:
    web_source = Path(__file__).parent / "web"
    shutil.copy2(web_source / "external_probe.html", output / "external_probe.html")
    shutil.copy2(web_source / "external_probe.js", output / "external_probe.js")
    (output / "vendor").mkdir()
    for asset in ("three.module.min.js", "three.core.min.js", "OrbitControls.js"):
        shutil.copy2(web_source / "vendor" / asset, output / "vendor" / asset)


def build_external_probe(
    audio_path: Path,
    source: Path = DEFAULT_SOURCE,
    world_b_checkpoint: Path = DEFAULT_WORLD_B,
    output: Path = ROOT / "artifacts/external-probe-001",
    *,
    hop_frames: int = 16,
) -> dict:
    if output.exists():
        raise FileExistsError(f"Output directory already exists: {output}")
    if audio_path.suffix.lower() not in {".mp3", ".wav"}:
        raise ValueError("External probe accepts only .mp3 or .wav")
    output.mkdir(parents=True)
    source = source.resolve()
    audio_path = audio_path.resolve()
    config = load_config(source / "config.toml")
    original_hash = _sha256(audio_path)
    audio, sample_rate, source_peak, source_clipping = _decode_audio(audio_path, config.data.sample_rate)
    canonical_audio = output / "probe-audio.wav"
    _save_canonical_audio(canonical_audio, audio, sample_rate)
    playback_audio = output / f"probe-audio{audio_path.suffix.lower()}"
    shutil.copy2(audio_path, playback_audio)
    features = spectrogram(canonical_audio, sample_rate, config.features)
    window_config = WindowConfig(config.features.crop_frames, hop_frames, "empty")
    windows = sliding_windows(features, window_config)

    index, train_features = load_features(source / "dataset_index.json", config)
    world_a_checkpoint = source / "checkpoint.pt"
    world_a_model = MaskedPredictor(config.features.fft_size // 2 + 1)
    world_a_state = torch.load(world_a_checkpoint, map_location="cpu", weights_only=True)
    world_a_model.load_state_dict(world_a_state["state_dict"])
    world_a_model.eval()
    world_a_train = embeddings(world_a_model, index, train_features, config)
    world_b_model = _load_world_b(world_b_checkpoint, config)
    world_b_train = _world_b_vectors(world_b_model, index, train_features)

    projection_config = {"features": asdict(config.features), "dimensions": 3, "normalization": "max-absolute-train"}
    world_a_projection = fit_projection(
        np.stack([world_a_train[item["id"]] for item in index if item["split"] == "train"]),
        checkpoint_sha256=_sha256(world_a_checkpoint), config=projection_config, dimensions=3,
    )
    world_b_projection = fit_projection(
        np.stack([world_b_train[item["id"]] for item in index if item["split"] == "train"]),
        checkpoint_sha256=_sha256(world_b_checkpoint), config=projection_config, dimensions=3,
    )
    world_a_vectors = _world_a_window_vectors(world_a_model, windows, config.features)
    world_b_vectors = _world_b_window_vectors(world_b_model, windows)
    world_a_points = transform_projection(world_a_vectors, world_a_projection)
    world_b_points = transform_projection(world_b_vectors, world_b_projection)
    step_seconds = config.features.hop_size * hop_frames / sample_rate
    world_gap = np.linalg.norm(world_a_points - world_b_points, axis=1) if len(windows) else np.array([])
    acoustic_features = _acoustic_window_features(
        audio, sample_rate, config.features.fft_size, config.features.hop_size,
        config.features.crop_frames, hop_frames, len(windows),
    )
    report = {
        "title": "Probe externo agnóstico · dois mundos",
        "experiment": "dual-world-external-probe-v1",
        "audio": {
            "original_path": str(audio_path), "original_sha256": original_hash,
            "canonical_sha256": _sha256(canonical_audio), "sample_rate": sample_rate,
            "duration_seconds": len(audio) / sample_rate, "samples": len(audio),
            "channels": 1, "source_peak": source_peak,
            "canonical_peak": float(np.max(np.abs(audio))) if len(audio) else 0.0,
            "silence": bool(source_peak == 0), "clipping": source_clipping,
        },
        "audio_url": playback_audio.name,
        "contract": {"window_frames": config.features.crop_frames, "hop_frames": hop_frames, "step_seconds": step_seconds, "short_audio": "empty"},
        "worlds": {
            "world_a": {"name": "encoder da Fase 1", "checkpoint_sha256": _sha256(world_a_checkpoint), "projection": world_a_projection.to_dict()},
            "world_b": {"name": "preditor de trecho futuro aprovado", "checkpoint_sha256": _sha256(world_b_checkpoint), "projection": world_b_projection.to_dict()},
        },
        "metrics": {
            "windows": len(windows),
            "world_a": _distance_metrics(world_a_points),
            "world_b": _distance_metrics(world_b_points),
            "world_gap_mean": float(world_gap.mean()) if len(world_gap) else 0.0,
            "world_gap_max": float(world_gap.max()) if len(world_gap) else 0.0,
        },
        "points": [
            {"window": i, "start_seconds": round(i * step_seconds, 6), "world_a": world_a_points[i].tolist(), "world_b": world_b_points[i].tolist(), "acoustic": acoustic_features[i]}
            for i in range(len(windows))
        ],
        "interpretive_layer": {
            "status": "exploratory_hypothesis",
            "signals": ["rms", "centroid", "spread", "flux", "attack"],
            "normalization": "fixed physical bounds and bounded transforms; no musical labels",
            "mappings": {"rms": "opacity_scale_and_halo", "centroid": "hue", "spread": "depth_offset", "flux": "density", "attack": "glow"},
        },
        "guardrails": {"training": False, "dataset_import": False, "checkpoint_mutation": False, "semantic_labels": False, "interpretive_layer": True},
    }
    (output / "experience_data.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "world_a_projection.json").write_text(json.dumps(world_a_projection.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "world_b_projection.json").write_text(json.dumps(world_b_projection.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_web(output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an external audio probe through both frozen acoustic worlds")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--world-b", type=Path, default=DEFAULT_WORLD_B)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hop-frames", type=int, default=16)
    args = parser.parse_args()
    started = time.perf_counter()
    result = build_external_probe(args.audio, args.source, args.world_b, args.output, hop_frames=args.hop_frames)
    result["runtime_seconds"] = round(time.perf_counter() - started, 3)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
