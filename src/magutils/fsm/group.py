import importlib
from asyncio import Event, Lock
from functools import lru_cache
from logging import getLogger
from typing import TypeVar

from pydantic import BaseModel

from ..bg_tasks import BgTask
from ..id import gen_id
from .state import State
from .types import (
    GroupCallbackType,
    GroupEvent,
    PackedStateGroup,
    StateError,
    group_etypes,
)

logger = getLogger(__name__)

T = TypeVar('T', bound=BaseModel)
MODELS_CACHE: dict[str, BaseModel] = {}


class StateGroup[T]():
    start_callback: GroupCallbackType = None
    finish_callback: GroupCallbackType = None

    def __init__(self, 
                id: str = None,
                current_state: str = None, 
                skip_init: bool = False, 
                model: T = None):
        self.id = id or gen_id()
        self.start_state = self._validate_fsm()
        self.all_states = {st.name: st 
                                    for st in self.__class__.__dict__.values() 
                                    if isinstance(st, State)}
        if current_state and current_state not in self.all_states:
            raise StateError(f'Unknown state: {current_state}')
        self.current_state = self.all_states.get(current_state)\
            or self.start_state
        self.model = model
        self.lock = Lock()
        self.can_pack = Event()
        if not skip_init:
            self._emit_callback_nowait('Started')
            self.current_state._emit_callback_nowait('EnterState', self.model)

    async def _emit_callback(self, typ: group_etypes):
        match typ:
            case 'Started':
                cb = self.__class__.start_callback
            case 'Finished':
                cb = self.__class__.finish_callback
        if cb:
            await cb(GroupEvent(typ, self, self.model))
        self.can_pack.set()

    def _emit_callback_nowait(self, typ: group_etypes):
        self.can_pack.clear()
        BgTask.create(self._emit_callback(typ))

    @classmethod
    def on_start(cls, callback: GroupCallbackType):
        cls.start_callback = callback
        return callback

    @classmethod
    def on_finish(cls, callback: GroupCallbackType):
        cls.finish_callback = callback
        return callback

    @classmethod
    @lru_cache(1)
    def _validate_fsm(cls):
        list_states = [st for st in cls.__dict__.values() 
                                if isinstance(st, State)]
        start_states = [st for st in list_states if st.start]
        if len(start_states) > 1:
            raise StateError('Only one state can be start!'
                             f' Current start states: {start_states}')
        elif len(start_states) < 1:
            raise StateError('No start state provided!')
        state_names = {st.name for st in list_states}
        if len(state_names) != len(list_states):
            raise StateError('State names must be unique')
        return start_states[0]

    def emit_nowait(self, state: str):
        self.get_new_state(state)  # Выполняем проверки на месте
        self.can_pack.clear()
        BgTask.create(self.emit(state))

    def get_new_state(self, state: str):
        if state not in self.all_states.keys():
            raise StateError(f'Invalid state: {state}')
        new_state = self.all_states[state]
        if self.current_state.final:
            raise StateError('Current state is final')
        return new_state

    async def emit(self, state: str):
        new_state = self.get_new_state(state)
        async with self.lock:
            if new_state is self.current_state:
                await self.current_state._emit_callback(
                    'ProgressState', self.model)
            else:
                await self.current_state._emit_callback(
                    'ExitState', self.model)
                self.current_state = self.all_states[state]
                await self.current_state._emit_callback(
                    'EnterState', self.model)
                if self.current_state.final:
                    await self._emit_callback('Finished')
        self.can_pack.set()

    async def dump(self, **kwargs) -> PackedStateGroup:
        await self.can_pack.wait()
        async with self.lock:
            if isinstance(self.model, BaseModel):
                path = f"{self.model.__class__.__module__}."\
                    f"{self.model.__class__.__qualname__}"
                model = self.model.model_dump(**kwargs)
            else:
                path = None
                model = None
            return {
                'name': self.__class__.__name__,
                'id': self.id,
                'current_state': self.current_state.name,
                'model': {
                    "path": path,
                    "data": model
                }
            }

    @classmethod
    def load(cls, pack: PackedStateGroup, strict: bool = False):
        pack = pack.copy()
        if pack['name'] != cls.__name__:
            raise StateError(f'Invalid state group name: {pack["name"]}')
        else:
            pack.pop('name')
        if path := pack.get('model', {}).get('path'):
            data = pack.get('model').get('data')
            try:
                parts = path.split('.')
                module = '.'.join(parts[:-1])
                model_name = parts[-1]
                if path in MODELS_CACHE.keys():
                    model = MODELS_CACHE[path]
                else:
                    mod = importlib.import_module(module)
                    model: BaseModel = getattr(mod, model_name)
                    MODELS_CACHE[path] = model
                pack['model'] = model.model_validate(data)
            except (ImportError, AttributeError, KeyError) as e:
                if strict:
                    raise StateError(f"Failed to load model {path}: {e}") from e
                else:
                    logger.warning(
                        "Failed to load model %r for %s: %s",
                        path, cls.__name__, e)
        if not isinstance(pack['model'], BaseModel):
            pack['model'] = None
        pack['skip_init'] = True
        return cls(**pack)