"""Manual entry point for a complete Phase 1 cycle."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import time

import numpy
import scipy
import soundfile
import torch

from .config import load_config
from .experience import build_experience
from .synth import generate_dataset
from .training import embeddings, load_features, train
from .visualization import project_2d, write_report


def run(config_path: Path, output: Path) -> dict:
    config = load_config(config_path)
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(config_path, output / "config.toml")
    print("Generating synthetic dataset...", flush=True)
    index_path, audit_path = generate_dataset(config.data, output)
    print("Loading and verifying WAVs...", flush=True)
    index, features = load_features(index_path, config)
    print("Training on CPU...", flush=True)
    model, metrics = train(index, features, config, output)
    vectors = embeddings(model, index, features, config)
    coordinates, projection = project_2d(index, vectors)
    (output / "pca_fit.json").write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metadata = {
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "config": asdict(config),
        "dataset_index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
        "provenance_audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "versions": {"numpy": numpy.__version__, "scipy": scipy.__version__, "soundfile": soundfile.__version__, "torch": torch.__version__},
        "device": "cpu",
        "metric": "mean squared error on masked log-magnitude STFT bins",
    }
    result = {"run": metadata, "metrics": metrics}
    (output / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(output, index, metrics, coordinates, started_at)
    print(f"Report: {output / 'report.html'}", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Acoustic Lab experiment 001")
    parser.add_argument("command", choices=["run", "experience"])
    parser.add_argument("--config", type=Path, default=Path("config/phase1.toml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("artifacts/phase1-final"))
    args = parser.parse_args()
    if args.command == "run":
        run(args.config, args.output)
    else:
        result = build_experience(args.source, args.output)
        print(f"Experience: {result['output']} ({result['points']} points)", flush=True)


if __name__ == "__main__":
    main()
