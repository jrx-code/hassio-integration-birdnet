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
 * Visual (GUI) config editor via `getConfigElement()` — a single `ha-form`
 * bound to a device selector scoped to the `birdnet_go` integration, since
 * the only config field is the optional `device_id`. `ha-form` and the
 * `device` selector are both loaded by the frontend already; no import
 * needed here, just use the custom element by tag name.
 */

class BirdnetGoCard extends HTMLElement {
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
    return 4;
  }

  static getStubConfig() {
    return {};
  }

  static getConfigElement() {
    return document.createElement("birdnet-go-card-editor");
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

    const imgState = this._state("last_detection_image");
    const imgUrl = imgState?.attributes?.entity_picture;
    const online = this._state("status")?.state === "on";

    if (!this.querySelector("ha-card")) {
      this.innerHTML = `
        <ha-card>
          <div class="bng-picture" part="picture"></div>
          <div class="bng-body">
            <div class="bng-headline">
              <span class="bng-name"></span>
              <span class="bng-dot" title="BirdNET-Go connectivity"></span>
            </div>
            <div class="bng-scientific"></div>
            <div class="bng-meta">
              <span class="bng-confidence"></span>
              <span class="bng-time"></span>
            </div>
            <div class="bng-stats">
              <div class="bng-stat">
                <div class="bng-stat-value bng-detections-today"></div>
                <div class="bng-stat-label">today</div>
              </div>
              <div class="bng-stat">
                <div class="bng-stat-value bng-species-today"></div>
                <div class="bng-stat-label">species</div>
              </div>
              <div class="bng-stat">
                <div class="bng-stat-value bng-total-detections"></div>
                <div class="bng-stat-label">total</div>
              </div>
            </div>
          </div>
        </ha-card>`;
      this._ensureStyle();
      this.querySelector(".bng-picture").addEventListener("click", () =>
        this._openMoreInfo("last_detection_image")
      );
      this.querySelector(".bng-headline").addEventListener("click", () =>
        this._openMoreInfo("last_detection")
      );
    }

    const pic = this.querySelector(".bng-picture");
    pic.style.backgroundImage = imgUrl ? `url(${imgUrl})` : "none";
    pic.classList.toggle("bng-no-image", !imgUrl);

    this.querySelector(".bng-name").textContent = this._text("last_detection");
    this.querySelector(".bng-scientific").textContent = this._text(
      "last_detection_scientific",
      ""
    );
    this.querySelector(".bng-dot").classList.toggle("bng-online", online);
    this.querySelector(".bng-dot").classList.toggle("bng-offline", !online);

    const confidence = this._text("last_detection_confidence", null);
    this.querySelector(".bng-confidence").textContent = confidence
      ? `${confidence}% confidence`
      : "";
    this.querySelector(".bng-time").textContent = this._time("last_detection_time");

    this.querySelector(".bng-detections-today").textContent = this._text(
      "detections_today",
      "0"
    );
    this.querySelector(".bng-species-today").textContent = this._text(
      "species_today",
      "0"
    );
    this.querySelector(".bng-total-detections").textContent = this._text(
      "total_detections",
      "0"
    );
  }

  _ensureStyle() {
    if (this.querySelector("style")) return;
    const style = document.createElement("style");
    style.textContent = `
      ha-card { overflow: hidden; }
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
      }
      .bng-body { padding: 12px 16px 16px; }
      .bng-headline {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
      }
      .bng-name {
        font-size: 20px;
        font-weight: 500;
        color: var(--primary-text-color);
        text-transform: capitalize;
      }
      .bng-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .bng-dot.bng-online { background: var(--state-active-color, #4caf50); }
      .bng-dot.bng-offline { background: var(--state-unavailable-color, #9e9e9e); }
      .bng-scientific {
        font-style: italic;
        font-size: 13px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .bng-meta {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-top: 8px;
      }
      .bng-stats {
        display: flex;
        margin-top: 14px;
        border-top: 1px solid var(--divider-color);
        padding-top: 10px;
      }
      .bng-stat { flex: 1; text-align: center; }
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
    `;
    this.appendChild(style);
  }
}

customElements.define("birdnet-go-card", BirdnetGoCard);

/**
 * Config editor for `birdnet-go-card`. Single field (`device_id`), so a
 * bare `ha-form` with a device selector scoped to this integration is all
 * that's needed — no per-field custom markup.
 */
class BirdnetGoCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _schema() {
    return [
      {
        name: "device_id",
        selector: { device: { filter: { integration: "birdnet_go" } } },
      },
    ];
  }

  _computeLabel(schema) {
    if (schema.name === "device_id") return "BirdNET-Go device (optional)";
    return schema.name;
  }

  _render() {
    if (!this._hass || !this._config) return;

    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }

    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = this._schema();
    this._form.computeLabel = this._computeLabel;
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
