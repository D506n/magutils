import re
from collections import deque
from typing import Any

TEMPLATE_REGEX = re.compile(r'(?<!\{)(\{[a-z\.0-9\+\-_]+\})(?!\})')


def get_by_path(obj: dict, path: str):
    keys = path.split('.')
    temp = obj
    for key in keys:
        if isinstance(temp, dict) and key in temp.keys():
            temp = temp[key]
        elif isinstance(temp, list):
            temp = temp[int(key)]
        else:
            raise KeyError(f"Key '{key}' not found in {temp}")
    return temp


def __set_in_list(obj: list, key: str | int, value):
    if key == '!a':
        obj.append(value)
        return
    elif isinstance(key, int) and key < len(obj):
        obj[key] = value
        return
    else:
        raise KeyError(f'Key {key} not found in {obj}')


def __add_layer(obj: dict | list | Any, key: str | int, keys: list[str]):
    if isinstance(obj, dict) and key in obj.keys():
        return
    elif isinstance(obj, list) and isinstance(key, int) and key < len(obj):
        return
    if isinstance(obj, dict) and key not in obj.keys():
        if isinstance(keys[0], int) or keys[0] == '!a':
            obj[key] = []
        else:
            obj[key] = {}
    elif isinstance(obj, list) and isinstance(key, int) or key == '!a':
        if isinstance(keys[0], int) or keys[0] == '!a':
            obj.append([])
        else:
            obj.append({})


def __set_by_path(obj: dict | list | Any, keys: deque[str | int], value):
    if len(keys) == 1 and isinstance(obj, dict):
        obj[keys[0]] = value
        return
    elif len(keys) == 1 and isinstance(obj, list):
        __set_in_list(obj, keys[0], value)
        return
    key = keys.popleft()
    __add_layer(obj, key, keys)
    if key == '!a':
        key = -1
    __set_by_path(obj[key], keys, value)


def set_by_path(obj, path: str, value):
    raw_keys = path.split('.')
    keys = deque()
    for key in raw_keys:
        if key == '!a':
            keys.append(key)
            continue
        try:
            keys.append(int(key))
        except Exception:
            keys.append(key)
    
    __set_by_path(obj, keys, value)


def format(template: str, data: dict):
    keys = TEMPLATE_REGEX.findall(template)
    for key in keys:
        template = template.replace(key, str(get_by_path(data, key[1:-1])))
    return template