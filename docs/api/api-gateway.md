The REST Gateway sits at the edge of the architecture, routing traffic from the frontend to the appropriate internal microservices.

- **Routing**: Directs `/auth/*` requests to the `auth_service`, `/users/*` requests to the `user_service`, and standard HTTP chat queries to the respective chat APIs.
- **WebSocket Streaming**: Manages persistent WebSocket connections for real-time chat token streaming, proxying the connections to the downstream `chat-api` instances while maintaining active session state.
- **Authentication Offloading**: Intercepts incoming requests and extracts the JWT `access_token` from the Authorization header or WebSocket connection parameters.
- **Key Validation**: Uses the **Public Key** (provided by the `auth_service`) to cryptographically verify the token's signature, expiration, and claims.
- **Rejection**: If a token is invalid, expired, or missing, the Gateway immediately returns an HTTP 401 Unauthorized (or closes the WebSocket handshake), protecting internal services from unauthenticated traffic.
- **Rate Limiting**: Enforces request throttling and quotas (e.g., using Redis) to protect downstream services from DDoS attacks or abuse, returning an HTTP 429 Too Many Requests when limits are exceeded.
