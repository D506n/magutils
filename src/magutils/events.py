from functools import partial
from logging import getLogger
from typing import Awaitable, Callable, TypeVar

from .bg_tasks import BgTask
from .id import gen_id

T = TypeVar('T', bound=dict)
logger = getLogger(__name__)


class Event[T]():
    def __init__(self):
        self.subscribers: dict[str, Callable[[T], Awaitable[None]]] = {}

    def subscribe(self, callback: Callable[[T], Awaitable[None]]):
        sub_id = gen_id()
        self.subscribers[sub_id] = callback
        return partial(self.unsubscribe, sub_id)

    def unsubscribe(self, key: str):
        if key not in self.subscribers.keys():
            logger.warning('Key %s not found', key)
        else:
            self.subscribers.pop(key)

    def emit(self, payload: T, raise_errors: bool = False):
        BgTask.create(
            *[coro(payload) for coro in self.subscribers],
            raise_errors=raise_errors
        )