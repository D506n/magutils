from logging import getLogger
from typing import Self

from pydantic import BaseModel

from ..bg_tasks import BgTask
from .types import StateCallbackType, StateError, StateEvent, state_etypes

logger = getLogger(__name__)


class State():
    def __init__(self, 
            name: str, 
            start: bool = False, 
            final: bool = False):
        self._parents: set[Self] = {}
        self.name = name
        self.start = start
        self.final = final
        if start and final:
            raise StateError('State cannot be both start and final')
        self.enter_callback: StateCallbackType = None
        self.progress_callback: StateCallbackType = None
        self.exit_callback: StateCallbackType = None

    def on_enter(self, callback: StateCallbackType):
        self.enter_callback = callback
        return callback

    def on_exit(self, callback: StateCallbackType):
        if self.final:
            raise StateError('Final state can call only enter callbacks!')
        self.exit_callback = callback
        return callback

    def on_progress(self, callback: StateCallbackType):
        if self.final:
            raise StateError('Final state can call only enter callbacks!')
        self.progress_callback = callback
        return callback

    async def _emit_callback(self, 
            typ: state_etypes, 
            model: BaseModel | None):
        match typ:
            case 'EnterState':
                cb = self.enter_callback
            case 'ExitState':
                cb = self.exit_callback
            case 'ProgressState':
                cb = self.progress_callback
            case _:
                raise StateError(f'Unknown callback type: {typ}')
        if cb:
            try:
                await cb(StateEvent(typ, self, model))
            except Exception as e:
                logger.error(e)

    def _emit_callback_nowait(self, 
            typ: state_etypes, 
            model: BaseModel | None):
        BgTask.create(self._emit_callback(typ, model))

    def __hash__(self):
        return hash(self.name)