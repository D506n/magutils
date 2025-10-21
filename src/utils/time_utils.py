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