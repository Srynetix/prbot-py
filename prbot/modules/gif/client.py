from abc import ABC, abstractmethod

from prbot.config.settings import get_global_settings
from prbot.modules.http.client import HttpClient, HttpClientImplementation

from .models import TenorGifResponse


class GifClient(ABC):
    _client: HttpClient

    @abstractmethod
    def __init__(self, client: HttpClient | None = None) -> None: ...

    @abstractmethod
    async def aclose(self) -> None: ...

    @abstractmethod
    async def query_first_match(self, query: str) -> str | None: ...


class GifClientImplementation(GifClient):
    _client: HttpClient

    def __init__(self, client: HttpClient | None = None) -> None:
        self._client = client or HttpClientImplementation()
        self._client.configure(headers={}, base_url="https://g.tenor.com/v1")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def query_first_match(self, query: str) -> str | None:
        settings = get_global_settings()

        response = await self._client.request(
            method="GET",
            path="/search",
            params={
                "q": query,
                "key": settings.tenor_key,
                "limit": 3,
                "locale": "en_US",
                "contentfilter": "low",
                "media_filter": "basic",
                "ar_range": "all",
            },
        )

        data = TenorGifResponse.model_validate(response.json())
        return self._find_first_gif(data)

    def _find_first_gif(self, response: TenorGifResponse) -> str | None:
        for result in response.results:
            for media in result.media:
                for k, v in media.items():
                    if k == "tinygif":
                        return v.url

        return None
