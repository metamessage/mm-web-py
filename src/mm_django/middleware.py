"""Django middleware for MetaMessage encoding and decoding.

Provides:
- GET/DELETE: decodes ?data=<hex> query param into request.mm_query
- POST/PUT/PATCH: decodes binary request body into request.mm_body
- Response headers set to MetaMessage content type when client expects it
"""

from typing import Optional, Set

from django.http import HttpRequest, HttpResponse
from metamessage import decode_to_value

from mm_core.types import CONTENT_TYPE_METAMESSAGE, MMDecoderError, MMEncoderError


class MMMiddleware:
    """Django middleware for automatic MetaMessage encoding and decoding.

    Follows mm-web-go pattern:
    - GET/DELETE: decodes ?data=<hex> query param into request.mm_query
    - POST/PUT/PATCH: decodes binary request body into request.mm_body

    Add to your Django settings:

        MIDDLEWARE = [
            ...
            'mm_django.middleware.MMMiddleware',
        ]
    """

    SKIP_ROUTES: Set[str] = set()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path in self.SKIP_ROUTES:
            return self.get_response(request)

        self._process_request(request)
        response = self.get_response(request)
        self._process_response(request, response)

        return response

    def _process_request(self, request: HttpRequest) -> None:
        """Process incoming request: decode query params or body."""
        content_type = request.META.get("CONTENT_TYPE", "")
        accept = request.META.get("HTTP_ACCEPT", "")

        request._mm_expects = (
            CONTENT_TYPE_METAMESSAGE in content_type.lower()
            or CONTENT_TYPE_METAMESSAGE in accept.lower()
        )

        # GET/DELETE: decode ?data=<hex> query param
        if request.method in ("GET", "DELETE"):
            self._bind_query(request)

        # POST/PUT/PATCH: decode binary body
        if request._mm_expects and request.method in ("POST", "PUT", "PATCH"):
            self._decode_body(request)

    def _bind_query(self, request: HttpRequest) -> None:
        """Bind ?data=<hex> query param to request.mm_query."""
        data_param = request.GET.get("data")
        if data_param:
            try:
                raw = bytes.fromhex(data_param)
                decoded = decode_to_value(raw)
                request.mm_query = decoded if isinstance(decoded, dict) else {}
            except Exception:
                request.mm_query = {}
        else:
            request.mm_query = {}

    def _decode_body(self, request: HttpRequest) -> None:
        """Decode binary MetaMessage request body into request.mm_body."""
        try:
            body = request.body

            if not body:
                request.mm_body = {}
                return

            decoded = decode_to_value(body)
            request.mm_body = decoded

        except Exception as exc:
            raise MMDecoderError(f"Failed to decode request body: {exc}") from exc

    def _process_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """Set MetaMessage content type on response when client expects it."""
        if getattr(request, "_mm_expects", False):
            body = response.content
            if body:
                response["Content-Type"] = CONTENT_TYPE_METAMESSAGE
                response["Content-Length"] = str(len(body))