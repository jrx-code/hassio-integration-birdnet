# Reverse proxy + SSE for BirdNET-Go

This integration keeps a long-lived **Server-Sent Events** connection open to BirdNET-Go at `GET /api/v2/detections/stream`, plus ordinary REST polling for stats. If you put BirdNET-Go behind nginx, Caddy, Traefik, or another reverse proxy, REST often still works while SSE fails quietly — last detection freezes, connectivity flaps, or the stream never reconnects cleanly.

This guide covers the proxy settings that matter for SSE and how to point the Home Assistant integration at an HTTPS frontend.

## What breaks

Typical reverse-proxy defaults assume short HTTP responses:

| Setting | Effect on SSE |
|---|---|
| Response buffering | Proxy waits for a full body; events never reach HA until the buffer fills or the connection dies |
| Short read / idle / proxy timeouts | Idle stream between detections is closed; HA reconnects with backoff (5s→120s) |
| Gzip / content-encoding on the stream | Can buffer or corrupt the event framing |
| Treating the path like WebSocket-only | SSE is plain HTTP with `text/event-stream`, not `Upgrade: websocket` |

REST endpoints (`/api/v2/analytics/...`, `/api/v2/detections/recent`) are short-lived and often look “fine” while the stream is broken.

## How the integration talks to the host

- **Host field** accepts `192.168.1.50:8080` (defaults to `http://`) or a full URL such as `https://birdnet.example.com`.
- **Verify SSL** should match your certificate story (public CA or trusted private CA → on; self-signed you accept knowingly → off).
- **Images** are fetched by Home Assistant and exposed via HA’s `/api/image_proxy/...`. The browser does **not** need a direct path to BirdNET-Go for thumbnails in the UI.
- The SSE endpoint on BirdNET-Go is currently **unauthenticated** and rate-limited (about 10 connections per minute per IP). Prefer keeping BirdNET-Go on LAN or behind auth at the proxy edge; do not expose the raw API to the public internet without additional controls.

## Required proxy behaviour

For the location / route that serves BirdNET-Go (at least `/api/`):

1. **Disable response buffering** for the SSE path (or for all API traffic if that is simpler).
2. **Raise or disable** proxy read / idle timeouts so an idle stream between birds is not cut after 60s.
3. **Pass through** `Content-Type: text/event-stream` and avoid compressing that response.
4. Prefer **HTTP/1.1** to the upstream for long-lived streams if your stack is picky about HTTP/2 upstreams.
5. Set sensible `Host` / `X-Forwarded-Proto` / `X-Forwarded-For` if BirdNET-Go or logs care; HA itself only needs a stable base URL that answers REST + SSE.

## nginx example

```nginx
upstream birdnet_go {
    server 192.168.1.50:8080;
}

server {
    listen 443 ssl http2;
    server_name birdnet.example.com;

    # ssl_certificate / …;
    # ssl_certificate_key / …;

    location / {
        proxy_pass http://birdnet_go;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Critical for SSE
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 24h;
        proxy_send_timeout 24h;

        # Optional: avoid compressing the event stream
        gzip off;
    }
}
```

If you prefer to special-case only the stream:

```nginx
location /api/v2/detections/stream {
    proxy_pass http://birdnet_go;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 24h;
    gzip off;
}
```

## Caddy example

```caddy
birdnet.example.com {
    reverse_proxy 192.168.1.50:8080 {
        flush_interval -1
        transport http {
            read_timeout 24h
            write_timeout 24h
        }
    }
}
```

`flush_interval -1` disables response buffering so SSE events are forwarded immediately. Adjust timeouts if your Caddy build uses different transport knobs.

## Traefik example

```yaml
http:
  routers:
    birdnet:
      rule: "Host(`birdnet.example.com`)"
      service: birdnet
      tls: {}
  services:
    birdnet:
      loadBalancer:
        servers:
          - url: "http://192.168.1.50:8080"
        responseForwarding:
          flushInterval: "0s"
```

Also raise entrypoint / transport idle timeouts if Traefik or a front CDN closes quiet connections early.

## Configuring the integration

| Setup | Host field | Verify SSL |
|---|---|---|
| Direct LAN | `192.168.1.50:8080` | usually off (plain HTTP) |
| HTTPS reverse proxy (public CA) | `https://birdnet.example.com` | on |
| HTTPS with self-signed cert | `https://birdnet.example.com` | off (or trust the CA in HA’s environment) |

Use the same hostname HA will keep using long-term. Changing host later means reconfigure / re-add the integration entry.

## Troubleshooting

**REST OK, last detection stuck**

1. From a machine that can reach the proxy (or from the HA host):

   ```bash
   curl -N -H 'Accept: text/event-stream' \
     'https://birdnet.example.com/api/v2/detections/stream'
   ```

   You should see an open connection and eventually `data: …` lines when BirdNET-Go emits a detection (or a heartbeat / connection message). If `curl` hangs with no events and then dies at ~60s, fix proxy timeouts/buffering.

2. Check HA logs for `BirdNET-Go SSE stream error, reconnecting` — repeated reconnects with increasing delay point at the proxy or upstream closing the stream.

3. Confirm you are not hitting BirdNET-Go’s connection rate limit (roughly 10 new connections per minute per IP) by reconnecting in a tight loop.

**Images missing in the browser but sensors update**

HA fetches images server-side. If `image.*` entities are unavailable, HA cannot reach the media URL on the BirdNET-Go base URL (wrong host, TLS failure, or proxy blocking `/api/v2/media/`). Fix reachability from the HA host, not from the browser.

**TLS errors in config flow**

Turn **Verify SSL** off only if you understand the risk, or install/trust the private CA on the Home Assistant OS / container.

## Out of scope here

- HAOS / Supervisor network topologies (separate doc).
- Adding API authentication to the integration (separate change).
