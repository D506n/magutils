import os
from dataclasses import MISSING, Field, dataclass
from functools import wraps
from pathlib import Path
from typing import get_origin

import orjson as orj
from dotenv import load_dotenv


class __DataclassMock:
    __dataclass_fields__: dict[str, Field] = {}
    _prefix: str


def _build_fields(
        cls: __DataclassMock, 
        default_priority: bool = False, 
        prefix: str = ''):
    result = {}
    for field in cls.__dataclass_fields__.values():
        if field.default is not MISSING and (
                not os.getenv(prefix + field.name) or default_priority):
            result[field.name] = field.default
        elif field.default_factory is not MISSING and (
                not os.getenv(prefix + field.name) or default_priority):
            result[field.name] = field.default_factory()
        else:
            orig = get_origin(field.type)
            if orig in {dict, list} or issubclass(field.type, (dict, list)):
                result[field.name] = orj.loads(os.getenv(prefix + field.name))
            else:
                result[field.name] = field.type(os.getenv(prefix + field.name))
    return result


class EnvironTools:
    """Опциональный класс для расширения функционала объектам окружения через 
    механизм наследования.
    
    :example:
    ```
        ...
        class Env(EnvironTools):
            TEST_DATA: int = 123
            TEST_PATH: Path = Path(__file__).parent/'test.json'
    
        Env().save()
    ```
    """

    def refresh(self, path: Path = None, default_priority: bool = False):
        if not path:
            path = Path.cwd() / '.env'
        load_dotenv(path, override=True)
        self.__dict__.update(_build_fields(self.__class__, default_priority))

    def save(self, path: Path = None):
        if not path:
            path = Path.cwd() / '.env'
        with open(path, 'r', encoding='utf-8') as f:
            current_data = {k: v for k, v in 
                            [row.split('=', 1) for row in f.read().split('\n')]}
        new_data = {}
        for key, value in self.__dict__.items():
            if not callable(value) and not key.startswith('_'):
                if isinstance(value, (dict, list)):
                    value = orj.dumps(value).decode()
                else:
                    value = str(value)
                if value == 'True' or value == 'False':
                    value = value.lower()
                new_data[f'{self._prefix}{key}'] = value
        current_data.update(new_data)
        prepared_data = [f'{k}={v}' for k, v in current_data.items()]
        with open(path, 'w') as f:
            f.write('\n'.join(prepared_data))


def environ(
        path: Path = None, 
        default_priority: bool = False, 
        prefix: str = ''):
    if not path:
        path = Path.cwd() / '.env'

    def environ_wrap(cls):
        instances: dict[type, __DataclassMock] = {}
        cls = dataclass()(cls)

        @wraps(cls)
        def wrapper():
            if cls not in instances:
                load_dotenv(path)
                fields = _build_fields(cls, default_priority, prefix)
                instances[cls] = cls(**fields)
                instances[cls]._prefix = prefix
            return instances[cls]
        return wrapper
    return environ_wrap