# Changelog

All notable changes to this project will be documented in this file.

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
