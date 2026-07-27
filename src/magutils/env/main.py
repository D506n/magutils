from functools import wraps
from pathlib import Path
from types import GenericAlias
from typing import get_type_hints

from dotenv import load_dotenv


class EnvValidationError(Exception):
    def __init__(self, *errs):
        self.text = 'Environ can\'t be parsed. Errors:\n' + '\n'.join(
                [str(e) for e in errs])

    def __str__(self):
        return self.text


def _find_env():
    path = Path(__file__).parent / '.env'
    stop = Path.cwd()
    while path != stop:
        path = path.parent
        if (path / '.env').exists():
            return path / '.env'  # nocov


class ClassWrapper:
    __wrapped_cls__: type = None
    __hints__: dict = None

    @property
    def as_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def __str__(self):
        fields = []
        for name, val in self.as_dict.items():
            if name not in self.__hints__.keys():
                continue
            hint = self.__hints__[name]
            if isinstance(hint, (GenericAlias)):
                fields.append(f'    {name}:{hint} = {val}')
            else:
                fields.append(f'    {name}:{hint.__name__} = {val}')
        return f'{self.__wrapped_cls__.__name__}:\n{"\n".join(fields)}'


def environ(env_path=None, prefix=''):
    instances = {}

    def environ_wrap(cls):
        @wraps(cls)
        def wrapper():
            if cls not in instances.keys():
                if not env_path:
                    epath = _find_env()
                else:
                    epath = env_path
                load_dotenv(epath)
                fields = {}
                for cl in [cl for cl in cls.__mro__ if cl is not object]:
                    fields.update({k: v for k, v 
                                   in cl.__dict__.items() 
                                   if not k.startswith('_')})
                hints = get_type_hints(cls)
                result = ClassWrapper()
                result.__wrapped_cls__ = cls
                result.__hints__ = {}
                errors = []
                ctx = {}
                for name, val in fields.items():
                    if name in hints.keys():
                        try:
                            setattr(result, 
                                name, 
                                val(field_name=name, 
                                    hint=hints[name], 
                                    env_prefix=prefix).get_value(ctx))
                        except Exception as e:
                            errors.append(e)
                        result.__hints__[name] = hints[name]
                    else:
                        setattr(result, name, val)
                if errors:
                    raise EnvValidationError(*errors)
                instances[cls] = result
            return instances[cls]
        return wrapper
    return environ_wrap