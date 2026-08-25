# BirdNET-Go — Home Assistant Integration

[![Validate](https://github.com/jrx-code/hassio-integration-birdnet/actions/workflows/validate.yml/badge.svg)](https://github.com/jrx-code/hassio-integration-birdnet/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/jrx-code/hassio-integration-birdnet)](https://github.com/jrx-code/hassio-integration-birdnet/releases)

A custom Home Assistant integration for [BirdNET-Go](https://github.com/tphakala/birdnet-go). Connects **directly to your BirdNET-Go host** over REST + SSE — no MQTT broker required.

<p align="center">
  <img src="docs/screenshots/device-entities.png" width="49%" alt="Device page — all entities, live data, thumbnail">
  <img src="docs/screenshots/config-flow.png" width="49%" alt="Add integration — host + verify SSL form">
</p>

Screenshots from a live install — real detection data (BirdNET-Go host redacted). Full UI, entity list and setup dialog automatically switch to your Home Assistant's language (English + Polish translations ship today, see [Localization](#localization)).

## Why no MQTT

BirdNET-Go has built-in MQTT auto-discovery (since nightly-20260111), but that's still an indirect path: BirdNET-Go → broker → HA's MQTT integration → entities, with the broker as an extra dependency. BirdNET-Go's REST API v2 also exposes `GET /api/v2/detections/stream` — a public SSE endpoint (Server-Sent Events, no auth, rate-limited to 10 connections/min/IP) that pushes new detections the instant they happen. Combined with REST polling for the slower-moving stats, this integration talks to BirdNET-Go directly — one less moving part in the chain.

## Architecture

- **`coordinator.py`** — a `DataUpdateCoordinator` with two data paths:
  - REST polling every 5 min (`/api/v2/analytics/species/daily`) and every hour (`/api/v2/analytics/species/summary`)
  - a background task reading `/api/v2/detections/stream` (SSE), reconnecting with exponential backoff (5s→120s), calling `async_set_updated_data()` on every new detection
- **`config_flow.py`** — add via the UI: host + verify SSL, validated against `GET /api/v2/detections/recent?limit=1`
- **`sensor.py`** / **`binary_sensor.py`** / **`image.py`** — a single "BirdNET-Go" device with 11 sensors, 2 image entities, 1 connectivity binary_sensor

All entities are enabled by default — nothing hidden behind "show disabled entities".

## Entities

| Entity | Source |
|---|---|
| `sensor.birdnet_go_last_detection` (+ scientific name, time, confidence) | SSE push |
| `sensor.birdnet_go_detections_today` / `species_today` | REST, every 5 min |
| `sensor.birdnet_go_top_species` (+ scientific name, count) | REST, every 5 min |
| `sensor.birdnet_go_total_species` / `total_detections` | REST, hourly |
| `image.birdnet_go_last_detection_image` | SSE push |
| `image.birdnet_go_top_species_thumbnail` | REST, every 5 min |
| `binary_sensor.birdnet_go_status` | connectivity — last REST/SSE contact succeeded |

The two `image` entities are HA's proper `image` platform, not a URL-string sensor — HA fetches and caches the picture itself and serves it back through its own `/api/image_proxy/...` endpoint, so it stays reachable even when the browser has no direct network path to the BirdNET-Go host.

## Card

The integration ships its own Lovelace card — `custom_components/birdnet_go/frontend/birdnet-go-card.js` — and registers it as a frontend resource automatically on startup (storage-mode Lovelace; no manual "add resource" step). It's a plain custom element with no build step, so there's no separate JS toolchain to keep in sync with the Python side.

```yaml
type: custom:birdnet-go-card
# device_id: <id>   # optional — only needed with more than one BirdNET-Go device
```

It finds its entities by scanning the entity registry for `platform: birdnet_go` and matching each one's `translation_key` — not by guessing entity_ids, so renaming entities or the device doesn't break it. (`unique_id` would have been the more obvious match target, but it isn't exposed on the frontend's entity registry snapshot at all.) No visual (GUI) editor; configure via the card picker's YAML/code editor.

<p align="center">
  <img src="docs/screenshots/birdnet-go-card.png" width="60%" alt="The bundled birdnet-go-card, rendered in a dashboard">
</p>

## Installation

### HACS (custom repository)
1. HACS → ⋮ → Custom repositories → add this repo URL, category **Integration**
2. Install "BirdNET-Go", restart Home Assistant

### Manual
Copy `custom_components/birdnet_go/` into your HA `config/custom_components/`, restart.

Then: **Settings → Devices & Services → Add Integration → "BirdNET-Go"** (pictured above), enter your BirdNET-Go host (e.g. `192.168.1.50:8080` or a domain if you reverse-proxy it with HTTPS).

<p align="center">
  <img src="docs/screenshots/add-integration-picker.png" width="60%" alt="Add integration search — brand icon in the picker">
</p>

## Quality

- `custom_components/birdnet_go/parsing.py` — the payload → entity-field mapping — is deliberately plain Python with **no `homeassistant` import**, so it's unit-testable without the full HA test harness. `tests/test_parsing.py` (19 tests) covers it, run with `pytest tests/`.
- Linted with [Ruff](https://docs.astral.sh/ruff/) against the same ruleset Home Assistant core uses for its own integrations (`pyproject.toml`).
- CI (`.github/workflows/validate.yml`): Hassfest, HACS validation, Ruff, pytest — all required to pass on every push/PR.

## Localization

HA picks `translations/<lang>.json` by the user's own HA language setting — nothing to configure. Currently shipped: `en`, `pl`. Contributions for more languages welcome (PR against `custom_components/birdnet_go/translations/`, `strings.json` is the English source of truth).

## Status

Running live against a real BirdNET-Go instance (screenshots above are from that install). `manifest.json`/`config_flow`/translations/brand assets are validated in CI (hassfest + HACS action, see badge at the top).

## License

MIT — see [LICENSE](LICENSE).
