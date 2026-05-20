from functools import lru_cache
from typing import overload

from .intent import Del, Get, Set
from .states import (
    DelState,
    IndexAccess,
    KeyAccess,
    KeySetAccess,
    ListAppend,
    State,
    WDel,
    WGet,
    WSet,
)

STATES: list[State] = [
    DelState(),
    KeyAccess(),
    IndexAccess(),
    KeySetAccess(),
    ListAppend(),
    WGet(),
    WSet(),
    WDel(),
]


@overload
def build_path(path: str) -> list[str | int]: ...


@lru_cache(1000)
def build_path(path: str) -> list[str | int]:
    parts = []
    for p in path.split('.'):
        if not p:
            continue
        elif p.lstrip('-').isnumeric():
            parts.append(int(p))
        else:
            parts.append(p)
    return parts


@overload
def build_states(path: list[str | int], intent: Get | Set | Del) -> list[list[State]]: ...  #noqa


@lru_cache(1000)
def build_states(path: list[str | int], intent: Get | Set | Del):
    states: list[list[State]] = []
    for i in range(len(path)):
        stage = [st for st in STATES if st.compile_check(path, i, intent)]
        stage.sort(key=lambda x: x.priority(path, i, intent))
        states.append(stage)
    return states