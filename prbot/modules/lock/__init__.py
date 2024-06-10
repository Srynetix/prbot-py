from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from redis.asyncio import Redis

from prbot.config.settings import get_global_settings


class LockException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Lock exception: {message}")


class LockClient(ABC):
    @abstractmethod
    async def aclose(self) -> None: ...

    @abstractmethod
    async def ping(self) -> bool: ...

    @asynccontextmanager
    @abstractmethod
    async def lock(self, key: str) -> AsyncGenerator[None, None]:
        yield


class LockClientImplementation(LockClient):
    _client: Redis

    def __init__(self) -> None:
        settings = get_global_settings()
        self._client = Redis.from_url(settings.lock_url)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def ping(self) -> bool:
        return bool(await self._client.ping())

    @asynccontextmanager
    async def lock(self, key: str) -> AsyncGenerator[None, None]:
        try:
            lock = self._client.lock(key)
            await lock.acquire(blocking_timeout=0.1)
            yield
            await lock.release()
        except Exception as exc:
            raise LockException(str(exc)) from exc
