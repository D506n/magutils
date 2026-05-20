import asyncio as aio
from datetime import datetime
from functools import lru_cache
from logging import getLogger
from typing import Callable, Coroutine, Generic, TypeVar

import cron_parser_py as cron

from .bg_tasks import BgTask
from .id import gen_id
from .time_utils import get_current_time, get_delta, get_tz, parse_time

T = TypeVar('T', bound=dict)
ET = TypeVar('ET', bound=datetime)
logger = getLogger(__name__)


class ScheduledTask(Generic[ET]):
    def __init__(self, expr: str, payload: T, id: str = None):
        self.raw_expr = expr
        self.executions = 0
        self.expr = self.parse_expr(self.raw_expr)
        self.payload = payload
        self.scheduled = False
        self.id = id or gen_id()
        self.subscribers: dict[str, Callable[[T], Coroutine]] = {}
        self._next_run = None

    def parse_expr(self, expr: str) -> ET:
        '''Парсит выражение задачи в внутреннее представление.
        
        Args:
            expr (str): Строковое выражение задачи.
            
        Returns:
            ET: Распарсенное выражение (зависит от подкласса).
            
        Raises:
            NotImplementedError: Метод должен быть реализован в подклассе.
        '''
        raise NotImplementedError()

    @property
    def next_run(self) -> datetime:
        '''Возвращает следующее время запуска задачи.
        
        Returns:
            datetime: Дата и время следующего запуска.
        '''
        return self.calc_next_run()

    @lru_cache(1)
    def calc_next_run(self):
        raise NotImplementedError()

    @classmethod
    def match(cls, expr: str):
        '''Проверяет, подходит ли выражение для данного типа задачи.
        
        Args:
            expr (str): Выражение для проверки.
            
        Returns:
            bool: True если выражение подходит, иначе False.
        '''
        raise NotImplementedError()

    def emit(self):
        '''Запускает выполнение задачи, вызывая всех подписчиков.
        
        Создаёт фоновые задачи для каждого коллбэка.
        '''
        tasks = [t(self.payload) for t in self.subscribers.values()]
        BgTask.create(*tasks)
        self.executions += 1
        self.calc_next_run.cache_clear()

    def subscribe(self, callback: Callable[[T], Coroutine]) -> str:
        '''Добавляет подписчика на выполнение задачи.
        
        Args:
            callback (Callable[[T], Coroutine]): Асинхронная функция, которая будет вызвана с payload задачи.
            
        Returns:
            str: Ключ подписки, который можно использовать для отписки.
        '''  # noqa
        key = gen_id()
        self.subscribers[key] = callback
        return key

    def unsubscribe(self, key: str):
        '''Удаляет подписчика по ключу.
        
        Args:
            key (str): Ключ подписки, полученный от subscribe.
        '''
        self.subscribers.pop(key)


class CronTask(ScheduledTask[cron.CronExpression]):
    validator = cron.CronValidator()
    parser = cron.CronParser()

    def parse_expr(self, expr):
        '''Парсит cron-выражение в объект CronExpression.
        
        Args:
            expr (str): Cron-выражение (например, '* * * * *').
            
        Returns:
            cron.CronExpression: Распарсенное cron-выражение.
            
        Raises:
            cron.CronValidationError: Если выражение некорректно.
        '''
        crexp = self.parser.parse(expr)
        self.validator.validate(crexp, strict=True)
        return crexp

    @lru_cache(1)
    def calc_next_run(self):
        '''Возвращает следующее время запуска cron-задачи.
        
        Returns:
            datetime: Дата и время следующего запуска согласно cron-выражению.
        '''
        return self.expr.next_run().replace(tzinfo=get_tz())

    @classmethod
    def match(cls, expr: str):
        '''Проверяет, является ли выражение валидным cron-выражением.
        
        Args:
            expr (str): Выражение для проверки.
            
        Returns:
            bool: True если выражение валидно, иначе False.
        '''
        try:
            expr = cls.parser.parse(expr)
        except cron.CronValidationError:
            return False
        return True


class OneTimeTask(ScheduledTask[datetime]):
    date_fmt = "%Y-%m-%d %H:%M"

    def parse_expr(self, expr):
        '''Парсит строку даты и времени в объект datetime.
        
        Args:
            expr (str): Строка даты в формате 'YYYY-MM-DD HH:MM'.
            
        Returns:
            datetime: Распарсенная дата и время.
            
        Raises:
            ValueError: Если строка не соответствует формату.
        '''
        return parse_time(expr, self.date_fmt).replace(tzinfo=get_tz())

    @property
    def next_run(self):
        '''Возвращает время запуска одноразовой задачи.
        
        Returns:
            datetime: Дата и время, указанные в выражении.
        '''
        return self.expr

    @classmethod
    def match(cls, expr: str):
        '''Проверяет, является ли выражение валидной датой в формате 'YYYY-MM-DD HH:MM'.
        
        Args:
            expr (str): Выражение для проверки.
            
        Returns:
            bool: True если выражение валидно, иначе False.
        ''' # noqa
        try:
            parse_time(expr, cls.date_fmt)
        except Exception:
            return False
        return True


classes: list[type[ScheduledTask]] = [OneTimeTask, CronTask]


class Scheduler():
    def __init__(self):
        self.tasks: dict[str, ScheduledTask] = {}
        self.sched_que: aio.Queue[str] = aio.Queue()
        self.alive = True
        self.main_task: aio.Task = None

    def add_task(self, expr: str, payload, id: str = None):
        '''Создаёт задачу из выражения.
        Форматы:
            'YYYY-MM-DD HH:MM' - одноразовая задача
            '* * * * *' - задача с кроном
        Args:
            expr (str): Выражение задачи.
            payload (Any): Данные задачи, будут переданы при вызове коллбэк функций.
            id (str): Идентификатор задачи (опционально).
        Returns:
            ScheduledTask: Задача.
        Raises:
            ValueError: Если выражение не подходит ни под один формат задачи.
        ''' # noqa
        for cls in classes:
            if cls.match(expr):
                inst = cls(expr, payload, id)
                self.tasks[inst.id] = inst
                self.sched_que.put_nowait(inst)
                if not self.main_task:
                    self.main_task = aio.create_task(self.main())
                return inst
        raise ValueError('Invalid expression')

    async def exec_wrapper(self, task: ScheduledTask):
        if task.next_run < get_current_time():
            if task.executions == 0:
                logger.warning('Task cannot be executed in past time: %s, %s',
                    task.id, task.next_run)
            return
        if task.executions == 0:
            logger.info('New task: %s, next run: %s', task.id, task.next_run)
        delta = get_delta(get_current_time(), task.next_run)
        wait = delta.total_seconds()
        task.scheduled = True
        logger.info('Task scheduled: %s. Wait: %s', task.id, wait)
        await aio.sleep(wait)
        task.emit()
        logger.info('Task completed: %s', task.id)
        task.scheduled = False
        if task.next_run < get_current_time():
            logger.info('Task %s finished', task.id)
            return
        else:
            logger.info('Task %s rescheduled: %s', task.id, task.next_run)
            BgTask.create(self.exec_wrapper(task))

    async def main(self):
        while self.alive:
            try:
                task = await self.sched_que.get()
            except aio.QueueShutDown:
                return
            BgTask.create(self.exec_wrapper(task))

    def shutdown(self):
        self.alive = False
        self.sched_que.shutdown()