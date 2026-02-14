import asyncio
from logging import getLogger

from src.utils.logging import config_async_logging
from src.utils.logging.formatters import MonocolorFormatter
from src.utils.logging.handlers import AsyncFileHandler

logger = getLogger()

fh = AsyncFileHandler('log.log')
fh.setFormatter(MonocolorFormatter())
config_async_logging(handlers=[fh])


async def main():
    for i in range(10):
        logger.info(i)

    await asyncio.sleep(1000)


asyncio.run(main())