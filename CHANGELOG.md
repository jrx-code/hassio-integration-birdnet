# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] — 2026-08-25

Preparing for a HACS default-repository submission — no functional/entity changes.

### Added
- `parsing.py` — the BirdNET-Go payload → entity-field mapping extracted into
  plain functions with no `homeassistant` import, so it's testable without
  the full HA test harness
- `tests/test_parsing.py` — 19 unit tests covering it (empty payloads, missing
  keys, the percent-encoding regression from 1.2.0, SSE payload shapes)
- `pyproject.toml` — Ruff configured with the same ruleset Home Assistant
  core uses for its own integrations; `ruff`/`pytest` CI jobs
- Docstrings on all public methods (was passing hassfest/HACS without them,
  but `ruff check` against HA's own ruleset flagged the gaps)

### Changed
- `coordinator.py` no longer contains any payload-shaping logic — it's pure
  async plumbing (HTTP/SSE/coordinator lifecycle) around `parsing.py`
- `datetime.utcnow()` → `dt_util.utcnow()` (HA's own helper; `utcnow()` is
  deprecated and returns a naive datetime)

## [1.2.0] — 2026-08-25

### Added
- Polish translation (`translations/pl.json`) — HA auto-selects it by the
  user's language setting
- `source_url` attribute on both `image` entities — the raw BirdNET-Go URL,
  for external consumers (notifications, WhatsApp API, ...) that can't use
  HA's authenticated `/api/image_proxy/...` link
- Screenshots in README (device page, add-integration picker, config flow)

### Fixed
- `last_detection_time` was permanently stuck `unavailable` —
  `device_class: timestamp` requires `native_value` to be a real
  `datetime.datetime` with tzinfo, not the ISO string BirdNET-Go returns;
  now parsed with `dt_util.parse_datetime()`
- `last_detection_image` source URL wasn't percent-encoded (a raw space in
  the scientific name produced an invalid URL)
- Two orphaned entity-registry rows left over from the pre-1.1.0
  URL-string sensors (`last_detection_image`, `top_species_thumbnail`)
  removed via the WS API

## [1.1.0] — 2026-08-25

### Changed
- All entities now enabled by default (previously the scientific-name and
  image-URL sensors were disabled by default)
- `last_detection_image` / `top_species_thumbnail` moved from URL-string
  sensors to proper `image` platform entities (`image.py`) — HA fetches and
  proxies the picture itself instead of the frontend loading the URL
  directly

## [1.0.0] — 2026-08-25

### Added
- Initial release — config_flow (host + verify_ssl)
- `DataUpdateCoordinator` with REST polling (daily 5 min / summary 1 h) + background SSE listener on `/api/v2/detections/stream`
- 13 sensors + 1 binary_sensor (connectivity), single "BirdNET-Go" device
- No MQTT dependency — direct REST+SSE connection to the BirdNET-Go host
