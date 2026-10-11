"""Didactic provenance for perceptual PALE analysis.

The explanations name observable signals and their limits. They deliberately
do not turn perceptual labels into musical, instrument, or intentional facts.
"""

from __future__ import annotations

from typing import Any, Mapping


DIDACTIC_VERSION = "pale-didactic-v1"
PROVENANCE_STATUSES = frozenset({"confirmed", "inferred", "uncertain"})

SIGNAL_DOMAINS = (
    {
        "id": "low",
        "label": "Grave",
        "signals": ("low",),
        "description": "energia relativa abaixo de 250 Hz",
        "limit": "não identifica uma nota, fonte ou instrumento específico",
    },
    {
        "id": "impact",
        "label": "Pulso/impacto",
        "signals": ("attack", "flux", "rms"),
        "description": "mudança de energia e fluxo espectral entre janelas",
        "limit": "não confirma um evento musical ou uma causa física",
    },
    {
        "id": "harmony",
        "label": "Harmonia",
        "signals": ("low", "mid", "high"),
        "description": "distribuição de energia em regiões de frequência",
        "limit": "não há rastreamento de notas ou acorde; harmonia não é determinada",
    },
    {
        "id": "line",
        "label": "Melodia/linha",
        "signals": ("centroid", "novelty", "repeat"),
        "description": "variação de brilho, novidade e recorrência ao longo do tempo",
        "limit": "não há pitch tracking; melodia não é determinada",
    },
    {
        "id": "texture",
        "label": "Textura/ruído",
        "signals": ("flatness", "spread", "high"),
        "description": "espalhamento e planicidade do espectro",
        "limit": "não identifica ruído como instrumento, gênero ou intenção",
    },
    {
        "id": "space",
        "label": "Silêncio/espaço",
        "signals": ("silence", "rms", "stereo_width"),
        "description": "energia baixa e, quando disponível, diferença entre canais",
        "limit": "silêncio perceptual depende do limiar e não prova ausência de som",
    },
)


def provenance_for_confidence(confidence: str, *, origin: str) -> dict[str, Any]:
    """Return a stable provenance record without upgrading confidence."""
    status = "uncertain" if confidence == "hypothesis" else confidence
    if status not in PROVENANCE_STATUSES:
        raise ValueError(f"unsupported provenance status: {confidence}")
    return {
        "status": status,
        "origin": origin,
        "basis": "parâmetros declarados pelo gerador" if origin == "synthetic" else "sinais acústicos medidos na janela",
        "limits": [
            "a visualização é uma leitura perceptual, não uma identificação factual",
            "instrumento, acorde e intenção não são afirmados sem evidência específica",
        ],
    }


def didactic_explanation(event: Mapping[str, Any], features: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Explain one event using only observable signals and explicit limits."""
    values = features or event
    signal_rows = []
    for domain in SIGNAL_DOMAINS:
        observations = {signal: round(float(values.get(signal, 0.0)), 8) for signal in domain["signals"] if signal in values}
        signal_rows.append({
            "id": domain["id"],
            "label": domain["label"],
            "observations": observations,
            "description": domain["description"],
            "limit": domain["limit"],
        })
    return {
        "version": DIDACTIC_VERSION,
        "provenance": event.get("provenance") or provenance_for_confidence(event["confidence"], origin=event["origin"]),
        "signals": signal_rows,
        "not_claimed": ["instrumento", "acorde", "melodia", "intenção"],
    }


def annotate_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Copy an event and add durable provenance plus a didactic explanation."""
    annotated = dict(event)
    annotated["provenance"] = provenance_for_confidence(event["confidence"], origin=event["origin"])
    annotated["explanation"] = didactic_explanation(annotated)
    return annotated
