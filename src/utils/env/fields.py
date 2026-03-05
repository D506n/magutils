import os
from functools import partial
from types import GenericAlias
from typing import Any, Callable

from pydantic import TypeAdapter


class UndefinedField:
    pass


class FieldRequiredError(Exception):
    def __init__(self, cls: type, name: str):
        self.field_name = name
        # self.prefix = _PrefixStorage._storage[cls]

    def __str__(self):
        return f'Field {self.field_name} is required!'


class FieldConstructor():
    def __init__(self, 
                 default_value: Any | None, 
                 default_factory: Callable[[], Any] | None, 
                 aliases: list[str] | None,
                 field_name: str,
                 hint: Any,
                 env_prefix: str | None):
        self.field_name = field_name
        self.default_value = default_value
        self.default_factory = default_factory
        self.aliases = aliases
        self.hint = hint
        self.adapter = TypeAdapter(hint)
        self.env_prefix = env_prefix

    def _get_value(self, ctx: dict):
        val = os.getenv(self.env_prefix + self.field_name)

        if not val and self.aliases:
            for alias in self.aliases:
                val = os.getenv(self.env_prefix + alias)
                if val:
                    break

        if val and isinstance(self.hint, GenericAlias)\
              or self.hint in {dict, list}:
            return self.adapter.validate_json(val)
        elif val:
            return self.adapter.validate_python(val)

        if not isinstance(self.default_value, UndefinedField):
            return self.default_value
        elif self.default_factory:
            try:
                return self.default_factory(ctx)
            except TypeError:
                return self.default_factory()

        raise ValueError(f"No value found for field {self.field_name}")

    def get_value(self, ctx: dict):
        result = self._get_value(ctx)
        ctx[self.field_name] = result
        return result


def field(
        default_value=UndefinedField(), 
        default_factory: Callable[[], Any] | Callable[[dict], Any] = None, 
        aliases: list[str] = None):
    return partial(FieldConstructor, default_value, default_factory, aliases)