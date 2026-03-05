import asyncio as a
import sys
import traceback
from functools import partial
from logging import getLogger
from typing import Coroutine, Self

logger = getLogger(__name__)


class BgTask:
    __inst: Self = None

    def __init__(self):
        self.tasks: dict[int, a.Task] = {}

    @classmethod
    def create(cls, *coros: Coroutine, raise_errors: bool = False):
        if not cls.__inst:
            cls.__inst = cls()
        self = cls.__inst

        for coro in coros:
            if not isinstance(coro, Coroutine):
                raise TypeError('coro must be a coroutine')
            task = a.create_task(coro)
            task.add_done_callback(
                partial(self._task_done, raise_errors=raise_errors))
            self.tasks[id(task)] = task

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
                    f'{e.__class__.__name__}: {e}')
            else:  # nocov
                logger.critical(
                    'Got critical error in background task. %s', 
                    traceback.format_exc())
                sys.exit(1)