from functools import lru_cache
from string import ascii_letters, digits

import nanoid


class ConfigMeta(type):
    _alphabet = ascii_letters + digits
    _size = 15

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        if value < 5:
            raise ValueError('The id size cannot be shorter than 5 characters.')
        self._size = value

    @property
    def alphabet(self):
        return self._alphabet

    @alphabet.setter
    def alphabet(self, value):
        if not value:
            raise ValueError(
                'The alphabet cannot be empty. '
                'Please provide a valid alphabet.'
            )
        if len(value) < 10:
            raise ValueError(
                'The alphabet must contain at least 10 characters. '
            )
        if len(set(value)) != len(value):
            raise ValueError(
                'Characters in the alphabet must be unique.'
            )
        self._alphabet = value


class Config(metaclass=ConfigMeta):
    pass


def gen_id():
    # 3 триллиона idшников исчерпаются примерно никогда https://zelark.github.io/nano-id-cc/
    return nanoid.generate(Config.alphabet, Config.size)


@lru_cache(maxsize=10000)
def is_valid(id):
    if len(id) < Config.size:
        raise ValueError(
            f"ID is too short, min length is {Config.size}, got {len(id)}")
    if len(id) > Config.size:
        raise ValueError(
            f"ID is too long, max length is {Config.size}, got {len(id)}"
        )
    alp = set(Config.alphabet)
    sid = set(id)
    if not sid.issubset(alp):
        raise ValueError("Invalid id")
    return True