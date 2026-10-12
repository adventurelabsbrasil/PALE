"""Versioned, local-only PALE artifact export and validation."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .event_contract import validate_entity, validate_event, validate_relation


ARTIFACT_VERSION = "pale-artifact-v1"
RESOURCE_LIMITS = {
    "max_audio_bytes": 100 * 1024 * 1024,
    "max_duration_seconds": 600,
    "max_frames": 30_000,
    "max_events": 30_000,
    "max_entities": 20_000,
    "max_gpu_instances": 20_000,
    "max_detailed_memory_seconds": 12,
    "max_export_bytes": 256 * 1024 * 1024,
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def analysis_identity(source_sha256: str, analyzer_version: str, contract_version: str, config: Mapping[str, Any]) -> str:
    payload = {
        "source_sha256": source_sha256,
        "analyzer_version": analyzer_version,
        "contract_version": contract_version,
        "config": dict(config),
    }
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def validate_analysis(analysis: Mapping[str, Any], *, limits: Mapping[str, int] = RESOURCE_LIMITS) -> None:
    """Validate a JSON analysis before it is persisted or rendered."""
    required = ("identity", "source", "config", "sample_rate", "duration", "frame_count", "events", "features", "spectra")
    missing = [key for key in required if key not in analysis]
    if missing:
        raise ValueError(f"analysis is missing fields: {', '.join(missing)}")
    source = analysis["source"]
    if not isinstance(source, Mapping) or not source.get("sha256"):
        raise ValueError("analysis source hash is required")
    if source.get("bytes", 0) > limits["max_audio_bytes"]:
        raise ValueError("audio file exceeds the PALE input-size limit")
    if not isinstance(analysis["sample_rate"], int) or analysis["sample_rate"] < 1:
        raise ValueError("sample rate must be a positive integer")
    if not _finite(analysis["duration"]) or analysis["duration"] < 0 or analysis["duration"] > limits["max_duration_seconds"]:
        raise ValueError("audio duration exceeds the PALE limit")
    frame_count = analysis["frame_count"]
    if not isinstance(frame_count, int) or frame_count < 1 or frame_count > limits["max_frames"]:
        raise ValueError("frame count exceeds the PALE limit")
    events = analysis["events"]
    if not isinstance(events, list) or len(events) != frame_count or len(events) > limits["max_events"]:
        raise ValueError("timeline event count does not match the bounded frame count")
    for event in events:
        validate_event(event)
        if not _finite(event["time"]) or not _finite(event["duration"]):
            raise ValueError("timeline contains a non-finite time")
        if event["time"] + event["duration"] > analysis["duration"] + 1e-6:
            raise ValueError("timeline event exceeds analysis duration")
    entities = analysis.get("entities", [])
    relations = analysis.get("relations", [])
    if not isinstance(entities, list) or len(entities) > limits["max_entities"]:
        raise ValueError("entity collection exceeds the PALE limit")
    if not isinstance(relations, list) or len(relations) > limits["max_entities"] * 2:
        raise ValueError("relation collection exceeds the PALE limit")
    entity_ids = set()
    event_ids = {event["id"] for event in events}
    for entity in entities:
        validate_entity(entity)
        if entity["id"] in entity_ids:
            raise ValueError("entity ids must be unique")
        entity_ids.add(entity["id"])
        if entity["time"] + entity["duration"] > analysis["duration"] + 1e-6:
            raise ValueError("entity exceeds analysis duration")
        if not set(entity["event_ids"]) <= event_ids:
            raise ValueError("entity references an unknown event")
    for relation in relations:
        validate_relation(relation)
        if relation["source"] not in entity_ids or relation["target"] not in entity_ids:
            raise ValueError("relation references an unknown entity")
        if not set(relation["event_ids"]) <= event_ids:
            raise ValueError("relation references an unknown event")
    if not isinstance(analysis["features"], Mapping) or not isinstance(analysis["spectra"], list):
        raise ValueError("analysis features and spectra must be JSON collections")
    for values in analysis["features"].values():
        if not isinstance(values, list) or len(values) != frame_count:
            if values and len(values) != 256:  # waveform is a bounded summary, not a frame series
                raise ValueError("feature series length does not match frame count")
        if not all(_finite(value) for value in values):
            raise ValueError("feature series contains a non-finite value")
    if len(analysis["spectra"]) != frame_count:
        raise ValueError("spectra length does not match frame count")
    if len(_canonical_json(analysis)) > limits["max_export_bytes"]:
        raise ValueError("analysis export exceeds the PALE memory/export limit")


def make_artifact(manifest: Mapping[str, Any], analysis: Mapping[str, Any], session: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a self-contained metadata/timeline artifact without audio bytes."""
    validate_analysis(analysis)
    if manifest.get("identity") != analysis.get("identity"):
        raise ValueError("manifest and analysis identities do not match")
    artifact = {
        "artifact": ARTIFACT_VERSION,
        "privacy": {"audio_included": False, "processing": "local-only", "remote_upload": False},
        "limits": dict(RESOURCE_LIMITS),
        "manifest": dict(manifest),
        "analysis": dict(analysis),
    }
    if session is not None:
        artifact["session"] = dict(session)
    return artifact


def write_artifact(output: Path, manifest: Mapping[str, Any], analysis: Mapping[str, Any], session: Mapping[str, Any] | None = None) -> Path:
    """Write a deterministic JSON artifact and return its path."""
    artifact = make_artifact(manifest, analysis, session)
    path = output / "artifact.json"
    path.write_bytes(_canonical_json(artifact) + b"\n")
    return path


def load_artifact(path: Path) -> dict[str, Any]:
    """Load and validate an exported artifact from a file or artifact directory."""
    path = path.expanduser().resolve()
    if path.is_dir():
        path = path / "artifact.json"
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid PALE artifact: {path}") from exc
    if artifact.get("artifact") != ARTIFACT_VERSION:
        raise ValueError("unsupported PALE artifact version")
    if artifact.get("privacy", {}).get("remote_upload") is not False:
        raise ValueError("PALE artifacts must declare local-only processing")
    validate_analysis(artifact.get("analysis", {}))
    manifest = artifact.get("manifest", {})
    if manifest.get("identity") != artifact["analysis"].get("identity"):
        raise ValueError("artifact manifest and analysis identities do not match")
    return artifact
