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
    __slots__ = ('type', 'state', 'model')

    def __init__(self, 
            event_type: state_etypes, 
            state: 'State', 
            model: T | None = None):
        self.type = event_type
        self.state = state
        self.model = model


class GroupEvent[T]():
    __slots__ = ('type', 'group', 'model')

    def __init__(self, 
            event_type: group_etypes, 
            group: 'StateGroup', 
            model: T | None = None):
        self.type = event_type
        self.group = group
        self.model = model


class TransitionEvent[T]():
    __slots__ = ('group', 'from_state', 'to_state', 'model')

    def __init__(self, 
                        group: 'StateGroup', 
                        from_state: 'State', 
                        to_state: 'State',
                        model: T | None = None):
        self.group = group
        self.from_state = from_state
        self.to_state = to_state
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
TransitionCallbackType = Callable[[TransitionEvent], Awaitable[None]]


class StateError(Exception):
    pass