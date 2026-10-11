"""Shared logical event contract for imported and live PALE timelines."""

from __future__ import annotations

from typing import Any, Mapping


CONTRACT_VERSION = "pale-timeline-v1"
REQUIRED_EVENT_FIELDS = (
    "id",
    "time",
    "duration",
    "layer",
    "energy",
    "frequency_region",
    "attack",
    "brightness",
    "confidence",
    "origin",
)

PERCEPTUAL_LAYERS = ("low", "impact", "harmony", "line", "texture", "space")
RELATION_TYPES = ("coexistence", "synchronization", "contrast")


def validate_event(event: Mapping[str, Any]) -> None:
    """Reject malformed timeline events without making inferences factual."""
    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
    if missing:
        raise ValueError(f"event is missing required fields: {', '.join(missing)}")
    if not isinstance(event["id"], str) or not event["id"]:
        raise ValueError("event id must be a non-empty string")
    if event["time"] < 0 or event["duration"] < 0:
        raise ValueError("event time and duration must be non-negative")
    for field in ("energy", "attack", "brightness"):
        if not 0 <= event[field] <= 1:
            raise ValueError(f"event {field} must be between 0 and 1")
    if event["origin"] not in {"audio", "synthetic"}:
        raise ValueError("event origin must be audio or synthetic")
    if event["confidence"] not in {"confirmed", "inferred", "hypothesis"}:
        raise ValueError("event confidence must preserve its epistemic status")


def validate_entity(entity: Mapping[str, Any]) -> None:
    """Validate a persistent perceptual entity without making it musical fact."""
    required = ("id", "layer", "confidence", "time", "duration", "position", "energy", "event_ids")
    missing = [field for field in required if field not in entity]
    if missing:
        raise ValueError(f"entity is missing required fields: {', '.join(missing)}")
    if not isinstance(entity["id"], str) or not entity["id"]:
        raise ValueError("entity id must be a non-empty string")
    if entity["layer"] not in PERCEPTUAL_LAYERS:
        raise ValueError("entity layer must be a perceptual PALE layer")
    if entity["confidence"] not in {"confirmed", "inferred", "hypothesis"}:
        raise ValueError("entity confidence must preserve its epistemic status")
    if entity["time"] < 0 or entity["duration"] < 0:
        raise ValueError("entity time and duration must be non-negative")
    if not isinstance(entity["position"], Mapping) or set(entity["position"]) != {"x", "y", "z"}:
        raise ValueError("entity position must contain x, y and z")
    if not 0 <= entity["energy"] <= 1:
        raise ValueError("entity energy must be between 0 and 1")
    if not isinstance(entity["event_ids"], list) or not all(isinstance(item, str) for item in entity["event_ids"]):
        raise ValueError("entity event_ids must be a list of strings")


def validate_relation(relation: Mapping[str, Any]) -> None:
    required = ("id", "source", "target", "type", "confidence", "strength", "event_ids")
    missing = [field for field in required if field not in relation]
    if missing:
        raise ValueError(f"relation is missing required fields: {', '.join(missing)}")
    if not relation["id"] or not relation["source"] or not relation["target"]:
        raise ValueError("relation identifiers must be non-empty")
    if relation["type"] not in RELATION_TYPES:
        raise ValueError("unsupported relation type")
    if relation["confidence"] not in {"confirmed", "inferred", "hypothesis"}:
        raise ValueError("relation confidence must preserve its epistemic status")
    if not 0 <= relation["strength"] <= 1:
        raise ValueError("relation strength must be between 0 and 1")
    if not isinstance(relation["event_ids"], list) or not all(isinstance(item, str) for item in relation["event_ids"]):
        raise ValueError("relation event_ids must be a list of strings")


def synthetic_event(
    *,
    event_id: str,
    time: float,
    duration: float,
    pitch: int,
    energy: float,
    attack: float,
    brightness: float,
    layer: str = "synthetic/note",
    frequency_region: str = "mid",
) -> dict[str, Any]:
    """Build a transparent live event using the same fields as audio analysis."""
    event = {
        "id": event_id,
        "time": round(time, 8),
        "duration": round(duration, 8),
        "layer": layer,
        "energy": round(max(0.0, min(1.0, energy)), 8),
        "frequency_region": frequency_region,
        "attack": round(max(0.0, min(1.0, attack)), 8),
        "brightness": round(max(0.0, min(1.0, brightness)), 8),
        "confidence": "confirmed",
        "origin": "synthetic",
        "pitch": pitch,
    }
    from .provenance import annotate_event

    event = annotate_event(event)
    validate_event(event)
    return event
