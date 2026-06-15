"""Client SDK for MetaMessage API.

MMClient provides both sync and async clients for communicating
with MetaMessage-based APIs, following mm-web-go patterns:
- GET/DELETE: hex-encoded MetaMessage in ?data=<hex> query param
- POST/PUT/PATCH: binary MetaMessage in request body
- Responses always decoded as binary MetaMessage
"""

import dataclasses
import typing
from typing import Any, Dict, Generic, Optional, Type, TypeVar, Union

import httpx
from metamessage import decode_to_jsonc, decode_to_value, encode_from_value

from .types import CONTENT_TYPE_METAMESSAGE

T = TypeVar("T")


def _from_dict(data: Any, target_type: Type[T]) -> Any:
    """Recursively reconstruct typed model from decoded dict.
    
    Handles nested types like List[User], Optional[str], Dict[str, Model],
    and arbitrary nested dataclasses.
    """
    if target_type is None or data is None:
        return data

    # Handle generic types (List[T], Dict[K,V], Optional[T], Union[...])
    origin = getattr(target_type, "__origin__", None)
    args = getattr(target_type, "__args__", ())

    if origin is list:
        if isinstance(data, (list, tuple)) and args:
            item_type = args[0]
            return [_from_dict(item, item_type) for item in data]
        return data

    if origin is dict:
        if isinstance(data, dict) and args and len(args) > 1:
            val_type = args[1]
            return {k: _from_dict(v, val_type) for k, v in data.items()}
        return data

    if origin is Union:
        real_types = [a for a in args if a is not type(None)]
        if real_types:
            return _from_dict(data, real_types[0])
        return data

    # Dataclass: recursively construct
    if dataclasses.is_dataclass(target_type):
        if isinstance(data, dict):
            hints = typing.get_type_hints(target_type)
            field_names = {f.name for f in dataclasses.fields(target_type)}
            kwargs = {}
            for key, val in data.items():
                if key not in field_names:
                    continue  # skip unknown fields
                field_type = hints.get(key, type(val))
                kwargs[key] = _from_dict(val, field_type)
            return target_type(**kwargs)
        return data

    # Primitive or unknown: return as-is
    return data


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

    def __init__(self, base_url: str, debug: bool = False):
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self._options_schema_md5: Dict[str, str] = {}
        self._client = httpx.Client(
            transport=httpx.HTTPTransport(trust_env=False),
        )

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
            return {}

        decoded = decode_to_value(data)

        if target_type is not None:
            return _from_dict(decoded, target_type)
        return decoded

    def _options_preflight(self, path: str, body_type: Optional[Type] = None) -> None:
        """Send OPTIONS preflight to validate request schema (Go impl pattern).

        Decodes the OPTIONS response using body_type as target_type to verify
        the request struct matches the server's expected schema.
        """
        resp = self._client.request(
            method="OPTIONS",
            url=self._get_url(path),
            headers={
                **self._build_headers(),
                "Cache-Control": "no-cache",
            },
        )
        if resp.status_code != 200:
            raise MMClientError(
                f"schema request failed: OPTIONS {path} -> {resp.status_code}"
            )
        # Cache schema-md5 from response headers for subsequent requests
        self._options_schema_md5[path] = resp.headers.get("schema-md5", "")
        if resp.content:
            try:
                v = decode_to_value(resp.content, target_type=body_type)
                print(f'OPTIONS value: { v }')
                print(f'OPTIONS decode_to_jsonc: { decode_to_jsonc(resp.content)}')
            except Exception as e:
                raise MMClientError(
                    f"schema mismatch for {path}: {e}"
                )

    def request(self,
        method: str,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        # Preflight: send OPTIONS to validate request schema (Go pattern)
        if method != "OPTIONS":
            self._options_preflight(path, body_type=type(body) if body is not None else None)

        headers = self._build_headers(extra_headers)
        # Add cached schema-md5 for schema validation
        schema_md5 = self._options_schema_md5.get(path)
        if schema_md5:
            headers["schema-md5"] = schema_md5
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

        # Go impl: only status 200 is success
        if resp.status_code != 200:
            err_msg = f"request failed: {resp.status_code} {method} {path}"
            try:
                jsonc = decode_to_jsonc(resp.content)
                err_msg += f" body={jsonc}"
            except Exception:
                err_msg += f" body={resp.content!r}"
            raise MMClientError(err_msg)

        try:
            decoded = self._decode_body(resp.content, target_type=target_type)
        except Exception as e:
            jsonc = decode_to_jsonc(resp.content)
            raise MMClientError(f"decode response failed: {e}: {jsonc}")

        # Debug: print JSONC (Go debug pattern)
        if self.debug:
            try:
                jsonc = decode_to_jsonc(resp.content)
                print(f"{method} {path}:\n{jsonc}")
            except Exception:
                print(f"{method} {path}: {resp.content!r}")

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

    def __init__(self, base_url: str, debug: bool = False):
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self._options_schema_md5: Dict[str, str] = {}
        self._client = httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(trust_env=False),
        )

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
            return {}

        decoded = decode_to_value(data)

        if target_type is not None:
            return _from_dict(decoded, target_type)
        return decoded

    async def _options_preflight(self, path: str, body_type: Optional[Type] = None) -> None:
        """Send OPTIONS preflight to validate request schema (Go impl pattern)."""
        resp = await self._client.request(
            method="OPTIONS",
            url=self._get_url(path),
            headers=self._build_headers(),
        )
        if resp.status_code != 200:
            raise MMClientError(
                f"schema request failed: OPTIONS {path} -> {resp.status_code}"
            )
        # Cache schema-md5 from response headers for subsequent requests
        self._options_schema_md5[path] = resp.headers.get("schema-md5", "")
        if resp.content:
            try:
                decode_to_value(resp.content, target_type=body_type)
            except Exception as e:
                raise MMClientError(
                    f"schema mismatch for {path}: {e}"
                )

    async def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        extra_headers: Optional[Dict[str, str]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> MMResponse:
        # Preflight: send OPTIONS to validate request schema (Go pattern)
        if method != "OPTIONS":
            await self._options_preflight(path, body_type=type(body) if body is not None else None)

        headers = self._build_headers(extra_headers)
        # Add cached schema-md5 for schema validation
        schema_md5 = self._options_schema_md5.get(path)
        if schema_md5:
            headers["schema-md5"] = schema_md5
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

        # Go impl: only status 200 is success
        if resp.status_code != 200:
            err_msg = f"request failed: {resp.status_code} {method} {path}"
            try:
                jsonc = decode_to_jsonc(resp.content)
                err_msg += f" body={jsonc}"
            except Exception:
                err_msg += f" body={resp.content!r}"
            raise MMClientError(err_msg)

        try:
            decoded = self._decode_body(resp.content, target_type=target_type)
        except Exception as e:
            jsonc = decode_to_jsonc(resp.content)
            raise MMClientError(f"decode response failed: {e}: {jsonc}")

        # Debug: print JSONC (Go debug pattern)
        if self.debug:
            try:
                jsonc = decode_to_jsonc(resp.content)
                print(f"{method} {path}:\n{jsonc}")
            except Exception:
                print(f"{method} {path}: {resp.content!r}")

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