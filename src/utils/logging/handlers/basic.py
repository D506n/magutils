import asyncio
import atexit
from asyncio import Queue, create_task
from logging import Handler, LogRecord


class BaseAsyncHandler(Handler):
    def __init__(self, level=0):
        super().__init__(level)
        self._closed = False 
        self.queue: Queue[LogRecord] = Queue()
        self.bg_task = None
        self._shutdown_marker = object()
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
        while True:
            record = await self.queue.get()
            try:
                await self.ahandle(record, at_exit=at_exit)
                self.queue.task_done()
            except Exception:  # nocov
                self.handleError(record)

    async def ahandle(self, record: LogRecord, at_exit=False):
        raise NotImplementedError()

    def chandle(self, record):
        pass

    def cflush(self):
        pass

    def close(self):
        super().close()

        while True:
            try:
                log = self.queue.get_nowait()
            except Exception:
                break
            self.chandle(log)
        if getattr(self, 'buffer'):
            self.cflush()