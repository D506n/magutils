from functools import partial
from logging import getLogger

from ..star.starlark import BaseCTX, Runner

HOOK_WRAPPER = '''
{setup}
{script}
results = (params, headers, body,)
'''
logger = getLogger('hook_executor')


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
    def __init__(self, size=5, storage: Storage = None, **kwargs):
        wrapper = self.build_wrapper(HOOK_WRAPPER)
        self.storage = storage or Storage()
        super().__init__(size, wrapper, partial(HookCtx, self.storage))

    def wrap_script(self, user_script):
        return self.wrap_template.format(script=user_script)

    @classmethod
    async def run(cls, 
                  script: str, 
                  params: dict, 
                  headers: dict, 
                  body: dict, 
                  **kwargs):
        if not kwargs.get('wrapper'):
            kwargs['wrapper'] = HOOK_WRAPPER
        add_ctx = {'params': params, 'headers': headers, 'body': body}
        r = await super().run(script, {}, add_ctx=add_ctx, **kwargs)
        return r.result[0], r.result[1], r.result[2]