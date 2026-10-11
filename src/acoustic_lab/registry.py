"""Registry and dispatch for experiments hosted by the PALE umbrella project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Experiment:
    """Stable public metadata for one PALE experiment."""

    experiment_id: str
    title: str
    status: str
    description: str
    entrypoint: str


EXPERIMENTS: tuple[Experiment, ...] = (
    Experiment(
        experiment_id="exp-001",
        title="Fase 1 · representação acústica",
        status="active",
        description="Aprendizado autossupervisionado com sons sintéticos e projeção local.",
        entrypoint="acoustic_lab run",
    ),
    Experiment(
        experiment_id="exp-002",
        title="Organism",
        status="active",
        description="Experiência audiovisual 3D local reativa a WAV/MP3.",
        entrypoint="acoustic_lab experiment2",
    ),
)


def list_experiments() -> tuple[Experiment, ...]:
    """Return the catalog in stable display order."""
    return EXPERIMENTS


def format_catalog() -> str:
    """Render a concise, human-readable catalog for the CLI."""
    lines = ["PALE · experimentos locais", ""]
    for experiment in list_experiments():
        lines.append(f"{experiment.experiment_id} [{experiment.status}] — {experiment.title}")
        lines.append(f"  {experiment.description}")
        lines.append(f"  entrypoint: {experiment.entrypoint}")
    return "\n".join(lines)


def get_experiment(experiment_id: str) -> Experiment:
    """Find an experiment or raise a useful error for the CLI."""
    for experiment in EXPERIMENTS:
        if experiment.experiment_id == experiment_id:
            return experiment
    available = ", ".join(item.experiment_id for item in EXPERIMENTS)
    raise ValueError(f"Unknown PALE experiment {experiment_id!r}; available: {available}")


def run_registered(
    experiment_id: str,
    *,
    config: Path | None = None,
    output: Path,
    audio: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = True,
    serve: bool = True,
) -> dict[str, Any]:
    """Dispatch one catalog entry while keeping existing entrypoints intact."""
    get_experiment(experiment_id)
    if experiment_id == "exp-001":
        from .__main__ import run

        return run(config or Path("config/phase1.toml"), output)

    if experiment_id == "exp-002":
        if audio is None:
            raise ValueError("PALE experiment exp-002 requires --audio")
        from .experiment2 import run_experiment2

        return run_experiment2(
            audio,
            output,
            host=host,
            port=port,
            open_browser=open_browser,
            serve=serve,
        )

    raise AssertionError(f"Unhandled registered experiment: {experiment_id}")
