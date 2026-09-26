import os
from functools import partial
from types import GenericAlias
from typing import Any, Callable
from typing import Optional as OP

from pydantic import TypeAdapter


class UndefinedField:
    def __bool__(self):
        return False


class FieldConstructor():
    def __init__(self, 
                 default_value: Any | None, 
                 default_factory: Callable[..., Any] | None, 
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
        self.env_prefix = env_prefix or ''

    def _get_value(self, ctx: dict):
        undef = UndefinedField()
        val = os.getenv(self.env_prefix + self.field_name) or undef

        if not val and self.aliases:
            for alias in self.aliases:
                val = os.getenv(self.env_prefix + alias) or undef
                if val:
                    break

        if isinstance(val, str) and (isinstance(self.hint, GenericAlias) 
              or self.hint in {dict, list}):
            return self.adapter.validate_json(val)
        elif isinstance(val, str):
            return self.adapter.validate_python(val)

        if self.default_factory:
            try:
                return self.default_factory(ctx)
            except TypeError:
                return self.default_factory()
        elif not isinstance(self.default_value, UndefinedField):
            return self.default_value 

        raise ValueError(f"No value found for field {self.field_name}")

    def get_value(self, ctx: dict):
        result = self._get_value(ctx)
        ctx[self.field_name] = result
        return result


def field(
        default_value=UndefinedField(), 
        default_factory: OP[Callable[[], Any] | Callable[[dict], Any]] = None, 
        aliases: OP[list[str]] = None):
    return partial(FieldConstructor, default_value, default_factory, aliases)