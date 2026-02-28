"""
Forward HTTP request to upstream and return response.
"""
from typing import Optional

import httpx
from fastapi import Request, Response


async def proxy_http(
    client: httpx.AsyncClient,
    upstream_base: str,
    request: Request,
    path: str,
    sub: Optional[str] = None,
) -> Response:
    """
    Forward request to upstream_base + path. Preserve method, headers, body.
    If sub (user id from JWT) is set, add X-User-Id for downstream.
    """
    url = upstream_base.rstrip("/") + path
    if request.url.query:
        url = f"{url}?{request.url.query}"

    forward_headers = dict(request.headers)
    for h in ("host", "connection", "transfer-encoding", "keep-alive", "te", "trailer", "upgrade"):
        forward_headers.pop(h.lower(), None)
    if sub is not None:
        forward_headers["x-user-id"] = sub

    body = await request.body()

    r = await client.request(
        request.method,
        url,
        headers=forward_headers,
        content=body,
    )

    out_headers = {k: v for k, v in r.headers.items() if k.lower() not in ("transfer-encoding", "connection", "keep-alive")}
    return Response(status_code=r.status_code, headers=out_headers, content=r.content)
