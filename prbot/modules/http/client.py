from abc import ABC, abstractmethod
from typing import Any

import backoff
import httpx
from httpx import AsyncClient, Response


class HttpClient(ABC):
    MAX_BACKOFF_TRIES = 2

    @abstractmethod
    def configure(self, *, headers: dict[str, Any], base_url: str) -> None: ...

    @abstractmethod
    def set_authentication_token(self, token: str) -> None: ...

    @abstractmethod
    async def aclose(self) -> None: ...

    @abstractmethod
    async def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Response: ...

    @backoff.on_exception(
        backoff.expo, httpx.HTTPStatusError, max_tries=MAX_BACKOFF_TRIES
    )
    async def _retry_request(
        self, *, method: str, path: str, **kwargs: Any
    ) -> Response:
        response = await self.request(method, path, **kwargs)
        response.raise_for_status()

        return response


class HttpClientImplementation(HttpClient):
    _client: AsyncClient

    def configure(self, *, headers: dict[str, Any], base_url: str) -> None:
        self._client = AsyncClient(headers=headers, base_url=base_url)

    def set_authentication_token(self, token: str) -> None:
        new_headers = httpx.Headers()
        for k, v in self._client.headers.items():
            if k.lower() == "authorization":
                continue

            new_headers[k] = v

        new_headers["authorization"] = f"Bearer {token}"
        self._client.headers = new_headers

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Response:
        return await self._client.request(
            method, path, content=body, params=params, json=json, **kwargs
        )
