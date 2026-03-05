import os
import zoneinfo
from datetime import datetime
from functools import lru_cache
from typing import overload


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


def seconds_stringify(seconds: int) -> str:
    """Преобразует количество секунд в часы/минуты.

    Args:
        seconds: Количество секунд для преобразования.

    Returns:
        Строка в формате x h./x m./x h. y m..
    """
    if seconds < 0:
        raise ValueError("Seconds must be non-negative")
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    result = ""
    if hours > 0:
        result += f"{hours} h. "
    if minutes > 0:
        result += f"{minutes} m."
    if not result:
        result = "0 m."
    return result.strip()


@overload
def from_timestamp(timestamp: int | float) -> datetime: ...  # noqa: F811 перегрузка для типизации


@lru_cache()
def from_timestamp(timestamp: int | float) -> datetime:
    return datetime.fromtimestamp(timestamp, get_tz())


@overload
def get_future_time(delta: int | float) -> datetime: ...  # noqa: F811 перегрузка для типизации


@lru_cache()
def get_future_time(delta: int | float) -> datetime:
    return get_current_time() + timedelta(seconds=delta)
