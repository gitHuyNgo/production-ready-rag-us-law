# API Documentation

The system exposes a single entry point (API Gateway). All client traffic goes through the gateway, which proxies to internal services.

| Document | Description |
|----------|-------------|
| [api-gateway](api-gateway.md) | Gateway: routing, auth, rate limiting, HTTP/WS proxy |
| [auth-api](auth-api.md) | Auth API: register, login, token, /me, OIDC |
| [user-api](user-api.md) | User API: profile CRUD (/profiles/me) |
| [chat-api](chat-api.md) | Chat API: RAG, sessions, messages, WebSocket streaming |

Base URL in development is typically `http://localhost:8080` (gateway). Internal services run on different ports (auth 8001, user 8002, chat 8000).
