import asyncio as aio
import re
import textwrap
import time
from contextlib import asynccontextmanager
from contextvars import copy_context
from functools import lru_cache, partial
from threading import Event
from typing import Any, Callable, Optional, Self, TypeVar, cast

try:
    import starlark as sl
except ImportError:
    raise ImportError('Starlark runtime not installed. '
    'Use `uv add starlark-pyo3` to install it.')

REGEX_CACHE: dict[str, re.Pattern] = {}

DEFAULT_SETUP = """
def star_elapsed():
    return time.now() - time.start

re = struct(
    findall = star_re_findall,
    search = star_re_search
)
time = struct(
    now = star_time,
    start = star_time(),
    elapsed = star_elapsed,
    sleep = star_sleep
)
"""

DEFAULT_WRAPPER = """
{setup}

def process(input):
{script}

def main(inp):
    result = process(inp)
    if result == None:
        return {{}}
    if type(result) not in ['dict', 'list']:
        result = {{'result': result}}
    return result

results = main(input)
"""

ResultType = TypeVar('ResultType', bound=dict)


class StarResult[ResultType]():
    def __init__(self):
        self._res: ResultType | None = None
        self.prints: list[str] = []
        self._error: Exception | None = None
        self.success: bool = False

    @property
    def result(self) -> ResultType:
        if self.success:
            return cast(ResultType, self._res)
        if self._error is not None:
            raise self._error
        raise RuntimeError('Starlark result is not available')

    @result.setter
    def result(self, value):
        self._res = value
        self.success = True

    @property
    def error(self):
        if self._error:
            raise self._error

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
        self.mod.add_callable('star_sleep', time.sleep)
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
    __inst: dict[str | None, Self] = {}

    def __init__(self, 
                 size: int = 5, 
                 wrapper: Optional[str] = None,
                 ctx_factory: Callable[[], BaseCTX] = BaseCTX):
        self.ctxs: aio.Queue[BaseCTX] = aio.Queue()
        for _ in range(size):
            self.ctxs.put_nowait(ctx_factory())
        self.wrapper = wrapper or self.build_wrapper()
        self.wrap_template = textwrap.dedent(self.wrapper)
        self.__class__.__inst[wrapper] = self

    @classmethod
    def build_wrapper(cls, wrapper: Optional[str] = None, **kwargs):
        if not wrapper:
            wrapper = DEFAULT_WRAPPER
        if 'setup' not in kwargs:
            kwargs['setup'] = DEFAULT_SETUP
        parts = [
            p.format(**kwargs).replace('{', '{{').replace('}', '}}') 
            for p in wrapper.split('{script}')]
        return '{script}'.join(parts)

    @asynccontextmanager
    async def get_ctx(self, add_ctx: Optional[dict] = None):
        ctx = await self.ctxs.get()
        try:
            self._prepare_ctx(ctx, add_ctx)
            yield ctx
        finally:
            self._release_ctx(ctx, add_ctx)

    @staticmethod
    def _prepare_ctx(ctx: BaseCTX, add_ctx: dict | None) -> None:
        if add_ctx:
            for key, value in add_ctx.items():
                ctx.mod[key] = value

    def _release_ctx(self, ctx: BaseCTX, add_ctx: dict | None) -> None:
        if add_ctx:
            for key in add_ctx:
                ctx.mod[key] = None
        ctx.clear()
        self.ctxs.put_nowait(ctx)

    def _finish_run(
        self, ctx: BaseCTX, add_ctx: dict | None,
        worker: aio.Future[StarResult[Any]],
    ) -> None:
        # The executor future completes only after the thread stops using ctx.
        self._release_ctx(ctx, add_ctx)
        if not worker.cancelled():
            worker.exception()

    @lru_cache()
    def wrap_script(self, user_script: str) -> str:
        script_indented = textwrap.indent(user_script.strip(), '   ')
        return self.wrap_template.format(script=script_indented)

    @lru_cache()
    def parse(self, script) -> sl.AstModule:
        return sl.parse('main.star', script)

    @staticmethod
    def _evaluate(
        ctx: BaseCTX, ast: sl.AstModule, cancelled: Event,
    ) -> StarResult[Any]:
        result: StarResult[Any] = StarResult()
        options = sl.EvalOptions(check_cancelled=cancelled.is_set)
        try:
            sl.eval_with(options, ctx.mod, ast, ctx.globs)
            result.result = ctx.mod['results']
        except Exception as exc:
            result.error = exc
        result.prints = ctx.prints.copy()
        return result

    async def _run(self,
                   script,
                   data,
                   add_ctx: Optional[dict] = None):
        wrapped_script = self.wrap_script(script)
        ctx = await self.ctxs.get()
        cancelled = Event()
        worker: aio.Future[StarResult[Any]] | None = None
        try:
            self._prepare_ctx(ctx, add_ctx)
            ctx.mod['input'] = data
            ast = self.parse(wrapped_script)
            # Preserve ContextVars just as asyncio.to_thread does. Shield keeps
            # cancellation from marking the worker done before it really ends.
            worker = aio.get_running_loop().run_in_executor(
                None, copy_context().run, self._evaluate, ctx, ast, cancelled,
            )
            worker.add_done_callback(partial(self._finish_run, ctx, add_ctx))
            return await aio.shield(worker)
        except aio.CancelledError:
            cancelled.set()
            raise
        except Exception as exc:
            result: StarResult[Any] = StarResult()
            result.error = exc
            return result
        finally:
            if worker is None:
                self._release_ctx(ctx, add_ctx)

    @classmethod
    def inst(cls, wrapper: Optional[str] = None):
        if wrapper not in cls.__inst.keys():
            cls(wrapper=wrapper)
        return cls.__inst[wrapper]

    @classmethod
    async def run(cls, 
                  script: str, 
                  data, 
                  wrapper: Optional[str] = None,
                  add_ctx: Optional[dict] = None, 
                  **kwargs) -> StarResult:
        if 'setup' not in kwargs:
            kwargs['setup'] = DEFAULT_SETUP
        if not wrapper:
            wrapper = DEFAULT_WRAPPER
        wrapper = cls.build_wrapper(wrapper, **kwargs)
        self = cls.inst(wrapper=wrapper)
        return await self._run(script, data, add_ctx)