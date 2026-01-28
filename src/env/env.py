import inspect
import os
from functools import partial, wraps
from pathlib import Path
from typing import get_origin

import orjson as orj
from dotenv import load_dotenv
from pydantic import TypeAdapter, ValidationError
from pydantic.dataclasses import dataclass
from pydantic_core import PydanticUndefined

try:
    from .ext import k8s
except ImportError:
    k8s = None


class _PrefixStorage:
    _storage: dict[type, str] = {}


class EnvParsingError(Exception):
    def __init__(self, cls: type, field: str, expected: type, val):
        self.prefix = _PrefixStorage._storage[cls]
        self.field = field
        self.expected = expected
        self.val = val

    def __str__(self):
        return (
            f'Field {self.prefix}{self.field} parsing error!'
            'A valid json string representing'
            f' <{self.expected.__name__}> is expected, '
            f'received <{type(self.val).__name__}>: {self.val}')


class FieldRequiredError(Exception):
    def __init__(self, cls: type, name: str):
        self.field_name = name
        self.prefix = _PrefixStorage._storage[cls]

    def __str__(self):
        return f'Field {self.prefix}{self.field_name} is required!'


class EnvValidationError(Exception):
    def __init__(self, *errs: FieldRequiredError | EnvParsingError):
        self.text = 'Environ can\'t be parsed. Errors:\n' + '\n'.join(
                [str(e) for e in errs])

    def __str__(self):
        return self.text


def _find_env():
    path = Path(__file__).parent / '.env'
    if path.exists():
        return path
    stop = Path.cwd()
    while path != stop:
        path = path.parent
        if (path / '.env').exists():
            return path / '.env'


def _build_fields( # noqa
        cls: type, 
        prefix: str = ''):

    def json_valid(obj: type):
        orig = get_origin(obj) or obj
        return orig in {dict, list}

    def factory_wrapper(factory, name, prefix):
        if not k8s:
            return factory
        else:
            sign = inspect.signature(factory)
            if len(sign.parameters) == 0:
                return factory
            else:
                return partial(factory, k8s.get_k8s_client(), name, prefix)

    pcls = dataclass()(cls)
    _PrefixStorage._storage[pcls] = prefix
    result: dict = {}
    errors: list[ValidationError] = []

    for name, f in pcls.__pydantic_fields__.items():
        default = f.default if f.default != PydanticUndefined else None
        dfactory = f.default_factory if f.default_factory else lambda: None
        env_val = os.getenv(prefix + name) \
            or default \
            or factory_wrapper(dfactory, name, prefix)()

        if env_val is None:
            try:
                TypeAdapter(f.annotation).validate_python(env_val)
            except Exception:
                errors.append(FieldRequiredError(pcls, name))
            else:
                result[name] = env_val
            continue

        adapt = TypeAdapter(f.annotation)

        if json_valid(f.annotation):
            try:
                data = adapt.validate_json(env_val)
            except ValidationError:
                errors.append(
                    EnvParsingError(pcls, name, f.annotation, env_val))
        else:
            try:
                data = adapt.validate_strings(env_val)
            except ValidationError:
                errors.append(
                    EnvParsingError(pcls, name, f.annotation, env_val))
        result[name] = data

    if errors:
        raise EnvValidationError(*errors)
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

    def save(self, path: Path = None, full_env: bool = False):
        if not path:
            path = _find_env()

        with open(path, 'r', encoding='utf-8') as f:
            current_data = {k: v for k, v in 
                            [row.split('=', 1) for row in f.read().split('\n')]}
        new_data = {}
        prefix = _PrefixStorage._storage[self.__class__]

        if full_env:
            variables = os.environ.items()
        else:
            variables = self.__dict__.items()

        for key, value in variables:
            if not callable(value) and not key.startswith('_'):
                if isinstance(value, (dict, list)):
                    value = orj.dumps(value).decode()
                else:
                    value = str(value)
                if value == 'True' or value == 'False':
                    value = value.lower()
                if key in self.__dict__.keys():
                    key = prefix + key
                new_data[f'{key}'] = value

        current_data.update(new_data)
        prepared_data = [f'{k}={v}' for k, v in current_data.items()]

        with open(path, 'w') as f:
            f.write('\n'.join(prepared_data))


def environ(
        path: Path = None, 
        prefix: str = ''):

    if not path:
        path = _find_env()

    def environ_wrap(cls):
        instances: dict = {}

        @wraps(cls)
        def wrapper():
            if cls not in instances:
                load_dotenv(path)
                fields = _build_fields(cls, prefix)
                pcls = dataclass()(cls)
                instances[pcls] = pcls(**fields)
                _PrefixStorage._storage[pcls] = prefix
            return instances[pcls]
        return wrapper
    return environ_wrap
