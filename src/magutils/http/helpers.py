from functools import partial
from logging import getLogger
from typing import Optional

import orjson

from ..star.starlark import BaseCTX, Runner

HOOK_WRAPPER = '''
{setup}

def process(params, headers, body):
{script}
   return params, headers, body

results = process(params, headers, body)
'''
logger = getLogger('hook_executor')


class HookResultError(ValueError):
    """HTTP hook returned values that cannot form a request or response."""


def validate_hook_result(result: object) -> tuple[dict, dict, object]:
    if not isinstance(result, (tuple, list)) or len(result) != 3:
        raise HookResultError('HTTP hook must return params, headers, body')
    params, headers, body = result
    if not isinstance(params, dict) or not isinstance(headers, dict):
        raise HookResultError(
            'HTTP hook params and headers must be dictionaries'
        )
    try:
        orjson.dumps(body)
    except (TypeError, ValueError):
        raise HookResultError(
            'HTTP hook body must be JSON serializable'
        ) from None
    return params, headers, body


class Storage():
    def __init__(self):
        self.storage = {}

    def save(self, key: str, value, **kwargs):
        self.storage[key] = value

    def load(self, key: str, default=None):
        return self.storage.get(key, default)


class HookCtx(BaseCTX):
    def __init__(self, storage: Storage):
        self.storage = storage
        super().__init__()

    def setup(self):
        super().setup()
        self.mod.add_callable('st_save', self.storage.save)
        self.mod.add_callable('st_load', self.storage.load)


class QHookRunner(Runner):
    def __init__(self, size=5, storage: Optional[Storage] = None, **kwargs):
        wrapper = self.build_wrapper(HOOK_WRAPPER)
        self.storage = storage or Storage()
        super().__init__(size, wrapper, partial(HookCtx, self.storage))

    @classmethod
    async def run(cls,  # type: ignore[override]
                  script: str,
                  params: dict,
                  headers: dict,
                  body: dict,
                  **kwargs):
        if not kwargs.get('wrapper'):
            kwargs['wrapper'] = HOOK_WRAPPER
        add_ctx = {'params': params, 'headers': headers, 'body': body}
        r = await super().run(script, {}, add_ctx=add_ctx, **kwargs)
        return validate_hook_result(r.result)