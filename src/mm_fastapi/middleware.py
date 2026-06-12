"""FastAPI middleware for MetaMessage encoding and decoding.

Similar to mm-web-go, provides automatic:
- GET/DELETE: hex-encoded MetaMessage in ?data=<hex> query param
- POST/PUT/PATCH: binary MetaMessage in request body
- Response always encoded as binary MetaMessage
"""

from typing import Callable, Optional, Set

from fastapi import Request, Response
from metamessage import decode_to_value
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mm_core.types import CONTENT_TYPE_METAMESSAGE, MMDecoderError, MMEncoderError


class MMMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic MetaMessage encoding and decoding.

    Follows mm-web-go pattern:
    - GET/DELETE: decodes ?data=<hex> query param into mm_query
    - POST/PUT/PATCH: decodes binary request body into mm_body
    - Responses always encoded as binary MetaMessage
    """

    SKIP_ROUTES: Set[str] = {
        "/openapi.json",
        "/docs",
        "/redoc",
        "/docs/oauth2-redirect",
    }

    def __init__(
        self,
        app: ASGIApp,
        skip_routes: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.skip_routes = self.SKIP_ROUTES.copy()
        if skip_routes:
            self.skip_routes.update(skip_routes)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.skip_routes:
            return await call_next(request)

        content_type = request.headers.get("content-type", "")
        accept = request.headers.get("accept", "")

        is_mm = CONTENT_TYPE_METAMESSAGE in content_type.lower() or CONTENT_TYPE_METAMESSAGE in accept.lower()

        # GET/DELETE: decode ?data=<hex> query param
        if request.method in ("GET", "DELETE"):
            await self._bind_query(request)

        # POST/PUT/PATCH: decode binary body
        if is_mm and request.method in ("POST", "PUT", "PATCH"):
            request = await self._decode_request(request)

        response = await call_next(request)

        # Encode response as binary if client expects MetaMessage
        if is_mm:
            response = await self._encode_response(response)

        return response

    async def _bind_query(self, request: Request) -> None:
        """Bind ?data=<hex> query param to request state.

        Follows mm-web-go: GET/DELETE params are hex-encoded MetaMessage binary.
        """
        data_param = request.query_params.get("data")
        if data_param:
            try:
                raw = bytes.fromhex(data_param)
                decoded = decode_to_value(raw)
                request.state.mm_query = decoded if isinstance(decoded, dict) else {}
            except Exception:
                request.state.mm_query = {}
        else:
            request.state.mm_query = {}

    async def _decode_request(self, request: Request) -> Request:
        """Decode binary MetaMessage request body."""
        try:
            body = await request.body()

            if not body:
                request.state.mm_body = {}
                return request

            decoded = decode_to_value(body)
            request.state.mm_body = decoded

            async def receive() -> Message:
                return {
                    "type": "http.request",
                    "body": body,
                }

            return Request(request.scope, receive)

        except Exception as exc:
            raise MMDecoderError(f"Failed to decode request body: {exc}") from exc

    async def _encode_response(self, response: Response) -> Response:
        """Ensure response is in binary MetaMessage format."""
        try:
            body_parts: list[bytes] = []
            async for chunk in response.body_iterator:
                body_parts.append(chunk)

            body = b"".join(body_parts)

            if not body:
                return response

            headers = dict(response.headers)
            headers["content-type"] = CONTENT_TYPE_METAMESSAGE
            headers["content-length"] = str(len(body))

            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=CONTENT_TYPE_METAMESSAGE,
            )

        except Exception as exc:
            raise MMEncoderError(f"Failed to encode response: {exc}") from exc


class MMRequestMiddleware:
    """Alternative middleware using ASGI interface."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)