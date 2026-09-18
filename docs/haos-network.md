# HAOS / network topologies for BirdNET-Go

How Home Assistant (especially **Home Assistant OS** with Supervisor) should reach BirdNET-Go for this integration. The integration is a normal custom component inside Core: it opens outbound REST + SSE to whatever host you enter in the config flow. There is no MQTT hop and no Supervisor “discovery” of BirdNET-Go.

For reverse-proxy buffering and SSE timeouts, see [reverse-proxy-sse.md](reverse-proxy-sse.md) (when that doc is on your branch / main).

## Mental model

```
┌─────────────────────────────┐         REST + SSE
│ Home Assistant Core         │ ──────────────────► BirdNET-Go
│  custom_components/birdnet_go│         (host from config)
│  + image fetch (server-side)│
└─────────────────────────────┘
```

- **Outbound from Core** must reach BirdNET-Go’s HTTP(S) API (`/api/v2/...`).
- The **browser** only needs HA. Thumbnails go through HA’s image proxy, not directly to BirdNET-Go.
- SSE is a long-lived connection from Core → BirdNET-Go; anything that NATs, firewalls, or isolates Core from that host will show up as stalled last-detection / reconnect loops.

## Topology A — BirdNET-Go on the LAN (recommended default)

BirdNET-Go runs on a Pi, NUC, or VM on the same LAN as HAOS.

| Field | Example |
|---|---|
| Host | `192.168.1.50:8080` |
| Verify SSL | off (plain HTTP) |

**Checks**

1. From HAOS: **Settings → System → Terminal** (or SSH add-on) and `curl -sS http://192.168.1.50:8080/api/v2/detections/recent?limit=1`.
2. Same host for SSE: `curl -N -H 'Accept: text/event-stream' http://192.168.1.50:8080/api/v2/detections/stream`.

If curl from HAOS fails but works from your laptop, look at VLANs, client isolation (guest Wi‑Fi), or firewall rules between the HA host and BirdNET-Go — not at the integration.

## Topology B — HTTPS name on the LAN / reverse proxy

BirdNET-Go sits behind nginx/Caddy/Traefik with a TLS certificate; HA still talks to the **public hostname**, not the raw IP.

| Field | Example |
|---|---|
| Host | `https://birdnet.home.arpa` |
| Verify SSL | on (trusted CA) or off (self-signed you accept) |

Core must resolve that DNS name (local DNS, AdGuard/Unbound rewrite, or `/etc/hosts` via HAOS tricks — prefer real LAN DNS). Split-horizon DNS is fine: phone uses public IP, HAOS uses LAN IP for the same name.

Configure proxy SSE settings as in the reverse-proxy runbook. Prefer pointing HA at the **internal** listener when possible to avoid hairpin NAT.

## Topology C — HAOS + BirdNET-Go as a separate machine on Proxmox / PVE

Common lab layout (this project has been verified on a PVE HA VM talking to an external BirdNET-Go host):

- HAOS VM bridged to LAN (`vmbr0` or equivalent).
- BirdNET-Go on another VM/LXC or bare metal on the same bridge.

Use Topology A with the BirdNET-Go VM’s LAN IP. Avoid putting BirdNET-Go only on a host-only network that Core cannot route to.

If you use **VLAN tagging** on the HAOS NIC, ensure the BirdNET-Go subnet is routed or bridged to that VLAN.

## Topology D — BirdNET-Go in Docker / Compose on another host

Publish BirdNET-Go’s HTTP port on the host interface (`8080:8080` or a reverse proxy on 443). Point HA at the **host LAN IP** or the proxy hostname — not `172.17.x.x` Docker bridge addresses (those are invisible from HAOS).

`host` networking on the BirdNET-Go container simplifies LAN reachability; bridge + published ports is fine if the publish address is the LAN IP.

## Topology E — BirdNET-Go as a Home Assistant add-on (if you run one)

This repository does **not** ship a Supervisor add-on. If you run a third-party BirdNET-Go add-on (or your own):

- From Core, the add-on is often reachable as `http://<slug>` or via the add-on’s published port on `homeassistant.local` / the host — **exact DNS names depend on the add-on and Supervisor version**.
- Prefer the documented internal hostname from that add-on’s docs, then fall back to the HA host’s LAN IP + published port.
- SSE still needs an unbuffered path; an add-on that only exposes MQTT is not enough for this integration.

If Core cannot resolve the add-on hostname, use the host’s LAN IP and the mapped port (Topology A).

## Topology F — Remote BirdNET-Go (VPN)

HAOS and BirdNET-Go on different sites:

1. Prefer a **site-to-site or always-on VPN** (WireGuard, Tailscale, etc.) so Core uses a stable VPN IP/hostname.
2. Avoid exposing the unauthenticated SSE/API to the public internet.
3. Watch idle timeouts on VPN and any middle proxies — same symptoms as a bad reverse proxy (REST OK, SSE dies).

## What usually goes wrong

| Symptom | Likely cause |
|---|---|
| Config flow “cannot connect” | Wrong IP/port, firewall, BirdNET-Go not listening on that interface |
| Stats update every ~5 min, last detection frozen | SSE blocked or timed out (proxy, firewall idle timeout, rate limit on reconnects) |
| Sensors OK, images unavailable | Core cannot fetch `/api/v2/media/...` (TLS or path blocked) while JSON API works |
| Works on laptop, fails on HAOS | DNS or routing differs on the HA host; test with curl **from HAOS** |
| Multiple HA instances | Each opens its own SSE connection — stay under BirdNET-Go’s connection rate limits |

## Quick verification checklist

1. From HAOS: REST `detections/recent?limit=1` → JSON.
2. From HAOS: SSE stream stays open (`curl -N`).
3. Integration host field matches the URL you just tested (including `https://` when TLS is used).
4. `binary_sensor.birdnet_go_status` stays on; last detection moves when a real bird is classified.

## Out of scope here

- Detailed nginx/Caddy/Traefik SSE snippets → reverse-proxy runbook.
- Adding API tokens / Basic auth to the integration → separate change.
