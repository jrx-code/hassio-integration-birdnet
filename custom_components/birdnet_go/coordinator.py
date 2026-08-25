"""Data coordinator for BirdNET-Go.

Combines two data paths against the BirdNET-Go host directly — no MQTT broker
involved:

- REST polling (`DataUpdateCoordinator`, every SCAN_INTERVAL_DAILY) for the
  slow-moving stats (today's/all-time species+detection counts).
- A long-lived SSE connection to `/api/v2/detections/stream` for the
  real-time "last detection" fields, pushed the instant BirdNET-Go emits one.

Either path calls `async_set_updated_data()` so entities update on whichever
happens first.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_PATH_DAILY,
    API_PATH_MEDIA_IMAGE,
    API_PATH_RECENT,
    API_PATH_STREAM,
    API_PATH_SUMMARY,
    REST_TIMEOUT,
    SCAN_INTERVAL_DAILY,
    SCAN_INTERVAL_SUMMARY,
    SSE_CONNECT_TIMEOUT,
    SSE_RECONNECT_MAX,
    SSE_RECONNECT_MIN,
)

_LOGGER = logging.getLogger(__name__)


def _empty_data() -> dict[str, Any]:
    return {
        "available": False,
        "detections_today": None,
        "species_today": None,
        "top_species": None,
        "top_species_scientific": None,
        "top_species_count": None,
        "top_species_thumbnail": None,
        "total_species": None,
        "total_detections": None,
        "last_detection": None,
        "last_detection_scientific": None,
        "last_detection_confidence": None,
        "last_detection_time": None,
        "last_detection_image": None,
    }


class BirdNetGoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator polling REST stats and streaming SSE detections."""

    def __init__(self, hass: HomeAssistant, host: str, verify_ssl: bool) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="BirdNET-Go",
            update_interval=timedelta(seconds=SCAN_INTERVAL_DAILY),
        )
        self._host = host.rstrip("/")
        self._base_url = f"https://{self._host}"
        self._verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession = async_get_clientsession(hass, verify_ssl=verify_ssl)
        self.data: dict[str, Any] = _empty_data()

        self._sse_task: asyncio.Task | None = None
        self._last_summary_fetch: datetime | None = None

    # ------------------------------------------------------------------
    # REST polling
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        data = dict(self.data)
        try:
            data.update(await self._fetch_daily())

            now = datetime.utcnow()
            if (
                self._last_summary_fetch is None
                or (now - self._last_summary_fetch).total_seconds() >= SCAN_INTERVAL_SUMMARY
            ):
                data.update(await self._fetch_summary())
                self._last_summary_fetch = now

            if data.get("last_detection") is None:
                data.update(await self._fetch_recent())

            data["available"] = True
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"BirdNET-Go host {self._host} unreachable: {err}") from err
        return data

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with self._session.get(
            f"{self._base_url}{path}",
            params=params,
            timeout=ClientTimeout(total=REST_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _fetch_daily(self) -> dict[str, Any]:
        payload = await self._get_json(API_PATH_DAILY)
        if not payload:
            return {"detections_today": 0, "species_today": 0}

        detections_today = sum(item.get("count", 0) for item in payload)
        top = max(payload, key=lambda item: item.get("count", 0))
        return {
            "detections_today": detections_today,
            "species_today": len(payload),
            "top_species": top.get("common_name"),
            "top_species_scientific": top.get("scientific_name"),
            "top_species_count": top.get("count"),
            "top_species_thumbnail": (
                f"{self._base_url}{top['thumbnail_url']}" if top.get("thumbnail_url") else None
            ),
        }

    async def _fetch_summary(self) -> dict[str, Any]:
        payload = await self._get_json(API_PATH_SUMMARY)
        if not payload:
            return {"total_species": 0, "total_detections": 0}
        return {
            "total_species": len(payload),
            "total_detections": sum(item.get("count", 0) for item in payload),
        }

    async def _fetch_recent(self) -> dict[str, Any]:
        payload = await self._get_json(API_PATH_RECENT, params={"limit": 1})
        if not payload:
            return {}
        return self._detection_to_fields(payload[0])

    # ------------------------------------------------------------------
    # SSE push
    # ------------------------------------------------------------------

    def _detection_to_fields(self, detection: dict[str, Any]) -> dict[str, Any]:
        scientific = detection.get("scientificName")
        return {
            "last_detection": detection.get("commonName"),
            "last_detection_scientific": scientific,
            "last_detection_confidence": (
                round(detection["confidence"] * 100) if detection.get("confidence") is not None else None
            ),
            "last_detection_time": detection.get("timestamp"),
            "last_detection_image": (
                f"{self._base_url}{API_PATH_MEDIA_IMAGE}{quote(scientific)}"
                if scientific
                else None
            ),
        }

    def start_sse(self) -> None:
        """Start the background SSE listener task."""
        if self._sse_task is None or self._sse_task.done():
            self._sse_task = self.hass.async_create_background_task(
                self._sse_loop(), name="birdnet_go_sse"
            )

    async def stop_sse(self) -> None:
        if self._sse_task is not None:
            self._sse_task.cancel()
            self._sse_task = None

    async def _sse_loop(self) -> None:
        """Reconnect-forever loop reading /api/v2/detections/stream."""
        backoff = SSE_RECONNECT_MIN
        while True:
            try:
                await self._sse_read_once()
                backoff = SSE_RECONNECT_MIN  # clean disconnect, reset backoff
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 — reconnect on anything, log and retry
                _LOGGER.debug("BirdNET-Go SSE stream error, reconnecting: %s", err)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, SSE_RECONNECT_MAX)

    async def _sse_read_once(self) -> None:
        async with self._session.get(
            f"{self._base_url}{API_PATH_STREAM}",
            timeout=ClientTimeout(total=None, sock_connect=SSE_CONNECT_TIMEOUT),
            headers={"Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            _LOGGER.debug("BirdNET-Go SSE connected")
            buffer = ""
            async for chunk in resp.content.iter_any():
                buffer += chunk.decode("utf-8", errors="ignore")
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    self._handle_sse_event(event)

    def _handle_sse_event(self, event: str) -> None:
        data_lines = [
            line[len("data:") :].strip()
            for line in event.splitlines()
            if line.startswith("data:")
        ]
        if not data_lines:
            return
        try:
            payload = json.loads("".join(data_lines))
        except json.JSONDecodeError:
            return

        detection = payload
        if isinstance(payload, dict) and "detection" in payload:
            detection = payload["detection"]
        if isinstance(detection, list):
            detection = detection[0] if detection else None
        if not isinstance(detection, dict) or "commonName" not in detection:
            return  # connection-confirmation / heartbeat message, not a detection

        new_data = dict(self.data)
        new_data.update(self._detection_to_fields(detection))
        new_data["available"] = True
        self.async_set_updated_data(new_data)
