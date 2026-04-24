from logging import getLogger

import uvicorn
from fastapi import FastAPI

from routers.root import build_root_router
from src.env import Env
from src.utils.logging import config_async_logging

env = Env()
config_async_logging()
logger = getLogger()


async def lifespan(app: FastAPI):
    logger.info('Successfully start app')
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(build_root_router())

if __name__ == '__main__':
    uvicorn.run(app, host=env.API_HOST, port=env.API_PORT, log_config=None)