# Changelog

All notable changes to this project will be documented in this file.

## [1.9.0] — 2026-08-27

### Added
- French translations (`translations/fr.json`) — contributed by
  [@Aimache](https://github.com/Aimache) in #2. Covers the config flow
  (host, SSL verification, error/abort messages) and all entity names
  (sensors, binary sensor, images). Key set verified identical to `en.json`.

### Fixed
- French: spelling/accents corrected after merge (`Connexion`, `Vérifier`,
  `Échec`, `espèces`, `détections`, `Statut`).

## [1.8.0] — 2026-08-26

### Added
- `birdnet-go-card` three new `layout` values — **Silhouette**, **Plaque**,
  **Bar** — compact fixed-height tile designs, not a caption treatment of
  the normal body like `overlay`: they replace header/stats/top-species
  entirely with a single small block. Silhouette bleeds the photo off the
  right edge, masked to fade into the card background, with the text
  column over the faded part. Plaque puts a rounded-square thumbnail
  beside left-aligned text. Bar puts a circular thumbnail beside
  right-aligned text. All three reuse the preset's existing `show_*`
  toggles for content — no new config fields — and bake in
  bleed/thumbnail-size/gap as fixed layout constants, tuned in a
  standalone POC (`ptaki-trzy.html`) against a real detection photo. Like
  `overlay`, each falls back to `stacked` whenever there's no photo (image
  hidden, or none loaded yet).
- Editor: three new options in the layout selector, alongside
  Stacked/Overlay.

Verified live on PVE VM 103 (`HA-inpost-dev`, 192.168.18.178): pushed the
updated card file directly (no HACS re-download needed for a JS-only
change), then all three layouts rendered correctly on a real detection
(Kopciuszek, 45%) in the card's own config-editor live preview — photo
bleed/fade, thumbnail shape/size, text alignment all as designed. Zero
console errors.

## [1.7.0] — 2026-08-26

### Added
- `birdnet-go-card` new `layout` config field, independent of `preset`:
  **Stacked** (default, unchanged) has name/scientific/badges below the
  photo; **Overlay** puts them as a gradient-scrim caption directly on the
  photo (poster style), with confidence/time as corner badges over the
  image and the connectivity pill top-right. Any preset can combine with
  either layout (e.g. "Nerd + Overlay"). Falls back to stacked whenever
  there's no photo to overlay onto (image hidden, or none loaded yet).
- Editor: "Photo caption style" selector (Stacked/Overlay), shown
  regardless of preset, right above the preset picker.

Verified live on PVE VM 103 (`HA-inpost-dev`, 192.168.18.178) via HACS
(custom repository → download v1.7.0 → restart): Nerd preset + Overlay
layout rendered correctly on a real detection (Kopciuszek, 42%) — name
and scientific name as a gradient-scrim caption on the photo, confidence
and time as corner chips, ONLINE pill top-right; stats row and
top-species section unaffected below.

## [1.6.0] — 2026-08-26

### Added
- `birdnet-go-card` layout presets: **Basic** (photo + name), **Simple**
  (+ confidence/time badges, today/species/total stats — the previous
  fixed layout, now the default), **Advanced** (+ connectivity pill, "top
  species today" mini-section), **Nerd** (+ all-time known-species count).
  Picking **Custom** in the editor unlocks eight individual `show_*`
  toggles (image, scientific name, confidence, time, connectivity,
  stats row, total-species count, top-species section) for people who
  want a mix that doesn't match a named preset.
- New optional entities surfaced when enabled: `sensor.birdnet_go_top_species`
  (+ scientific name, count, thumbnail) in a dedicated card section, and
  `sensor.birdnet_go_total_species` as a fourth stat.
- Visual restyle: confidence/time as icon chips, connectivity as a colored
  online/offline pill (was a plain dot), stat row got icons and dividers,
  top-species section is a circular-thumbnail mini-card.
- Editor UX: switching a card to "Custom" seeds the eight toggles from
  whichever named preset was active, instead of starting blank; switching
  back to a named preset drops the per-field overrides so the saved config
  stays a minimal `{ preset, device_id }` for the common case.

### Changed
- Card rebuilds its full DOM on every render instead of patching individual
  nodes — the preset/toggle-driven layout has too many structurally
  different shapes (image or not, stats row or not, top-species section or
  not) for incremental patching to stay simple and correct. A dedicated
  delegated click listener (bound once in the constructor, not per render)
  keeps more-info navigation working across rebuilds.
- `getStubConfig()` now returns `{ preset: "simple" }` instead of `{}`, so
  a freshly added card explicitly shows what it defaults to.

Verified live on PVE VM 103 (`HA-inpost-dev`, 192.168.18.178) via HACS
(custom repository → download v1.6.0 → restart): editor shows the preset
radio list plus live preview; Nerd preset rendered all four stats (incl.
the 162 all-time known-species count) and the top-species-today
mini-card with circular thumbnail on a real new detection (Kopciuszek,
42% confidence); Custom correctly seeded all eight toggles from Nerd's
values when switched into.

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
