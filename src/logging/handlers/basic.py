from logging import Handler, LogRecord
from asyncio import Queue, create_task
import atexit
import asyncio
from threading import Semaphore, Event

class BaseAsyncHandler(Handler):
    def __init__(self, level = 0):
        super().__init__(level)
        self._closed = False 
        self.queue = Queue()
        self.bg_task = None
        self._shutdown_marker = object()
        self.closing_event = Event()
        self.closing_semaphore = Semaphore()
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
            if record is self._shutdown_marker:
                self.queue.task_done()
                # self.queue.shutdown() # отключено для py 3.9
                break

            await self.ahandle(record, at_exit=at_exit)
            self.queue.task_done()

    async def ahandle(self, record:LogRecord, at_exit=False):
        raise NotImplementedError()

    async def ajoin(self):
        if self.bg_task and (self.bg_task.done() or self.bg_task.cancelled()) and not self.queue.empty():
            await self.read_queue(at_exit=True)
            self.bg_task = None

    def close(self):
        self.closing_semaphore.acquire()
        if self.closing_event.is_set():
            return
        self.closing_event.set()
        self.closing_semaphore.release()
        super().close()
        print('closing')

        # try:
        self.queue.put_nowait(self._shutdown_marker)
        # except asyncio.QueueShutDown:
        #     pass

        try:
            asyncio.get_event_loop().run_until_complete(self.ajoin())
        except RuntimeError:
            asyncio.run(self.ajoin())