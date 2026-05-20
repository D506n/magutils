import asyncio

from .basic import BaseAsyncHandler


class AsyncConsoleHandler(BaseAsyncHandler):
    def __init__(self, buffer_size: int = 500, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer: list[str] = []
        self.buffer_size = buffer_size
        self.delayed_flush: asyncio.Task = None
        self.alock = asyncio.Lock()

    async def daflush(self):
        await asyncio.sleep(0.01)
        await self.aflush()
        self.delayed_flush = None

    async def aflush(self):
        async with self.alock:
            if self.buffer:
                await asyncio.to_thread(self.cflush)

    def cflush(self):
        if self.buffer:
            print('\n'.join(self.buffer))
            self.buffer.clear()

    async def ahandle(self, record, at_exit):
        msg = self.format(record)
        if len(self.buffer) < self.buffer_size:
            self.buffer.append(msg)
        else:
            await self.aflush()
            self.buffer.append(msg)
        if self.delayed_flush is None:
            self.delayed_flush = asyncio.create_task(self.daflush())

    def chandle(self, record):
        msg = self.format(record)
        if len(self.buffer) < self.buffer_size:
            self.buffer.append(msg)
        else:
            self.cflush()
            self.buffer.append(msg)