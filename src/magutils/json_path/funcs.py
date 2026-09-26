import re
from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
from typing import Any

from .data_to_path import data_to_paths
from .intent import Del, Get, Set
from .walker import Walker

FORMAT_REGEX = re.compile(r'(?<!\{)(\{[a-z\.0-9\+\-_]+\})(?!\})')


def get_by_path(
        path: str, 
        data: dict | list, 
        item_type=type[dict], 
        default=None, 
        silent=True):
    walker: Walker[Any] = Walker[list[item_type]].make(path, Get)
    result = walker.walk(data, default=default, silent=silent)
    return result.result


def set_by_path(path: str, data: dict | list, value: Any, silent=True):
    walker: Walker[Any] = Walker.make(path, Set)
    walker.walk(data, value, silent=silent)


def del_by_path(path: str, data: dict | list, silent=True):
    walker: Walker[Any] = Walker.make(path, Del)
    walker.walk(data, silent=silent)


@lru_cache(1000)
def make_reb_paths(*paths: str) -> tuple[list[str], list[str]]:
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
    from_walkers: list[Walker[Any]] = [
        Walker.make(fp, Get) for fp in from_paths]
    result: Any = []
    for fwalker, tpath in zip(from_walkers, to_paths):
        temp = fwalker.walk(data, silent=silent)
        if len(result) < len(temp.result):
            twalker: Walker[Any] = Walker.make(tpath, Set)
            start_from_append = twalker.path[0] == '!a'
            if len(twalker.path) > 1 and not start_from_append:
                result = [twalker.template() for _ in range(len(temp.result))]
            elif start_from_append:
                result = []
            else:
                result = {}
        twalkers: list[Walker[Any]] = [
            Walker.make(
                tpath.replace('*', '{i}').format(i=idx), Set)
                    for idx in range(len(temp.result))]
        res: Any = result
        if len(twalkers) == 1 and not tpath.startswith('*')\
                and len(res) > 0 and isinstance(res, list):
            res = res[0]
        for val, twalker in zip(temp.result, twalkers):
            twalker.walk(res, val, silent=silent)
    return result


def __deepmerge(old: dict[Any, Any], new: Mapping[Any, Any]) -> dict[Any, Any]:
    for k, v in new.items():
        if isinstance(v, Mapping):
            old[k] = __deepmerge(old.get(k, {}), v)
        elif isinstance(v, (list, set)) and isinstance(old.get(k), (list, set)):
            for o, n in zip(old[k], new[k]):
                __deepmerge(o, n)
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


def to_flat(data: dict | list[dict]) -> dict[str, Any]:
    """Преобразует вложенную структуру в плоский dict: путь -> значение.

    Ключами являются пути в strict-режиме (списки получают числовые
    индексы). Пути, не дающие значений (например, от пустых списков),
    пропускаются.
    """
    paths = data_to_paths(data, 'strict')
    flat = {}
    for path in paths:
        values = get_by_path(path, data)
        if values:
            flat[path] = values[0]
    return flat


def get_diff(old: list[dict] | dict, new: list[dict] | dict):
    """Возвращает структурированный дифф между двумя структурами.

    Результат содержит три секции:
    - 'add' — пути, появившиеся в new;
    - 'del' — пути, пропавшие из old;
    - 'upd' — пути, значения которых изменились ('old'/'new').
    """
    flat_old = to_flat(old)
    flat_new = to_flat(new)
    old_paths = set(data_to_paths(old, 'strict'))
    new_paths = set(data_to_paths(new, 'strict'))
    delete = sorted(list(old_paths - new_paths))
    add = sorted(list(new_paths - old_paths))
    update = sorted(list(
        old_paths.intersection(new_paths)
        .intersection(flat_old.keys())
        .intersection(flat_new.keys())
    ))
    return {
        "add": {k: flat_new[k] for k in add if k in flat_new},
        'del': {k: flat_old[k] for k in delete if k in flat_old},
        'upd': {k: {
            'old': flat_old[k],
            'new': flat_new[k]}
            for k in update if flat_old[k] != flat_new[k]
        }
    }