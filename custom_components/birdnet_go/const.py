"""Constants for the BirdNET-Go integration."""

from __future__ import annotations

DOMAIN = "birdnet_go"

CONF_HOST = "host"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_HOST = ""
DEFAULT_VERIFY_SSL = True

# REST polling — stats that only change slowly, no point pushing them over SSE
SCAN_INTERVAL_DAILY = 300  # 5 min — today's species/detections
SCAN_INTERVAL_SUMMARY = 3600  # 1 h — all-time totals

# SSE reconnect backoff (seconds)
SSE_RECONNECT_MIN = 5
SSE_RECONNECT_MAX = 120

API_PATH_DAILY = "/api/v2/analytics/species/daily"
API_PATH_SUMMARY = "/api/v2/analytics/species/summary"
API_PATH_RECENT = "/api/v2/detections/recent"
API_PATH_STREAM = "/api/v2/detections/stream"
API_PATH_MEDIA_IMAGE = "/api/v2/media/image/"

# request timeouts
REST_TIMEOUT = 15
SSE_CONNECT_TIMEOUT = 15
