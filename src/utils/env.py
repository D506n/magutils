import os
from pathlib import Path
from dotenv import load_dotenv
from functools import wraps
from dataclasses import dataclass, MISSING, Field
from typing import get_origin
import orjson

class __DataclassMock:
    __dataclass_fields__:dict[str, Field] = {}

def _build_fields(cls: __DataclassMock, default_priority:bool=False):
    result = {}
    for field in cls.__dataclass_fields__.values():
        if field.default is not MISSING and (not os.getenv(field.name) or default_priority):
            result[field.name] = field.default
        elif field.default_factory is not MISSING and (not os.getenv(field.name) or default_priority):
            result[field.name] = field.default_factory()
        else:
            orig = get_origin(field.type)
            if orig in {dict, list} or issubclass(field.type, (dict, list)):
                result[field.name] = orjson.loads(os.getenv(field.name))
            else:
                result[field.name] = field.type(os.getenv(field.name))
    return result

class EnvironTools:
    """Опциональный класс для расширения функционала объектам окружения через механизм наследования.
    
    :example:
    ```
        ...
        class Env(EnvironTools):
            TEST_DATA: int = 123
            TEST_PATH: Path = Path(__file__).parent/'test.json'
    
        Env().save()
    ```
    """

    def refresh(self, path:Path=None, default_priority:bool=False):
        if not path:
            path = Path.cwd()/'.env'
        load_dotenv(path, override=True)
        self.__dict__.update(_build_fields(self.__class__, default_priority))

    def save(self, path:Path=None):
        if not path:
            path = Path.cwd()/'.env'
        prepared_data = []
        for key, value in self.__dict__.items():
            if not callable(value) and not key.startswith('_'):
                if isinstance(value, (dict, list)):
                    value = orjson.dumps(value).decode()
                else:
                    value = str(value)
                prepared_data.append(f'{key}={value}')
        with open(path, 'w') as f:
            f.write('\n'.join(prepared_data))

def environ(path:Path=None, default_priority:bool=False):
    if not path:
        path = Path.cwd()/'.env'
    def environ_wrap(cls):
        instances = {}
        cls = dataclass()(cls)
        @wraps(cls)
        def wrapper():
            if cls not in instances:
                load_dotenv(path)
                fields = _build_fields(cls, default_priority)
                instances[cls] = cls(**fields)
            return instances[cls]
        return wrapper
    return environ_wrap