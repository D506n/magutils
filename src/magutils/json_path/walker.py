from typing import Self, TypeVar

from .builder import build_path, build_states
from .ctx import Ctx, StopWalk
from .intent import Intent
from .states import WildcardState

T = TypeVar('T', bound=list)


class Walker[T]():
    __cache: dict[tuple, Self] = {}

    def __init__(self, path: str, intent: type[Intent]):
        self.path = build_path(path)
        self.states = build_states(tuple(self.path), intent)
        self.intent = intent

    def walk(self, 
             data: dict | list, 
             value=None, 
             default=None, 
             silent=True):
        ctx = Ctx[T](
            data, 
            self.path, 
            self.intent, 
            val=value, 
            default=default, 
            silent=silent)
        self._walk(ctx)
        return ctx

    def _walk(self, ctx: Ctx):
        try:
            states = self.states[ctx.pos]
            alls = 0
            ws = 0
            for state in states:
                alls += 1
                if not state.wildcard and state.run_check(ctx):
                    state(ctx)
                    ws += 1
                    break
                elif state.wildcard and state.run_check(ctx):
                    self._wildwalk(state, ctx)
                    ws += 1
                    break
            if not alls or not ws:  # nocov может стрельнуть, но тестами 
                # не покрывается, сигнал о том, что не предусмотрел состояния
                raise KeyError(
                    'Not found states for path: %s', 
                    '/'.join([str(p) for p in ctx.path[:ctx.pos + 1]]))
            if not ctx.last_pos:
                ctx.pos += 1
                self._walk(ctx)
        except StopWalk:
            if ctx.silent:
                return
            else:
                raise StopWalk()

    def _wildwalk(self, state: WildcardState, ctx: Ctx):
        if ctx.last_pos:
            state(ctx)
        else:
            curr_pos = ctx.pos
            data = ctx.data
            if data:
                for item in data:
                    ctx.pos = curr_pos + 1
                    ctx.data = item
                    self._walk(ctx)
            else:
                state(ctx)
                raise StopWalk()

    @classmethod
    def make(cls, path: str, intent: type[Intent], item_type: T = type[dict]):
        key = (path, intent, item_type,)
        if key in cls.__cache:
            return cls.__cache[key]
        else:
            cls.__cache[key] = cls[list[item_type]](path, intent)
            return cls.__cache[key]

    @property
    def template(self):
        if self.path[0] == '*':
            idx = 1
        else:
            idx = 0
        if (isinstance(self.path[idx], str) 
                and self.path[idx] not in {'*', '!a'}):
            return dict
        else:
            return list
