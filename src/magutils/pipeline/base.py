import inspect
import warnings
from functools import wraps
from logging import getLogger
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    Protocol,
    Self,
    TypeVar,
    Union,
)

from pydantic import BaseModel

from ..id import gen_id

T = TypeVar('T', bound=BaseModel)

StepsType = list[tuple[str, int]]

logger = getLogger(__name__)

#  Отключаю лишний шум от asyncio, т.к. это сообщение для шагов 
#  пайплайна не несёт смысловой нагрузки, любой из них может
#  становиться точкой выхода из пайплайна
warnings.filterwarnings('ignore', 
                        "coroutine 'Pipeline.last_step' was never awaited", 
                        RuntimeWarning)


class StopPipeline(Exception): ...


class PipelineMeta(type):
    def __new__(mcs, name: str, bases: tuple, attrs: dict) -> 'type':
        steps: StepsType = []
        for attr_name, attr in attrs.items():
            if callable(attr) and hasattr(attr, '_step_order'):
                steps.append((attr_name, attr._step_order))
        steps.sort(key=lambda x: x[1])
        attrs['_steps'] = steps
        cls = super().__new__(mcs, name, bases, attrs)
        return cls


PipelineStep = Union[
    Callable[..., Awaitable[Any]],
    Callable[..., AsyncGenerator[Any, None]],
    Callable[..., Generator[Any, None, Any]],
    Callable[..., Any],
]


def step(order: int) -> PipelineStep:  # noqa: C901
    """Декоратор для пометки шагов в конвеере."""
    def decorator(func: PipelineStep) -> PipelineStep:  # noqa: C901
        warnings.filterwarnings(
            'ignore', 
            f"coroutine '.+{func.__name__}' was never awaited", 
            RuntimeWarning)  # В пайплайне это предупреждение не нужно

        def select_wrap(func):
            if inspect.iscoroutinefunction(func):
                wrap = async_wrapper
            elif inspect.isasyncgenfunction(func):
                wrap = async_gen_wrapper
            elif inspect.isgeneratorfunction(func):
                wrap = sync_gen_wrap
            elif inspect.isfunction(func):
                wrap = sync_wrap
            else:
                raise TypeError('Unknown function type!')
            return wrap

        def refresh_pipeline(*args):
            p: 'Pipeline' = args[0]
            p.step_num = order
            p.step_name = func.__name__
            logger.info(
                '%s runs %s step: %s', p.name, p.step_num, p.step_name)
            return p

        async def async_call(func, *args, **kwargs):
            self: 'Pipeline' = refresh_pipeline(*args)
            if inspect.isasyncgen(func):
                return await func.__anext__()
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                logger.error('%s failed on %s step: %s', self.name, 
                             func.__name__, self.step_num)
                raise e
            if inspect.isasyncgen(result):
                return result
            if result is not None:
                self.result = result
                raise StopPipeline

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            call_next = kwargs.pop('_call_next')
            await async_call(func, *args, **kwargs)
            await call_next

        @wraps(func)
        async def async_gen_wrapper(*args, **kwargs):
            call_next = kwargs.pop('_call_next')
            gen = func(*args, **kwargs)
            await async_call(gen, *args, **kwargs)
            try:
                await call_next
            except StopPipeline:
                pass
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

        def sync_call(func, *args, **kwargs):
            self: 'Pipeline' = refresh_pipeline(*args)
            if inspect.isgenerator(func):
                return next(func)
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logger.error('%s failed on %s step: %s', self.name, 
                             func.__name__, self.step_num)
                raise e
            if inspect.isgenerator(result):
                return result
            if result is not None and self.result is None:
                self.result = result
                raise StopPipeline

        @wraps(func)
        async def sync_wrap(*args, **kwargs):
            call_next = kwargs.pop('_call_next')
            sync_call(func, *args, **kwargs)
            await call_next

        @wraps(func)
        async def sync_gen_wrap(*args, **kwargs):
            call_next = kwargs.pop('_call_next')
            gen = sync_call(func, *args, **kwargs)
            next(gen)
            try:
                await call_next
            except StopPipeline:
                pass
            try:
                next(gen)
            except StopIteration:
                pass

        wrap: PipelineStep = select_wrap(func)

        wrap._step_order = order
        return wrap
    return decorator


class PipeCTX():
    def __init__(self, **kwargs):
        self.id = gen_id()
        self.kwargs = kwargs


class PipeCTXFactory(Protocol):
    def __call__(self, **kwds: Any) -> PipeCTX: ...


class Pipeline[T](metaclass=PipelineMeta):
    def __init__(self, ctx_factory: PipeCTXFactory = PipeCTX, **kwargs):
        super().__init__()
        self.result: T = None
        self.step_num = 0
        self.step_name: str = None
        self.ctx = ctx_factory(**kwargs)

    async def last_step(self):
        logger.info(
            '%s call last step',
            self.name)
        return None

    def get_steps(self) -> StepsType:
        """Возвращает отсортированный список шагов."""
        return self.__class__._steps

    @property
    def name(self):
        return f'{self.__class__.__name__}<{self.ctx.id}>'

    @classmethod
    async def run(cls, ctx_factory: PipeCTXFactory = PipeCTX, **kwargs) -> Self:
        self = cls(ctx_factory, **kwargs)
        coros: list[Awaitable] = []
        prew = self.last_step()
        coro = None
        for method_name, _ in reversed(self.get_steps()):
            coro = getattr(self, method_name)(_call_next=prew)
            prew = coro
            coros.append(coro)
        if not coro:
            raise RuntimeError('No steps assigned')
        try:
            await coro
        except StopPipeline:
            pass
        return self