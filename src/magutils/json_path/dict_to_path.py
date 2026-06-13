from typing import Any, Literal, Self

modes = Literal['wild', 'full', 'strict']


class Path():
    def __init__(self, key: str = None, parent: Self = None):
        self.parent = parent
        self.children: list[Self] = []
        self.key = key
        if self.parent:
            self.parent.children.append(self)

    def compile(self) -> list[str]:
        if not self.parent and not self.key and not self.children:
            return []
        if not self.children:
            return [self.key]
        result = []
        for child in self.children:
            result.extend(list(dict.fromkeys(child.compile()).keys()))
        if self.key:
            key = f'{self.key}.'
        else:
            key = ''
        return [f'{key}{ch}' for ch in result]


def __add_dict_layer(parent: Path, data: dict, mode: modes):
    for k, v in data.items():
        path = Path(k, parent)
        __add_layer(path, v, mode)


def __add_list_layer(parent: Path, data: list, mode: modes):
    if mode == 'wild' or len(data) == 0:
        path = Path('*', parent)
        if len(data) == 0:
            return
        __add_layer(path, data[0], mode)
    elif mode == 'strict':
        for i, item in enumerate(data):
            path = Path(str(i), parent)
            __add_layer(path, item, mode)
    elif mode == 'full':
        for i, item in enumerate(data):
            path = Path('*', parent)
            __add_layer(path, item, mode)
        

def __add_layer(parent: Path, data: dict | list | Any, mode: modes):
    if isinstance(data, dict):
        __add_dict_layer(parent, data, mode)
    elif isinstance(data, list):
        __add_list_layer(parent, data, mode)


def dict_to_paths(data: dict, mode: modes = 'wild'):
    result = Path()
    for k, v in data.items():
        path = Path(k, result)
        __add_layer(path, v, mode)
    return result.compile()