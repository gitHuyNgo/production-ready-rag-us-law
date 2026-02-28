# API Gateway

The REST Gateway sits at the edge of the architecture, routing traffic from the frontend to the appropriate internal microservices. It is the single entry point for client applications and runs in front of auth-api, user-api, and chat-api.

## Responsibilities

- **Routing**: Forwards `/auth/*` to auth-api, `/profiles/*` to user-api, `/chat/*` to chat-api (HTTP and WebSocket).
- **Authentication**: Extracts JWT from `Authorization: Bearer <token>` (or WebSocket auth header). Verifies signature and expiration using the auth-api **public key** (RS256). Unauthenticated requests to protected routes receive `401 Unauthorized`.
- **Public routes** (no JWT required): `/health`, `/`, `/auth/register`, `/auth/token`, `/docs`, `/openapi.json`, `/redoc`, and OAuth callback paths as implemented.
- **Rate limiting**: Per-IP limits via SlowAPI; returns `429 Too Many Requests` when exceeded.
- **CORS**: Configurable origins, credentials, methods, and headers.
- **Proxy**: Preserves method, headers, and body; adds `X-User-Id` (JWT `sub`) when token is valid so downstream services can identify the user.

## Implementation Notes

- **HTTP proxy**: `proxy_http()` in `src/proxy/http_proxy.py` forwards to upstream base URL + path, strips hop-by-hop headers, and injects `X-User-Id` when `sub` is set.
- **WebSocket proxy**: `proxy_websocket()` in `src/proxy/ws_proxy.py` upgrades the client connection and proxies to chat-api’s WebSocket endpoint; query string is forwarded.
- **JWT**: `src/auth/jwt.py` uses `JWT_PUBLIC_KEY` or `JWT_PUBLIC_KEY_PATH` (same key as auth-api’s public key) to decode and validate tokens.

## Endpoints (Gateway Itself)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Liveness; returns `{"status":"ok","service":"api-gateway"}` |
| GET | `/` | No | Service info and link to `/docs` |

All other paths are proxied to the appropriate backend as described above.
