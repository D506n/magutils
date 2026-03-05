import asyncio
from logging import getLogger

from src.utils.logging import config_async_logging

config_async_logging()
logger = getLogger()


async def main():
    logger.info('Hello world!')


if __name__ == '__main__':
    asyncio.run(main())