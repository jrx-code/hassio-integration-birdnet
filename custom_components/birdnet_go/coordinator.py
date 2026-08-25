"""Data coordinator for BirdNET-Go.

Combines two data paths against the BirdNET-Go host directly — no MQTT broker
involved:

- REST polling (`DataUpdateCoordinator`, every SCAN_INTERVAL_DAILY) for the
  slow-moving stats (today's/all-time species+detection counts).
- A long-lived SSE connection to `/api/v2/detections/stream` for the
  real-time "last detection" fields, pushed the instant BirdNET-Go emits one.

Either path calls `async_set_updated_data()` so entities update on whichever
happens first.

The actual payload → field mapping lives in `parsing.py` as plain functions —
this module is just the async plumbing (HTTP, SSE, coordinator lifecycle)
around them.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_PATH_DAILY,
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
from .parsing import (
    daily_to_fields,
    detection_to_fields,
    parse_sse_detection,
    summary_to_fields,
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
        """Initialize the coordinator for the given BirdNET-Go host."""
        super().__init__(
            hass,
            _LOGGER,
            name="BirdNET-Go",
            update_interval=timedelta(seconds=SCAN_INTERVAL_DAILY),
        )
        self._host = host.rstrip("/")
        self._base_url = f"https://{self._host}"
        self._verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession = async_get_clientsession(
            hass, verify_ssl=verify_ssl
        )
        self.data: dict[str, Any] = _empty_data()

        self._sse_task: asyncio.Task | None = None
        self._last_summary_fetch: datetime | None = None

    # ------------------------------------------------------------------
    # REST polling
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        data = dict(self.data)
        try:
            data.update(
                daily_to_fields(await self._get_json(API_PATH_DAILY), self._base_url)
            )

            now = dt_util.utcnow()
            if (
                self._last_summary_fetch is None
                or (now - self._last_summary_fetch).total_seconds()
                >= SCAN_INTERVAL_SUMMARY
            ):
                data.update(summary_to_fields(await self._get_json(API_PATH_SUMMARY)))
                self._last_summary_fetch = now

            if data.get("last_detection") is None:
                recent = await self._get_json(API_PATH_RECENT, params={"limit": 1})
                if recent:
                    data.update(detection_to_fields(recent[0], self._base_url))

            data["available"] = True
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(
                f"BirdNET-Go host {self._host} unreachable: {err}"
            ) from err
        return data

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with self._session.get(
            f"{self._base_url}{path}",
            params=params,
            timeout=ClientTimeout(total=REST_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    # ------------------------------------------------------------------
    # SSE push
    # ------------------------------------------------------------------

    def start_sse(self) -> None:
        """Start the background SSE listener task."""
        if self._sse_task is None or self._sse_task.done():
            self._sse_task = self.hass.async_create_background_task(
                self._sse_loop(), name="birdnet_go_sse"
            )

    async def stop_sse(self) -> None:
        """Cancel the background SSE listener task, if running."""
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

        detection = parse_sse_detection(payload)
        if detection is None:
            return  # connection-confirmation / heartbeat message, not a detection

        new_data = dict(self.data)
        new_data.update(detection_to_fields(detection, self._base_url))
        new_data["available"] = True
        self.async_set_updated_data(new_data)
