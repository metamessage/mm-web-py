"""Flask middleware for MetaMessage encoding and decoding.

Provides before_request/after_request hooks that:
- GET/DELETE: decodes ?data=<hex> query param into g.mm_query
- POST/PUT/PATCH: decodes binary request body into g.mm_body
- Responses encoded as binary MetaMessage when client expects it
"""

from typing import Optional, Set

import flask
from flask import Flask, Response, request
from metamessage import decode_to_value

from mm_core.types import CONTENT_TYPE_METAMESSAGE, MMDecoderError, MMEncoderError


class MMMiddleware:
    """Flask middleware for automatic MetaMessage encoding and decoding.

    Follows mm-web-go pattern:
    - GET/DELETE: decodes ?data=<hex> query param into g.mm_query
    - POST/PUT/PATCH: decodes binary request body into g.mm_body
    """

    SKIP_ROUTES: Set[str] = {
        "/openapi.json",
        "/docs",
        "/redoc",
    }

    def __init__(self, app: Flask, skip_routes: Optional[Set[str]] = None):
        self.app = app
        self.skip_routes = self.SKIP_ROUTES.copy()
        if skip_routes:
            self.skip_routes.update(skip_routes)
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register before_request and after_request hooks."""
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)

    def _should_skip(self) -> bool:
        """Check if current request path should be skipped."""
        return request.path in self.skip_routes

    def _before_request(self) -> None:
        """Process request before handler."""
        if self._should_skip():
            return

        content_type = request.headers.get("content-type", "")
        accept = request.headers.get("accept", "")

        flask.g._mm_expects = CONTENT_TYPE_METAMESSAGE in content_type.lower() or CONTENT_TYPE_METAMESSAGE in accept.lower()

        # GET/DELETE: decode ?data=<hex> query param
        if request.method in ("GET", "DELETE"):
            self._bind_query()

        # POST/PUT/PATCH: decode binary body
        if flask.g._mm_expects and request.method in ("POST", "PUT", "PATCH"):
            self._decode_body()

    def _after_request(self, response: Response) -> Response:
        """Process response after handler."""
        if self._should_skip():
            return response

        # Only encode if client expects MetaMessage
        if getattr(flask.g, "_mm_expects", False):
            return self._encode_response(response)

        return response

    def _bind_query(self) -> None:
        """Bind ?data=<hex> query param to g.mm_query."""
        data_param = request.args.get("data")
        if data_param:
            try:
                raw = bytes.fromhex(data_param)
                decoded = decode_to_value(raw)
                flask.g.mm_query = decoded if isinstance(decoded, dict) else {}
            except Exception:
                flask.g.mm_query = {}
        else:
            flask.g.mm_query = {}

    def _decode_body(self) -> None:
        """Decode binary MetaMessage request body."""
        try:
            body = request.get_data()

            if not body:
                flask.g.mm_body = {}
                return

            decoded = decode_to_value(body)
            flask.g.mm_body = decoded

        except Exception as exc:
            raise MMDecoderError(f"Failed to decode request body: {exc}") from exc

    def _encode_response(self, response: Response) -> Response:
        """Ensure response is in binary MetaMessage format."""
        try:
            body = response.get_data()

            if not body:
                return response

            response.headers["content-type"] = CONTENT_TYPE_METAMESSAGE
            response.headers["content-length"] = str(len(body))

            return response

        except Exception as exc:
            raise MMEncoderError(f"Failed to encode response: {exc}") from exc