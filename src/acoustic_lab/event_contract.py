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
    validate_event(event)
    return event
