import asyncio as a
import sys
from collections.abc import Awaitable, Coroutine
from functools import partial
from logging import getLogger
from typing import Any, Optional, cast

logger = getLogger(__name__)


class BgTask:
    __inst: Optional['BgTask'] = None

    def __init__(self):
        self.tasks: dict[int, a.Task] = {}

    @classmethod
    def create(
        cls,
        *coros: Awaitable[Any],
        raise_errors: bool = False,
    ):
        inst = cls.__inst
        if not inst:
            inst = cls()
            cls.__inst = inst

        for coro in coros:
            if not isinstance(coro, Awaitable):
                raise TypeError('coro must be a Awaitable')
            task: a.Task = a.create_task(
                cast(Coroutine[Any, Any, Any], coro))
            task.add_done_callback(
                partial(inst._task_done, raise_errors=raise_errors))
            inst.tasks[id(task)] = task

    def _task_done(self, task: a.Task, raise_errors: bool):
        self.tasks.pop(id(task))
        try:
            task.result()
        except a.CancelledError:
            pass
        except Exception as e:
            if not raise_errors:
                logger.error(
                    'Got exception in background task. %s', 
                    e)
            else:  # nocov
                logger.critical(
                    'Got critical error in background task. %s', 
                    e)
                sys.exit(1)