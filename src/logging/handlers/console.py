from .basic import BaseAsyncHandler
from aioconsole import aprint

class AsyncConsoleHandler(BaseAsyncHandler):
    async def ahandle(self, record, at_exit):
        msg = self.format(record)
        if at_exit:
            print(msg)
        else:
            await aprint(msg)