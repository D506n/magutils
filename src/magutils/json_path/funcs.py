import re
from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
from typing import Any, overload

from .intent import Del, Get, Set
from .walker import Walker

FORMAT_REGEX = re.compile(r'(?<!\{)(\{[a-z\.0-9\+\-_]+\})(?!\})')


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
            start_from_append = twalker.path[0] == '!a'
            if len(twalker.path) > 1 and not start_from_append:
                result = [twalker.template() for _ in range(len(temp.result))]
            elif start_from_append:
                result = []
            else:
                result = {}
        twalkers = [
            Walker.make(
                tpath.replace('*', '{i}').format(i=idx), Set) 
                    for idx in range(len(temp.result))]
        res = result
        if len(twalkers) == 1 and not tpath.startswith('*')\
                and len(res) > 0 and isinstance(res, list):
            res = res[0]
        for val, twalker in zip(temp.result, twalkers):
            twalker.walk(res, val, silent=silent)
    return result


def __deepmerge(old: dict, new: dict):
    for k, v in new.items():
        if isinstance(v, Mapping):
            old[k] = __deepmerge(old.get(k, {}), v)
        else:
            old[k] = v
    return old


def deepmerge(old: dict, new: dict, copy_old: bool = True):
    if copy_old:
        result = deepcopy(old)
    else:
        result = old
    return __deepmerge(result, new)


def format(text: str, data: dict):
    keys = FORMAT_REGEX.findall(text)
    for key in keys:
        new_val = ', '.join([str(s) for s in 
            get_by_path(key[1:-1], data, default=key[1:-1])])
        text = text.replace(key, new_val)
    return text