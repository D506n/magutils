import os
import time
import zoneinfo
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from inspect import iscoroutinefunction
from typing import Callable, overload


@overload
def get_tz() -> zoneinfo.ZoneInfo: ...  # noqa: F811 перегрузка для типизации


@lru_cache(maxsize=1)
def get_tz():
    return zoneinfo.ZoneInfo(os.getenv("TIMEZONE", "UTC"))


def get_current_time():
    return datetime.now(get_tz())


@overload
def parse_time(time_str: str, format_str: str = None) -> datetime: ...  # noqa: F811 перегрузка для типизации


@lru_cache()
def parse_time(time_str: str, format_str: str = None):
    return datetime.strptime(
        time_str,
        format_str or os.getenv("TIME_FORMAT", "%Y-%m-%dT%H:%M:%S.%f%z"),
    )


@overload
def format_time(time_obj: datetime, format_str: str = None) -> str: ...  # noqa: F811 перегрузка для типизации


@lru_cache()
def format_time(time_obj: datetime, format_str: str = None):
    format_str = format_str or os.getenv(
        "TIME_FORMAT", "%Y-%m-%dT%H:%M:%S.%f%z"
    )
    return time_obj.strftime(format_str)


def get_delta(dt: datetime, dt2: datetime = None):
    if dt2 is None:
        dt2 = get_current_time()
    return dt2 - dt


@overload
def seconds_stringify(seconds: int) -> str: ...  # noqa: F811 перегрузка для типизации

@lru_cache()
def seconds_stringify(seconds: int) -> str:
    """Преобразует количество секунд в человекочитаемый вид.

    Args:
        seconds: Количество секунд для преобразования.
    """
    if seconds < 0:
        raise ValueError("Seconds must be non-negative")
    elif seconds == 0:
        return '0 s'
    units = [
        ('w ', 604_800),
        ('d', 86_400),
        ('h', 3600),
        ('m', 60),
        ('s', 1)
    ]
    parts = []
    remaining = seconds
    for unit, divisor in units:
        if remaining >= divisor:
            value = remaining // divisor
            remaining %= divisor
            parts.append(f"{value} {unit}")
    return " ".join(parts)


@overload
def ns_stringify(ns: int) -> str: ...  # noqa: F811 перегрузка для типизации

@lru_cache()
def ns_stringify(ns: int) -> str:
    """Преобразует количество наносекунд в человекочитаемый формат.

    Args:
        ns: Количество наносекунд (неотрицательное целое).

    Returns:
        Строка в формате "X s Y ms Z µs W ns", где нулевые единицы пропускаются.

    Raises:
        ValueError: Если ns отрицательное.
    """
    if ns < 0:
        raise ValueError("ns must be non-negative")
    if ns == 0:
        return "0 ns"
    units = [
        ("m", 60_000_000_000),
        ("s", 1_000_000_000),
        ("ms", 1_000_000),
        ("µs", 1_000),
        ("ns", 1),
    ]
    parts = []
    remaining = ns
    for unit, divisor in units:
        if remaining >= divisor:
            value = remaining // divisor
            remaining %= divisor
            parts.append(f"{value} {unit}")
    return " ".join(parts)


@overload
def from_timestamp(timestamp: int | float) -> datetime: ...  # noqa: F811 перегрузка для типизации


@lru_cache()
def from_timestamp(timestamp: int | float) -> datetime:
    return datetime.fromtimestamp(timestamp, get_tz())


@overload
def get_future_time(delta: int | float) -> datetime: ...  # noqa: F811 перегрузка для типизации


def get_future_time(delta: int | float) -> datetime:
    return get_current_time() + timedelta(seconds=delta)


def perf_counter(handler: Callable[[str], None] = print):  # nocov: нужен только
    # для разработки и тестировать проще руками
    def inner(func):
        def printer(st: int):
            perf = ns_stringify(time.perf_counter_ns() - st)
            res = f'{func.__name__}: {perf}'
            handler(res)
        if iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                st = time.perf_counter_ns()
                result = await func(*args, **kwargs)
                printer(st)
                return result
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                st = time.perf_counter_ns()
                result = func(*args, **kwargs)
                printer(st)
                return result
        return wrapper
    return inner
