from functools import lru_cache
from typing import Any, Self, TypeVar, overload

from .builder import build_path, build_states
from .ctx import Ctx, StopWalk
from .intent import Del, Get, Intent, Set
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
            if not alls or not ws:
                raise KeyError()
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


def get_by_path(
        path: str, 
        data: dict | list, 
        item_type=type[dict], 
        default=None, 
        silent=True):
    walker = Walker[list[item_type]].make(path, Get)
    result = walker.walk(data, default=default, silent=silent)
    return result.result


def set_by_path(path: str, data: dict | list, value: Any, silent=True):
    walker = Walker.make(path, Set)
    walker.walk(data, value, silent=silent)


def del_by_path(path: str, data: dict | list, silent=True):
    walker = Walker.make(path, Del)
    walker.walk(data, silent=silent)


@overload
def make_reb_paths(*paths: str) -> tuple[list[Walker], list[str]]: ...


@lru_cache(1000)
def make_reb_paths(*paths: str):
    from_paths = []
    to_paths = []
    for path in paths:
        pair = [p.strip() for p in path.split('->')]
        if len(pair) == 1:
            from_path = pair[0]
            to_path = pair[0].split('.')[-1]
        else:
            from_path = pair[0]
            to_path = pair[-1]
        from_paths.append(from_path)
        to_paths.append(to_path)
    return from_paths, to_paths


def rebuild(*paths: str, data: dict | list, silent=True):
    from_paths, to_paths = make_reb_paths(*paths)
    from_walkers = [Walker.make(fp, Get) for fp in from_paths]
    result = []
    for fwalker, tpath in zip(from_walkers, to_paths):
        temp = fwalker.walk(data, silent=silent)
        if len(result) < len(temp.result):
            twalker = Walker.make(tpath, Set)
            result = [twalker.template() for _ in range(len(temp.result))]
        twalkers = [
            Walker.make(
                tpath.replace('*', '{i}').format(i=idx), Set) 
                    for idx in range(len(temp.result))]
        res = result
        if len(twalkers) == 1 and not tpath.startswith('*'):
            res = res[0]
        for val, twalker in zip(temp.result, twalkers):
            twalker.walk(res, val, silent=silent)
    return result