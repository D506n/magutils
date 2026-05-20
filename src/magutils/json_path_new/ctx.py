from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from .intent import Intent


T = TypeVar('T', bound=list[dict])


class StopWalk(Exception):
    pass


@dataclass
class Ctx[T]():
    data: dict | list = field()
    path: list[str | int] = field()
    intent: 'Intent' = field()
    pos: int = field(default=0)
    full_data: dict | list = field(default=None)
    parent: dict | list = field(default=None)
    val: Any = field(default=None)
    default: Any = field(default=None)
    result: T | list[dict] = field(default_factory=list)
    silent: bool = field(default=True)

    def __post_init__(self):
        self.full_data = self.data
        self.parent = self.data

    def __setattr__(self, name, value):
        if name == 'data' and hasattr(self, 'data'):
            self.parent = self.data
        super().__setattr__(name, value)

    @property
    def value(self):
        if not self.val:
            return self.default
        return self.val

    @property
    def last_pos(self):
        return self.pos == len(self.path) - 1

    @property
    def key(self):
        key = self.path[self.pos]
        if (isinstance(key, int) 
                and (isinstance(self.data, list) and key >= len(self.data))):
            key = len(self.data) - 1
        elif key == '!a':
            key = -1
        return key

    @property
    def nkey(self):
        return self.path[self.pos + 1]

    def is_key(self, key: str | int):
        if isinstance(key, int) or key in {'*', '!a'}:
            return False
        return True