from contextlib import asynccontextmanager as actx
from typing import Self

from aiolimiter import AsyncLimiter


class Limiter():
    __inst: Self = None

    def __init__(self):
        self.limiters: dict[str, AsyncLimiter] = {}
        self.__class__.__inst = self

    @classmethod
    def inst(cls):
        if cls.__inst is None:
            cls.__inst = cls()
        return cls.__inst

    @classmethod
    def set(cls, key: str, limit: int = 10, per: int = 1):
        self = cls.inst()
        if key not in self.limiters.keys():
            self.limiters[key] = AsyncLimiter(limit, per)

    @classmethod
    def get(cls, key: str):
        self = cls.inst()
        if key not in self.limiters.keys():
            self.set(key)
        return self.limiters[key]

    @classmethod
    @actx
    async def rate_limit(cls, key: str):
        limiter = cls.get(key)
        async with limiter:
            yield