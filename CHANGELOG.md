# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] — 2026-08-25

### Added
- Initial release — config_flow (host + verify_ssl)
- `DataUpdateCoordinator` with REST polling (daily 5 min / summary 1 h) + background SSE listener on `/api/v2/detections/stream`
- 13 sensors + 1 binary_sensor (connectivity), single "BirdNET-Go" device
- No MQTT dependency — direct REST+SSE connection to the BirdNET-Go host
