# Proposal: API authentication for the BirdNET-Go HA integration

**Status:** design only — no code in this PR. Implement only after maintainer decision.

## Problem

Today the integration calls BirdNET-Go with **no credentials**:

- Config flow: `host` + `verify_ssl`
- REST + SSE use the shared `aiohttp` session with no `Authorization` header

That matches BirdNET-Go’s current public read surface: analytics and `GET /api/v2/detections/stream` are usable without auth (SSE is rate-limited; unauthenticated clients may get **anonymized** source display names).

Gaps:

1. Operators who lock down BirdNET-Go (OAuth2 / basic / subnet policies, or a reverse proxy that requires a bearer) cannot use this integration once those endpoints start returning `401`.
2. Authenticated SSE clients get fuller payloads (e.g. source display names); we may want that later.
3. BirdNET-Go documents **API key** as a future auth method; we should design so a key can plug in without another config-flow rewrite.

Upstream references (BirdNET-Go):

- Auth methods in architecture: `none`, `subnet`, `oauth2`, `apikey` (future)
- Login: `POST /api/v2/auth/login`; bearer on subsequent requests
- Security wiki: basic auth / Google / GitHub / Cloudflare Access
- SSE detections stream: public (`❌⚡`), with auth-aware payload sanitization

## Goals

- Optional credentials in config flow / options flow; existing LAN installs keep working with empty auth.
- Same credential path for REST polling, SSE, and image fetches (one session / shared headers).
- Store secrets in the HA config entry (`async_set_unique_id` / entry data) using HA conventions — never log tokens.
- Clear errors in config flow when auth fails (`401`/`403` vs host unreachable).

## Non-goals (this proposal)

- Implementing OAuth browser redirect inside HA (heavy; avoid as v1).
- Shipping a BirdNET-Go add-on or changing upstream auth.
- Proxy-only Basic auth at nginx without teaching the integration (operators can still use LAN IP and leave integration auth empty).

## Recommended approach (phased)

### Phase 1 — Optional Bearer token (implement first)

**Why:** BirdNET-Go already validates `Authorization: Bearer <token>`. Operators can mint/obtain a token via BirdNET-Go’s login / UI and paste it into HA. No interactive OAuth in HA.

**Config**

| Key | Type | Required | Notes |
|---|---|---|---|
| `host` | str | yes | unchanged |
| `verify_ssl` | bool | yes | unchanged |
| `access_token` | str | no | blank = current behaviour |

**Flow**

1. Config flow step 1: host + verify_ssl (+ optional token field, or “advanced” step).
2. Validation request: `GET /api/v2/detections/recent?limit=1` **with** `Authorization: Bearer …` when token set.
3. On `401`/`403`: abort with a dedicated error key (`invalid_auth`).
4. Persist token in entry data; options flow allows rotate/clear without re-adding the integration.

**Coordinator / session**

- When building requests (REST + SSE + media), attach the bearer header if present.
- SSE: pass headers on the long-lived `GET` to `/api/v2/detections/stream` (already uses the shared session — set default headers on the session or per-request).

**Secrets**

- Prefer HA’s config entry data; document that backups include it.
- Do not put the token in entity attributes or `source_url` query strings.

### Phase 2 — Username / password → token (optional)

If BirdNET-Go basic/password login via `POST /api/v2/auth/login` is stable for machine clients:

- Options: `username` + `password` (exclusive with pasted token, or “get token” helper).
- On setup / periodic refresh: login, store access token (+ refresh if upstream provides one).
- More moving parts (token expiry); only worth it if paste-token UX is painful.

### Phase 3 — API key (when upstream ships it)

When `AuthMethodAPIKey` lands upstream:

- Add `api_key` (or reuse one `credential` + `auth_type` enum: `none` | `bearer` | `api_key`).
- Header shape per upstream docs (likely `Authorization: Bearer` or a dedicated header — **confirm against BirdNET-Go release notes before coding**).

### Explicitly deferred — full OAuth in HA

Google/GitHub OAuth with redirect URIs is a poor fit for a local push integration. Prefer: user authenticates in BirdNET-Go UI, copies token; or reverse-proxy auth that HA never sees (LAN bypass / subnet allowlist for the HA host).

## Config flow UX sketch

```
[ Host: _______________ ]
[ ✓ Verify SSL          ]
[ Access token (optional) ]  ← password field
[ Submit ]
```

Reconfigure (options): same fields; empty token clears auth.

Translations: add keys for `invalid_auth`, optional-token helper text (`en` + `pl` at minimum).

## Testing plan (when implementing)

- Unit: request helper adds/omits `Authorization` correctly; never asserts on real secrets in logs.
- Config flow: mock 200 / 401 / timeout.
- Manual: LAN without token (regression); with invalid token → `invalid_auth`; with valid bearer → REST + SSE + image.

## Rollout

1. Merge this design after review.
2. Implementation PR on a separate branch (`feat/optional-bearer-auth`), bumping integration version in `manifest.json` / changelog.
3. README: short “Authentication (optional)” pointing here or to a trimmed user-facing section once shipped.

## Decision ask

Please choose before coding:

| Option | Meaning |
|---|---|
| **A (recommended)** | Phase 1 only — optional bearer in config/options |
| **B** | Phase 1 + Phase 2 (login with user/password) |
| **C** | Wait until upstream API keys are GA, then Phase 3 |
| **D** | No integration auth; document proxy/subnet only |

No merge of implementation without an explicit decision on A/B/C/D.
