"""Pure BirdNET-Go payload → coordinator.data field mapping.

Deliberately has no `homeassistant` import — this is the part of the
integration that's actually worth unit testing in isolation (see
`tests/test_parsing.py`), independent of any Home Assistant test harness.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .const import API_PATH_MEDIA_IMAGE


def daily_to_fields(payload: list[dict[str, Any]], base_url: str) -> dict[str, Any]:
    """Map a `/api/v2/analytics/species/daily` payload to coordinator fields."""
    if not payload:
        return {
            "detections_today": 0,
            "species_today": 0,
            "top_species": None,
            "top_species_scientific": None,
            "top_species_count": None,
            "top_species_thumbnail": None,
        }

    detections_today = sum(item.get("count", 0) for item in payload)
    top = max(payload, key=lambda item: item.get("count", 0))
    return {
        "detections_today": detections_today,
        "species_today": len(payload),
        "top_species": top.get("common_name"),
        "top_species_scientific": top.get("scientific_name"),
        "top_species_count": top.get("count"),
        "top_species_thumbnail": (
            f"{base_url}{top['thumbnail_url']}" if top.get("thumbnail_url") else None
        ),
    }


def summary_to_fields(payload: list[dict[str, Any]]) -> dict[str, Any]:
    """Map a `/api/v2/analytics/species/summary` payload to coordinator fields."""
    if not payload:
        return {"total_species": 0, "total_detections": 0}
    return {
        "total_species": len(payload),
        "total_detections": sum(item.get("count", 0) for item in payload),
    }


def detection_to_fields(detection: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Map one `/api/v2/detections/...` item to `last_detection_*` fields."""
    scientific = detection.get("scientificName")
    confidence = detection.get("confidence")
    return {
        "last_detection": detection.get("commonName"),
        "last_detection_scientific": scientific,
        "last_detection_confidence": (
            round(confidence * 100) if confidence is not None else None
        ),
        "last_detection_time": detection.get("timestamp"),
        "last_detection_image": (
            f"{base_url}{API_PATH_MEDIA_IMAGE}{quote(scientific)}"
            if scientific
            else None
        ),
    }


def parse_sse_detection(payload: Any) -> dict[str, Any] | None:
    """Extract the detection dict from one decoded SSE event payload.

    Returns None for anything that isn't a detection (BirdNET-Go's
    connection-confirmation/heartbeat messages, malformed payloads).
    """
    detection = payload
    if isinstance(payload, dict) and "detection" in payload:
        detection = payload["detection"]
    if isinstance(detection, list):
        detection = detection[0] if detection else None
    if not isinstance(detection, dict) or "commonName" not in detection:
        return None
    return detection
