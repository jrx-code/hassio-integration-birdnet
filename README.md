# BirdNET-Go — Home Assistant Integration

[![Validate](https://github.com/jrx-code/hassio-integration-birdnet/actions/workflows/validate.yml/badge.svg)](https://github.com/jrx-code/hassio-integration-birdnet/actions/workflows/validate.yml)

A custom Home Assistant integration for [BirdNET-Go](https://github.com/tphakala/birdnet-go). Connects **directly to your BirdNET-Go host** over REST + SSE — no MQTT broker required.

## Why no MQTT

BirdNET-Go has built-in MQTT auto-discovery (since nightly-20260111), but that's still an indirect path: BirdNET-Go → broker → HA's MQTT integration → entities, with the broker as an extra dependency. BirdNET-Go's REST API v2 also exposes `GET /api/v2/detections/stream` — a public SSE endpoint (Server-Sent Events, no auth, rate-limited to 10 connections/min/IP) that pushes new detections the instant they happen. Combined with REST polling for the slower-moving stats, this integration talks to BirdNET-Go directly — one less moving part in the chain.

## Architecture

- **`coordinator.py`** — a `DataUpdateCoordinator` with two data paths:
  - REST polling every 5 min (`/api/v2/analytics/species/daily`) and every hour (`/api/v2/analytics/species/summary`)
  - a background task reading `/api/v2/detections/stream` (SSE), reconnecting with exponential backoff (5s→120s), calling `async_set_updated_data()` on every new detection
- **`config_flow.py`** — add via the UI: host + verify SSL, validated against `GET /api/v2/detections/recent?limit=1`
- **`sensor.py`** / **`binary_sensor.py`** — a single "BirdNET-Go" device with 13 sensors + 1 connectivity binary_sensor

## Entities

| Entity | Source |
|---|---|
| `sensor.birdnet_go_last_detection` (+ scientific name, time, confidence, image) | SSE push |
| `sensor.birdnet_go_detections_today` / `species_today` | REST, every 5 min |
| `sensor.birdnet_go_top_species` (+ scientific name, count, thumbnail) | REST, every 5 min |
| `sensor.birdnet_go_total_species` / `total_detections` | REST, hourly |
| `binary_sensor.birdnet_go_status` | connectivity — last REST/SSE contact succeeded |

## Installation

### HACS (custom repository)
1. HACS → ⋮ → Custom repositories → add this repo URL, category **Integration**
2. Install "BirdNET-Go", restart Home Assistant

### Manual
Copy `custom_components/birdnet_go/` into your HA `config/custom_components/`, restart.

Then: **Settings → Devices & Services → Add Integration → "BirdNET-Go"**, enter your BirdNET-Go host (e.g. `192.168.1.50:8080` or a domain if you reverse-proxy it with HTTPS).

## Status

No screenshots yet — the integration hasn't been added to a live Home Assistant instance in this repo's history yet, so there's nothing real to show. `manifest.json`/`config_flow`/translations/brand assets are validated in CI (hassfest + HACS action, see badge at the top); functional testing against a live BirdNET-Go instance is still open.

## License

MIT — see [LICENSE](LICENSE).
