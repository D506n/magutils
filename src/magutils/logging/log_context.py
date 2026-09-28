from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

log_ctx: ContextVar[dict[str, Any]] = ContextVar('log_ctx', default={})


@contextmanager
def add_log_context(**kw):
    token = log_ctx.set(kw)
    try:
        yield
    finally:
        log_ctx.reset(token)


def ctx_add(**kw):
    return log_ctx.set({**log_ctx.get(), **kw})