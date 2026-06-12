"""Client SDK for MetaMessage API.

MMClient provides both sync and async clients for communicating
with MetaMessage-based APIs, following mm-web-go patterns:
- GET/DELETE: hex-encoded MetaMessage in ?data=<hex> query param
- POST/PUT/PATCH: binary MetaMessage in request body
- Responses always decoded as binary MetaMessage
"""

from typing import Any, Dict, Generic, Optional, Type, TypeVar, Union

import httpx
from metamessage import decode_to_value, encode_from_value

from .types import CONTENT_TYPE_METAMESSAGE

T = TypeVar("T")


class MMResponse(Generic[T]):
    """A MetaMessage response wrapper.

    Attributes:
        data: The decoded response data (dict or typed model if target_type provided)
        status_code: HTTP status code
        raw_data: Raw response bytes
    """

    def __init__(self, data: T, status_code: int, raw_data: bytes):
        self.data = data
        self.status_code = status_code
        self.raw_data = raw_data


class MMClientError(Exception):
    """Exception raised for MMClient errors."""
    pass


class MMClient:
    """Synchronous MetaMessage HTTP client.

    Follows mm-web-go client pattern:
    - GET/DELETE: hex-encode body, send as ?data=<hex>
    - POST/PUT/PATCH: binary body in request body
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client()

    def _get_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _build_headers(
        self,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": CONTENT_TYPE_METAMESSAGE,
            "Content-Type": CONTENT_TYPE_METAMESSAGE,
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _encode_body(self, data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        # Convert model instances to dict
        if hasattr(data, '__dict__') and not isinstance(data, (dict, list)):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
        return encode_from_value(data)

    def _decode_body(
        self,
        data: bytes,
        target_type: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        if not data:
            return {} if target_type is None else target_type()

        decoded = decode_to_value(data)

        if target_type is not None and isinstance(decoded, dict):
            return target_type(**decoded)
        return decoded

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        headers = self._build_headers(extra_headers)

        url = self._get_url(path)
        content = None

        if method in ("GET", "DELETE"):
            if body is not None:
                raw = self._encode_body(body)
                query = raw.hex()
                url = f"{url}?data={query}"
        else:
            if body is not None:
                content = self._encode_body(body)

        resp = self._client.request(
            method=method,
            url=url,
            content=content,
            headers=headers,
        )

        try:
            decoded = self._decode_body(resp.content, target_type=target_type)
        except Exception:
            decoded = resp.content

        return MMResponse(data=decoded, status_code=resp.status_code, raw_data=resp.content)

    def get(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return self.request("GET", path, body=body, extra_headers=extra_headers, target_type=target_type)

    def post(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return self.request("POST", path, body=body, extra_headers=extra_headers, target_type=target_type)

    def put(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return self.request("PUT", path, body=body, extra_headers=extra_headers, target_type=target_type)

    def patch(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return self.request("PATCH", path, body=body, extra_headers=extra_headers, target_type=target_type)

    def delete(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return self.request("DELETE", path, body=body, extra_headers=extra_headers, target_type=target_type)

    def health(self) -> str:
        """Simple health check."""
        try:
            resp = self._client.get(f"{self.base_url}/health")
            return "ok" if resp.status_code == 200 else f"error: {resp.status_code}"
        except Exception as e:
            return f"error: {e}"

    def close(self) -> None:
        self._client.close()


class AsyncMMClient:
    """Asynchronous MetaMessage HTTP client."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient()

    def _get_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _build_headers(
        self,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": CONTENT_TYPE_METAMESSAGE,
            "Content-Type": CONTENT_TYPE_METAMESSAGE,
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _encode_body(self, data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        if hasattr(data, '__dict__') and not isinstance(data, (dict, list)):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
        return encode_from_value(data)

    def _decode_body(
        self,
        data: bytes,
        target_type: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        if not data:
            return {} if target_type is None else target_type()

        decoded = decode_to_value(data)

        if target_type is not None and isinstance(decoded, dict):
            return target_type(**decoded)
        return decoded

    async def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        headers = self._build_headers(extra_headers)

        url = self._get_url(path)
        content = None

        if method in ("GET", "DELETE"):
            if body is not None:
                raw = self._encode_body(body)
                query = raw.hex()
                url = f"{url}?data={query}"
        else:
            if body is not None:
                content = self._encode_body(body)

        resp = await self._client.request(
            method=method,
            url=url,
            content=content,
            headers=headers,
        )

        try:
            decoded = self._decode_body(resp.content, target_type=target_type)
        except Exception:
            decoded = resp.content

        return MMResponse(data=decoded, status_code=resp.status_code, raw_data=resp.content)

    async def get(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return await self.request("GET", path, body=body, extra_headers=extra_headers, target_type=target_type)

    async def post(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return await self.request("POST", path, body=body, extra_headers=extra_headers, target_type=target_type)

    async def put(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return await self.request("PUT", path, body=body, extra_headers=extra_headers, target_type=target_type)

    async def patch(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return await self.request("PATCH", path, body=body, extra_headers=extra_headers, target_type=target_type)

    async def delete(
        self,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        return await self.request("DELETE", path, body=body, extra_headers=extra_headers, target_type=target_type)