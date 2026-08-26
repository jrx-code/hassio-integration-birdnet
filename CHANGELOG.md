# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0] — 2026-08-26

### Added
- `birdnet-go-card` visual (GUI) config editor via `getConfigElement()` —
  a single `ha-form` bound to a device selector scoped to the `birdnet_go`
  integration. Previously the card picker showed "Visual editor not
  supported" and forced YAML for the one optional `device_id` field.

Verified live on PVE VM 103 (`HA-inpost-dev`, 192.168.18.178) via HACS
(custom repository → download v1.5.0 → restart): editing the existing
card now opens a "Config" tab with a "Select a device" dropdown instead
of the YAML-only fallback, live preview updates alongside it.

## [1.4.1] — 2026-08-26

### Fixed
- `birdnet-go-card` never found its entities — `unique_id` isn't exposed
  on the frontend's `hass.entities` snapshot at all (confirmed live), so
  the `.endsWith(unique_id)` matching always came up empty. Now matches
  on `translation_key` instead, which the frontend does expose and is set
  to the exact same string as each entity description's `key`.
- `frontend/__init__.py` never actually created the Lovelace resource —
  checked `lovelace.mode`, but `LovelaceData`'s real field is
  `resource_mode` (confirmed against home-assistant/core source); the
  wrong attribute name meant `getattr(..., None)` silently took the
  "not storage mode" branch every time, no error logged.
- `binary_sensor.py`: `entity_category="diagnostic"` (a plain string)
  crashed `binary_sensor` platform setup with `ValueError: entity_category
  must be a valid EntityCategory instance` on this restart — now uses
  `EntityCategory.DIAGNOSTIC`. Root cause of why it hadn't errored on
  earlier restarts this session is still open — the registry validation
  path for an already-registered entity vs. one entity_registry treats as
  new isn't fully understood; flagging as a known unknown rather than
  guessing.
- Added `lovelace` to `manifest.json` dependencies (was relying on load
  order without declaring it).

All three fixes verified: the entity/resource-mode fixes against a
synthetic `hass` object injected client-side into PVE VM 103
(`HomeAssistant-test`, 192.168.18.178) — a test instance, not production;
the `entity_category` fix and the resource registration itself against
production, since that's where the crash and the missing resource were
first found (before the "test VM only" instruction landed).

## [1.4.0] — 2026-08-26

### Added
- `birdnet-go-card` — a Lovelace card bundled with the integration and
  auto-registered as a frontend resource on startup (storage-mode
  Lovelace; no manual "add resource" step). Plain custom element, no
  build step/bundler dependency. Resolves its entities by scanning
  `hass.entities` for `platform === "birdnet_go"` and matching each
  one's `unique_id` suffix, so it survives entity renames; picks the
  first BirdNET-Go device found, or a specific one via `device_id` in
  the card config.
- `manifest.json` now declares `dependencies: ["frontend", "http"]`,
  required for the static-path/resource registration to work.

No visual (GUI) card editor — configure via the card picker's YAML/code
editor. Reasonable for a card with a single optional `device_id` option.

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
