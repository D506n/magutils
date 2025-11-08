from datetime import datetime
import pytz
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def get_tz():
    return pytz.timezone(os.getenv('TIMEZONE', 'Europe/Moscow'))

def get_current_time():
    return datetime.now(get_tz())

@lru_cache()
def parse_time(time_str: str):
    return datetime.strptime(time_str, os.getenv('TIME_FORMAT', '%Y-%m-%dT%H:%M:%S.%f%z'))

@lru_cache()
def format_time(time_obj: datetime):
    return time_obj.strftime(os.getenv('TIME_FORMAT', '%Y-%m-%dT%H:%M:%S.%f%z'))

def get_delta(dt:datetime, dt2:datetime=None):
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
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    result = ''
    if hours>0:
        result += f'{hours} h. '
    if minutes>0:
        result += f'{minutes} m.'
    return result.strip()