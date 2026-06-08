import warnings
from functools import wraps
from logging import getLogger
from typing import Any, Awaitable, Protocol, Self, TypeVar

from pydantic import BaseModel

from magutils.id import gen_id

T = TypeVar('T', bound=BaseModel)

StepsType = list[tuple[str, int]]

logger = getLogger(__name__)

#  Отключаю лишний шум от asyncio, т.к. это сообщение для шагов 
#  пайплайна не несёт смысловой нагрузки, любой из них может
#  становиться точкой выхода из пайплайна
warnings.filterwarnings('ignore', 
                        "coroutine 'Pipeline.last_step' was never awaited", 
                        RuntimeWarning)


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


class PipelineStep(Protocol):
    def __call__(self, call_next: Awaitable) -> Awaitable: ...


def step(order: int) -> PipelineStep:
    """Декоратор для пометки шагов в пайплайне."""
    def decorator(func: PipelineStep) -> PipelineStep:
        warnings.filterwarnings(
            'ignore', 
            f"coroutine '.+{func.__name__}' was never awaited", 
            RuntimeWarning)  # В пайплайне это предупреждение не нужно

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self: Pipeline = args[0]
            self.step_num = order
            self.step_name = func.__name__

            logger.info(
                '%s runs %s step: %s', self.name, self.step_num, self.step_name)

            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                logger.error('%s failed on %s step: %s', self.name, 
                             func.__name__, self.step_num)
                raise e
            if result is not None and self.result is None:
                self.result = result
                return
        wrapper._step_order = order
        return wrapper
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
            coro = getattr(self, method_name)(prew)
            prew = coro
            coros.append(coro)
        if not coro:
            raise RuntimeError('No steps assigned')
        await coro
        return self