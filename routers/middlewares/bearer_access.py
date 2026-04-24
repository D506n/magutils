from typing import Iterable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class BearerAccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, 
                app, 
                token: str, 
                excluded_paths: Iterable[str] = None, 
                header: str = 'Authorization'):
        super().__init__(app)
        self.token = token
        if not excluded_paths:
            excluded_paths = {"/login", "/docs", "/openapi.json"}
        else:
            excluded_paths = set(excluded_paths)
        self.excluded = excluded_paths
        self.header = header

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.excluded:
            return await call_next(request)

        auth_header = request.headers.get(self.header)
        if not auth_header:
            return JSONResponse(
                status_code=401, content={'detail': "Unauthorized"})

        if not auth_header == self.token:
            return JSONResponse(
                status_code=401, content={'detail': "Invalid token"})

        response = await call_next(request)
        return response
