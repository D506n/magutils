import asyncio as aio
import re
import textwrap
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Callable, Self

try:
    import starlark as sl
except ImportError:
    raise ImportError('Starlark runtime not installed. '
    'Use `uv add starlark-pyo3` to install it.')

REGEX_CACHE: dict[str, re.Pattern] = {}

DEFAULT_WRAPPER = """
re = struct(
    findall = star_re_findall,
    search = star_re_search
)
time = struct(
    now = star_time
)

def process(input):
{script}

def main(inp):
    result = process(inp)
    if not result:
        return {{}}
    if type(result) not in ['dict', 'list']:
        result = {{'result': result}}
    return result

results = main(input)
"""


class StarResult():
    def __init__(self):
        self._res: dict | None = None
        self.prints: list[str] = []
        self._error: Exception | None = None
        self.success: bool = False

    @property
    def result(self):
        if self.success:
            return self._res
        else:
            raise self.error

    @result.setter
    def result(self, value):
        self._res = value
        self.success = True

    @property
    def error(self):
        if self._error:
            raise self._error
        return None

    @error.setter
    def error(self, value):
        self._error = value
        self.success = False


class BaseCTX():
    def __init__(self):
        self.mod = sl.Module()
        self.prints: list[str] = []
        self.globs = sl.Globals.extended_by([
            sl.LibraryExtension.Json,
            sl.LibraryExtension.StructType
        ])
        self.setup()

    def setup(self):
        self.mod.add_callable('print', self.print)
        self.mod.add_callable('star_re_findall', re.findall)
        self.mod.add_callable('star_re_search', self.re_search)
        self.mod.add_callable('star_time', time.time)
        self.mod['results'] = {}
        self.mod['input'] = {}

    def re_search(self, pattern: str, text: str, group: int = 0):
        if pattern not in REGEX_CACHE:
            REGEX_CACHE[pattern] = re.compile(pattern)
        temp = REGEX_CACHE[pattern].search(text)
        if temp:
            return temp.group(group)
        return

    def print(self, *msgs):
        for msg in msgs:
            self.prints.append(str(msg))

    def clear(self):
        self.mod['results'] = {}
        self.mod['input'] = {}
        self.prints.clear()


class Runner:
    __inst: dict[str, Self] = {}

    def __init__(self, 
                 size: int = 5, 
                 wrapper: str = None,
                 ctx_factory: Callable[[], BaseCTX] = BaseCTX):
        self.ctxs: aio.Queue[BaseCTX] = aio.Queue()
        for _ in range(size):
            self.ctxs.put_nowait(ctx_factory())
        self.wrapper = wrapper or DEFAULT_WRAPPER
        self.wrap_template = textwrap.dedent(self.wrapper)
        self.__class__.__inst[wrapper] = self

    @asynccontextmanager
    async def get_ctx(self):
        ctx = await self.ctxs.get()
        yield ctx
        ctx.clear()
        self.ctxs.put_nowait(ctx)

    @lru_cache()
    def wrap_script(self, user_script: str) -> str:
        script_indented = textwrap.indent(user_script.strip(), '   ')
        return self.wrap_template.format(script=script_indented)

    @lru_cache()
    def parse(self, script) -> sl.AstModule:
        return sl.parse('main.star', script)

    async def _run(self, script, data):
        wrapped_script = self.wrap_script(script)
        res = StarResult()
        async with self.get_ctx() as ctx:
            globs = ctx.globs
            mod = ctx.mod
            mod['input'] = data
            try:
                ast = self.parse(wrapped_script)
                await aio.to_thread(sl.eval, mod, ast, globs)
            except Exception as e:
                res.error = e
            else:
                res.result = mod['results']
            res.prints = ctx.prints.copy()
            return res

    @classmethod
    def inst(cls, wrapper: str = None):
        if not wrapper:
            wrapper = DEFAULT_WRAPPER
        if wrapper not in cls.__inst.keys():
            cls(wrapper=wrapper)
        return cls.__inst[wrapper]

    @classmethod
    async def run(cls, script: str, data, wrapper: str = None) -> StarResult:
        self = cls.inst(wrapper=wrapper)
        return await self._run(script, data)