"""
Proxy WebSocket connection to upstream (e.g. chat-api).
"""
import asyncio
import logging
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import connect as ws_connect

logger = logging.getLogger(__name__)


def _redact_url(url: str) -> str:
    """Redact token= from URL for logging."""
    if "token=" in url:
        i = url.index("token=")
        j = url.index("&", i) if "&" in url[i:] else len(url)
        url = url[:i] + "token=***" + url[j:]
    return url


async def proxy_websocket(
    websocket: WebSocket,
    upstream_ws_url: str,
    sub: Optional[str] = None,
) -> None:
    """
    Accept client WebSocket, connect to upstream_ws_url, forward frames both ways.
    Pass optional sub (from JWT) as header or query for backend if needed.
    """
    extra_headers = {}
    if sub is not None:
        extra_headers["x-user-id"] = sub
    # Forward important headers from client to backend
    for name in ("authorization", "x-session-id"):
        v = websocket.headers.get(name)
        if v:
            extra_headers[name] = v

    await websocket.accept()

    try:
        async with ws_connect(
            upstream_ws_url,
            additional_headers=extra_headers or None,
            close_timeout=2,
            open_timeout=10,
            max_size=2**20,
            ping_interval=None,
            ping_timeout=None,
        ) as backend:
            async def client_to_backend():
                try:
                    while True:
                        msg = await websocket.receive()
                        if msg.get("type") == "websocket.disconnect":
                            break
                        if "text" in msg:
                            await backend.send(msg["text"])
                        elif "bytes" in msg:
                            await backend.send(msg["bytes"])
                except WebSocketDisconnect:
                    pass
                except Exception:
                    raise

            async def backend_to_client():
                try:
                    while True:
                        message = await backend.recv()
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception:
                    raise

            await asyncio.gather(
                client_to_backend(),
                backend_to_client(),
            )
    except Exception as e:
        logger.warning(
            "WebSocket proxy upstream error: %s – %s",
            _redact_url(upstream_ws_url),
            e,
            exc_info=True,
        )
        try:
            await websocket.close(code=1011, reason="Upstream error")
        except Exception:
            pass
