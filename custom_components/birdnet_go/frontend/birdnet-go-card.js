/**
 * BirdNET-Go Card — ships with the integration, auto-registered as a
 * Lovelace resource (see frontend/__init__.py). No build step: a plain
 * custom element, no Lit/bundler dependency, so there's nothing to compile
 * and nothing that can drift out of sync with a separate build pipeline.
 *
 * Resolves its entities by scanning `hass.entities` for
 * `platform === "birdnet_go"` and matching each one's `translation_key`
 * (set to the exact same string as each entity description's `key` in
 * sensor.py/image.py/binary_sensor.py) — not by guessing entity_ids from a
 * naming convention, so it keeps working if the user renames entities or
 * the device. `unique_id` would have been the more obvious match target,
 * but it isn't exposed on the frontend's `hass.entities` snapshot at all
 * (confirmed live 2026-08-26). If more than one BirdNET-Go device is
 * configured, pass `device_id` in the card config to pick one; otherwise
 * the first one found is used.
 *
 * What shows is preset-driven (`config.preset`): basic/simple/advanced/nerd
 * each turn a fixed set of `show_*` booleans on, so most people never touch
 * an individual toggle. Picking "custom" in the editor unlocks the
 * individual `show_*` fields for fine control. Presets aren't persisted
 * into the saved config — only `preset` (+ overrides when it's "custom")
 * is, so a later preset addition/tweak here applies retroactively to any
 * card still on a named preset.
 *
 * How it's arranged is a separate, orthogonal knob: `config.layout`.
 * "stacked" (default) is name/scientific/badges below the photo. "overlay"
 * puts name/scientific/status as a gradient-scrim caption directly on the
 * photo (poster style) and confidence/time as corner badges over it —
 * independent of which preset is active, so e.g. "nerd + overlay" is a
 * valid combination. Falls back to stacked whenever there's no photo to
 * overlay onto (image hidden, or none downloaded yet).
 *
 * Three more layouts — "silhouette", "plaque", "bar" — are compact,
 * fixed-height tile designs, not a caption treatment of the normal body:
 * they replace header/stats/top-species entirely with a single small block
 * (see `_renderTile`). Tuned against a real detection photo in a standalone
 * POC (`ptaki-trzy.html`, panel-salon-sekcje, 2026-08-26) and ported here at
 * the values that POC settled on — bleed/fade/thumbnail-size/gap are fixed
 * per layout, not exposed as card config, same as overlay's scrim isn't.
 * The POC's saturation/brightness sliders aren't ported: those existed to
 * tame a generic Wikimedia stock illustration used while tuning, and don't
 * apply to a real BirdNET-Go detection photo. Like overlay, each falls back
 * to stacked whenever there's no photo (image hidden, or none yet).
 *
 * Visual (GUI) config editor via `getConfigElement()` — `ha-form` with a
 * device selector plus the preset/toggle schema below. `ha-form`, `ha-icon`
 * and the `device` selector are all loaded by the frontend already; no
 * import needed here, just use the custom elements by tag name.
 */

const PRESETS = {
  basic: {
    show_image: true,
    show_scientific: false,
    show_confidence: false,
    show_time: false,
    show_status: false,
    show_stats: false,
    show_total_species: false,
    show_top_species: false,
  },
  simple: {
    show_image: true,
    show_scientific: true,
    show_confidence: true,
    show_time: true,
    show_status: true,
    show_stats: true,
    show_total_species: false,
    show_top_species: false,
  },
  advanced: {
    show_image: true,
    show_scientific: true,
    show_confidence: true,
    show_time: true,
    show_status: true,
    show_stats: true,
    show_total_species: false,
    show_top_species: true,
  },
  nerd: {
    show_image: true,
    show_scientific: true,
    show_confidence: true,
    show_time: true,
    show_status: true,
    show_stats: true,
    show_total_species: true,
    show_top_species: true,
  },
};

const TOGGLE_FIELDS = Object.keys(PRESETS.simple);

// Fixed-height tile layouts — see the class doc comment above for what
// they are and why the POC's photo-tinting sliders aren't ported.
const TILE_LAYOUTS = ["silhouette", "plaque", "bar"];
// Pre-1.10 configs used Polish layout values; keep them working unchanged.
const LAYOUT_ALIASES = { sylwetka: "silhouette", tabliczka: "plaque", pasek: "bar" };
const normalizeLayout = (layout) => LAYOUT_ALIASES[layout] || layout;

// UI strings, picked by the HA user's language (hass.locale.language),
// falling back to English. Config values themselves are always English.
const STRINGS = {
  en: {
    layout_stacked: "Stacked — text below the photo",
    layout_overlay: "Overlay — caption on the photo",
    layout_silhouette: "Silhouette — photo bleeds off the edge",
    layout_plaque: "Plaque — rounded thumbnail beside text",
    layout_bar: "Bar — circular thumbnail, right-aligned text",
    preset_basic: "Basic — photo & name only",
    preset_simple: "Simple — + confidence, time, stats",
    preset_advanced: "Advanced — + status & top species today",
    preset_nerd: "Nerd — everything, incl. all-time species count",
    preset_custom: "Custom — pick fields individually",
    field_device_id: "BirdNET-Go device (optional)",
    field_layout: "Card layout",
    field_preset: "Information preset",
    field_show_image: "Last detection photo",
    field_show_scientific: "Scientific name",
    field_show_confidence: "Confidence badge",
    field_show_time: "Time badge",
    field_show_status: "Connectivity pill",
    field_show_stats: "Today / species / total stats row",
    field_show_total_species: "All-time known species count",
    field_show_top_species: "Top species today section",
    stat_today: "today",
    stat_species: "species",
    stat_total: "total",
    stat_known: "known",
    online: "online",
    offline: "offline",
    top_species_today: "Top species today",
  },
  pl: {
    layout_stacked: "Stos — tekst pod zdjęciem",
    layout_overlay: "Nakładka — podpis na zdjęciu",
    layout_silhouette: "Sylwetka — zdjęcie wychodzi poza krawędź",
    layout_plaque: "Tabliczka — zaokrąglona miniatura obok tekstu",
    layout_bar: "Pasek — okrągła miniatura, tekst do prawej",
    preset_basic: "Podstawowy — tylko zdjęcie i nazwa",
    preset_simple: "Prosty — + pewność, czas, statystyki",
    preset_advanced: "Zaawansowany — + status i gatunek dnia",
    preset_nerd: "Nerd — wszystko, łącznie z liczbą znanych gatunków",
    preset_custom: "Własny — wybierz pola ręcznie",
    field_device_id: "Urządzenie BirdNET-Go (opcjonalne)",
    field_layout: "Układ karty",
    field_preset: "Zestaw informacji",
    field_show_image: "Zdjęcie ostatniej detekcji",
    field_show_scientific: "Nazwa naukowa",
    field_show_confidence: "Znacznik pewności",
    field_show_time: "Znacznik czasu",
    field_show_status: "Wskaźnik połączenia",
    field_show_stats: "Wiersz statystyk: dziś / gatunki / razem",
    field_show_total_species: "Liczba wszystkich znanych gatunków",
    field_show_top_species: "Sekcja gatunku dnia",
    stat_today: "dziś",
    stat_species: "gatunki",
    stat_total: "razem",
    stat_known: "znane",
    online: "online",
    offline: "offline",
    top_species_today: "Gatunek dnia",
  },
  fr: {
    layout_stacked: "Empilé — texte sous la photo",
    layout_overlay: "Superposé — légende sur la photo",
    layout_silhouette: "Silhouette — la photo déborde du bord",
    layout_plaque: "Plaque — vignette arrondie à côté du texte",
    layout_bar: "Barre — vignette ronde, texte aligné à droite",
    preset_basic: "Basique — photo et nom uniquement",
    preset_simple: "Simple — + confiance, heure, statistiques",
    preset_advanced: "Avancé — + statut et espèce du jour",
    preset_nerd: "Nerd — tout, y compris le total d'espèces connues",
    preset_custom: "Personnalisé — choisir les champs un par un",
    field_device_id: "Appareil BirdNET-Go (optionnel)",
    field_layout: "Disposition de la carte",
    field_preset: "Niveau d'information",
    field_show_image: "Photo de la dernière détection",
    field_show_scientific: "Nom scientifique",
    field_show_confidence: "Badge de confiance",
    field_show_time: "Badge d'heure",
    field_show_status: "Indicateur de connexion",
    field_show_stats: "Ligne de statistiques : jour / espèces / total",
    field_show_total_species: "Nombre total d'espèces connues",
    field_show_top_species: "Section espèce du jour",
    stat_today: "aujourd'hui",
    stat_species: "espèces",
    stat_total: "total",
    stat_known: "connues",
    online: "en ligne",
    offline: "hors ligne",
    top_species_today: "Espèce du jour",
  },
};

function translate(hass, key) {
  const lang = (hass?.locale?.language || hass?.language || "en").split("-")[0];
  return STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key;
}
const TILE_HEIGHT = 190; // px — the POC's tuned "wys" default

class BirdnetGoCard extends HTMLElement {
  constructor() {
    super();
    // One delegated listener survives every _render() rebuilding the DOM —
    // no per-render addEventListener/element churn to keep in sync.
    this.addEventListener("click", (ev) => {
      const el = ev.target.closest("[data-action]");
      if (!el) return;
      const actions = {
        "open-image": "last_detection_image",
        "open-detection": "last_detection",
        "open-top-species": "top_species",
      };
      this._openMoreInfo(actions[el.dataset.action]);
    });
  }

  setConfig(config) {
    this._config = config || {};
    this._entityIds = null; // force re-resolution on config change
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._entityIds) {
      this._entityIds = this._resolveEntities(hass);
    }
    this._render();
  }

  getCardSize() {
    const cfg = this._effectiveConfig();
    if (TILE_LAYOUTS.includes(cfg.layout)) {
      return Math.max(1, Math.round(TILE_HEIGHT / 56)); // fixed-height tile, ~56px/row
    }
    let size = 1;
    if (cfg.show_image) size += 3;
    if (cfg.show_stats || cfg.show_total_species) size += 1;
    if (cfg.show_top_species) size += 1;
    return size;
  }

  static getStubConfig() {
    return { preset: "simple", layout: "stacked" };
  }

  static getConfigElement() {
    return document.createElement("birdnet-go-card-editor");
  }

  // Named preset → fixed flags; "custom" → preset fields with the user's
  // per-toggle overrides layered on top, so a half-filled custom config
  // (only some `show_*` keys set) still has sane defaults for the rest.
  // `layout` rides along unchanged — it's independent of preset.
  _effectiveConfig() {
    const config = this._config || {};
    const preset = config.preset || "simple";
    const requested = normalizeLayout(config.layout);
    const layout = ["overlay", ...TILE_LAYOUTS].includes(requested) ? requested : "stacked";
    if (preset !== "custom") {
      return { ...(PRESETS[preset] || PRESETS.simple), layout };
    }
    const merged = { ...PRESETS.simple, layout };
    for (const field of TOGGLE_FIELDS) {
      if (typeof config[field] === "boolean") merged[field] = config[field];
    }
    return merged;
  }

  _resolveEntities(hass) {
    const entries = Object.values(hass.entities || {}).filter(
      (e) => e.platform === "birdnet_go"
    );
    if (this._config.device_id) {
      const scoped = entries.filter((e) => e.device_id === this._config.device_id);
      if (scoped.length) return this._matchByTranslationKey(scoped);
    }
    return this._matchByTranslationKey(entries);
  }

  // `unique_id` isn't exposed on the frontend's `hass.entities` registry
  // snapshot (confirmed live 2026-08-26 — the field is simply absent, not
  // just empty), so `translation_key` is what identifies each entity's
  // role; it's set to the exact same string as each entity description's
  // `key` in sensor.py/image.py/binary_sensor.py.
  _matchByTranslationKey(entries) {
    const found = {};
    for (const entry of entries) {
      if (entry.translation_key && !found[entry.translation_key]) {
        found[entry.translation_key] = entry.entity_id;
      }
    }
    return found;
  }

  _state(key) {
    const entityId = this._entityIds && this._entityIds[key];
    if (!entityId || !this._hass) return undefined;
    return this._hass.states[entityId];
  }

  _text(key, fallback = "—") {
    const st = this._state(key);
    if (!st || st.state === "unknown" || st.state === "unavailable") return fallback;
    return st.state;
  }

  _time(key) {
    const st = this._state(key);
    if (!st || !st.state || st.state === "unknown" || st.state === "unavailable") {
      return "—";
    }
    const d = new Date(st.state);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleTimeString(this._hass.locale?.language || undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  _openMoreInfo(key) {
    const entityId = this._entityIds && this._entityIds[key];
    if (!entityId) return;
    const event = new Event("hass-more-info", { bubbles: true, composed: true });
    event.detail = { entityId };
    this.dispatchEvent(event);
  }

  _escape(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  _t(key) {
    return translate(this._hass, key);
  }

  _renderStats(cfg) {
    const items = [];
    if (cfg.show_stats) {
      items.push({ icon: "mdi:calendar-today", value: this._text("detections_today", "0"), label: this._t("stat_today") });
      items.push({ icon: "mdi:bird", value: this._text("species_today", "0"), label: this._t("stat_species") });
      items.push({ icon: "mdi:counter", value: this._text("total_detections", "0"), label: this._t("stat_total") });
    }
    if (cfg.show_total_species) {
      items.push({ icon: "mdi:format-list-bulleted-square", value: this._text("total_species", "0"), label: this._t("stat_known") });
    }
    if (!items.length) return "";
    return `
      <div class="bng-stats">
        ${items
          .map(
            (s) => `
          <div class="bng-stat">
            <ha-icon icon="${s.icon}" class="bng-stat-icon"></ha-icon>
            <div class="bng-stat-value">${this._escape(s.value)}</div>
            <div class="bng-stat-label">${this._escape(s.label)}</div>
          </div>`
          )
          .join("")}
      </div>`;
  }

  _renderTopSpecies(cfg) {
    if (!cfg.show_top_species) return "";
    const name = this._text("top_species", "");
    if (!name || name === "—") return "";
    const scientific = this._text("top_species_scientific", "");
    const count = this._text("top_species_count", "0");
    const thumbUrl = this._state("top_species_thumbnail")?.attributes?.entity_picture;
    return `
      <div class="bng-top" data-action="open-top-species">
        <div class="bng-top-thumb${thumbUrl ? "" : " bng-top-thumb-empty"}"
             ${thumbUrl ? `style="background-image:url(${thumbUrl})"` : ""}>
          ${thumbUrl ? "" : '<ha-icon icon="mdi:bird"></ha-icon>'}
        </div>
        <div class="bng-top-info">
          <div class="bng-top-label">${this._escape(this._t("top_species_today"))}</div>
          <div class="bng-top-name">${this._escape(name)}</div>
          ${scientific ? `<div class="bng-top-scientific">${this._escape(scientific)}</div>` : ""}
        </div>
        <div class="bng-top-count">${this._escape(count)}<span>×</span></div>
      </div>`;
  }

  // The three tile layouts. Each reuses the preset's existing show_* flags
  // for content (no new config fields) and bakes in the POC's tuned
  // bleed/thumbnail/gap values as fixed layout constants — see the class
  // doc comment for why. No top-species section here: these are compact
  // single-detection tiles, same scope as the POC they came from.
  _renderTile(cfg, layout, d) {
    const metaParts = [];
    if (cfg.show_confidence && d.confidence) metaParts.push(`${this._escape(d.confidence)}%`);
    if (cfg.show_time) metaParts.push(d.time);
    const metaHtml = metaParts.length ? `<div class="bng-tile-meta">${metaParts.join(" · ")}</div>` : "";
    const counterHtml = cfg.show_stats
      ? `<div class="bng-tile-counter">${this._escape(this._text("detections_today", "0"))} ${this._escape(this._t("stat_today"))} · ${this._escape(
          this._text("species_today", "0")
        )} ${this._escape(this._t("stat_species"))}</div>`
      : "";
    const dotHtml = cfg.show_status
      ? `<span class="bng-tile-dot ${d.online ? "bng-tile-dot-on" : "bng-tile-dot-off"}"></span>`
      : "";
    const nameHtml = (size) => `<div class="bng-tile-name" style="font-size:${size}px">${this._escape(d.name)}</div>`;
    const sciHtml = (size) =>
      cfg.show_scientific && d.scientific
        ? `<div class="bng-tile-scientific" style="font-size:${size}px">${this._escape(d.scientific)}</div>`
        : "";

    if (layout === "silhouette") {
      // Photo bleeds off the right edge, masked to fade into the card
      // background — the text column sits where the fade has taken over.
      return `
        <div class="bng-tile bng-tile-silhouette" data-action="open-detection">
          <img class="bng-tile-photo bng-tile-photo-bleed" src="${d.imgUrl}" alt="">
          <div class="bng-tile-silhouette-text">
            <div class="bng-tile-label">${dotHtml}<span>Last heard</span></div>
            ${nameHtml(18)}${sciHtml(12)}${metaHtml}
            <div class="bng-tile-divider"></div>
            ${counterHtml}
          </div>
        </div>`;
    }
    if (layout === "plaque") {
      // Rounded-square thumbnail beside a left-aligned text column.
      return `
        <div class="bng-tile bng-tile-plaque" data-action="open-detection">
          <img class="bng-tile-photo bng-tile-photo-plaque" src="${d.imgUrl}" alt="">
          <div class="bng-tile-plaque-text">
            <div class="bng-tile-label">${dotHtml}<span>BirdNET</span></div>
            ${nameHtml(17)}${sciHtml(12)}
            <div class="bng-tile-divider"></div>
            ${metaHtml}${counterHtml}
          </div>
        </div>`;
    }
    // bar — circular thumbnail beside a right-aligned text column.
    return `
      <div class="bng-tile bng-tile-bar" data-action="open-detection">
        <img class="bng-tile-photo bng-tile-photo-bar" src="${d.imgUrl}" alt="">
        <div class="bng-tile-bar-text">
          <div class="bng-tile-label bng-tile-label-right">${dotHtml}<span>Last heard</span></div>
          ${nameHtml(16)}${sciHtml(11)}${metaHtml}${counterHtml}
        </div>
      </div>`;
  }

  _render() {
    if (!this._entityIds || Object.keys(this._entityIds).length === 0) {
      this.innerHTML = `
        <ha-card>
          <div class="bng-empty">
            No BirdNET-Go entities found. Add the BirdNET-Go integration
            first (Settings → Devices &amp; Services).
          </div>
        </ha-card>`;
      this._ensureStyle();
      return;
    }

    const cfg = this._effectiveConfig();
    const imgUrl = cfg.show_image
      ? this._state("last_detection_image")?.attributes?.entity_picture
      : null;
    const online = this._state("status")?.state === "on";
    const name = this._text("last_detection");
    const scientific = this._text("last_detection_scientific", "");
    const confidence = this._text("last_detection_confidence", null);
    const time = this._time("last_detection_time");
    // Overlay and the tile layouts all need an actual photo — fall back to
    // stacked when the image is hidden or hasn't loaded yet.
    const overlay = cfg.layout === "overlay" && !!imgUrl;
    const tile = TILE_LAYOUTS.includes(cfg.layout) && cfg.show_image && !!imgUrl;

    if (tile) {
      this.innerHTML = `<ha-card>${this._renderTile(cfg, cfg.layout, {
        name,
        scientific,
        confidence,
        time,
        online,
        imgUrl,
      })}</ha-card>`;
      this._ensureStyle();
      return;
    }

    const statusPill = cfg.show_status
      ? `<span class="bng-status-pill ${online ? "bng-online" : "bng-offline"}">
           <ha-icon icon="${online ? "mdi:wifi" : "mdi:wifi-off"}"></ha-icon>
           ${this._escape(this._t(online ? "online" : "offline"))}
         </span>`
      : "";
    const confidenceChip =
      cfg.show_confidence && confidence
        ? `<span class="bng-chip"><ha-icon icon="mdi:target"></ha-icon>${this._escape(confidence)}%</span>`
        : "";
    const timeChip = cfg.show_time
      ? `<span class="bng-chip"><ha-icon icon="mdi:clock-outline"></ha-icon>${time}</span>`
      : "";
    const metaChips = confidenceChip + timeChip;

    let pictureHtml = "";
    let headerHtml = "";

    if (cfg.show_image && overlay) {
      pictureHtml = `
        <div class="bng-picture bng-overlay" style="background-image:url(${imgUrl})" data-action="open-image">
          ${
            metaChips || statusPill
              ? `<div class="bng-overlay-top">
                   <div class="bng-meta">${metaChips}</div>
                   ${statusPill}
                 </div>`
              : ""
          }
          <div class="bng-overlay-caption" data-action="open-detection">
            <div class="bng-name">${this._escape(name)}</div>
            ${cfg.show_scientific && scientific ? `<div class="bng-scientific">${this._escape(scientific)}</div>` : ""}
          </div>
        </div>`;
    } else if (cfg.show_image) {
      pictureHtml = `
        <div class="bng-picture${imgUrl ? "" : " bng-no-image"}"
             ${imgUrl ? `style="background-image:url(${imgUrl})"` : ""}
             data-action="open-image">
          ${imgUrl ? "" : '<ha-icon icon="mdi:image-off-outline"></ha-icon>'}
        </div>`;
    }

    if (!overlay) {
      headerHtml = `
        <div class="bng-headline" data-action="open-detection">
          <span class="bng-name">${this._escape(name)}</span>
          ${statusPill}
        </div>
        ${cfg.show_scientific && scientific ? `<div class="bng-scientific">${this._escape(scientific)}</div>` : ""}
        ${metaChips ? `<div class="bng-meta">${metaChips}</div>` : ""}`;
    }

    const statsHtml = this._renderStats(cfg);
    const topSpeciesHtml = this._renderTopSpecies(cfg);
    const bodyHtml =
      headerHtml || statsHtml || topSpeciesHtml
        ? `<div class="bng-body">${headerHtml}${statsHtml}${topSpeciesHtml}</div>`
        : "";

    this.innerHTML = `<ha-card>${pictureHtml}${bodyHtml}</ha-card>`;
    this._ensureStyle();
  }

  _ensureStyle() {
    if (this.querySelector("style")) return;
    const style = document.createElement("style");
    style.textContent = `
      ha-card { overflow: hidden; }
      ha-icon { --mdc-icon-size: 16px; }
      .bng-empty {
        padding: 16px;
        color: var(--secondary-text-color);
        font-size: 14px;
      }
      .bng-picture {
        width: 100%;
        aspect-ratio: 16 / 9;
        background-color: var(--divider-color, #333);
        background-size: cover;
        background-position: center;
        cursor: pointer;
      }
      .bng-picture.bng-no-image {
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--secondary-text-color);
      }
      .bng-picture.bng-no-image ha-icon { --mdc-icon-size: 32px; }
      .bng-picture.bng-overlay {
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      .bng-picture.bng-overlay::after {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(
          to top,
          rgba(0, 0, 0, 0.8) 0%,
          rgba(0, 0, 0, 0.35) 40%,
          rgba(0, 0, 0, 0) 75%
        );
        pointer-events: none;
      }
      .bng-overlay-top {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
        padding: 10px;
      }
      .bng-overlay-top .bng-meta { margin-top: 0; }
      .bng-overlay-top .bng-chip {
        color: #fff;
        background: rgba(0, 0, 0, 0.45);
        backdrop-filter: blur(2px);
      }
      .bng-overlay-top .bng-status-pill.bng-online {
        color: #fff;
        background: rgba(76, 175, 80, 0.85);
      }
      .bng-overlay-top .bng-status-pill.bng-offline {
        color: #fff;
        background: rgba(60, 60, 60, 0.6);
      }
      .bng-overlay-caption {
        position: relative;
        z-index: 1;
        padding: 10px 14px 14px;
        cursor: pointer;
      }
      .bng-overlay-caption .bng-name {
        color: #fff;
        text-shadow: 0 1px 4px rgba(0, 0, 0, 0.7);
      }
      .bng-overlay-caption .bng-scientific {
        color: rgba(255, 255, 255, 0.88);
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7);
      }
      .bng-body { padding: 12px 16px 16px; }
      .bng-headline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        cursor: pointer;
      }
      .bng-name {
        font-size: 20px;
        font-weight: 500;
        color: var(--primary-text-color);
        text-transform: capitalize;
      }
      .bng-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        flex-shrink: 0;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.03em;
      }
      .bng-status-pill ha-icon { --mdc-icon-size: 13px; }
      .bng-status-pill.bng-online {
        color: var(--state-active-color, #4caf50);
        background: rgba(76, 175, 80, 0.12);
      }
      .bng-status-pill.bng-offline {
        color: var(--state-unavailable-color, #9e9e9e);
        background: rgba(158, 158, 158, 0.12);
      }
      .bng-scientific {
        font-style: italic;
        font-size: 13px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .bng-meta {
        display: flex;
        gap: 8px;
        margin-top: 10px;
      }
      .bng-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        color: var(--secondary-text-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
        border-radius: 6px;
        padding: 3px 8px;
      }
      .bng-stats {
        display: flex;
        margin-top: 14px;
        border-top: 1px solid var(--divider-color);
        padding-top: 12px;
      }
      .bng-stat {
        flex: 1;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        position: relative;
      }
      .bng-stat:not(:first-child)::before {
        content: "";
        position: absolute;
        left: 0;
        top: 4px;
        bottom: 4px;
        width: 1px;
        background: var(--divider-color);
      }
      .bng-stat-icon { color: var(--secondary-text-color); }
      .bng-stat-value {
        font-size: 18px;
        font-weight: 500;
        color: var(--primary-text-color);
      }
      .bng-stat-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--secondary-text-color);
      }
      .bng-top {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 14px;
        padding: 8px 10px;
        border-radius: 10px;
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
        cursor: pointer;
      }
      .bng-top-thumb {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        flex-shrink: 0;
        background-size: cover;
        background-position: center;
        background-color: var(--divider-color, #333);
      }
      .bng-top-thumb-empty {
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--secondary-text-color);
      }
      .bng-top-info { flex: 1; min-width: 0; }
      .bng-top-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--secondary-text-color);
      }
      .bng-top-name {
        font-size: 14px;
        font-weight: 500;
        color: var(--primary-text-color);
        text-transform: capitalize;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .bng-top-scientific {
        font-size: 11px;
        font-style: italic;
        color: var(--secondary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .bng-top-count {
        font-size: 15px;
        font-weight: 600;
        color: var(--primary-text-color);
        flex-shrink: 0;
      }
      .bng-top-count span {
        font-size: 11px;
        font-weight: 400;
        color: var(--secondary-text-color);
        margin-left: 1px;
      }
      .bng-tile {
        height: ${TILE_HEIGHT}px;
        box-sizing: border-box;
        cursor: pointer;
      }
      .bng-tile-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--secondary-text-color);
      }
      .bng-tile-label-right { justify-content: flex-end; }
      .bng-tile-name {
        font-weight: 500;
        color: var(--primary-text-color);
        text-transform: capitalize;
      }
      .bng-tile-scientific { font-style: italic; color: var(--secondary-text-color); }
      .bng-tile-meta, .bng-tile-counter { font-size: 11px; color: var(--secondary-text-color); }
      .bng-tile-divider { height: 1px; background: var(--divider-color); margin: 4px 0; }
      .bng-tile-dot { width: 6px; height: 6px; border-radius: 50%; flex: none; }
      .bng-tile-dot-on {
        background: var(--state-active-color, #4caf50);
        box-shadow: 0 0 6px rgba(76, 175, 80, 0.7);
      }
      .bng-tile-dot-off { background: var(--state-unavailable-color, #9e9e9e); }
      /* silhouette — photo bleeds off the right edge, masked to fade into
         the card background; the text column sits over the faded part. */
      .bng-tile-silhouette { position: relative; overflow: hidden; }
      .bng-tile-silhouette .bng-tile-photo-bleed {
        position: absolute;
        right: -22px;
        top: 0;
        height: 100%;
        width: 62%;
        object-fit: cover;
        -webkit-mask-image: linear-gradient(270deg, #000 42%, transparent 100%);
        mask-image: linear-gradient(270deg, #000 42%, transparent 100%);
      }
      .bng-tile-silhouette-text {
        position: relative;
        z-index: 1;
        height: 100%;
        max-width: 64%;
        box-sizing: border-box;
        padding: 13px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 4px;
      }
      /* plaque — rounded-square thumbnail beside left-aligned text. */
      .bng-tile-plaque {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 13px;
      }
      .bng-tile-plaque .bng-tile-photo-plaque {
        width: 92px;
        height: 92px;
        flex: none;
        object-fit: cover;
        border-radius: 10px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
      }
      .bng-tile-plaque-text {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 3px;
      }
      /* bar — circular thumbnail beside right-aligned text. */
      .bng-tile-bar {
        display: flex;
        align-items: center;
        gap: 13px;
        padding: 13px;
      }
      .bng-tile-bar .bng-tile-photo-bar {
        width: 84px;
        height: 84px;
        flex: none;
        object-fit: cover;
        border-radius: 50%;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
      }
      .bng-tile-bar-text {
        flex: 1;
        min-width: 0;
        text-align: right;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
    `;
    this.appendChild(style);
  }
}

customElements.define("birdnet-go-card", BirdnetGoCard);

/**
 * Config editor for `birdnet-go-card`: device selector + preset picker,
 * with the individual `show_*` toggles only appearing once "Custom" is
 * selected. Switching *into* custom seeds the toggles from whichever named
 * preset was active, so the user fine-tunes from a sane starting point
 * instead of a blank slate; switching *out of* custom drops the per-field
 * overrides again so the saved config stays a plain `{ preset, device_id }`
 * for the common case.
 */
class BirdnetGoCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { preset: "simple", layout: "stacked", ...(config || {}) };
    this._config.layout = normalizeLayout(this._config.layout);
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _schema() {
    const schema = [
      { name: "device_id", selector: { device: { filter: { integration: "birdnet_go" } } } },
      {
        name: "layout",
        selector: {
          select: {
            mode: "list",
            options: ["stacked", "overlay", ...TILE_LAYOUTS].map((value) => ({
              value,
              label: translate(this._hass, `layout_${value}`),
            })),
          },
        },
      },
      {
        name: "preset",
        selector: {
          select: {
            mode: "list",
            options: ["basic", "simple", "advanced", "nerd", "custom"].map((value) => ({
              value,
              label: translate(this._hass, `preset_${value}`),
            })),
          },
        },
      },
    ];

    if ((this._config.preset || "simple") === "custom") {
      schema.push(
        { name: "show_image", selector: { boolean: {} } },
        { name: "show_scientific", selector: { boolean: {} } },
        { name: "show_confidence", selector: { boolean: {} } },
        { name: "show_time", selector: { boolean: {} } },
        { name: "show_status", selector: { boolean: {} } },
        { name: "show_stats", selector: { boolean: {} } },
        { name: "show_total_species", selector: { boolean: {} } },
        { name: "show_top_species", selector: { boolean: {} } }
      );
    }
    return schema;
  }

  _computeLabel(schema) {
    return translate(this._hass, `field_${schema.name}`);
  }

  _handleValueChanged(ev) {
    ev.stopPropagation();
    const oldPreset = this._config.preset || "simple";
    const newValue = { ...ev.detail.value };
    const newPreset = newValue.preset || "simple";

    if (newPreset === "custom" && oldPreset !== "custom") {
      // Entering custom — seed the toggles from the preset being left, so
      // there's something sensible to fine-tune rather than a blank form.
      const seed = PRESETS[oldPreset] || PRESETS.simple;
      for (const field of TOGGLE_FIELDS) {
        if (typeof newValue[field] !== "boolean") newValue[field] = seed[field];
      }
    } else if (newPreset !== "custom") {
      // Leaving custom (or never in it) — named presets carry no per-field
      // overrides, keep the saved config minimal.
      for (const field of TOGGLE_FIELDS) delete newValue[field];
    }

    this._config = newValue;
    this._render();
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this._hass || !this._config) return;

    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => this._handleValueChanged(ev));
      this.appendChild(this._form);
    }

    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = this._schema();
    this._form.computeLabel = (schema) => this._computeLabel(schema);
  }
}

customElements.define("birdnet-go-card-editor", BirdnetGoCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "birdnet-go-card",
  name: "BirdNET-Go Card",
  description: "Last detection picture, species and today's stats from a BirdNET-Go integration device.",
  preview: false,
});
