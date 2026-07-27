import asyncio
import atexit
from asyncio import Queue, create_task
from logging import Handler, LogRecord
from threading import Event
from typing import Any, Generator

from ..formatters.base import BaseFormatter


class BaseAsyncHandler(Handler):
    def __init__(self, level=0):
        super().__init__(level)
        self._closed = False 
        self.queue: Queue[LogRecord] = Queue()
        self.bg_task = None
        self.closing_event = Event()
        atexit.register(self.close)

    def emit(self, record):
        if self._closed:
            return

        self.queue.put_nowait(record)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        if self.bg_task is None:
            self.bg_task = create_task(self.read_queue())

    async def read_queue(self, at_exit=False):
        while not self.closing_event.is_set():
            try:
                record = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            try:
                await self.ahandle(record, at_exit=at_exit)
                self.queue.task_done()
            except Exception:  # nocov я пока не нашёл случаев когда может 
                # возникнуть такая ошибка, в будущем дополню
                self.handleError(record)
        self.queue.shutdown()

    async def ahandle(self, record: LogRecord, at_exit=False):
        raise NotImplementedError()

    def chandle(self, record):
        pass

    def cflush(self):
        pass

    def close(self):
        if self.closing_event.is_set():
            return
        self.closing_event.set()
        super().close()

        while True:
            try:
                log = self.queue.get_nowait()
            except Exception:
                break
            self.chandle(log)
        if getattr(self, 'buffer', None):
            self.cflush()

    def extract_exception(self, record: LogRecord):
        result = None
        if isinstance(record.msg, Exception):
            result = record.msg
        elif len(record.args) == 1 and isinstance(record.args[0], Exception):
            result = record.args[0]
        return result

    def format_exception(self, 
            record: LogRecord,
            e: Exception,
            trace_id: str,
            limit: int = 25
    ) -> Generator[str, Any, None] | list[str]:
        fmt = self.formatter
        if not fmt or not hasattr(fmt, 'format_exception'):
            fmt = BaseFormatter()
        return fmt.format_exception(record, e, trace_id, limit)