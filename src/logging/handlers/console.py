from aioconsole import aprint

from .basic import BaseAsyncHandler


class AsyncConsoleHandler(BaseAsyncHandler):
    async def ahandle(self, record, at_exit):
        msg = self.format(record)
        if at_exit:
            print(msg)
        else:
            await aprint(msg)