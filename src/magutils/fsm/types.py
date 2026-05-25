from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Literal,
    TypedDict,
    TypeVar,
)

from pydantic import BaseModel

if TYPE_CHECKING:  # nocov
    from .group import StateGroup
    from .state import State


T = TypeVar('T', bound=BaseModel)
state_etypes = Literal['EnterState', 'ExitState', 'ProgressState']
group_etypes = Literal['Started', 'Finished']


class StateEvent[T]():
    def __init__(self, 
            event_type: state_etypes, 
            state: 'State', 
            model: T | None = None):
        self.type = event_type
        self.state = state
        self.model = model


class GroupEvent[T]():
    def __init__(self, 
            event_type: group_etypes, 
            group: 'StateGroup', 
            model: T | None = None):
        self.type = event_type
        self.group = group
        self.model = model


class ModelPacked(TypedDict):
    path: str | None
    data: str | None


class PackedTransition(TypedDict):
    st_from: str
    st_to: str


class PackedStateGroup(TypedDict):
    name: str
    id: str
    current_state: str
    model: ModelPacked


StateCallbackType = Callable[[StateEvent], Awaitable[None]]
GroupCallbackType = Callable[[GroupEvent], Awaitable[None]]


class StateError(Exception):
    pass