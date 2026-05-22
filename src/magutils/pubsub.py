from functools import partial
from logging import getLogger
from typing import Awaitable, Callable, TypeVar

from .bg_tasks import BgTask
from .id import gen_id

T = TypeVar('T', bound=dict)
logger = getLogger(__name__)


class PubSub[T]():
    """
    Класс для реализации системы событий (паттерн «Наблюдатель»).
    
    Позволяет подписываться на события асинхронными колбэками и эмитировать
    события с передачей полезной нагрузки.
    
    Generic параметр:
        T: тип полезной нагрузки события.
    
    Пример использования:
        >>> event = Event[dict]()
        >>> async def handler(payload):
        ...     print(f"Received: {payload}")
        >>> unsubscribe = event.subscribe(handler)
        >>> event.emit({"data": "test"})
        >>> unsubscribe()
    """
    
    def __init__(self):
        """Инициализирует событие с пустым списком подписчиков."""
        self.subscribers: dict[str, Callable[[T], Awaitable[None]]] = {}

    def subscribe(self, callback: Callable[[T], Awaitable[None]]):
        """
        Подписывает колбэк на событие.
        
        Args:
            callback: Асинхронная функция, принимающая полезную нагрузку
                типа T и возвращающая None.
        
        Returns:
            Функция для отписки (без аргументов). Вызов этой функции
            удаляет колбэк из списка подписчиков.
        
        Пример:
            >>> unsubscribe = event.subscribe(async_handler)
            >>> unsubscribe()  # отписаться
        """
        sub_id = gen_id()
        self.subscribers[sub_id] = callback
        return partial(self.unsubscribe, sub_id)

    def unsubscribe(self, key: str):
        """
        Отписывает колбэк по ключу.
        
        Внутренний метод, обычно вызывается через функцию, возвращённую
        subscribe(). Если ключ не найден, логируется предупреждение.
        
        Args:
            key: Идентификатор подписки.
        """
        if key not in self.subscribers.keys():
            logger.warning('Key %s not found', key)
        else:
            self.subscribers.pop(key)

    def emit(self, payload: T, raise_errors: bool = False):
        """
        Эмитирует событие, вызывая все подписанные колбэки.
        
        Колбэки выполняются асинхронно в фоновых задачах через BgTask.
        
        Args:
            payload: Полезная нагрузка события (тип T).
            raise_errors: Если True, исключения в колбэках приводят к
                завершению программы через sys.exit(1). Если False,
                ошибки логируются, но программа продолжает работу.
        
        Пример:
            >>> event.emit({"user_id": 123}, raise_errors=False)
        """
        BgTask.create(
            *[coro(payload) for coro in self.subscribers.values()],
            raise_errors=raise_errors
        )